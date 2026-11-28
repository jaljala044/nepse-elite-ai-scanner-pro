"""Versioned, human-approved source schema profiles; never infer provider columns."""
from __future__ import annotations
import hashlib, json
from datetime import datetime
from typing import Mapping
from app.historical_pilot_evidence_ingest import _SCHEMAS


def validate_source_schema_profile(profile: Mapping[str, object]) -> dict:
    required_meta = ("profile_id", "version", "source_id", "publisher_id", "dataset_kind",
                     "column_map", "approved_by", "approval_reference", "approved_at")
    errors=[]
    for field in required_meta:
        if profile.get(field) in (None, "", {}):
            errors.append({"field":field,"reason":"required_profile_metadata_missing"})
    kind=profile.get("dataset_kind")
    schema=_SCHEMAS.get(kind) if isinstance(kind,str) else None
    mapping=profile.get("column_map")
    if schema is None:
        errors.append({"field":"dataset_kind","reason":"unsupported_dataset_kind"})
    if not isinstance(mapping,Mapping):
        errors.append({"field":"column_map","reason":"explicit_mapping_required"})
        mapping={}
    else:
        required=set(schema["required"]) if schema else set()
        unknown=set(mapping)-set(schema.keys() if schema else ())
        if not required.issubset(mapping):
            errors.append({"field":"column_map","reason":"required_semantic_fields_missing","fields":sorted(required-set(mapping))})
        if unknown:
            errors.append({"field":"column_map","reason":"unknown_semantic_fields","fields":sorted(unknown)})
        values=list(mapping.values())
        if any(not isinstance(v,str) or not v.strip() for v in values) or len(values)!=len(set(values)):
            errors.append({"field":"column_map","reason":"source_columns_must_be_nonblank_and_unique"})
    try:
        dt=datetime.fromisoformat(str(profile.get("approved_at","")).replace("Z","+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None: raise ValueError
    except (ValueError,TypeError):
        errors.append({"field":"approved_at","reason":"approval_timestamp_must_be_timezone_aware"})
    if profile.get("approved") is not True:
        errors.append({"field":"approved","reason":"human_approval_required"})
    canonical=json.dumps(dict(profile),sort_keys=True,separators=(",",":"),default=str).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    return {"status":"APPROVED_PROFILE_VALID" if not errors else "BLOCKED",
            "profile_id":profile.get("profile_id"),"version":profile.get("version"),
            "dataset_kind":kind,"source_id":profile.get("source_id"),
            "column_map":dict(mapping) if not errors else None,
            "profile_sha256":digest,"errors":errors,
            "provider_schema_authenticated":False,
            "limitations":["Approval records operator review; it does not authenticate the publisher or prove schema completeness."]}
