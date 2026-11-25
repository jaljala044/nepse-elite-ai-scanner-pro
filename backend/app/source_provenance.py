"""Source provenance and rights assertions for immutable market-data batches.

Rights fields are declarations with evidence references, not legal conclusions.
Unknown values remain unknown; ingestion must not infer a redistribution grant.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json


RIGHTS_STATES = {"unknown", "review_required", "research_only", "internal_use",
                 "redistribution_permitted", "prohibited"}
PROVENANCE_STATES = {"primary", "publisher", "aggregator", "user_supplied", "derived", "unknown"}


def _utc(value: str) -> str:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("provenance timestamps must be timezone-aware")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SourceProvenance:
    source_id: str
    publisher_name: str
    source_url: str | None
    provenance_class: str
    rights_state: str
    rights_evidence_id: str | None
    attribution_required: bool | None
    redistribution_allowed: bool | None
    terms_reviewed_at: str | None
    reviewer: str | None = None

    def __post_init__(self):
        if not self.source_id.strip() or not self.publisher_name.strip():
            raise ValueError("source identity and publisher are required")
        if self.provenance_class not in PROVENANCE_STATES:
            raise ValueError("unsupported provenance_class")
        if self.rights_state not in RIGHTS_STATES:
            raise ValueError("unsupported rights_state")
        if self.redistribution_allowed is True and self.rights_state != "redistribution_permitted":
            raise ValueError("redistribution permission requires explicit permitted rights_state")
        if self.rights_state == "redistribution_permitted" and not self.rights_evidence_id:
            raise ValueError("redistribution permission requires rights evidence")
        if self.terms_reviewed_at:
            _utc(self.terms_reviewed_at)


def build_batch_provenance(source: SourceProvenance, *, payload: bytes,
                           captured_at: str, acquired_by: str,
                           acquisition_method: str, source_record_id: str | None = None) -> dict:
    if not acquired_by.strip() or not acquisition_method.strip():
        raise ValueError("acquisition actor and method are required")
    captured = _utc(captured_at)
    payload_hash = hashlib.sha256(payload).hexdigest()
    body = {
        "schema_version": 1,
        "source": asdict(source),
        "capture": {
            "captured_at": captured, "acquired_by": acquired_by,
            "acquisition_method": acquisition_method,
            "source_record_id": source_record_id,
            "payload_sha256": payload_hash, "payload_bytes": len(payload),
        },
        "training_eligibility": {
            "rights_clearance": source.rights_state in {"research_only", "internal_use", "redistribution_permitted"},
            "redistribution_allowed": source.redistribution_allowed is True,
            "requires_human_rights_review": source.rights_state in {"unknown", "review_required"},
        },
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "provenance_sha256": hashlib.sha256(canonical.encode()).hexdigest()}
