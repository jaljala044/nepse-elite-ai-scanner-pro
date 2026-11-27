"""Controlled import of captured NEPSE historical files with byte-level provenance.

No network retrieval is performed. The caller supplies the exact captured bytes.
"""
from __future__ import annotations
import csv, hashlib, io
from datetime import datetime, timezone
from app.nepse_official_adapters import SCHEMAS, validate_nepse_dataset

def _time(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def ingest_captured_csv(*, raw_bytes, dataset_kind, source_id, publisher, source_uri,
    evidence_id, captured_at, decision_cutoff, rights_status, registry_review_id,
    source_validation_status="verified", finality_status="final"):
    """Parse exact CSV bytes, calculate their SHA-256, then run strict dataset validation."""
    if not isinstance(raw_bytes,(bytes,bytearray)) or not raw_bytes:
        raise ValueError("non_empty_raw_bytes_required")
    if dataset_kind not in SCHEMAS: raise ValueError("unsupported_dataset_kind")
    captured, cutoff = _time(captured_at), _time(decision_cutoff)
    if captured is None or cutoff is None: raise ValueError("timezone_aware_capture_and_cutoff_required")
    if captured > cutoff: raise ValueError("capture_after_decision_cutoff")
    for name,value in (("source_id",source_id),("publisher",publisher),("source_uri",source_uri),
        ("evidence_id",evidence_id),("registry_review_id",registry_review_id)):
        if not isinstance(value,str) or not value.strip(): raise ValueError(name+"_required")
    try: text=bytes(raw_bytes).decode("utf-8-sig")
    except UnicodeDecodeError: raise ValueError("csv_must_be_utf8") from None
    try:
        reader=csv.DictReader(io.StringIO(text,newline=""))
        headers=reader.fieldnames or []
        missing=sorted(set(SCHEMAS[dataset_kind])-set(headers))
        if missing: raise ValueError("csv_missing_required_columns:"+",".join(missing))
        rows=[{k:(v.strip() if isinstance(v,str) else v) for k,v in row.items() if k is not None}
            for row in reader]
    except csv.Error: raise ValueError("csv_parse_error") from None
    if not rows: raise ValueError("csv_contains_no_data_rows")
    digest=hashlib.sha256(bytes(raw_bytes)).hexdigest()
    envelope={"source_id":source_id.strip(),"publisher":publisher.strip(),
        "source_uri":source_uri.strip(),"evidence_id":evidence_id.strip(),
        "raw_sha256":digest,"available_at":captured.isoformat(),
        "rights_status":rights_status,"source_validation_status":source_validation_status,
        "finality_status":finality_status,"registry_review_id":registry_review_id.strip()}
    validation=validate_nepse_dataset(dataset_kind=dataset_kind,rows=rows,
        source_envelope=envelope,decision_cutoff=cutoff.isoformat())
    return {"schema_version":"nepse-captured-intake-1.0.0","dataset_kind":dataset_kind,
        "raw_sha256":digest,"raw_byte_count":len(raw_bytes),"row_count":len(rows),
        "captured_at":captured.isoformat(),"source_envelope":envelope,
        "validation":validation,"status":validation["status"],
        "network_retrieval_performed":False,"production_enabled":False,
        "limitations":["The module imports user/provider-supplied captured bytes; it does not fetch, authenticate or certify the publisher.",
            "Rights approval, source validation and registry review are asserted inputs that require external governance.",
            "A matching byte hash proves payload integrity after capture, not publisher authenticity or correctness."]}
