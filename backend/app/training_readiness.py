"""Fail-closed real-data readiness gate before any model training."""
from __future__ import annotations


REQUIRED_GATES = (
    "universe_verified", "session_calendar_verified", "source_rights_cleared",
    "source_lineage_complete", "ohlcv_integrity_passed", "broker_identity_policy_passed",
    "point_in_time_leakage_checks_passed", "corporate_action_policy_reviewed",
    "historical_coverage_threshold_met", "holdout_protocol_defined",
)


def evaluate_training_readiness(evidence: dict, *,
                                minimum_ohlcv_coverage: float = 0.98,
                                minimum_broker_identity_coverage: float = 0.95) -> dict:
    """Require explicit evidence for every gate; missing fields are failures."""
    if not 0 <= minimum_ohlcv_coverage <= 1 or not 0 <= minimum_broker_identity_coverage <= 1:
        raise ValueError("coverage thresholds must be between zero and one")
    checks = {}
    for key in REQUIRED_GATES:
        checks[key] = evidence.get(key) is True
    ohlcv = evidence.get("ohlcv_coverage")
    broker = evidence.get("broker_identity_coverage")
    try:
        checks["ohlcv_coverage_threshold"] = ohlcv is not None and float(ohlcv) >= minimum_ohlcv_coverage
        checks["broker_identity_coverage_threshold"] = broker is not None and float(broker) >= minimum_broker_identity_coverage
    except (TypeError, ValueError):
        checks["ohlcv_coverage_threshold"] = False
        checks["broker_identity_coverage_threshold"] = False
    blockers = [key for key, passed in checks.items() if not passed]
    return {
        "training_ready": not blockers,
        "model_training_allowed": not blockers,
        "checks": checks,
        "blockers": blockers,
        "thresholds": {
            "minimum_ohlcv_coverage": minimum_ohlcv_coverage,
            "minimum_broker_identity_coverage": minimum_broker_identity_coverage,
        },
        "evidence_snapshot_id": evidence.get("evidence_snapshot_id"),
        "policy": "fail_closed_missing_or_false_evidence_blocks_training",
        "model_performance_claimed": False,
    }
