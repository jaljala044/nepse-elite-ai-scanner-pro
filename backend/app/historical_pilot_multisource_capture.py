"""Capture a required set of registered datasets without guessing endpoints."""
from __future__ import annotations
from typing import Callable, Mapping
from app.historical_pilot_source_capture import capture_approved_historical_source
from app.historical_pilot_capture_package import accept_historical_capture_package

_ALLOWED_KINDS = {
    "official_eod_ohlcv", "official_market_calendar", "official_security_master",
    "official_corporate_actions", "official_floorsheet", "cdsc_first_trade",
    "official_sector_indices", "official_broker_trade_summary",
}


def capture_required_historical_datasets(*, source_contract_reports: Mapping[str, Mapping[str, object]], transports: Mapping[str, Callable[[str], Mapping[str, object]]], required_dataset_kinds: list[str], captured_at: str, decision_cutoff: str) -> dict:
    """Capture each required dataset using only its own approved contract and transport."""
    if (not isinstance(required_dataset_kinds, list) or not required_dataset_kinds
            or any(not isinstance(kind, str) or not kind for kind in required_dataset_kinds)
            or len(required_dataset_kinds) != len(set(required_dataset_kinds))):
        raise ValueError("required_dataset_kinds must be a nonempty unique list")
    unsupported = sorted(set(required_dataset_kinds) - _ALLOWED_KINDS)
    if unsupported:
        raise ValueError(f"unsupported required dataset kinds: {unsupported}")
    if not isinstance(source_contract_reports, Mapping) or not isinstance(transports, Mapping):
        raise ValueError("source_contract_reports_and_transports_must_be_mappings")

    # Validate the contract inventory before invoking any injected transport.
    # A missing or duplicate contract for a required dataset type is a planning
    # error, not something to discover after partial source capture has started.
    contract_keys_by_kind = {kind: [] for kind in required_dataset_kinds}
    invalid_report_keys = []
    unapproved_contract_keys = []
    invalid_capture_id_keys = []
    capture_id_keys = {}
    for key, report in source_contract_reports.items():
        if not isinstance(key, str) or not key or not isinstance(report, Mapping):
            invalid_report_keys.append(str(key))
            continue
        spec = report.get("capture_spec")
        kind = spec.get("dataset_kind") if isinstance(spec, Mapping) else None
        if not isinstance(kind, str) or kind not in _ALLOWED_KINDS:
            invalid_report_keys.append(key)
            continue
        if kind in contract_keys_by_kind:
            contract_keys_by_kind[kind].append(key)
            if report.get("status") != "SOURCE_CONTRACT_APPROVED_FOR_CAPTURE" or report.get("capture_allowed") is not True:
                unapproved_contract_keys.append(key)
            capture_id = spec.get("capture_id")
            if not isinstance(capture_id, str) or not capture_id.strip() or capture_id != capture_id.strip():
                invalid_capture_id_keys.append(key)
            else:
                capture_id_keys.setdefault(capture_id, []).append(key)
    duplicate_capture_ids = {cid: sorted(keys) for cid, keys in capture_id_keys.items() if len(keys) > 1}
    missing_contract_kinds = sorted(kind for kind, keys in contract_keys_by_kind.items() if not keys)
    duplicate_contract_kinds = {
        kind: sorted(keys) for kind, keys in contract_keys_by_kind.items() if len(keys) > 1
    }
    missing_transport_kinds = sorted(
        kind for kind, keys in contract_keys_by_kind.items()
        if len(keys) == 1 and not callable(transports.get(keys[0]))
    )
    missing_dataset_kinds = sorted(set(missing_contract_kinds) | set(missing_transport_kinds))
    if (missing_dataset_kinds or duplicate_contract_kinds or invalid_report_keys
            or unapproved_contract_keys or invalid_capture_id_keys or duplicate_capture_ids):
        return {
            "status": "BLOCKED",
            "required_dataset_kinds": list(required_dataset_kinds),
            "captured_dataset_kinds": [],
            "missing_dataset_kinds": missing_dataset_kinds,
            "capture_results": {},
            "errors": [{
                "reason": "required_capture_contract_cardinality_invalid",
                "missing_contract_kinds": missing_contract_kinds,
                "missing_transport_kinds": missing_transport_kinds,
                "duplicate_contract_kinds": duplicate_contract_kinds,
                "invalid_report_keys": sorted(invalid_report_keys),
                "unapproved_contract_keys": sorted(unapproved_contract_keys),
                "invalid_capture_id_keys": sorted(invalid_capture_id_keys),
                "duplicate_capture_ids": duplicate_capture_ids,
            }],
            "all_required_capture_packages_validated": False,
            "publisher_authenticity_proven": False,
            "exchange_completeness_proven": False,
            "panel_assembly_allowed": False,
            "backtest_admission_allowed": False,
            "production_enabled": False,
        }

    results, errors, seen_capture_ids = {}, [], set()
    for key in sorted(source_contract_reports):
        report = source_contract_reports[key]
        if not isinstance(report, Mapping):
            results[key] = {"status":"CAPTURE_BLOCKED","errors":[{"reason":"source_contract_report_invalid"}]}
            errors.append({"capture_key":key,"reason":"source_contract_report_invalid"})
            continue
        spec = report.get("capture_spec")
        kind = spec.get("dataset_kind") if isinstance(spec,Mapping) else None
        if kind not in required_dataset_kinds:
            continue
        transport = transports.get(key)
        if not callable(transport):
            results[key] = {"status":"CAPTURE_BLOCKED","errors":[{"reason":"operator_transport_missing"}]}
            errors.append({"capture_key":key,"reason":"operator_transport_missing"})
            continue
        capture = capture_approved_historical_source(source_contract_report=report,fetch_page=transport,captured_at=captured_at,decision_cutoff=decision_cutoff)
        if capture.get("status") != "CAPTURED_PENDING_MANIFEST_VALIDATION" or not isinstance(capture.get("manifest"),Mapping):
            results[key] = {"status":"CAPTURE_BLOCKED","capture":capture,"errors":capture.get("errors",[])}
            errors.append({"capture_key":key,"reason":"capture_incomplete"})
            continue
        capture_id = capture["manifest"].get("capture_id")
        if not isinstance(capture_id,str) or not capture_id or capture_id != spec.get("capture_id") or capture_id in seen_capture_ids:
            results[key] = {"status":"CAPTURE_BLOCKED","capture":capture,"errors":[{"reason":"capture_id_missing_or_duplicate"}]}
            errors.append({"capture_key":key,"reason":"capture_id_missing_or_duplicate"})
            continue
        seen_capture_ids.add(capture_id)
        package = accept_historical_capture_package(source_contract_report=report,capture_result=capture,payloads=capture.get("payloads",{}),decision_cutoff=decision_cutoff)
        accepted = package.get("status") == "CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION"
        results[key] = {"status":"CAPTURE_PACKAGE_ACCEPTED" if accepted else "CAPTURE_PACKAGE_BLOCKED","dataset_kind":kind,"capture":capture,"package":package}
        if not accepted:
            errors.append({"capture_key":key,"reason":"strict_capture_package_validation_failed"})
    captured_kinds = [v.get("dataset_kind") for v in results.values() if v.get("status") == "CAPTURE_PACKAGE_ACCEPTED"]
    missing_kinds = sorted(set(required_dataset_kinds) - set(captured_kinds))
    if missing_kinds:
        errors.append({"reason":"required_dataset_kinds_missing","dataset_kinds":missing_kinds})
    complete = not errors and not missing_kinds and len(captured_kinds) == len(required_dataset_kinds)
    return {
        "status":"REQUIRED_DATASET_CAPTURE_SET_VALIDATED" if complete else "BLOCKED",
        "required_dataset_kinds":list(required_dataset_kinds),"captured_dataset_kinds":captured_kinds,
        "missing_dataset_kinds":missing_kinds,"capture_results":results,"errors":errors,
        "all_required_capture_packages_validated":complete,
        "publisher_authenticity_proven":False,"exchange_completeness_proven":False,
        "panel_assembly_allowed":complete,"backtest_admission_allowed":False,"production_enabled":False,
        "limitations":[
            "Each source endpoint, publisher, licence, pagination contract and transport must be supplied and approved by an operator.",
            "The same dataset kind must be captured only once per run; multiple publishers for one dataset require distinct contract keys and a separately designed reconciliation step.",
            "Raw payload durability and secure credential handling remain the operator's responsibility.",
            "Capture package validation does not normalize calendar, security master, corporate actions, floorsheet or CDSC evidence.",
        ],
    }
