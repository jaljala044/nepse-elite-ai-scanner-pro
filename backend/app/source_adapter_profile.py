"""Evidence-backed source adapter profiles; sample mappings are never assumed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Mapping


@dataclass(frozen=True)
class SourceAdapterProfile:
    source_id: str
    publisher_name: str
    schema_version: str
    mapping: Mapping[str, str]
    sample_payload_sha256: str
    sample_header_sha256: str
    reviewer: str
    reviewed_at: str
    evidence_id: str

    def __post_init__(self):
        if not all((self.source_id.strip(), self.publisher_name.strip(),
                    self.schema_version.strip(), self.reviewer.strip(),
                    self.evidence_id.strip())):
            raise ValueError("profile identity, reviewer and evidence are required")
        for field, value in (("sample_payload_sha256", self.sample_payload_sha256),
                             ("sample_header_sha256", self.sample_header_sha256)):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
                raise ValueError(f"{field} must be a SHA-256 hex digest")
        parsed = datetime.fromisoformat(self.reviewed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("reviewed_at must be timezone-aware")


def header_fingerprint(payload: bytes, *, encoding: str = "utf-8-sig",
                       delimiter: str = ",") -> str:
    try:
        first_line = payload.decode(encoding).splitlines()[0]
    except (UnicodeDecodeError, LookupError, IndexError) as exc:
        raise ValueError("cannot read source header") from exc
    headers = next(__import__("csv").reader([first_line], delimiter=delimiter))
    canonical = json.dumps(headers, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_adapter_profile(profile: SourceAdapterProfile, sample_payload: bytes, *,
                           encoding: str = "utf-8-sig", delimiter: str = ",") -> dict:
    payload_hash = hashlib.sha256(sample_payload).hexdigest()
    header_hash = header_fingerprint(sample_payload, encoding=encoding, delimiter=delimiter)
    payload_match = payload_hash == profile.sample_payload_sha256
    header_match = header_hash == profile.sample_header_sha256
    return {
        "source_id": profile.source_id,
        "profile_schema_version": profile.schema_version,
        "payload_hash_match": payload_match,
        "header_hash_match": header_match,
        "review_evidence_id": profile.evidence_id,
        "reviewer": profile.reviewer,
        "reviewed_at": profile.reviewed_at,
        "mapping_verified_for_exact_sample": payload_match and header_match,
        "profile_sha256": hashlib.sha256(json.dumps({
            "source_id": profile.source_id, "publisher_name": profile.publisher_name,
            "schema_version": profile.schema_version, "mapping": dict(profile.mapping),
            "sample_payload_sha256": profile.sample_payload_sha256,
            "sample_header_sha256": profile.sample_header_sha256,
            "reviewer": profile.reviewer, "reviewed_at": profile.reviewed_at,
            "evidence_id": profile.evidence_id,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
