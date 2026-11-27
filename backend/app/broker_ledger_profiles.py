"""Read-only P4.38 ledger adapter. No caller-controlled paths or promotion."""
from datetime import date,timedelta
from pathlib import Path
from hashlib import sha256
from decimal import Decimal
from zoneinfo import ZoneInfo
import os,json,csv,duckdb
from .broker_context_integration import stamp
from .broker_lifecycle_gate import load_lifecycle,lifecycle_reason
from .session_calendar import load_calendar
from .broker_rolling_profiles import build_rolling_broker_profiles,DEFAULT_WINDOWS

ROOT=Path(__file__).resolve().parents[2]
def unavailable(reason):
    return {"status":"insufficient_evidence","reason":reason,"profiles":[],"production_eligible":False,"signals_enabled":False}

def quarantine_category(security_id,mapping,quarantine,start,end):
    symbols=mapping.get(security_id,set())
    if len(symbols)!=1: return "identity_unmapped"
    if any(s in symbols and start<=d<=end for s,d in quarantine): return "quarantine_blocked"
    return "snapshot_crosswalk_clear"

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
          CAST(coverage_ratio AS VARCHAR),CAST(available_at AS VARCHAR),status,batch_id,payload_json,natural_key,observation_id,source_row_count
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
    keys=("security_id","broker_id","session_date","side","amount","quantity","source_id","evidence_id","source_payload_sha256","coverage_ratio","available_at","status","batch_id","payload_json","natural_key","observation_id","source_row_count")
    rows=[]
    for item in observations:
        r=dict(zip(keys,item)); payload=json.loads(r.pop("payload_json"))
        key=[r[k] for k in ("security_id","broker_id","session_date","side","source_id","evidence_id")]
        canonical=json.dumps(key,separators=(",",":"),ensure_ascii=False)
        if (payload["natural_key"]!=key or r["natural_key"]!=canonical
            or sha256(canonical.encode()).hexdigest()!=r["observation_id"]
            or any(Decimal(payload[k])!=Decimal(r[k]) for k in ("amount","quantity","coverage_ratio"))
            or any(payload[k]!=r[k] for k in ("batch_id","status","source_payload_sha256","source_row_count"))
            or stamp(payload["available_at"])!=stamp(r["available_at"])):
            return unavailable("observation_payload_mismatch")
        if r["session_date"] not in valid or r["batch_id"]!=valid[r["session_date"]]: return unavailable("observation_manifest_mismatch")
        if Decimal(r["coverage_ratio"])!=1: return unavailable("observation_coverage_incomplete")
        rows.append(r)
    if {r["session_date"] for r in rows}!=set(expected): return unavailable("missing_ledger_observations")
    result=build_rolling_broker_profiles(rows,verified_exchange_sessions=expected,complete_source_sessions=expected,as_of_date=as_of_date,as_of_timestamp=decision_time,windows={window:DEFAULT_WINDOWS[window]},min_coverage=Decimal(1))
    with (ROOT/"data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv").open(newline="",encoding="utf-8-sig") as f:
        mapping={}
        for r in csv.DictReader(f):
            mapping.setdefault(r["security_id"],set()).add(r["symbol"].strip().upper())
    registry=json.loads((ROOT/"data/reference/p443_equity_quarantine.json").read_text())
    q={(r["symbol"],date.fromisoformat(r["date"]).isoformat()) for r in registry["records"]}
    if registry["schema_version"]!=1 or len(q)!=1329 or len(registry["records"])!=1329:
        return unavailable("invalid_quarantine_registry")
    blocked=unknown=clear=0
    lifecycle=load_lifecycle()
    lifecycle_counts={}
    for p in result["profiles"]:
        category=quarantine_category(p["security_id"],mapping,q,expected[0],expected[-1])
        if category=="identity_unmapped": unknown+=1
        elif category=="quarantine_blocked": blocked+=1
        else:
            clear+=1
            reason=lifecycle_reason(p['security_id'],next(iter(mapping[p['security_id']])),expected[0],expected[-1],lifecycle)
            lifecycle_counts[reason]=lifecycle_counts.get(reason,0)+1
    # Snapshot identity is only a conservative exclusion aid, not historical certification.
    # No stock-price or historical identity clearance here: do not expose
    # per-security profiles until the P4.43 registry and identity joins are applied.
    return {"status":"descriptive_only","window":window,"expected_sessions":expected,
        "complete_sessions":len(expected),"observation_count":len(rows),
        "profile_count":len(result["profiles"]),"lifecycle_exclusion_counts":lifecycle_counts,
        "quarantine_blocked_profiles":blocked,"identity_unmapped_profiles":unknown,"snapshot_crosswalk_clear_profiles":clear,"profiles":[],"production_eligible":False,"signals_enabled":False,
        "reason":"security_profiles_withheld_pending_identity_quarantine_join",
        "manifest_hashes":{d:h for d,raw,h in manifests},
        "source_authentication_performed":False}
