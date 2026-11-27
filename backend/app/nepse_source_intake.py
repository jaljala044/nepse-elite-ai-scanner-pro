"""Trusted NEPSE source intake adapter; no network retrieval is performed.

A caller must obtain the bytes through an authorized channel and supply a
reviewed registry record. This module verifies the envelope and delegates
immutable capture plus canonical CSV admission to the existing validators.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from app.canonical_data_admission import capture_raw_artifact, validate_and_admit_ohlcv_csv


def ingest_trusted_nepse_ohlcv(*, raw_bytes, registry_record, source_id,
    source_uri, publisher, captured_at, published_at, decision_cutoff,
    expected_symbols, verified_session_status, adjustment_basis, output_root,
    minimum_coverage=0.98):
    errors=[]
    if not isinstance(registry_record, dict):
        registry_record={}
        errors.append("trusted_source_registry_record_missing")
    required=("source_id","publisher","source_uri","rights_status",
              "source_validation_status","finality_status","registry_status",
              "review_id","reviewed_at","signature_status")
    missing=[k for k in required if not registry_record.get(k)]
    if missing: errors.append("registry_fields_missing:"+",".join(missing))
    if registry_record.get("registry_status") != "approved": errors.append("source_registry_not_approved")
    if registry_record.get("signature_status") != "independently_verified": errors.append("publisher_signature_not_independently_verified")
    if registry_record.get("rights_status") != "approved": errors.append("source_rights_not_approved")
    if registry_record.get("source_validation_status") != "verified": errors.append("source_validation_not_verified")
    if registry_record.get("finality_status") != "final": errors.append("source_finality_not_verified")
    for field,value in (("source_id",source_id),("publisher",publisher),("source_uri",source_uri)):
        if registry_record.get(field) != value: errors.append(field+"_registry_mismatch")
    if not isinstance(raw_bytes,bytes) or not raw_bytes: errors.append("raw_bytes_missing")
    expected_hash=registry_record.get("expected_sha256")
    if expected_hash and isinstance(raw_bytes,bytes) and hashlib.sha256(raw_bytes).hexdigest()!=expected_hash:
        errors.append("registry_sha256_mismatch")
    if errors:
        return {"status":"blocked","errors":errors,"capture":None,"admission":None,
                "research_review_allowed":False,"production_promotion_allowed":False}
    capture=capture_raw_artifact(raw_bytes,source_id=source_id,source_uri=source_uri,
        publisher=publisher,captured_at=captured_at,published_at=published_at,
        rights_status=registry_record["rights_status"],
        source_validation_status=registry_record["source_validation_status"],
        finality_status=registry_record["finality_status"],output_root=output_root)
    # Preserve reviewed registry provenance in the returned envelope. The raw
    # content-addressed capture itself remains immutable and publisher identity
    # is not inferred from the digest.
    trusted_manifest={**capture,"registry_review_id":registry_record["review_id"],
        "registry_reviewed_at":registry_record["reviewed_at"],
        "signature_status":registry_record["signature_status"],
        "independence_group":registry_record.get("independence_group"),
        "independence_review_status":registry_record.get("independence_review_status")}
    admission=validate_and_admit_ohlcv_csv(raw_path=Path(output_root)/capture["raw_path"],
        manifest=trusted_manifest,expected_symbols=expected_symbols,
        verified_session_status=verified_session_status,decision_cutoff=decision_cutoff,
        adjustment_basis=adjustment_basis,minimum_coverage=minimum_coverage)
    return {"status":"admitted_for_research_review" if admission.get("admission_allowed") else "captured_but_admission_blocked",
        "capture":trusted_manifest,"admission":admission,
        "research_review_allowed":admission.get("admission_allowed") is True,
        "production_promotion_allowed":False,
        "limitations":["No HTTP fetch or scraping is performed.",
        "The registry and signature review must be maintained by a trusted operator.",
        "A SHA-256 digest proves byte integrity, not publisher authenticity."]}
