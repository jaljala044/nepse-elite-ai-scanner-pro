#!/usr/bin/env python3
"""Build a date-by-date source coverage matrix without inferring NEPSE sessions.

Inputs are JSONL source manifests containing at least a dated filename and source
identifier. The output distinguishes explicit exchange evidence from weekday
schedule candidates and from mere file presence.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.session_calendar import load_calendar, schedule_candidate


def load_manifests(paths: list[str | Path]) -> dict[date, dict[str, Any]]:
    coverage: dict[date, dict[str, Any]] = defaultdict(
        lambda: {"file_count": 0, "total_size_bytes": 0, "sources": {}, "paths": []}
    )
    seen: set[tuple[str, str]] = set()
    for manifest_path in paths:
        with Path(manifest_path).open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    day = date.fromisoformat(str(row["date"]))
                    path = str(row["path"])
                    source = str(row.get("repo_id") or row.get("repository") or row.get("source_id") or row.get("source") or "").strip()
                    if not source or not path:
                        raise ValueError("missing source identifier or path")
                    size = int(row.get("size_bytes") or 0)
                    if size < 0:
                        raise ValueError("negative size_bytes")
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"{manifest_path}:{line_no}: invalid manifest row: {exc}") from exc
                key = (source, path)
                if key in seen:
                    raise ValueError(f"{manifest_path}:{line_no}: duplicate manifest entry {source}:{path}")
                seen.add(key)
                item = coverage[day]
                item["file_count"] += 1
                item["total_size_bytes"] += size
                item["sources"][source] = item["sources"].get(source, 0) + 1
                item["paths"].append({"source": source, "path": path, "size_bytes": size})
    return coverage


def build_matrix(
    manifest_paths: list[str | Path],
    calendar_path: str | Path,
    start: date,
    end: date,
) -> dict[str, Any]:
    if end < start:
        raise ValueError("end date must not precede start date")
    evidence = load_calendar(calendar_path)
    coverage = load_manifests(manifest_paths)
    rows = []
    day = start
    while day <= end:
        candidate, schedule_note = schedule_candidate(day)
        explicit = evidence.get(day)
        observed = coverage.get(day, {"file_count": 0, "total_size_bytes": 0, "sources": {}, "paths": []})
        classification = explicit["status"] if explicit else (
            "unverified_session_candidate" if candidate else "unverified_non_session_candidate"
        )
        flags = []
        if not explicit:
            flags.append("calendar_evidence_missing")
            if observed["file_count"]:
                flags.append("source_file_on_unverified_calendar_date")
        if observed["file_count"] and explicit and explicit["status"] in {"verified_closed", "verified_exceptional_closed"}:
            flags.append("source_file_on_verified_closed_date")
        if not observed["file_count"] and explicit and explicit["status"] in {"verified_open", "verified_exceptional_open"}:
            flags.append("verified_open_date_without_source_file")
        rows.append({
            "date": day.isoformat(),
            "calendar_classification": classification,
            "schedule_candidate_note": schedule_note,
            "source_file_count": observed["file_count"],
            "source_count": len(observed["sources"]),
            "source_file_counts": dict(sorted(observed["sources"].items())),
            "total_size_bytes": observed["total_size_bytes"],
            "flags": flags,
            "files": sorted(observed["paths"], key=lambda x: (x["source"], x["path"])),
            "calendar_evidence": ({
                "source_id": explicit["source_id"],
                "evidence_uri": explicit["evidence_uri"],
                "raw_evidence_sha256": explicit["raw_evidence_sha256"],
                "published_at": explicit["published_at"],
                "retrieved_at_utc": explicit["retrieved_at_utc"],
                "verified_at_utc": explicit["verified_at_utc"],
                "scope": explicit["scope"],
                "notes": explicit["notes"],
            } if explicit else None),
        })
        day += timedelta(days=1)
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days_in_matrix": len(rows),
        "manifest_files_observed": sum(r["source_file_count"] for r in rows),
        "days_with_source_files": sum(bool(r["source_file_count"]) for r in rows),
        "days_with_explicit_calendar_evidence": sum(bool(r["calendar_evidence"]) for r in rows),
        "days_missing_calendar_evidence": sum("calendar_evidence_missing" in r["flags"] for r in rows),
        "rows": rows,
        "interpretation": (
            "File presence is not proof of a valid trading session or complete archive. "
            "Unverified schedule candidates are not promoted to verified sessions. "
            "A source file on a verified closure is flagged for investigation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, help="JSONL source manifest; repeatable")
    parser.add_argument("--calendar", required=True, help="Evidence-backed NEPSE calendar CSV")
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--output", type=Path, default=Path("data/reports/calendar-coverage-matrix.json"))
    args = parser.parse_args()
    report = build_matrix(args.manifest, args.calendar, args.start_date, args.end_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "days_in_matrix", "manifest_files_observed", "days_with_source_files",
        "days_with_explicit_calendar_evidence", "days_missing_calendar_evidence"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
