"""Multi-horizon IDPAT research validation; never a trading recommendation."""
from __future__ import annotations
from copy import deepcopy
from app.idpat_scanner_integration import build_idpat_scanner_bundle

HORIZON_REQUIREMENTS = {
    "t_plus_2": {"minimum_bars": 21, "description": "3-5 trading-day research window"},
    "swing": {"minimum_bars": 40, "description": "1-4 week research window"},
    "positional": {"minimum_bars": 60, "description": "1-6 month research window"},
    "investment": {"minimum_bars": 120, "description": "6-24 month research window"},
}

def validate_idpat_horizons(*, snapshot, as_of_date, as_of_timestamp, history_validation,
    session_calendar=None, trusted_gate_evidence=None, methodology_version="idpat-15.0.0"):
    """Run partial IDPAT engines on trailing slices after the history gate passes."""
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot_required")
    evidence = snapshot.get("price_volume")
    bars = evidence.get("bars") if isinstance(evidence, dict) else None
    if not isinstance(bars, list):
        bars = []
    history_ok = (isinstance(history_validation, dict)
        and history_validation.get("research_review_allowed") is True
        and history_validation.get("production_promotion_allowed") is False)
    results = {}
    for horizon, req in HORIZON_REQUIREMENTS.items():
        minimum = req["minimum_bars"]
        if not history_ok:
            results[horizon] = {"status": "withheld", "action": "NO_TRADE",
                "reason": "120_session_history_gate_not_passed", "available_bars": len(bars),
                "required_bars": minimum, "overall_score": None, "probability": None}
            continue
        if len(bars) < minimum:
            results[horizon] = {"status": "withheld", "action": "NO_TRADE",
                "reason": "horizon_history_below_minimum", "available_bars": len(bars),
                "required_bars": minimum, "overall_score": None, "probability": None}
            continue
        sliced = deepcopy(snapshot)
        sliced["price_volume"]["bars"] = bars[-minimum:]
        bundle = build_idpat_scanner_bundle(snapshot=sliced, as_of_date=as_of_date,
            as_of_timestamp=as_of_timestamp, session_calendar=session_calendar,
            gate_evidence=trusted_gate_evidence, risk_inputs=None,
            methodology_version=methodology_version)
        record = bundle.get("record", {})
        results[horizon] = {"status": "research_components_evaluated" if record else "withheld",
            "bundle_status": bundle.get("status"), "signal_id": bundle.get("signal_id"),
            "action": "NO_TRADE", "available_bars": minimum, "required_bars": minimum,
            "overall_score": None, "probability": None,
            "blocked_gates": record.get("blocked_gates", []), "engines": record.get("engines", {}),
            "risk_plan": record.get("risk_plan")}
    complete = all(x.get("status") == "research_components_evaluated" for x in results.values())
    return {"status": "all_horizons_research_validated" if complete else "horizon_validation_partial_or_blocked",
        "symbol": snapshot.get("symbol"), "decision_date": as_of_date,
        "methodology_version": methodology_version, "horizons": results, "action": "NO_TRADE",
        "overall_score": None, "probability": None, "production_recommendations_enabled": False,
        "production_promotion_allowed": False,
        "limitations": [
            "History-length thresholds are minimum data requirements, not calibrated forecast horizons.",
            "Existing IDPAT engines remain partial; Wyckoff, Minervini, RS, VSA, broker and sector engines are not newly scored here.",
            "HTTP clients cannot attest gates; production wiring requires trusted server-side source adapters.",
            "No BUY/SELL, probability, backtest, live fetch, fill or order is produced."]}
