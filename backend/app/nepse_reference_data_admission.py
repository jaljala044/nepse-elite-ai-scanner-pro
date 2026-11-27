"""Fail-closed admission of official calendar and instrument-universe evidence."""
from __future__ import annotations
import hashlib
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Mapping
from app.calendar_evidence_manifest import validate_calendar_evidence_manifest
from app.universe_snapshot import validate_universe_snapshot


def _utc(value):
    if not isinstance(value, str): return None
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0: return None
    return parsed.astimezone(timezone.utc)


def admit_reference_data_bundle(*, calendar_rows, captures, universe_snapshot,
                                 evidence_root, expected_calendar_dates,
                                 decision_cutoff, expected_equities=281,
                                 expected_mutual_funds=47, minimum_independent_sources=2):
    """Validate bytes, official URLs, timestamps, rights, source independence,
    full date coverage and a dated official universe snapshot.

    This returns a research-review decision only. It never enables production.
    """
    cutoff = _utc(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_utc_aware")
    if isinstance(minimum_independent_sources, bool) or not isinstance(minimum_independent_sources, int) or minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources_invalid")
    root = Path(evidence_root).resolve()
    verified, capture_errors, by_id = [], [], {}
    for capture in captures if isinstance(captures, list) else []:
        if not isinstance(capture, Mapping):
            capture_errors.append({"source_id": None, "reason": "capture_not_object"})
            continue
        source_id = capture.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip() or source_id in by_id:
            capture_errors.append({"source_id": source_id, "reason": "source_id_missing_or_duplicate"})
            continue
        url = capture.get("final_url") or capture.get("url")
        captured_at = _utc(capture.get("retrieved_at_utc"))
        group = capture.get("independence_group")
        failures = []
        if capture.get("rights_status") != "approved": failures.append("rights_not_approved")
        if capture.get("source_validation_status") != "verified": failures.append("source_not_verified")
        if capture.get("finality_status") != "final": failures.append("source_finality_not_verified")
        if captured_at is None: failures.append("retrieved_at_not_utc")
        elif captured_at > cutoff: failures.append("capture_after_decision_cutoff")
        if capture.get("independence_review_status") != "approved" or not isinstance(group, str) or not group.strip():
            failures.append("independence_not_reviewed")
        rel = capture.get("raw_evidence_path")
        digest = str(capture.get("raw_evidence_sha256", "")).lower()
        if not isinstance(rel, str) or not rel.strip(): failures.append("raw_evidence_path_missing")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            failures.append("raw_evidence_sha256_invalid")
        actual = None
        if isinstance(rel, str) and rel.strip():
            path = (root / rel).resolve()
            if root not in path.parents or path.is_symlink():
                failures.append("raw_evidence_path_outside_root_or_symlink")
            else:
                try: actual = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError: failures.append("raw_evidence_file_unavailable")
        if actual is not None and actual != digest: failures.append("raw_evidence_hash_mismatch")
        if failures:
            capture_errors.append({"source_id": source_id, "reasons": failures})
            continue
        verified_capture = dict(capture)
        verified_capture["raw_evidence_sha256"] = digest
        verified_capture["independence_group"] = group
        by_id[source_id] = verified_capture
        verified.append(verified_capture)

    calendar_result = None
    try:
        calendar_result = validate_calendar_evidence_manifest(calendar_rows, verified)
    except (TypeError, ValueError) as exc:
        capture_errors.append({"reason": "calendar_manifest_invalid", "detail": str(exc)})
    calendar_errors = []
    expected_dates = []
    for value in expected_calendar_dates if isinstance(expected_calendar_dates, list) else []:
        try: expected_dates.append(date.fromisoformat(value).isoformat())
        except (TypeError, ValueError): calendar_errors.append("expected_calendar_date_invalid:" + str(value))
    if not expected_dates: calendar_errors.append("expected_calendar_dates_missing")
    if len(expected_dates) != len(set(expected_dates)): calendar_errors.append("expected_calendar_dates_duplicate")
    claims = calendar_result.get("claims", []) if calendar_result else []
    by_day = {}
    for claim in claims:
        if claim.get("scope") not in {"*", "all_securities"}:
            continue
        by_day.setdefault(claim["date"], []).append(claim)
    for day in expected_dates:
        matches = by_day.get(day, [])
        if len(matches) != 1:
            calendar_errors.append("calendar_date_missing_or_ambiguous:" + day)
            continue
        groups = {by_id[sid]["independence_group"] for sid in matches[0]["source_ids"] if sid in by_id}
        if len(groups) < minimum_independent_sources:
            calendar_errors.append("calendar_date_lacks_independent_sources:" + day)
    if calendar_result and calendar_result.get("conflict_count"):
        calendar_errors.append("calendar_scope_conflicts_present")

    universe_result, universe_errors = None, []
    if not isinstance(universe_snapshot, Mapping):
        universe_errors.append("universe_snapshot_missing")
    else:
        source_id = universe_snapshot.get("source_id")
        capture = by_id.get(source_id)
        if capture is None:
            universe_errors.append("universe_snapshot_source_not_verified_capture")
        else:
            if universe_snapshot.get("source_url") != (capture.get("final_url") or capture.get("url")):
                universe_errors.append("universe_snapshot_url_capture_mismatch")
            if str(universe_snapshot.get("raw_payload_sha256", "")).lower() != capture.get("raw_evidence_sha256"):
                universe_errors.append("universe_snapshot_hash_capture_mismatch")
            retrieved = _utc(universe_snapshot.get("retrieved_at_utc"))
            captured = _utc(capture.get("retrieved_at_utc"))
            if retrieved is None or captured is None or retrieved != captured:
                universe_errors.append("universe_snapshot_retrieval_timestamp_mismatch")
        try:
            universe_result = validate_universe_snapshot(
                dict(universe_snapshot), expected_equities=expected_equities,
                expected_mutual_funds=expected_mutual_funds)
        except (TypeError, ValueError) as exc:
            universe_errors.append("universe_snapshot_invalid:" + str(exc))

    all_errors = capture_errors + calendar_errors + universe_errors
    allowed = bool(verified) and not all_errors and bool(calendar_result and calendar_result.get("status") == "valid") and bool(universe_result and universe_result.get("manifest_verified"))
    return {
        "status": "reference_evidence_ready_for_research_review" if allowed else "blocked_or_incomplete",
        "capture_count": len(captures) if isinstance(captures, list) else 0,
        "verified_capture_count": len(verified),
        "calendar_claim_count": calendar_result.get("calendar_claim_count", 0) if calendar_result else 0,
        "expected_calendar_date_count": len(expected_dates),
        "verified_full_scope_calendar_date_count": sum(1 for d in expected_dates if len(by_day.get(d, [])) == 1),
        "universe_result": universe_result,
        "calendar_result": calendar_result,
        "errors": all_errors,
        "research_review_allowed": allowed,
        "production_promotion_allowed": False,
        "policy": "raw_bytes_rehashed_point_in_time_rights_and_independent_sources_required_no_implicit_calendar_or_universe_completion",
    }
