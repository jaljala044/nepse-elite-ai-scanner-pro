"""Validate date-level calendar claims against captured raw notice evidence."""
from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import urlparse

OPEN = {"verified_open", "verified_exceptional_open"}
CLOSED = {"verified_closed", "verified_exceptional_closed"}
ALLOWED = OPEN | CLOSED


def _scope_ids(scope: str) -> set[str] | None:
    value = scope.strip()
    if value in {"*", "all_securities"}:
        return None
    ids = {item.strip() for item in value.split(",") if item.strip()}
    if not ids:
        raise ValueError("calendar evidence scope must be all_securities or a comma-separated security ID list")
    return ids


def _overlap(left: set[str] | None, right: set[str] | None) -> bool:
    return left is None or right is None or bool(left & right)


def validate_calendar_evidence_manifest(rows: list[dict], captures: list[dict]) -> dict:
    """Require every calendar claim to cite captured bytes and reject scope conflicts."""
    capture_by_id = {}
    for capture in captures:
        source_id = str(capture.get("source_id") or "").strip()
        digest = str(capture.get("raw_evidence_sha256") or "").lower()
        url = str(capture.get("final_url") or capture.get("url") or "")
        parsed = urlparse(url)
        if not source_id or source_id in capture_by_id:
            raise ValueError("capture source IDs must be present and unique")
        if parsed.scheme != "https" or parsed.hostname not in {
            "nepalstock.com.np", "www.nepalstock.com.np", "sebon.gov.np", "www.sebon.gov.np"
        }:
            raise ValueError(f"capture {source_id}: URL is not an approved official host")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"capture {source_id}: invalid raw evidence SHA-256")
        capture_by_id[source_id] = capture

    by_date = defaultdict(list)
    for index, row in enumerate(rows):
        day = str(row.get("date") or "")
        status = row.get("status")
        source_ids = row.get("source_ids")
        if not day or status not in ALLOWED:
            raise ValueError(f"calendar row {index}: date/status missing or unsupported")
        if not isinstance(source_ids, list) or not source_ids:
            raise ValueError(f"calendar row {index}: source_ids must be a non-empty list")
        for source_id in source_ids:
            if source_id not in capture_by_id:
                raise ValueError(f"calendar row {index}: missing captured evidence for {source_id}")
        scope = _scope_ids(str(row.get("scope") or ""))
        by_date[day].append({**row, "_scope_ids": scope})

    conflicts = []
    normalized = []
    for day, items in sorted(by_date.items()):
        for index, left in enumerate(items):
            for right in items[index + 1:]:
                left_open, right_open = left["status"] in OPEN, right["status"] in OPEN
                if left_open != right_open and _overlap(left["_scope_ids"], right["_scope_ids"]):
                    conflicts.append({
                        "date": day,
                        "left_status": left["status"], "right_status": right["status"],
                        "left_scope": left["scope"], "right_scope": right["scope"],
                        "left_source_ids": left["source_ids"], "right_source_ids": right["source_ids"],
                    })
        for item in items:
            normalized.append({
                "date": day, "status": item["status"], "scope": item["scope"],
                "source_ids": sorted(set(item["source_ids"])),
                "raw_evidence_sha256": sorted({
                    capture_by_id[source_id]["raw_evidence_sha256"].lower()
                    for source_id in item["source_ids"]
                }),
            })
    return {
        "calendar_claim_count": len(normalized),
        "captured_source_count": len(capture_by_id),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "claims": normalized,
        "status": "valid" if normalized and not conflicts else "conflict_or_empty",
        "calendar_population_allowed": False,
        "policy": "evidence_manifest_validation_only_no_automatic_calendar_promotion",
    }
