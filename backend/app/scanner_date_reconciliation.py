"""Conservative cohort admission; never automatically shifts dates."""
from .scanner_calendar_audit import candidate
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def reconcile_dates(rows,session_evidence,assessment_time):
    cutoff=_time(assessment_time)
    accepted=[]; quarantined=[]; seen=set()
    for row in rows:
        key=(row["symbol"],row["date"])
        if key in seen: raise ValueError("duplicate_symbol_date")
        seen.add(key)
        evidence=session_evidence.get(row["date"])
        reason=None
        if not evidence: reason="missing_session_evidence"
        else:
            _available(evidence,cutoff,"session")
            if evidence.get("date")!=row["date"] or evidence.get("traded") is not True: reason="session_not_confirmed"
            elif not row.get("basis_id") or row.get("price_basis")!="corporate_action_reviewed": reason="unreviewed_price_basis"
            elif row.get("status")!="verified" or not row.get("available_at") or not row.get("source_id"): reason="missing_row_provenance"
            else: _available(row,cutoff,"bar")
        if reason: quarantined.append(dict(symbol=key[0],date=key[1],reason=reason,candidate_weekday=candidate(key[1])))
        else: accepted.append(row)
    return dict(accepted=accepted,quarantined=quarantined,production_eligible=False)
