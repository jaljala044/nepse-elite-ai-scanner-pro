"""Explicit human-approved research replay admission contract; does not execute replay."""
from __future__ import annotations
import re
from typing import Mapping

STRATEGIES = ("trend_momentum", "idpat_smart_money", "broker_footprint", "smc_ict_liquidity", "hybrid_consensus", "fundamental_investment")
HORIZONS = ("t_plus_2", "swing", "positional", "investment")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def evaluate_six_scanner_replay_admission(
    *, quality_dashboard: Mapping[str, object], replay_preflight: Mapping[str, object],
    strategy_ids: list[str], horizons: list[str], dataset_manifest_sha256: str,
    partition: str, cost_model: Mapping[str, object], execution_model: Mapping[str, object],
    human_review: Mapping[str, object],
) -> dict:
    """Fail closed unless all strategies share one reviewed, point-in-time OOS dataset."""
    errors = []
    if quality_dashboard.get("status") != "QUALITY_REVIEW_READY": errors.append("quality_dashboard_not_ready")
    if replay_preflight.get("status") != "BOUNDED_PILOT_REPLAY_PREFLIGHT_READY": errors.append("source_replay_preflight_not_ready")
    if replay_preflight.get("historical_replay_executed") is not False: errors.append("preflight_execution_state_invalid")
    expected_hash = replay_preflight.get("dataset_manifest", {}).get("sha256")
    if not isinstance(dataset_manifest_sha256, str) or not _SHA256.fullmatch(dataset_manifest_sha256): errors.append("dataset_manifest_hash_invalid")
    elif dataset_manifest_sha256 != expected_hash: errors.append("dataset_manifest_hash_mismatch")
    if sorted(strategy_ids) != sorted(STRATEGIES) or len(strategy_ids) != len(set(strategy_ids)): errors.append("six_strategy_set_incomplete_or_duplicate")
    if sorted(horizons) != sorted(HORIZONS) or len(horizons) != len(set(horizons)): errors.append("four_horizon_set_incomplete_or_duplicate")
    if partition != "untouched_out_of_sample": errors.append("replay_partition_must_be_untouched_oos")
    required_costs = ("commission", "regulatory_fees", "taxes", "slippage")
    if not all(cost_model.get(k) is not None and cost_model.get(k) != "" for k in required_costs): errors.append("realistic_cost_model_incomplete")
    required_execution = ("next_session_execution", "liquidity_cap", "settlement_delay", "stop_first", "circuit_and_no_bid_handling")
    if not all(execution_model.get(k) not in (None, "") for k in required_execution): errors.append("execution_model_incomplete")
    if human_review.get("reviewed") is not True or human_review.get("approved") is not True or not str(human_review.get("reviewer_id", "")).strip() or not str(human_review.get("reviewed_at", "")).strip():
        errors.append("explicit_human_research_approval_missing")
    admitted = not errors
    return {
        "status": "ADMITTED_FOR_RESEARCH_REPLAY" if admitted else "BLOCKED",
        "admitted": admitted, "strategy_ids": list(strategy_ids), "horizons": list(horizons),
        "partition": partition, "dataset_manifest_sha256": dataset_manifest_sha256 if isinstance(dataset_manifest_sha256, str) else None,
        "blocking_reasons": errors,
        "historical_replay_executed": False, "performance_metrics_available": False,
        "probabilities_calibrated": False, "canonical_promotion_allowed": False, "production_enabled": False,
        "handoff": {"ready_to_invoke_existing_replay_runner": admitted, "common_dataset_required": True, "strategy_horizon_runs": len(STRATEGIES) * len(HORIZONS) if admitted else 0},
        "limitations": [
            "Admission is a research-only authorization contract; this function does not launch or execute a backtest.",
            "The caller must pass the same immutable point-in-time dataset fingerprint to every strategy and horizon.",
            "Execution realism is declared by the supplied model and still requires independent validation against exchange behavior.",
            "No results or probabilities are inferred from admission.",
        ],
    }
