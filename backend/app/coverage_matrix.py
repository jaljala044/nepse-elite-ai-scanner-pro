"""Build a conservative, source-separated NEPSE historical file coverage report.

This module never infers exchange sessions from weekdays or filenames. A dated
source file is evidence of a file, not proof that the date was a trading session.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


CALENDAR_STATUSES = {
    "confirmed_session", "confirmed_non_session",
    "candidate_unverified", "conflict",
}


def path_date(path: str) -> str | None:
    match = re.search(r"(?<!\d)((?:19|20)\d{2}[-_]\d{2}[-_]\d{2})(?!\d)", path)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1).replace("_", "-")).isoformat()
    except ValueError:
        return None


def load_calendar(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for line_no, item in enumerate(csv.DictReader(handle), start=2):
            raw_date = (item.get("session_date") or "").strip()
            raw_status = (item.get("calendar_status") or "").strip()
            try:
                normalized = date.fromisoformat(raw_date).isoformat()
            except ValueError as exc:
                raise ValueError(f"Invalid session_date at {path}:{line_no}: {raw_date!r}") from exc
            if raw_status not in CALENDAR_STATUSES:
                raise ValueError(f"Invalid calendar_status at {path}:{line_no}: {raw_status!r}")
            if normalized in rows:
                raise ValueError(f"Duplicate calendar date at {path}:{line_no}: {normalized}")
            rows[normalized] = {
                "calendar_status": raw_status,
                "evidence_source": (item.get("evidence_source") or "").strip(),
                "evidence_ref": (item.get("evidence_ref") or "").strip(),
                "decision_reason": (item.get("decision_reason") or "").strip(),
            }
    return rows


def _manifest_sources(payload: dict[str, Any], source_label: str) -> list[dict[str, Any]]:
    """Normalize supported HF collector and GitHub tree inventory shapes."""
    datasets = payload.get("datasets")
    if isinstance(datasets, dict):
        result = []
        for dataset_key, dataset in datasets.items():
            if not isinstance(dataset, dict):
                continue
            result.append({
                "source": dataset.get("repo") or source_label,
                "dataset": dataset_key,
                "revision": dataset.get("revision"),
                "listing_complete": dataset.get("listing_complete"),
                "inventory_complete": dataset.get("inventory_complete"),
                "files_found": dataset.get("files_found"),
                "files_considered": dataset.get("files_considered"),
                "files": dataset.get("records", []),
            })
        return result

    repos = payload.get("repositories")
    if isinstance(repos, list):
        result = []
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            result.append({
                "source": repo.get("repository") or source_label,
                "dataset": "github_repository",
                "revision": repo.get("commit_sha"),
                "listing_complete": not bool(repo.get("truncated", False)),
                "files": repo.get("files", []),
            })
        return result

    raise ValueError("Unsupported manifest: expected 'datasets' or 'repositories'")


def build_coverage(calendar: dict[str, dict[str, str]], manifest_paths: list[Path]) -> dict[str, Any]:
    matrix: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    undated: list[dict[str, Any]] = []

    for manifest_path in manifest_paths:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for source_info in _manifest_sources(payload, manifest_path.stem):
            source = str(source_info["source"])
            dataset = str(source_info["dataset"])
            revision = source_info.get("revision")
            files = source_info.get("files") or []
            counts: Counter[str] = Counter()

            for item in files:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path") or "")
                if not path:
                    continue
                day = path_date(path)
                if day is None:
                    undated.append({
                        "source": source, "dataset": dataset,
                        "revision": revision, "path": path,
                    })
                    counts["undated_files"] += 1
                    continue

                calendar_row = calendar.get(day)
                calendar_status = (
                    calendar_row["calendar_status"] if calendar_row
                    else "candidate_unverified"
                )
                if calendar_status == "confirmed_session":
                    assessment = "file_present_on_confirmed_session"
                elif calendar_status == "confirmed_non_session":
                    assessment = "file_on_confirmed_non_session_review"
                elif calendar_status == "conflict":
                    assessment = "calendar_conflict_review"
                else:
                    assessment = "date_unverified"

                matrix.append({
                    "source": source,
                    "dataset": dataset,
                    "revision": revision,
                    "date": day,
                    "path": path,
                    "file_sha_or_oid": item.get("sha") or item.get("oid"),
                    "lfs_sha256": (item.get("lfs") or {}).get("oid")
                        if isinstance(item.get("lfs"), dict) else None,
                    "size_bytes": item.get("size"),
                    "calendar_status": calendar_status,
                    "calendar_evidence_source": calendar_row.get("evidence_source")
                        if calendar_row else None,
                    "calendar_evidence_ref": calendar_row.get("evidence_ref")
                        if calendar_row else None,
                    "assessment": assessment,
                })
                counts[assessment] += 1

            source_summaries.append({
                "source": source,
                "dataset": dataset,
                "revision": revision,
                "file_count_in_manifest": len(files),
                "listing_complete": source_info.get("listing_complete"),
                "inventory_complete": source_info.get("inventory_complete"),
                "files_found": source_info.get("files_found"),
                "files_considered": source_info.get("files_considered"),
                "dated_file_count": sum(counts.values()),
                **dict(sorted(counts.items())),
            })

    matrix.sort(key=lambda row: (
        row["source"], row["dataset"], row["date"], row["path"]
    ))
    confirmed_sessions = sum(
        1 for item in calendar.values()
        if item["calendar_status"] == "confirmed_session"
    )
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_type": "source_separated_file_level_coverage",
        "calendar_date_count": len(calendar),
        "confirmed_session_count": confirmed_sessions,
        "calendar_status_counts": dict(Counter(
            item["calendar_status"] for item in calendar.values()
        )),
        "source_summaries": source_summaries,
        "dated_file_matrix": matrix,
        "undated_files": undated,
        "limitations": [
            "A file dated on a confirmed session is not proof that its rows are complete or valid.",
            "A missing dated file is not classified as a missing exchange session by this report.",
            "Unlisted dates remain candidate_unverified; weekdays are never used to infer sessions.",
            "This report is file-level only; symbol-level and row-level coverage require normalized audit outputs.",
            "Rights status must be reviewed separately before data is promoted or redistributed.",
        ],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", required=True, type=Path,
                        help="Evidence-backed calendar CSV")
    parser.add_argument("--manifest", required=True, action="append", type=Path,
                        help="Source manifest JSON; repeat for multiple sources")
    parser.add_argument("--output", default="data/reports/historical-coverage-matrix.json", type=Path)
    args = parser.parse_args()

    calendar = load_calendar(args.calendar)
    report = build_coverage(calendar, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "calendar_dates": report["calendar_date_count"],
        "confirmed_sessions": report["confirmed_session_count"],
        "source_datasets": len(report["source_summaries"]),
        "dated_file_rows": len(report["dated_file_matrix"]),
        "undated_files": len(report["undated_files"]),
    }, indent=2))


if __name__ == "__main__":
    main()
