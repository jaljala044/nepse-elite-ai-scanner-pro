"""Read-only P4.38 ledger adapter. No caller-controlled paths or promotion."""
from datetime import date,timedelta
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
from zoneinfo import ZoneInfo
import os,json,duckdb
from .broker_context_integration import stamp
from .session_calendar import load_calendar
from .broker_rolling_profiles import build_rolling_broker_profiles,DEFAULT_WINDOWS

ROOT=Path(__file__).resolve().parents[2]
def unavailable(reason):
    return {"status":"insufficient_evidence","reason":reason,"profiles":[],"production_eligible":False,"signals_enabled":False}

def ledger_profiles(*,as_of_date,decision_time,window):
    if window not in DEFAULT_WINDOWS: raise ValueError("unsupported window")
    day=date.fromisoformat(as_of_date)
    cutoff=stamp(decision_time)
    if day>cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date(): raise ValueError("future session")
    configured=os.environ.get("NEPSE_BROKER_LEDGER_PATH")
    if not configured or not Path(configured).is_file(): return unavailable("ledger_not_configured")
    cal=load_calendar(ROOT/"data/reference/nepse_session_calendar.csv")
    expected=[]
    cursor=day
    while len(expected)<DEFAULT_WINDOWS[window]:
        if (day-cursor).days>3660: return unavailable("calendar_window_limit")
        row=cal.get(cursor)
        if not row or row["scope"]!="market_wide" or stamp(row["verified_at_utc"])>cutoff:
            return unavailable("trusted_calendar_incomplete")
        if row["status"] in {"verified_open","verified_exceptional_open"}: expected.append(cursor.isoformat())
        cursor-=timedelta(days=1)
    expected.reverse()
    con=duckdb.connect(configured,read_only=True)
    try:
        manifests=con.execute("""SELECT CAST(session_date AS VARCHAR),manifest_json,manifest_sha256
          FROM broker_daily_session_manifests WHERE session_date BETWEEN ? AND ? AND available_at<=?
          ORDER BY session_date""",[expected[0],expected[-1],cutoff]).fetchall()
        observations=con.execute("""SELECT security_id,broker_id,CAST(session_date AS VARCHAR),side,
          CAST(amount AS VARCHAR),CAST(quantity AS VARCHAR),source_id,evidence_id,source_payload_sha256,
          CAST(coverage_ratio AS VARCHAR),CAST(available_at AS VARCHAR),status,batch_id,payload_json
          FROM broker_daily_observations WHERE session_date BETWEEN ? AND ? AND available_at<=?
          ORDER BY session_date,security_id,broker_id,side,source_id,evidence_id""",[expected[0],expected[-1],cutoff]).fetchall()
    finally: con.close()
    valid={}
    for d,raw,digest in manifests:
        if sha256(raw.encode()).hexdigest()!=digest: return unavailable("manifest_hash_mismatch")
        m=json.loads(raw)
        if d not in expected or m["session_date"]!=d or stamp(m["available_at"])>cutoff: return unavailable("manifest_scope_mismatch")
        if (m["source_coverage_status"]=="complete" and m["identity_coverage_status"]=="complete"
            and m["source_control_reconciled"] is True and m["verified_session"] is True
            and Decimal(m["source_coverage_ratio"])==1 and Decimal(m["identity_coverage_min"])==1):
            valid[d]=m["batch_id"]
    if set(valid)!=set(expected): return unavailable("complete_session_manifest_missing")
    keys=("security_id","broker_id","session_date","side","amount","quantity","source_id","evidence_id","source_payload_sha256","coverage_ratio","available_at","status","batch_id","payload_json")
    rows=[]
    for item in observations:
        r=dict(zip(keys,item)); payload=json.loads(r.pop("payload_json"))
        if r["session_date"] not in valid or r["batch_id"]!=valid[r["session_date"]]: return unavailable("observation_manifest_mismatch")
        if Decimal(r["coverage_ratio"])!=1: return unavailable("observation_coverage_incomplete")
        rows.append(r)
    if {r["session_date"] for r in rows}!=set(expected): return unavailable("missing_ledger_observations")
    result=build_rolling_broker_profiles(rows,verified_exchange_sessions=expected,complete_source_sessions=expected,as_of_date=as_of_date,as_of_timestamp=decision_time,windows={window:DEFAULT_WINDOWS[window]},min_coverage=Decimal(1))
    # No stock-price or historical identity clearance here: do not expose
    # per-security profiles until the P4.43 registry and identity joins are applied.
    return {"status":"descriptive_only","window":window,"expected_sessions":expected,
        "complete_sessions":len(expected),"observation_count":len(rows),
        "profile_count":len(result["profiles"]),"profiles":[],"production_eligible":False,"signals_enabled":False,
        "reason":"security_profiles_withheld_pending_identity_quarantine_join",
        "manifest_hashes":{d:h for d,raw,h in manifests},
        "source_authentication_performed":False}
