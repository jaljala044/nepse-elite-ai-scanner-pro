"""Historical NEPSE dataset coverage and readiness assessment.

Consumes captured intake reports only. A READY result permits research-panel assembly;
it does not authenticate publishers, certify all securities, or permit production use.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

REQUIRED = ("ohlcv", "session_calendar", "instrument_universe", "corporate_actions")
OPTIONAL = ("floorsheet", "broker_summary", "sector_membership", "sector_index", "fundamentals")
ALL = REQUIRED + OPTIONAL
DATE_FIELDS = {"ohlcv":"session_date","session_calendar":"session_date","floorsheet":"session_date",
    "broker_summary":"session_date","sector_index":"session_date","instrument_universe":"effective_from",
    "sector_membership":"effective_from","corporate_actions":"announcement_date","fundamentals":"period_end"}
OPEN = {"OPEN","TRADING","OPEN_FOR_TRADING"}
ACTIVE = {"ACTIVE","LISTED","TRADING"}

def _date(value):
    try: return date.fromisoformat(str(value))
    except (TypeError, ValueError): return None

def _time(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _reports(value):
    if value is None: return []
    return value if isinstance(value,list) else [value]

def _rows(report):
    if not isinstance(report,dict) or report.get("status")!="validated_for_research":
        return []
    validation=report.get("validation")
    return validation.get("accepted_rows",[]) if isinstance(validation,dict) else report.get("accepted_rows",[])

def assess_historical_dataset_readiness(*, intake_reports, start_date, end_date, decision_cutoff,
        minimum_session_coverage_pct="100", require_optional=()):
    """Inventory, measure coverage and fail closed on critical gaps or duplicate OHLCV."""
    start,end=_date(start_date),_date(end_date)
    cutoff=_time(decision_cutoff)
    if start is None or end is None or start>end: raise ValueError("invalid_date_range")
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(intake_reports,dict): raise ValueError("intake_reports_required")
    minimum=Decimal(str(minimum_session_coverage_pct))
    if not minimum.is_finite() or not (0<minimum<=100): raise ValueError("minimum_session_coverage_invalid")
    if not isinstance(require_optional,(list,tuple,set)) or set(require_optional)-set(OPTIONAL):
        raise ValueError("required_optional_dataset_invalid")
    errors=[]; inventory={}; normalized={}
    unknown=sorted(set(intake_reports)-set(ALL))
    errors.extend("unsupported_dataset:"+x for x in unknown)
    for kind in ALL:
        source_reports=_reports(intake_reports.get(kind))
        valid=[]; source_ids=set(); publishers=set(); row_total=0; late=0
        for report in source_reports:
            if not isinstance(report,dict) or report.get("dataset_kind")!=kind:
                errors.append("invalid_report:"+kind); continue
            env=report.get("source_envelope",{})
            available=_time(env.get("available_at")) if isinstance(env,dict) else None
            if available is None or available>cutoff:
                late+=1; errors.append("not_point_in_time:"+kind)
                continue
            rows=_rows(report)
            if report.get("status")!="validated_for_research" or not rows:
                errors.append("report_not_validated_or_empty:"+kind); continue
            source_ids.add(str(env.get("source_id","")))
            publishers.add(str(env.get("publisher","")))
            row_total+=len(rows)
            valid.append((report,rows))
        normalized[kind]=valid
        required=kind in REQUIRED or kind in require_optional
        if not valid and required: errors.append("required_dataset_unavailable:"+kind)
        inventory[kind]={"report_count":len(source_reports),"validated_report_count":len(valid),
            "source_count":len(source_ids-{""}),"publisher_count":len(publishers-{""}),
            "accepted_row_count":row_total,"late_report_count":late,
            "availability":"available" if valid else ("missing_optional" if not required else "missing_required")}

    calendar_rows=[r for _,rows in normalized["session_calendar"] for r in rows]
    session_counts=Counter(str(r.get("session_date")) for r in calendar_rows if str(r.get("session_status","")).upper() in OPEN)
    duplicate_sessions=sorted(d for d,n in session_counts.items() if n>1)
    sessions=sorted(d for d,n in session_counts.items() if n==1 and start.isoformat()<=d<=end.isoformat() and _date(d))
    if duplicate_sessions: errors.append("duplicate_calendar_sessions")
    if not sessions: errors.append("no_valid_open_sessions_in_range")

    ohlcv_rows=[r for _,rows in normalized["ohlcv"] for r in rows]
    bar_counts=Counter((str(r.get("security_id","")).strip(),str(r.get("session_date",""))) for r in ohlcv_rows
        if start.isoformat()<=str(r.get("session_date",""))<=end.isoformat())
    duplicate_bars=sorted([{"security_id":s,"session_date":d,"count":n} for (s,d),n in bar_counts.items() if n>1],
        key=lambda x:(x["security_id"],x["session_date"]))
    if duplicate_bars: errors.append("duplicate_ohlcv_security_sessions")

    universe_rows=[r for _,rows in normalized["instrument_universe"] for r in rows]
    active_at_start={}
    for row in universe_rows:
        symbol=str(row.get("symbol","")).strip().upper()
        sid=str(row.get("security_id","")).strip().upper()
        effective=_date(row.get("effective_from"))
        status=str(row.get("listing_status","")).upper()
        if symbol and sid and effective and effective<=start and status in ACTIVE:
            active_at_start.setdefault(sid,symbol)
    expected=len(sessions)*len(active_at_start)
    observed=len({(sid,d) for (sid,d),n in bar_counts.items() if sid in active_at_start and d in set(sessions) and n==1})
    coverage=(Decimal(observed)/expected*100) if expected else Decimal("0")
    per_security=[]
    session_set=set(sessions)
    for sid,symbol in sorted(active_at_start.items()):
        actual={d for (security,d),n in bar_counts.items() if security==sid and n==1}
        missing=sorted(session_set-actual)
        per_security.append({"security_id":sid,"symbol":symbol,"expected_sessions":len(sessions),
            "observed_sessions":len(actual & session_set),"missing_sessions":missing,
            "coverage_pct":str(Decimal(len(actual & session_set))/len(sessions)*100) if sessions else "0",
            "status":"complete" if not missing else "incomplete"})
    if not active_at_start: errors.append("no_historical_universe_members_at_sample_start")
    if expected and coverage<minimum: errors.append("ohlcv_session_coverage_below_threshold")
    if any(x["status"]!="complete" for x in per_security): errors.append("incomplete_security_history")
    # Validate OHLCV sanity independently, even if source adapter already checked it.
    invalid_bars=[]
    for row in ohlcv_rows:
        try:
            o,h,l,c,v,t=[Decimal(str(row[k])) for k in ("open","high","low","close","volume","turnover")]
            if any(not x.is_finite() for x in (o,h,l,c,v,t)) or min(o,h,l,c)<=0 or v<0 or t<0 or h<max(o,c,l) or l>min(o,c,h):
                raise ValueError()
        except (KeyError,InvalidOperation,TypeError,ValueError):
            invalid_bars.append({"security_id":row.get("security_id"),"session_date":row.get("session_date")})
    if invalid_bars: errors.append("ohlcv_price_volume_anomalies")
    # Corporate action reconciliation is a distinct mandatory gate; never assume that a
    # single accepted feed or a clean schema means adjusted prices are ready.
    ca_rows=[r for _,rows in normalized["corporate_actions"] for r in rows]
    ca_report_count=len(normalized["corporate_actions"])
    if not ca_report_count: errors.append("corporate_action_source_missing")
    quality="LOW" if errors else ("MEDIUM" if any(inventory[k]["availability"]=="missing_optional" for k in OPTIONAL) else "HIGH")
    status="BLOCKED" if errors else ("PARTIAL" if quality=="MEDIUM" else "READY")
    return {"schema_version":"nepse-historical-readiness-1.0.0","status":status,
        "data_quality":quality,"research_panel_assembly_allowed":status=="READY",
        "start_date":start.isoformat(),"end_date":end.isoformat(),"decision_cutoff":cutoff.isoformat(),
        "open_session_count":len(sessions),"open_session_dates":sessions,
        "historical_universe_symbol_count":len(active_at_start),"expected_ohlcv_rows":expected,
        "observed_unique_ohlcv_rows":observed,"ohlcv_session_coverage_pct":str(coverage),
        "minimum_session_coverage_pct":str(minimum),"per_security_coverage":per_security,
        "duplicate_calendar_sessions":duplicate_sessions,"duplicate_ohlcv_records":duplicate_bars,
        "invalid_ohlcv_records":invalid_bars,"inventory":inventory,"errors":sorted(set(errors)),
        "corporate_action_rows_for_reconciliation":len(ca_rows),
        "limitations":["Coverage is measured only for securities explicitly active at sample start; this does not prove delisted-security completeness or eliminate survivorship bias.",
            "A single dataset report can contain many rows but is not independent corroboration.",
            "Corporate actions must pass the separate cross-source reconciliation and adjustment gate.",
            "No publisher authenticity, source licensing, live retrieval or production readiness is certified.",
            "A READY result means only that configured research-panel admission checks passed."],
        "live_data_acquired":False,"performance_claimed":False,"production_enabled":False}
