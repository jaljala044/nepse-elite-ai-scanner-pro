#!/usr/bin/env python3
"""Acquire a pinned date-list window of GitHub-hosted NEPSE floorsheets."""
from __future__ import annotations

import argparse
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any


def load_dates(path: str | Path) -> list[str]:
    values = []
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "date" not in (reader.fieldnames or []):
            raise ValueError("date-list CSV must contain a date column")
        for line, row in enumerate(reader, 2):
            day = str(row.get("date") or "").strip()
            try:
                date.fromisoformat(day)
            except ValueError as exc:
                raise ValueError(f"{path}:{line}: invalid date {day!r}") from exc
            values.append(day)
    if not values:
        raise ValueError("date list is empty")
    if len(values) != len(set(values)):
        raise ValueError("date list contains duplicate dates")
    return sorted(values)


def select_window(rows: list[dict[str, Any]], expected_dates: list[str], max_total_bytes: int) -> list[dict[str, Any]]:
    if max_total_bytes <= 0:
        raise ValueError("max_total_bytes must be positive")
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("date") in set(expected_dates):
            by_date.setdefault(str(row["date"]), []).append(row)
    missing = sorted(set(expected_dates) - set(by_date))
    duplicates = {day: len(items) for day, items in by_date.items() if len(items) != 1}
    if missing:
        raise ValueError("missing source files for dates: " + ", ".join(missing))
    if duplicates:
        raise ValueError("multiple source files for dates: " + json.dumps(duplicates, sort_keys=True))
    selected = [by_date[day][0] for day in expected_dates]
    if any(not row.get("git_blob_sha1") for row in selected):
        raise ValueError("one or more selected files have no Git blob SHA-1")
    total = sum(int(row["size_bytes"]) for row in selected)
    if total > max_total_bytes:
        raise ValueError(f"window size {total} exceeds max_total_bytes {max_total_bytes}")
    return selected


def _download_with_retries(row: dict[str, Any], raw_root: Path, retries: int) -> dict[str, Any]:
    from acquire_floorsheet_archive import download_one
    last_error = None
    for attempt in range(retries + 1):
        try:
            return download_one(dict(row), raw_root)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"{row.get('date')} {row.get('path')}: {last_error}") from last_error


def acquire_window(
    *,
    owner: str,
    repo: str,
    revision: str,
    prefix: str,
    date_list: str | Path,
    raw_root: str | Path,
    max_total_bytes: int,
    workers: int,
    confirm_data_rights: bool,
    output: str | Path,
) -> dict[str, Any]:
    if not confirm_data_rights:
        raise ValueError("explicit rights-review confirmation is required")
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between 1 and 8")
    expected_dates = load_dates(date_list)
    from acquire_floorsheet_archive import enumerate_files
    commit_sha, rows = enumerate_files(owner, repo, revision, prefix)
    if revision not in {"main", "master"} and commit_sha != revision:
        raise ValueError(f"GitHub resolved revision {revision} to unexpected commit {commit_sha}")
    selected = select_window(rows, expected_dates, max_total_bytes)

    acquired = []
    errors = []
    root = Path(raw_root).resolve()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download_with_retries, row, root, 3): row for row in selected}
        for future in as_completed(futures):
            row = futures[future]
            try:
                acquired.append(future.result())
            except Exception as exc:
                errors.append({
                    "date": row.get("date"),
                    "path": row.get("path"),
                    "error": f"{type(exc).__name__}: {exc}",
                })
    acquired.sort(key=lambda item: item["date"])
    repository_root = Path.cwd().resolve()
    for item in acquired:
        local_path = Path(item["local_path"]).resolve()
        item["local_path"] = str(local_path)
        item["repository_path"] = local_path.relative_to(repository_root).as_posix()
    report = {
        "repository": f"{owner}/{repo}",
        "resolved_commit_sha": commit_sha,
        "prefix": prefix,
        "date_list_path": str(date_list),
        "expected_date_count": len(expected_dates),
        "selected_file_count": len(selected),
        "acquired_file_count": len(acquired),
        "download_error_count": len(errors),
        "total_expected_bytes": sum(int(row["size_bytes"]) for row in selected),
        "total_downloaded_bytes": sum(int(row.get("downloaded_bytes", 0)) for row in acquired),
        "max_total_bytes": max_total_bytes,
        "files": acquired,
        "errors": errors,
        "rights_review": {
            "repository_data_license": "MIT; LICENSE explicitly licenses the Data",
            "upstream_data_rights_independently_verified": False,
            "user_requested_source": True,
            "raw_data_redistributed": False,
            "limitations": [
                "Publisher MIT license is recorded as the dataset reuse grant; original upstream collection lineage is not independently verified.",
                "The date list is an observed-index-date candidate set, not a verified NEPSE session calendar.",
                "File date is not accepted as trade date until row-level calculation_date and contract date are checked.",
                "No rows are merged, deduplicated or corrected during acquisition.",
            ],
        },
        "status": "complete" if not errors and len(acquired) == len(selected) else "partial_failure",
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--prefix", default="floorsheet")
    parser.add_argument("--date-list", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/floorsheet"))
    parser.add_argument("--max-total-bytes", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-data-rights", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/reports/floorsheet-window-acquisition.json"))
    args = parser.parse_args()
    report = acquire_window(
        owner=args.owner,
        repo=args.repo,
        revision=args.revision,
        prefix=args.prefix,
        date_list=args.date_list,
        raw_root=args.raw_root,
        max_total_bytes=args.max_total_bytes,
        workers=args.workers,
        confirm_data_rights=args.confirm_data_rights,
        output=args.output,
    )
    print(json.dumps({
        "repository": report["repository"],
        "resolved_commit_sha": report["resolved_commit_sha"],
        "expected_date_count": report["expected_date_count"],
        "acquired_file_count": report["acquired_file_count"],
        "download_error_count": report["download_error_count"],
        "total_downloaded_bytes": report["total_downloaded_bytes"],
        "status": report["status"],
        "output": str(args.output),
    }, indent=2))
    if report["status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
