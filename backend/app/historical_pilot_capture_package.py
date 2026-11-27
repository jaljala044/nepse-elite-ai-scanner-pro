"""Validate a completed source capture as a bounded, ingestible evidence package."""
from __future__ import annotations
from typing import Mapping
from app.historical_pilot_capture import validate_official_capture_manifest


def accept_historical_capture_package(*, source_contract_report: Mapping[str, object], capture_result: Mapping[str, object], payloads: Mapping[str, bytes], decision_cutoff: str) -> dict:
    """Join approved source contract, runner output and exact raw-payload validation."""
    errors = []
    if source_contract_report.get("status") != "SOURCE_CONTRACT_APPROVED_FOR_CAPTURE" or source_contract_report.get("capture_allowed") is not True:
        return {"status":"PACKAGE_BLOCKED","errors":[{"reason":"source_contract_not_approved"}],"capture_validated":False,"panel_ingestion_allowed":False,"backtest_admission_allowed":False}
    spec = source_contract_report.get("capture_spec")
    registry = source_contract_report.get("registry_record")
    manifest = capture_result.get("manifest")
    if not isinstance(spec,Mapping) or not isinstance(registry,Mapping) or not isinstance(manifest,Mapping):
        return {"status":"PACKAGE_BLOCKED","errors":[{"reason":"capture_spec_registry_or_manifest_missing"}],"capture_validated":False,"panel_ingestion_allowed":False,"backtest_admission_allowed":False}
    if capture_result.get("capture_complete") is not True or capture_result.get("status") != "CAPTURED_PENDING_MANIFEST_VALIDATION":
        errors.append({"reason":"capture_runner_did_not_report_complete_capture"})
    for field, expected in (("source_id",spec.get("source_id")),("publisher_id",spec.get("publisher_id")),("capture_id",spec.get("capture_id")),("request_url",spec.get("endpoint_url")),("window_start",spec.get("window_start")),("window_end",spec.get("window_end"))):
        if manifest.get(field) != expected:
            errors.append({"reason":"manifest_contract_mismatch","field":field})
    allowed_types = set(spec.get("allowed_content_types",[]))
    if manifest.get("response_content_type") not in allowed_types:
        errors.append({"reason":"manifest_content_type_not_in_contract"})
    if capture_result.get("raw_payload_count") != len(payloads) or capture_result.get("all_pages_hashed") is not True:
        errors.append({"reason":"raw_payload_inventory_or_hash_coverage_mismatch"})
    validation = validate_official_capture_manifest(manifest,payloads,approved_registry=[registry],decision_cutoff=decision_cutoff)
    if validation.get("status") != "CAPTURE_VALIDATED":
        errors.append({"reason":"strict_capture_manifest_validation_failed","details":validation.get("errors",[])})
    ok = not errors
    return {
        "status":"CAPTURE_PACKAGE_ACCEPTED_FOR_PANEL_INGESTION" if ok else "PACKAGE_BLOCKED",
        "capture_validated":ok,"panel_ingestion_allowed":ok,"backtest_admission_allowed":False,
        "production_enabled":False,"source_id":manifest.get("source_id"),"publisher_id":manifest.get("publisher_id"),
        "capture_id":manifest.get("capture_id"),"dataset_kind":spec.get("dataset_kind"),
        "manifest_sha256":validation.get("manifest_sha256"),"verified_page_count":validation.get("page_count",0),
        "verified_pages":validation.get("verified_pages",[]),"validation_report":validation,"errors":errors,
        "publisher_authenticity_proven":False,"exchange_completeness_proven":False,
        "limitations":[
            "Package acceptance verifies supplied bytes against the approved registry contract; it does not authenticate the publisher cryptographically.",
            "A complete pagination manifest is not independent proof that the endpoint returned every exchange record.",
            "Raw payload durability, immutable storage and access control remain the operator's responsibility.",
            "Panel ingestion still requires the dataset-specific explicit column mapping and downstream identity/calendar/corporate-action checks.",
        ],
    }
