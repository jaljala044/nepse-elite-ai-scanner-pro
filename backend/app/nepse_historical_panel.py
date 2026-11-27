"""Build a survivorship-aware, point-in-time NEPSE historical panel from admitted datasets.

This module consumes records already admitted by nepse_official_adapters. It does
not download data, adjust prices, or claim that source publishers are authentic.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from app.nepse_historical_universe import build_effective_universe
from app.nepse_corporate_action_reconciliation import apply_reconciled_adjustments

REQUIRED_KINDS = ("ohlcv", "session_calendar", "instrument_universe", "corporate_actions")

def _day(v):
    try: return date.fromisoformat(str(v))
    except (TypeError, ValueError): return None

def _time(v):
    if not isinstance(v, str): return None
    try: x = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError: return None
    if x.tzinfo is None or x.utcoffset() is None: return None
    return x.astimezone(timezone.utc)

def _num(v):
    try: x = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError): return None
    return x if x.is_finite() else None

def assemble_historical_panel(*, datasets, start_date, end_date, decision_cutoff,
                              require_corporate_action_clearance=True, readiness_report=None, corporate_action_reconciliation=None, allow_partial_readiness=True):
    """Assemble a common-session panel; exclude symbols with gaps or unresolved actions."""
    start, end, cutoff = _day(start_date), _day(end_date), _time(decision_cutoff)
    if start is None or end is None or start > end: raise ValueError("invalid_date_range")
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(datasets, dict): raise ValueError("datasets_required")
    if not isinstance(readiness_report, dict) or readiness_report.get("status") not in ({"READY","PARTIAL"} if allow_partial_readiness else {"READY"}):
        return {"status":"blocked","errors":["historical_readiness_gate_missing_or_blocked"],"panel":[],"eligible_symbols":[],"excluded_symbols":{},"session_dates":[],"data_quality":"LOW","performance_claimed":False,"production_enabled":False}
    missing = [k for k in REQUIRED_KINDS if k not in datasets]
    if missing: raise ValueError("required_datasets_missing:"+",".join(missing))
    reports = {}
    errors = []
    for kind in REQUIRED_KINDS:
        report = datasets.get(kind)
        if not isinstance(report, dict): errors.append("dataset_report_invalid:"+kind); continue
        if report.get("status") != "validated_for_research" or report.get("research_review_allowed") is not True:
            errors.append("dataset_not_fully_validated:"+kind)
        available = _time(report.get("available_at"))
        if available is None or available > cutoff: errors.append("dataset_not_available_by_cutoff:"+kind)
        if not isinstance(report.get("accepted_rows"), list) or not report["accepted_rows"]:
            errors.append("dataset_rows_missing:"+kind)
        reports[kind] = report
    if errors:
        return {"status":"blocked","errors":errors,"panel":[],"eligible_symbols":[],
            "excluded_symbols":{},"session_dates":[],"data_quality":"LOW",
            "performance_claimed":False,"production_enabled":False}

    calendar = {}
    for row in reports["session_calendar"]["accepted_rows"]:
        d = _day(row.get("session_date"))
        if d and start <= d <= end:
            if d in calendar: errors.append("duplicate_calendar_session:"+d.isoformat())
            calendar[d] = row.get("session_status")
    sessions = sorted(d.isoformat() for d,s in calendar.items() if str(s).upper() in {"OPEN","TRADING","OPEN_FOR_TRADING"})
    if len(sessions) < 2: errors.append("insufficient_open_sessions")
    session_set = set(sessions)

    universe_result = build_effective_universe(universe_rows=reports["instrument_universe"]["accepted_rows"], session_dates=sessions)
    errors.extend(universe_result["errors"])
    security_to_symbol = {sid: names[-1] for sid,names in universe_result["symbols_by_security"].items()}
    active_by_session = universe_result["active_by_session"]
    symbols_by_security = universe_result["symbols_by_security"]
    bars_by_security = {}
    for row in reports["ohlcv"]["accepted_rows"]:
        security_id = str(row.get("security_id","")).strip().upper()
        d = _day(row.get("session_date"))
        if not security_id or d is None or not (start <= d <= end): continue
        if d.isoformat() not in session_set:
            errors.append("ohlcv_on_non_trading_session:"+security_id+":"+d.isoformat()); continue
        symbol = str(row.get("symbol") or security_to_symbol.get(security_id) or "").strip().upper()
        if symbol: bars_by_security.setdefault(security_id, []).append({**row,"symbol":symbol})
    actions = {}
    for row in reports["corporate_actions"]["accepted_rows"]:
        symbol = str(row.get("symbol") or security_to_symbol.get(str(row.get("security_id","")).strip().upper()) or "").strip().upper()
        effective = _day(row.get("effective_date"))
        if symbol and effective and start <= effective <= end and str(row.get("status","")).lower() not in {"cancelled","rejected","withdrawn"}:
            actions.setdefault(symbol, []).append(row)

    panel, eligible, excluded = [], [], {}
    for security_id in sorted(set(bars_by_security) | set(universe_result["security_ids"])):
        symbol = security_to_symbol.get(security_id) or (symbols_by_security.get(security_id) or [security_id])[-1]
        bars = bars_by_security.get(security_id, [])
        reasons = []
        bars.sort(key=lambda r: _day(r.get("session_date")) or date.max)
        if len({_day(r.get("session_date")) for r in bars}) != len(bars): reasons.append("duplicate_security_session")
        by_date = {_day(r.get("session_date")).isoformat():r for r in bars if _day(r.get("session_date"))}
        expected_dates = sorted(d for d, members in active_by_session.items() if security_id in members)
        if not expected_dates: 
            if bars: reasons.append("bars_outside_effective_listing_status")
            else: continue
        missing_dates = sorted(set(expected_dates) - set(by_date))
        if missing_dates: reasons.append("incomplete_session_history:"+str(len(missing_dates)))
        unexpected = sorted(set(by_date) - set(expected_dates))
        if unexpected: reasons.append("bars_when_not_listed_or_suspended")
        action_rows = actions.get(symbol, [])
        if action_rows:
            reconciled = (corporate_action_reconciliation or {}).get("reconciled_events", [])
            action_keys = {(str(x.get("security_id")),str(x.get("action_type")).lower(),str(x.get("announcement_date")),str(x.get("effective_date"))) for x in reconciled if isinstance(x,dict)}
            for action in action_rows:
                key=(security_id,str(action.get("action_type","")).lower(),str(action.get("announcement_date")),str(action.get("effective_date")))
                if key not in action_keys: reasons.append("corporate_action_unreconciled:"+key[1])
            if require_corporate_action_clearance and not isinstance(corporate_action_reconciliation,dict):
                reasons.append("corporate_action_reconciliation_required")
            if not reasons and reconciled:
                adjusted=apply_reconciled_adjustments(bars=bars,reconciled_events=[x for x in reconciled if str(x.get("security_id"))==security_id],decision_cutoff=cutoff.isoformat())
                bars=adjusted["bars"]
        if reasons:
            excluded[symbol] = sorted(set(reasons)); continue
        for row in bars:
            values = {k:_num(row.get(k)) for k in ("open","high","low","close","volume","turnover")}
            if any(v is None for v in values.values()):
                excluded[symbol] = ["ohlcv_numeric_validation_failed"]; break
            panel.append({"symbol":symbol,"security_id":security_id,"session_date":row["session_date"],**{k:str(v) for k,v in values.items()},
                "source_id":reports["ohlcv"].get("source_id"),"evidence_id":reports["ohlcv"].get("evidence_id"),
                "available_at":reports["ohlcv"].get("available_at"),
                "adjustment_status":row.get("adjustment_status","unadjusted_no_pre_event_factor")})
        if security_id not in excluded: eligible.append(symbol)
    panel.sort(key=lambda r:(r["session_date"],r["symbol"]))
    quality = "HIGH" if eligible and not excluded and not errors else ("MEDIUM" if eligible else "LOW")
    return {"schema_version":"nepse-historical-panel-1.0.0",
        "status":"validated_for_research" if eligible and not errors else "blocked_or_partial",
        "start_date":start.isoformat(),"end_date":end.isoformat(),"decision_cutoff":cutoff.isoformat(),
        "session_dates":sessions,"session_count":len(sessions),"eligible_symbols":eligible,
        "excluded_symbols":excluded,"panel":panel,"panel_rows":len(panel),"errors":errors,
        "data_quality":quality,"corporate_actions_checked":True,"readiness_status":readiness_report.get("status"),"readiness_data_quality":readiness_report.get("data_quality"),"strategy_eligibility":readiness_report.get("strategy_eligibility",{}),"historical_universe_security_count":len(universe_result["security_ids"]),"inactive_universe_events":universe_result["inactive_history"],
        "corporate_action_policy":"exclude affected securities until independently reconciled and consistently adjusted",
        "survivorship_policy":"uses effective-dated permanent security IDs; later IPOs enter from listing date and delisted/suspended securities remain in the historical inventory",
        "common_universe_policy":"only complete symbol histories on the common open-session calendar are admitted",
        "limitations":["No publisher authentication or live retrieval is performed.",
            "The caller must supply fully validated source reports and trustworthy symbol/security-ID mapping.",
            "Corporate-action-adjusted OHLCV is not calculated; affected symbols are excluded.",
            "Historical universe coverage depends on the completeness of the supplied effective-dated universe."],
        "performance_claimed":False,"production_enabled":False}
