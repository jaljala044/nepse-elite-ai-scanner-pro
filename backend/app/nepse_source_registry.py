"""Governed source registry and reproducible capture receipts.

The registry validates configured source metadata; it does not authenticate publishers
or perform network requests. Connector/browser acquisition must supply exact bytes
and an independently reviewed source record.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse
from app.nepse_official_adapters import SCHEMAS
from app.nepse_historical_intake import ingest_captured_csv

AUTHORITY={"exchange_official","regulator_depository","third_party"}
STATES={"candidate","approved","suspended","blocked"}

def _time(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _host(uri):
    try:
        parsed=urlparse(uri)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password: return None
        return parsed.hostname.lower().rstrip(".")
    except (TypeError,ValueError): return None

def validate_source_registry(records):
    if not isinstance(records,list): raise ValueError("source_registry_list_required")
    seen=set(); output=[]; errors=[]
    for index,record in enumerate(records):
        if not isinstance(record,dict):
            errors.append({"index":index,"reason":"record_not_object"}); continue
        sid=record.get("source_id"); publisher=record.get("publisher_id")
        host=_host(record.get("canonical_uri"))
        authority=record.get("authority_type"); state=record.get("status")
        datasets=record.get("dataset_kinds")
        required=("source_id","publisher_id","publisher_group","publisher_name","review_id","reviewed_at")
        missing=[k for k in required if not isinstance(record.get(k),str) or not record[k].strip()]
        why=[]
        if missing: why.append("missing:"+",".join(missing))
        if not host: why.append("canonical_uri_must_be_https")
        if authority not in AUTHORITY: why.append("authority_type_invalid")
        if state not in STATES: why.append("status_invalid")
        if not isinstance(datasets,list) or not datasets or any(not isinstance(x,str) or x not in SCHEMAS for x in datasets):
            why.append("dataset_kinds_invalid")
        reviewed=_time(record.get("reviewed_at"))
        if reviewed is None: why.append("reviewed_at_must_be_timezone_aware")
        if (isinstance(sid,str) and sid in seen) or (isinstance(publisher,str) and publisher in seen): why.append("duplicate_source_or_publisher_id")
        if sid: seen.add(sid)
        if publisher: seen.add(publisher)
        if why: errors.append({"index":index,"reason":why}); continue
        output.append({**record,"canonical_host":host,"reviewed_at":reviewed.isoformat(),
            "registry_valid":True,"publisher_authentication":"not_performed"})
    return {"schema_version":"nepse-source-registry-1.0.0","sources":output,
        "valid_count":len(output),"rejected_count":len(errors),"errors":errors,
        "production_enabled":False,
        "limitations":["Registry approval is a governance assertion, not cryptographic publisher authentication.",
            "Publisher independence must be established outside this software; different IDs or domains do not prove independence.",
            "No HTTP request, scraping, credential handling or data download is performed."]}

def build_source_capture_run(*, registry, captures, decision_cutoff):
    checked=validate_source_registry(registry)
    if checked["errors"]: raise ValueError("source_registry_contains_invalid_records")
    cutoff=_time(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if not isinstance(captures,list): raise ValueError("captures_must_be_list")
    by_id={x["source_id"]:x for x in checked["sources"]}
    receipts=[]; rejected=[]; hashes={}
    for index,item in enumerate(captures):
        if not isinstance(item,dict):
            rejected.append({"index":index,"reason":"capture_not_object"}); continue
        source_key=item.get("source_id")\n        source=by_id.get(source_key) if isinstance(source_key,str) else None
        if source is None or source["status"]!="approved":
            rejected.append({"index":index,"reason":"source_not_approved"}); continue
        dataset=item.get("dataset_kind")
        if dataset not in source["dataset_kinds"]:
            rejected.append({"index":index,"reason":"dataset_not_authorized_for_source"}); continue
        uri=item.get("source_uri"); host=_host(uri)
        if host!=source["canonical_host"]:
            rejected.append({"index":index,"reason":"capture_host_mismatch"}); continue
        captured=_time(item.get("captured_at"))
        if captured is None or captured>cutoff:
            rejected.append({"index":index,"reason":"capture_time_invalid_or_after_cutoff"}); continue
        raw=item.get("raw_bytes")
        if not isinstance(raw,(bytes,bytearray)) or not raw:
            rejected.append({"index":index,"reason":"raw_bytes_required"}); continue
        digest=sha256(bytes(raw)).hexdigest()
        if digest in hashes:
            prior=hashes[digest]
            rejected.append({"index":index,"reason":"duplicate_payload_hash",
                "prior_source_id":prior["source_id"],"cross_publisher_duplicate":prior["publisher_id"]!=source["publisher_id"]})
            continue
        try:
            intake=ingest_captured_csv(raw_bytes=raw,dataset_kind=dataset,
                source_id=source["source_id"],publisher=source["publisher_name"],source_uri=uri,
                evidence_id=item.get("evidence_id"),captured_at=item["captured_at"],
                decision_cutoff=decision_cutoff,rights_status=item.get("rights_status"),
                registry_review_id=source["review_id"],
                source_validation_status=item.get("source_validation_status","verified"),
                finality_status=item.get("finality_status","final"))
        except (ValueError,KeyError) as exc:
            rejected.append({"index":index,"reason":"intake_rejected:"+str(exc)}); continue
        if intake["status"]!="validated_for_research":
            rejected.append({"index":index,"reason":"dataset_validation_failed",
                "validation_errors":intake["validation"]["envelope_errors"],
                "quarantined_count":intake["validation"]["quarantined_count"]}); continue
        receipt={"capture_index":index,"source_id":source["source_id"],
            "publisher_id":source["publisher_id"],"publisher_group":source["publisher_group"],
            "dataset_kind":dataset,"source_uri":uri,"captured_at":captured.isoformat(),
            "raw_sha256":digest,"raw_byte_count":len(raw),"row_count":intake["row_count"],
            "evidence_id":item["evidence_id"],"status":"validated_for_research"}
        receipts.append(receipt); hashes[digest]=receipt
    return {"schema_version":"nepse-source-capture-run-1.0.0",
        "decision_cutoff":cutoff.isoformat(),"receipts":receipts,"rejected":rejected,
        "capture_count":len(receipts),"rejected_count":len(rejected),
        "research_only":True,"production_enabled":False,
        "limitations":["The capture caller supplies bytes; no live official-source connection is implemented.",
            "HTTPS host matching and SHA-256 provide transport/configuration and byte-integrity checks only.",
            "A source receipt does not establish publisher authenticity, completeness, finality or independent corroboration."]}
