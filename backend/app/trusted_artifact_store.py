"""Server-side, allowlisted artifact loader for Part 2 intelligence snapshots.

The registry is deployment-controlled configuration, never request data. A
registry entry pins an immutable payload path and SHA-256 digest. This module
does not fetch external websites or treat uploaded CSVs as trusted sources.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .market_intelligence_snapshot import REQUIRED_MODULES


class TrustedArtifactError(ValueError):
    """Raised when a deployment-pinned artifact cannot be safely admitted."""


def _canonical_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise TrustedArtifactError(f"{field}_must_be_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise TrustedArtifactError(f"{field}_must_be_iso_date") from None
    if parsed.isoformat() != value:
        raise TrustedArtifactError(f"{field}_must_be_iso_date")
    return parsed


def _timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise TrustedArtifactError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise TrustedArtifactError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TrustedArtifactError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _safe_payload_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise TrustedArtifactError("payload_path_missing")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or "\\" in relative:
        raise TrustedArtifactError("payload_path_unsafe")
    root_resolved = root.resolve()
    path = (root_resolved / relative).resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise TrustedArtifactError("payload_path_escapes_store")
    return path


class TrustedArtifactStore:
    """Load only artifacts pinned by server-owned registry configuration.

    registry schema:
      {module: {source_id, payload_path, payload_sha256, evidence_ids,
                as_of_date, available_at, status, coverage_ratio,
                finality_status, source_validation_status}}

    The registry must come from deployment configuration with write access
    restricted to the ingestion/approval service. Hashes supplied by API
    clients are never consulted.
    """

    def __init__(self, root: str | Path, registry: Mapping[str, Any], *,
                 max_age_days: int = 7) -> None:
        self.root = Path(root)
        self.registry = registry
        if isinstance(max_age_days, bool) or not isinstance(max_age_days, int) or max_age_days < 0:
            raise ValueError("max_age_days_must_be_nonnegative_integer")
        self.max_age_days = max_age_days

    def load(self, *, decision_date: str, decision_time: str,
             required_modules: tuple[str, ...] = REQUIRED_MODULES) -> dict[str, dict]:
        cutoff_date = _canonical_date(decision_date, "decision_date")
        # Compare the supplied timestamp's own calendar date before
        # normalizing it to UTC. A valid Nepal-local midnight timestamp can
        # fall on the previous UTC date and must not be rejected.
        if not isinstance(decision_time, str):
            raise TrustedArtifactError("decision_time_must_be_timezone_aware")
        try:
            local_cutoff = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
        except ValueError:
            raise TrustedArtifactError("decision_time_must_be_timezone_aware") from None
        if local_cutoff.tzinfo is None or local_cutoff.utcoffset() is None:
            raise TrustedArtifactError("decision_time_must_be_timezone_aware")
        if local_cutoff.date() < cutoff_date:
            raise TrustedArtifactError("decision_time_precedes_decision_date")
        cutoff = _timestamp(decision_time, "decision_time")
        if not isinstance(self.registry, Mapping):
            raise TrustedArtifactError("server_registry_invalid")

        output: dict[str, dict] = {}
        for module in required_modules:
            entry = self.registry.get(module)
            if not isinstance(entry, Mapping):
                continue
            try:
                source_id = entry.get("source_id")
                if not isinstance(source_id, str) or not source_id.strip():
                    raise TrustedArtifactError("source_id_missing")
                evidence_ids = entry.get("evidence_ids")
                if (not isinstance(evidence_ids, list) or not evidence_ids
                        or any(not isinstance(item, str) or not item.strip() for item in evidence_ids)
                        or len(evidence_ids) != len(set(evidence_ids))):
                    raise TrustedArtifactError("evidence_ids_missing_or_duplicate")

                as_of = _canonical_date(entry.get("as_of_date"), "artifact_as_of_date")
                if as_of > cutoff_date:
                    raise TrustedArtifactError("artifact_as_of_after_decision_date")
                if cutoff_date - as_of > timedelta(days=self.max_age_days):
                    raise TrustedArtifactError("artifact_stale")

                available_at = _timestamp(entry.get("available_at"), "available_at")
                if available_at > cutoff:
                    raise TrustedArtifactError("artifact_available_after_decision_time")
                payload_path = _safe_payload_path(self.root, entry.get("payload_path"))
                raw = payload_path.read_bytes()
                expected_hash = entry.get("payload_sha256")
                actual_hash = sha256(raw).hexdigest()
                if (not isinstance(expected_hash, str) or len(expected_hash) != 64
                        or actual_hash != expected_hash.lower()):
                    raise TrustedArtifactError("payload_sha256_mismatch")

                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise TrustedArtifactError("payload_must_be_json_object")
                if entry.get("source_validation_status") != "verified":
                    raise TrustedArtifactError("source_not_verified")
                if entry.get("finality_status") != "final":
                    raise TrustedArtifactError("source_finality_not_verified")
                coverage = entry.get("coverage_ratio")
                if (isinstance(coverage, bool) or not isinstance(coverage, (int, float))
                        or not 0 < coverage <= 1):
                    raise TrustedArtifactError("coverage_ratio_invalid")
                status = entry.get("status")
                if status not in {"observed", "research_only", "descriptive_only"}:
                    raise TrustedArtifactError("artifact_status_not_admissible")

                calendar_id = entry.get("session_calendar_id")
                if not isinstance(calendar_id, str) or not calendar_id.strip():
                    raise TrustedArtifactError("session_calendar_id_missing")
                context = {"session_calendar_id": calendar_id}
                price_modules = {
                    "market_health", "index_intelligence", "sector_rotation",
                    "relative_strength", "wyckoff", "market_structure",
                }
                if module in price_modules:
                    action_status = entry.get("corporate_action_status")
                    if action_status not in {"verified", "confirmed_none"}:
                        raise TrustedArtifactError("corporate_action_status_unverified")
                    context["corporate_action_status"] = action_status
                if module in {"sector_rotation", "broker_sector_rotation"}:
                    membership_status = entry.get("sector_membership_status")
                    membership_version = entry.get("sector_membership_version")
                    if membership_status != "verified" or not isinstance(membership_version, str) or not membership_version.strip():
                        raise TrustedArtifactError("sector_membership_version_unverified")
                    context["sector_membership_status"] = membership_status
                    context["sector_membership_version"] = membership_version
                if module in {"broker_profiles", "broker_sector_rotation"}:
                    broker_status = entry.get("broker_code_mapping_status")
                    broker_coverage = entry.get("broker_identity_coverage_ratio")
                    if broker_status != "verified":
                        raise TrustedArtifactError("broker_code_mapping_unverified")
                    if (isinstance(broker_coverage, bool)
                            or not isinstance(broker_coverage, (int, float))
                            or not 0 < broker_coverage <= 1):
                        raise TrustedArtifactError("broker_identity_coverage_invalid")
                    context["broker_code_mapping_status"] = broker_status
                    context["broker_identity_coverage_ratio"] = float(broker_coverage)

                output[module] = {
                    "status": status,
                    "as_of_date": as_of.isoformat(),
                    "available_at": available_at.isoformat(),
                    "session_calendar_id": calendar_id,
                    "quality_context": context,
                    "source_ids": [source_id],
                    "evidence_ids": list(evidence_ids),
                    "coverage_ratio": float(coverage),
                    "source_validation_status": "verified",
                    "finality_status": "final",
                    "evidence_gate_passed": True,
                    "data": data,
                }
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                reason = str(exc) or "artifact_unavailable"
                output[module] = {"status": "unavailable", "rejection_reason": reason}
        return output


def build_trusted_market_snapshot(store: TrustedArtifactStore, *,
                                  decision_date: str, decision_time: str) -> dict:
    """Load pinned server-side artifacts and pass only admitted envelopes onward."""
    from .market_intelligence_snapshot import build_market_intelligence_snapshot

    artifacts = store.load(decision_date=decision_date, decision_time=decision_time)
    return build_market_intelligence_snapshot(
        artifacts, decision_date=decision_date, decision_time=decision_time
    )
