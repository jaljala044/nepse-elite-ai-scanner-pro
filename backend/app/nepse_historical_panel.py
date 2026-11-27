"""Build a survivorship-aware, point-in-time NEPSE historical panel from admitted datasets.

This module consumes records already admitted by nepse_official_adapters. It does
not download data, adjust prices, or claim that source publishers are authentic.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

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
                              require_corporate_action_clearance=True):
    """Assemble a common-session panel; exclude symbols with gaps or unresolved actions."""
    start, end, cutoff = _day(start_date), _day(end_date), _time(decision_cutoff)
    if start is None or end is None or start > end: raise ValueError("invalid_date_range")
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(datasets, dict): raise ValueError("datasets_required")
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

    universe = {}
    for row in reports["instrument_universe"]["accepted_rows"]:
        symbol = str(row.get("symbol","")).strip().upper()
        effective = _day(row.get("effective_from"))
        if not symbol or effective is None: continue
        universe.setdefault(symbol, []).append((effective, str(row.get("listing_status","")).upper(), row))
    bars_by_symbol = {}
    for row in reports["ohlcv"]["accepted_rows"]:
        symbol = str(row.get("symbol") or row.get("security_id") or "").strip().upper()
        d = _day(row.get("session_date"))
        if not symbol or d is None or not (start <= d <= end): continue
        if d.isoformat() not in session_set:
            errors.append("ohlcv_on_non_trading_session:"+symbol+":"+d.isoformat()); continue
        bars_by_symbol.setdefault(symbol, []).append(row)
    actions = {}
    for row in reports["corporate_actions"]["accepted_rows"]:
        symbol = str(row.get("symbol") or row.get("security_id") or "").strip().upper()
        effective = _day(row.get("effective_date"))
        if symbol and effective and start <= effective <= end and str(row.get("status","")).lower() not in {"cancelled","rejected","withdrawn"}:
            actions.setdefault(symbol, []).append(row)

    panel, eligible, excluded = [], [], {}
    for symbol, bars in sorted(bars_by_symbol.items()):
        reasons = []
        bars.sort(key=lambda r: _day(r.get("session_date")) or date.max)
        if len({_day(r.get("session_date")) for r in bars}) != len(bars): reasons.append("duplicate_symbol_session")
        dates = {_day(r.get("session_date")).isoformat() for r in bars if _day(r.get("session_date"))}
        missing_dates = sorted(session_set - dates)
        if missing_dates: reasons.append("incomplete_session_history:"+str(len(missing_dates)))
        listings = sorted(universe.get(symbol, []), key=lambda x:x[0])
        if not listings: reasons.append("instrument_universe_membership_missing")
        elif not any(status in {"ACTIVE","LISTED","TRADING"} and effective <= start for effective,status,_ in listings):
            # A security listed during the requested interval is not eligible for the full-period comparison.
            reasons.append("not_listed_at_start_of_sample")
        for action in actions.get(symbol, []):
            kind = str(action.get("action_type","")).lower()
            if kind in {"bonus","rights","split","merger","other"}:
                reasons.append("corporate_action_adjustment_unresolved:"+kind)
            elif kind == "delisting": reasons.append("delisting_during_sample")
        if require_corporate_action_clearance and actions.get(symbol):
            # Even dividend/other actions require an explicit adjustment/reconciliation ledger before admitting adjusted returns.
            reasons.append("corporate_action_reconciliation_required")
        if reasons:
            excluded[symbol] = sorted(set(reasons)); continue
        for row in bars:
            values = {k:_num(row.get(k)) for k in ("open","high","low","close","volume","turnover")}
            if any(v is None for v in values.values()):
                excluded[symbol] = ["ohlcv_numeric_validation_failed"]; break
            panel.append({"symbol":symbol,"session_date":row["session_date"],**{k:str(v) for k,v in values.items()},
                "source_id":reports["ohlcv"].get("source_id"),"evidence_id":reports["ohlcv"].get("evidence_id"),
                "available_at":reports["ohlcv"].get("available_at")})
        if symbol not in excluded: eligible.append(symbol)
    panel.sort(key=lambda r:(r["session_date"],r["symbol"]))
    quality = "HIGH" if eligible and not excluded and not errors else ("MEDIUM" if eligible else "LOW")
    return {"schema_version":"nepse-historical-panel-1.0.0",
        "status":"validated_for_research" if eligible and not errors else "blocked_or_partial",
        "start_date":start.isoformat(),"end_date":end.isoformat(),"decision_cutoff":cutoff.isoformat(),
        "session_dates":sessions,"session_count":len(sessions),"eligible_symbols":eligible,
        "excluded_symbols":excluded,"panel":panel,"panel_rows":len(panel),"errors":errors,
        "data_quality":quality,"corporate_actions_checked":True,
        "corporate_action_policy":"exclude affected securities until independently reconciled and consistently adjusted",
        "survivorship_policy":"requires historical instrument-universe membership and excludes securities not listed at sample start",
        "common_universe_policy":"only complete symbol histories on the common open-session calendar are admitted",
        "limitations":["No publisher authentication or live retrieval is performed.",
            "The caller must supply fully validated source reports and trustworthy symbol/security-ID mapping.",
            "Corporate-action-adjusted OHLCV is not calculated; affected symbols are excluded.",
            "Historical universe coverage depends on the completeness of the supplied effective-dated universe."],
        "performance_claimed":False,"production_enabled":False}
