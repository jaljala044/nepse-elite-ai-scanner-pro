"""Orchestrate supplied official-source captures and lifecycle boundary evidence.

This is an offline evidence workflow: callers supply exact raw bytes and manifests.
It does not fetch URLs, authenticate publishers, or infer missing records.
"""
from __future__ import annotations
from typing import Iterable, Mapping

from app.historical_pilot_capture import validate_official_capture_manifest
from app.historical_pilot_verification import validate_official_first_trade_evidence


def reconcile_lifecycle_pilot_sources(
    *,
    cohort_rows: Iterable[Mapping[str, object]],
    capture_artifacts: Mapping[str, Mapping[str, object]],
    required_capture_keys: Iterable[str],
    approved_registry: Iterable[Mapping[str, object]],
    official_first_trade_rows: Iterable[Mapping[str, object]],
    decision_cutoff: str,
) -> dict:
    cohort = list(cohort_rows)
    registry = list(approved_registry)
    required = list(required_capture_keys)
    if not required or len(required) != len(set(required)):
        raise ValueError("required_capture_keys must be nonempty and unique")
    capture_reports, missing, duplicate_capture_ids = {}, [], []
    seen_ids = set()
    for key in required:
        artifact = capture_artifacts.get(key)
        if not isinstance(artifact, Mapping):
            missing.append(key)
            continue
        manifest, payloads = artifact.get("manifest"), artifact.get("payloads")
        if not isinstance(manifest, Mapping) or not isinstance(payloads, Mapping):
            capture_reports[key] = {"status": "CAPTURE_BLOCKED", "errors": [{"reason": "manifest_or_payloads_missing"}]}
            continue
        capture_id = str(manifest.get("capture_id", ""))
        if not capture_id or capture_id in seen_ids:
            duplicate_capture_ids.append({"capture_key": key, "capture_id": capture_id or None})
        else:
            seen_ids.add(capture_id)
        report = validate_official_capture_manifest(manifest, payloads, approved_registry=registry, decision_cutoff=decision_cutoff)
        capture_reports[key] = {**report, "capture_key": key, "request_url": manifest.get("request_url"), "window_start": manifest.get("window_start"), "window_end": manifest.get("window_end"), "capture_complete": manifest.get("capture_complete") is True}
    first_trade = validate_official_first_trade_evidence(cohort, official_first_trade_rows, decision_cutoff=decision_cutoff)
    failed = [key for key, report in capture_reports.items() if report.get("status") != "CAPTURE_VALIDATED"]
    all_valid = not missing and not failed and not duplicate_capture_ids
    first_complete = first_trade.get("all_cohort_first_trades_verified") is True
    return {
        "status": "SOURCE_EVIDENCE_RECONCILED" if all_valid and first_complete else "BLOCKED",
        "required_capture_keys": required,
        "capture_reports": capture_reports,
        "missing_capture_keys": missing,
        "failed_capture_keys": failed,
        "duplicate_capture_ids": duplicate_capture_ids,
        "first_trade_report": first_trade,
        "capture_gate_passed": all_valid,
        "first_trade_gate_passed": first_complete,
        "source_reconciliation_passed": all_valid and first_complete,
        "actual_source_payloads_supplied": bool(capture_reports) and not missing,
        "publisher_authenticity_proven": False,
        "exchange_completeness_proven": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "All raw bytes and manifests must be supplied by the operator; this module performs no network requests.",
            "Registry allowlisting and SHA-256 integrity do not authenticate the publisher cryptographically.",
            "Capture completeness declarations are not independent proof of exchange-wide completeness.",
            "A reconciled subset does not imply the whole pilot cohort or calendar is verified.",
        ],
    }
