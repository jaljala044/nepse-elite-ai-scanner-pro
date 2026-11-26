"""Fail-closed audit of reconstructed NEPSE session-date candidates."""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from app.session_calendar import load_calendar, schedule_candidate

CANDIDATE_FIELDS = (
    "date", "status", "source_repository", "source_revision", "source_path",
    "git_blob_sha1", "source_bytes", "lineage",
)


def audit_session_candidates(
    candidate_csv: str | Path,
    calendar_csv: str | Path,
    source_root: str | Path | None = None,
    expected_source_repository: str | None = None,
    expected_source_revision: str | None = None,
) -> dict[str, Any]:
    """Audit candidate inventory consistency without promoting any date."""
    rows: list[dict[str, str]] = []
    seen: set[date] = set()
    duplicates: list[str] = []
    malformed: list[dict[str, Any]] = []
    source_failures: list[dict[str, Any]] = []
    source_verified = 0
    with Path(candidate_csv).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(CANDIDATE_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("candidate file missing columns: " + ", ".join(sorted(missing)))
        for line, raw in enumerate(reader, 2):
            try:
                day = date.fromisoformat((raw.get("date") or "").strip())
            except ValueError:
                malformed.append({"line": line, "reason": "invalid_iso_date"})
                continue
            if day in seen:
                duplicates.append(day.isoformat())
            seen.add(day)
            digest = (raw.get("git_blob_sha1") or "").strip().lower()
            revision = (raw.get("source_revision") or "").strip().lower()
            try:
                size = int((raw.get("source_bytes") or "").strip())
            except ValueError:
                size = -1
            if len(digest) != 40 or any(c not in "0123456789abcdef" for c in digest):
                malformed.append({"line": line, "date": day.isoformat(), "reason": "invalid_git_blob_sha1"})
            if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
                malformed.append({"line": line, "date": day.isoformat(), "reason": "invalid_source_revision"})
            if expected_source_repository and raw.get("source_repository") != expected_source_repository:
                malformed.append({"line": line, "date": day.isoformat(), "reason": "unexpected_source_repository"})
            if expected_source_revision and revision != expected_source_revision.lower():
                malformed.append({"line": line, "date": day.isoformat(), "reason": "unexpected_source_revision"})
            if size <= 0:
                malformed.append({"line": line, "date": day.isoformat(), "reason": "invalid_source_bytes"})
            if raw.get("status") != "candidate_unverified":
                malformed.append({"line": line, "date": day.isoformat(), "reason": "candidate_status_not_unverified"})
            if not all((raw.get(k) or "").strip() for k in ("source_repository", "source_revision", "source_path", "lineage")):
                malformed.append({"line": line, "date": day.isoformat(), "reason": "missing_source_lineage"})
            candidate = {k: (v or "").strip() for k, v in raw.items()}
            rows.append(candidate)
            if source_root is not None and candidate.get("source_path"):
                try:
                    root_path = Path(source_root).resolve(strict=True)
                    source_path = (root_path / candidate["source_path"]).resolve(strict=True)
                    source_path.relative_to(root_path)
                    payload = source_path.read_bytes()
                    actual_size = len(payload)
                    actual_blob = hashlib.sha1(
                        b"blob " + str(actual_size).encode("ascii") + b"\0" + payload
                    ).hexdigest()
                    if actual_size != size:
                        source_failures.append({"line": line, "date": day.isoformat(), "reason": "source_byte_count_mismatch", "expected": size, "actual": actual_size})
                    elif actual_blob != digest:
                        source_failures.append({"line": line, "date": day.isoformat(), "reason": "git_blob_sha1_mismatch", "expected": digest, "actual": actual_blob})
                    else:
                        source_verified += 1
                except ValueError:
                    source_failures.append({"line": line, "date": day.isoformat(), "reason": "source_path_outside_root", "path": candidate["source_path"]})
                except OSError:
                    source_failures.append({"line": line, "date": day.isoformat(), "reason": "source_file_missing", "path": candidate["source_path"]})

    evidence = load_calendar(calendar_csv)
    candidate_dates = {date.fromisoformat(row["date"]) for row in rows if row.get("date")}
    closed_conflicts = sorted(
        day.isoformat() for day in candidate_dates
        if evidence.get(day, {}).get("status") in {"verified_closed", "verified_exceptional_closed"}
    )
    open_overlaps = sorted(
        day.isoformat() for day in candidate_dates
        if evidence.get(day, {}).get("status") in {"verified_open", "verified_exceptional_open"}
    )
    weekday_violations = []
    for day in sorted(candidate_dates):
        eligible, note = schedule_candidate(day)
        if not eligible:
            weekday_violations.append({"date": day.isoformat(), "schedule_rule": note})

    by_year = Counter(day.year for day in candidate_dates)
    by_weekday = Counter(day.strftime("%A") for day in candidate_dates)
    source_revisions = sorted({row.get("source_revision", "") for row in rows})
    expected_window = (
        min(candidate_dates).isoformat() if candidate_dates else None,
        max(candidate_dates).isoformat() if candidate_dates else None,
    )
    return {
        "schema_version": 1,
        "candidate_rows": len(rows),
        "unique_candidate_dates": len(candidate_dates),
        "duplicate_dates": sorted(set(duplicates)),
        "malformed_rows": malformed,
        "source_files_verified": source_verified,
        "source_file_failures": source_failures,
        "source_file_verification_required": source_root is not None,
        "expected_source_repository": expected_source_repository,
        "expected_source_revision": expected_source_revision,
        "date_window": {"first": expected_window[0], "last": expected_window[1]},
        "counts_by_year": {str(k): by_year[k] for k in sorted(by_year)},
        "counts_by_weekday": {k: by_weekday[k] for k in sorted(by_weekday)},
        "source_revisions": source_revisions,
        "weekday_regime_violations": weekday_violations,
        "verified_closure_conflicts": closed_conflicts,
        "verified_open_overlaps": open_overlaps,
        "canonical_open_dates_promoted": 0,
        "promotion_allowed": False,
        "gate_pass": bool(rows) and source_root is not None and source_verified == len(rows) and not source_failures and not duplicates and not malformed and not weekday_violations and not closed_conflicts,
        "policy": "Candidate archive dates are not exchange-confirmed sessions. This audit never promotes dates; only independently reviewed date-scoped evidence may do so.",
    }
