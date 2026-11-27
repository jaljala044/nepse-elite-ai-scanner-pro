"""Repeatable historical dataset bundle acquisition using the governed source registry."""
from __future__ import annotations
from hashlib import sha256
import json
from app.nepse_source_connectors import acquire_registered_capture
from app.nepse_historical_intake import ingest_captured_csv
from app.nepse_dataset_readiness import assess_historical_dataset_readiness
from app.nepse_official_adapters import SCHEMAS

def acquire_historical_dataset_bundle(*, registry, requests, decision_cutoff,
    start_date, end_date, minimum_session_coverage_pct="100",
    require_optional=(), transport_by_source=None, fail_fast=False):
    """Acquire explicitly enumerated CSV snapshots and run the dataset readiness gate.

    One request is one bounded CSV object. Pagination/archives must be enumerated
    as separate requests by the caller; this function never guesses URL patterns.
    """
    if not isinstance(requests,list) or not requests:
        raise ValueError("non_empty_dataset_requests_required")
    if transport_by_source is None: transport_by_source={}
    if not isinstance(transport_by_source,dict): raise ValueError("transport_by_source_must_be_dict")
    intake={kind:[] for kind in SCHEMAS}
    captures=[]; failures=[]; seen_request_ids=set(); seen_hashes=set()
    for index,request in enumerate(requests):
        if not isinstance(request,dict):
            failures.append({"index":index,"reason":"request_not_object"})
            if fail_fast: break
            continue
        request_id=request.get("request_id")
        kind=request.get("dataset_kind")
        source_id=request.get("source_id")
        if (not isinstance(request_id,str) or not request_id.strip() or request_id in seen_request_ids
            or kind not in SCHEMAS or not isinstance(source_id,str) or not source_id.strip()):
            failures.append({"index":index,"reason":"request_identity_or_dataset_invalid"})
            if fail_fast: break
            continue
        seen_request_ids.add(request_id)
        try:
            result=acquire_registered_capture(registry=registry,source_id=source_id,
                dataset_kind=kind,endpoint_uri=request.get("endpoint_uri"),
                evidence_id=request.get("evidence_id"),captured_at=request.get("captured_at"),
                decision_cutoff=decision_cutoff,rights_status=request.get("rights_status"),
                timeout_seconds=request.get("timeout_seconds",15),
                max_bytes=request.get("max_bytes",25_000_000),
                transport=transport_by_source.get(source_id))
            receipt=result["receipt"]
            if receipt["raw_sha256"] in seen_hashes:
                failures.append({"request_id":request_id,"reason":"duplicate_raw_payload_across_bundle"})
                if fail_fast: break
                continue
            seen_hashes.add(receipt["raw_sha256"])
            report=ingest_captured_csv(raw_bytes=result["raw_bytes"],dataset_kind=kind,
                source_id=source_id,publisher=receipt["publisher_id"],
                source_uri=request["endpoint_uri"],evidence_id=request["evidence_id"],
                captured_at=request["captured_at"],decision_cutoff=decision_cutoff,
                rights_status=request["rights_status"],registry_review_id=receipt["registry_review_id"],
                source_validation_status="verified",finality_status="final")
            if report["status"]!="validated_for_research":
                failures.append({"request_id":request_id,"reason":"captured_csv_failed_schema_validation",
                    "validation_errors":report["validation"].get("envelope_errors",[])})
                if fail_fast: break
                continue
            intake[kind].append(report)
            captures.append({"request_id":request_id,"dataset_kind":kind,
                "source_id":source_id,"raw_sha256":receipt["raw_sha256"],
                "raw_byte_count":receipt["raw_byte_count"],"accepted_rows":report["row_count"],
                "captured_at":report["captured_at"],"status":"validated_for_research"})
        except (ValueError,KeyError,TypeError) as exc:
            failures.append({"request_id":request_id,"reason":"acquisition_rejected:"+str(exc)})
            if fail_fast: break
    readiness=assess_historical_dataset_readiness(intake_reports=intake,
        start_date=start_date,end_date=end_date,decision_cutoff=decision_cutoff,
        minimum_session_coverage_pct=minimum_session_coverage_pct,
        require_optional=require_optional)
    manifest_payload={"decision_cutoff":decision_cutoff,"start_date":start_date,
        "end_date":end_date,"captures":captures,"failures":failures,
        "readiness_status":readiness["status"]}
    manifest_hash=sha256(json.dumps(manifest_payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"schema_version":"nepse-historical-bundle-1.0.0",
        "manifest":{**manifest_payload,"manifest_sha256":manifest_hash},
        "intake_reports":intake,"readiness":readiness,
        "capture_count":len(captures),"failure_count":len(failures),
        "historical_panel_promotion_allowed":readiness["status"]=="READY" and not failures,
        "corporate_action_reconciliation_required":True,
        "live_data_acquired":bool(captures),"production_enabled":False,
        "limitations":[
            "Only explicitly enumerated endpoint URLs are fetched; no endpoint discovery or implicit pagination occurs.",
            "The operator must independently verify official publisher identity, licensing, completeness and finality.",
            "Dataset readiness is a coverage/schema gate, not independent corporate-action reconciliation.",
            "Corporate actions must separately pass two-source factor reconciliation before adjusted history is promoted.",
            "Missing optional feeds remain unavailable to dependent strategies; no missing values are imputed."]}
