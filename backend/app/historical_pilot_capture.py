"""Validate captured official-source payloads before lifecycle pilot admission.

This module deliberately performs no network requests. It verifies supplied
capture artifacts against an operator-reviewed registry and the requested
capture window; a valid manifest is not proof that a publisher is authentic.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Iterable, Mapping
from urllib.parse import urlparse


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include timezone")
    return parsed


def manifest_sha256(manifest: Mapping[str, object]) -> str:
    """Hash the exact structured manifest used by both validation and ingestion."""
    encoded = json.dumps(
        dict(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_official_capture_manifest(
    manifest: Mapping[str, object],
    payloads: Mapping[str, bytes],
    *,
    approved_registry: Iterable[Mapping[str, object]],
    decision_cutoff: str,
) -> dict:
    """Validate exact raw payload hashes, manifest identity and pagination."""
    cutoff = _dt(decision_cutoff, "decision_cutoff")
    registry = list(approved_registry)
    source_id = str(manifest.get("source_id", ""))
    source = next(
        (x for x in registry
         if x.get("source_id") == source_id and x.get("review_status") == "approved"),
        None,
    )
    errors = []
    try:
        fingerprint = manifest_sha256(manifest)
    except (TypeError, ValueError):
        fingerprint = None
        errors.append({"reason": "manifest_not_canonical_json"})

    if source is None:
        errors.append({"reason": "source_not_in_approved_registry"})
    publisher = str(manifest.get("publisher_id", "")).strip()
    if not publisher or (source and publisher != str(source.get("publisher_id", ""))):
        errors.append({"reason": "publisher_id_missing_or_mismatched"})
    url = str(manifest.get("request_url", ""))
    parsed = urlparse(url)
    allowed_hosts = set(source.get("allowed_hosts", [])) if source else set()
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname not in allowed_hosts:
        errors.append({"reason": "request_url_not_https_allowlisted"})

    try:
        captured_at = _dt(manifest.get("captured_at"), "captured_at")
        available_at = _dt(manifest.get("available_at"), "available_at")
        window_start = _dt(manifest.get("window_start"), "window_start")
        window_end = _dt(manifest.get("window_end"), "window_end")
    except ValueError:
        captured_at = available_at = window_start = window_end = None
        errors.append({"reason": "invalid_capture_or_window_timestamp"})
    if captured_at and available_at and (captured_at > cutoff or available_at > cutoff):
        errors.append({"reason": "capture_available_after_decision_cutoff"})
    if window_start and window_end and window_end < window_start:
        errors.append({"reason": "capture_window_inverted"})

    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        pages = []
        errors.append({"reason": "capture_pages_missing"})
    page_numbers, payload_ids, payload_hashes, verified_pages = set(), set(), set(), []
    for index, page in enumerate(pages):
        if not isinstance(page, Mapping):
            errors.append({"page": index, "reason": "invalid_page_manifest"})
            continue
        page_no, payload_id = page.get("page_number"), str(page.get("payload_id", "")).strip()
        if isinstance(page_no, bool) or not isinstance(page_no, int) or page_no < 1 or page_no in page_numbers:
            errors.append({"page": index, "reason": "invalid_or_duplicate_page_number"})
        else:
            page_numbers.add(page_no)
        if not payload_id or payload_id in payload_ids:
            errors.append({"page": index, "reason": "missing_or_duplicate_payload_id"})
        else:
            payload_ids.add(payload_id)
        raw = payloads.get(payload_id)
        if not payload_id or not isinstance(raw, bytes):
            errors.append({"page": index, "reason": "raw_payload_missing"})
            continue
        actual = hashlib.sha256(raw).hexdigest()
        expected = str(page.get("raw_sha256", ""))
        if actual != expected:
            errors.append({"page": index, "reason": "raw_payload_sha256_mismatch"})
            continue
        if page.get("http_status") != 200 or not isinstance(page.get("final_page"), bool):
            errors.append({"page": index, "reason": "http_or_pagination_status_invalid"})
            continue
        payload_hashes.add(actual)
        verified_pages.append({
            "page_number": page_no, "payload_id": payload_id, "raw_sha256": actual,
        })

    expected_count = manifest.get("expected_page_count")
    if (isinstance(expected_count, bool) or not isinstance(expected_count, int)
            or expected_count <= 0 or len(page_numbers) != expected_count
            or page_numbers != set(range(1, expected_count + 1))):
        errors.append({"reason": "pagination_incomplete_or_noncontiguous"})
    if pages:
        final_flags = [
            page.get("final_page") is True if isinstance(page, Mapping) else False
            for page in pages
        ]
        if final_flags.count(True) != 1 or not final_flags[-1]:
            errors.append({"reason": "final_page_not_unique_and_last"})
    if manifest.get("capture_complete") is not True:
        errors.append({"reason": "capture_not_certified_complete"})
    if manifest.get("response_content_type") not in (
        "text/csv", "application/json", "application/octet-stream"
    ):
        errors.append({"reason": "unsupported_or_missing_content_type"})
    if not str(manifest.get("capture_id", "")).strip():
        errors.append({"reason": "capture_id_missing"})

    ok = not errors
    return {
        "status": "CAPTURE_VALIDATED" if ok else "CAPTURE_BLOCKED",
        "source_id": source_id or None,
        "publisher_id": publisher or None,
        "capture_id": manifest.get("capture_id"),
        "manifest_sha256": fingerprint,
        "request_url": manifest.get("request_url"),
        "captured_at": manifest.get("captured_at"),
        "available_at": manifest.get("available_at"),
        "window_start": manifest.get("window_start"),
        "window_end": manifest.get("window_end"),
        "expected_page_count": manifest.get("expected_page_count"),
        "page_count": len(verified_pages),
        "verified_pages": verified_pages,
        "errors": errors,
        "raw_payload_hashes": sorted(payload_hashes),
        "research_evidence_eligible": ok,
        "exchange_publisher_authenticity_proven": False,
        "capture_window_completeness_independently_proven": False,
        "backtest_admission_allowed": False,
        "production_enabled": False,
        "limitations": [
            "No live network retrieval is performed.",
            "Registry approval and publisher identity require independent governance.",
            "A complete page manifest cannot prove that the source endpoint returned every exchange record.",
            "The manifest digest binds the validator output to the consumed manifest; it is not a digital signature.",
        ],
    }
