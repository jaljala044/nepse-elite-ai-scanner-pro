"""IDPAT-5 fail-closed orchestration adapter for the existing scanner.

This is a separate research endpoint. It does not alter the existing /v1/scan
ranking or production recommendation paths and never emits BUY/SELL decisions.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal

from app.idpat_price_volume import analyze_idpat_price_volume
from app.idpat_accumulation_distribution import analyze_idpat_accumulation_distribution
from app.idpat_market_structure import analyze_idpat_market_structure
from app.idpat_risk_management import build_idpat_risk_plan


REQUIRED_GATES = (
    "market", "sector", "broker", "liquidity", "execution",
    "corporate_actions", "source_quality",
)


def _aware(value, field):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError(f"invalid_{field}") from None
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return result


def _gate_report(gates, cutoff):
    if not isinstance(gates, dict):
        gates = {}
    report, blocked = {}, []
    for name in REQUIRED_GATES:
        item = gates.get(name)
        reason = None
        if not isinstance(item, dict):
            reason = "missing_gate_evidence"
        elif item.get("status") != "verified":
            reason = "gate_not_verified"
        elif not isinstance(item.get("evidence_id"), str) or not item["evidence_id"].strip():
            reason = "gate_evidence_id_missing"
        else:
            try:
                available = _aware(item.get("available_at"), f"{name}_available_at")
                if available > cutoff:
                    reason = "gate_evidence_after_decision_cutoff"
            except ValueError:
                reason = "gate_evidence_timestamp_invalid"
        report[name] = {"status": "blocked" if reason else "verified",
                        "reason": reason,
                        "evidence_id": item.get("evidence_id") if isinstance(item, dict) else None}
        if reason:
            blocked.append(f"{name}:{reason}")
    return report, blocked


def build_idpat_scanner_bundle(*, snapshot, as_of_date, as_of_timestamp,
                               session_calendar=None, gate_evidence=None,
                               risk_inputs=None, methodology_version="idpat-5.0.0"):
    cutoff = _aware(as_of_timestamp, "as_of_timestamp")
    gate_report, blocked = _gate_report(gate_evidence, cutoff)
    price_volume = analyze_idpat_price_volume(
        snapshot, as_of_date=as_of_date, as_of_timestamp=as_of_timestamp)
    accumulation_distribution = analyze_idpat_accumulation_distribution(
        snapshot, as_of_date=as_of_date, as_of_timestamp=as_of_timestamp)
    market_structure = analyze_idpat_market_structure(
        snapshot, as_of_date=as_of_date, as_of_timestamp=as_of_timestamp,
        session_calendar=session_calendar)

    risk_plan = {"status": "withheld", "action": "NO_TRADE",
                 "reason": "independent_scanner_gates_not_all_verified"}
    if not blocked and price_volume.get("status") == "partial_research_only":
        if not isinstance(risk_inputs, dict):
            risk_plan = {"status": "withheld", "action": "NO_TRADE",
                         "reason": "explicit_risk_inputs_required"}
        else:
            try:
                risk_plan = build_idpat_risk_plan(**risk_inputs)
            except (ValueError, TypeError) as exc:
                risk_plan = {"status": "withheld", "action": "NO_TRADE",
                             "reason": str(exc)}

    evidence_ids = sorted(
        item["evidence_id"] for item in gate_report.values()
        if item["status"] == "verified"
    )
    record = {
        "schema_version": "idpat-5.0.0",
        "methodology_version": methodology_version,
        "symbol": snapshot.get("symbol") if isinstance(snapshot, dict) else None,
        "decision_time": cutoff.isoformat(),
        "decision_date": as_of_date,
        "classification": "research_only_not_execution",
        "action": "NO_TRADE",
        "overall_score": None,
        "probability": None,
        "gate_report": gate_report,
        "blocked_gates": blocked,
        "evidence_ids": evidence_ids,
        "engines": {
            "price_volume": price_volume,
            "accumulation_distribution": accumulation_distribution,
            "market_structure": market_structure,
        },
        "risk_plan": risk_plan,
        "production_recommendations_enabled": False,
        "limitations": [
            "IDPAT-1 through IDPAT-4 are research components and are not a production-certified proprietary IDPAT implementation.",
            "All market, sector, broker, liquidity, execution, corporate-action and source-quality gates must be independently verified at decision time.",
            "A REVIEW_ONLY risk plan is not a BUY instruction or order authorization.",
            "No live data fetch, canonical persistence, exchange execution or verified fills occur in this adapter.",
        ],
    }
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {
        "status": "research_bundle_ready" if not blocked else "gates_blocked",
        "action": "NO_TRADE",
        "signal_id": hashlib.sha256(encoded.encode()).hexdigest(),
        "record": record,
        "immutable_snapshot": True,
        "persisted": False,
    }
