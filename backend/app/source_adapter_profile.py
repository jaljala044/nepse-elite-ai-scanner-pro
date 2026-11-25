"""Evidence-backed source adapter profiles; sample mappings are never assumed."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
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
        if not self.mapping or any(not str(k).strip() or not str(v).strip()
                                   for k, v in self.mapping.items()):
            raise ValueError("mapping must contain non-blank normalized and source headers")
        if len(set(self.mapping.values())) != len(self.mapping):
            raise ValueError("each normalized field must map to a distinct source header")
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
        text = payload.decode(encoding)
        headers = next(csv.reader([text.splitlines()[0]], delimiter=delimiter))
    except (UnicodeDecodeError, LookupError, IndexError, StopIteration) as exc:
        raise ValueError("cannot read source header") from exc
    canonical = json.dumps(headers, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_adapter_profile(profile: SourceAdapterProfile, sample_payload: bytes, *,
                           encoding: str = "utf-8-sig", delimiter: str = ",") -> dict:
    payload_hash = hashlib.sha256(sample_payload).hexdigest()
    header_hash = header_fingerprint(sample_payload, encoding=encoding, delimiter=delimiter)
    try:
        decoded_headers = next(csv.reader(
            [sample_payload.decode(encoding).splitlines()[0]], delimiter=delimiter))
    except (UnicodeDecodeError, LookupError, IndexError, StopIteration) as exc:
        raise ValueError("cannot read source header") from exc
    missing_mapping_headers = sorted(set(profile.mapping.values()) - set(decoded_headers))
    payload_match = payload_hash == profile.sample_payload_sha256
    header_match = header_hash == profile.sample_header_sha256
    mapping_present = not missing_mapping_headers
    return {
        "source_id": profile.source_id,
        "profile_schema_version": profile.schema_version,
        "payload_hash_match": payload_match,
        "header_hash_match": header_match,
        "mapping_headers_present": mapping_present,
        "missing_mapping_headers": missing_mapping_headers,
        "review_evidence_id": profile.evidence_id,
        "reviewer": profile.reviewer,
        "reviewed_at": profile.reviewed_at,
        "mapping_verified_for_exact_sample": payload_match and header_match and mapping_present,
        "profile_sha256": hashlib.sha256(json.dumps({
            "source_id": profile.source_id, "publisher_name": profile.publisher_name,
            "schema_version": profile.schema_version, "mapping": dict(profile.mapping),
            "sample_payload_sha256": profile.sample_payload_sha256,
            "sample_header_sha256": profile.sample_header_sha256,
            "reviewer": profile.reviewer, "reviewed_at": profile.reviewed_at,
            "evidence_id": profile.evidence_id,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }
