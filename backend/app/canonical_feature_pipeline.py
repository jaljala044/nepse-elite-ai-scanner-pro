"""Connect verified canonical evidence to the descriptive feature pipeline."""
from __future__ import annotations
from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any
from .canonical_evidence import load_canonical_evidence_records
from .feature_pipeline import build_feature_snapshot
from .session_calendar import load_calendar

def build_canonical_feature_snapshot(*, database_path: str | Path | None, ledger_path: str | Path, registry: dict[str, Any], trusted_registry_sha256: str, reviewer_keys: dict[str, bytes], calendar_path: str | Path, trusted_calendar_sha256: str, decision_time: str, expected_symbols: list[str] | None = None, sector_membership: dict | None = None, expected_sector_members: dict | None = None) -> dict[str, Any]:
    """Only promoted records and evidence-backed open sessions reach features."""
    try:
        cutoff = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise ValueError("decision_time must be timezone-aware")
        canonical = load_canonical_evidence_records(database_path=database_path, ledger_path=ledger_path, registry=registry, trusted_registry_sha256=trusted_registry_sha256, reviewer_keys=reviewer_keys, decision_time=decision_time)
        calendar_bytes = Path(calendar_path).read_bytes()
        actual_calendar_sha256 = hashlib.sha256(calendar_bytes).hexdigest()
        if actual_calendar_sha256 != trusted_calendar_sha256.lower():
            raise ValueError("session calendar digest does not match trusted deployment pin")
        calendar = load_calendar(calendar_path)
        session_dates = []
        for day, evidence in sorted(calendar.items()):
            if day > cutoff.date() or evidence["status"] not in {"verified_open", "verified_exceptional_open"}:
                continue
            verified_at = datetime.fromisoformat(evidence["verified_at_utc"].replace("Z", "+00:00"))
            retrieved_at = datetime.fromisoformat(evidence["retrieved_at_utc"].replace("Z", "+00:00"))
            if verified_at <= cutoff and retrieved_at <= cutoff:
                session_dates.append(day.isoformat())
        if not canonical["records"] or not session_dates:
            missing = (["canonical_promoted_records"] if not canonical["records"] else []) + (["verified_session_calendar"] if not session_dates else [])
            return {"status":"insufficient_evidence","decision_status":"UNKNOWN","action":"PRESERVE_CAPITAL","feature_snapshot":None,"canonical_evidence":{k:v for k,v in canonical.items() if k!="records"},"calendar_session_count":len(session_dates),"missing":missing,"production_source_claim":False}
        features = build_feature_snapshot(canonical["records"], decision_time, expected_symbols=expected_symbols, sector_membership=sector_membership, expected_sector_members=expected_sector_members, session_dates=session_dates)
        return {"status":"ready" if features.get("point_in_time_eligible") else "insufficient_evidence","decision_status":"RESEARCH_ONLY" if features.get("point_in_time_eligible") else "UNKNOWN","action":"NO_TRADE","feature_snapshot":features,"canonical_evidence":{k:v for k,v in canonical.items() if k!="records"},"calendar_session_count":len(session_dates),"production_source_claim":False,"policy":"canonical_evidence_only_no_secondary_or_bronze_fallback"}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"status":"insufficient_evidence","decision_status":"UNKNOWN","action":"PRESERVE_CAPITAL","feature_snapshot":None,"missing":["canonical_evidence_or_verified_calendar"],"error_code":type(exc).__name__,"production_source_claim":False}
