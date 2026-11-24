#!/usr/bin/env python3
"""Acquire all available pinned Urekmazino floorsheets in an observed-date window."""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Any


def load_dates(path: str | Path) -> list[str]:
    dates = []
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
            dates.append(day)
    if not dates:
        raise ValueError("date list is empty")
    if len(dates) != len(set(dates)):
        raise ValueError("date list contains duplicate dates")
    return sorted(dates)


def extract_window_metadata(
    siblings: list[Any],
    repo_id: str,
    commit_sha: str,
    folder: str,
    expected_dates: list[str],
) -> tuple[list[dict[str, Any]], list[str], int]:
    from acquire_hf_floorsheet_sample import extract_sample_metadata
    selected = []
    folder_count = 0
    for day in expected_dates:
        rows, count = extract_sample_metadata(siblings, repo_id, commit_sha, folder, day)
        folder_count = max(folder_count, count)
        if len(rows) > 1:
            raise ValueError(f"multiple Hub files for {day}: {[x['path'] for x in rows]}")
        selected.extend(rows)
    available = {row["date"] for row in selected}
    missing = sorted(set(expected_dates) - available)
    return selected, missing, folder_count


def _download(row: dict[str, Any], raw_root: Path, retries: int) -> dict[str, Any]:
    from acquire_hf_floorsheet_archive import download_one
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
    repo_id: str,
    folder: str,
    revision: str,
    date_list: str | Path,
    raw_root: str | Path,
    max_total_bytes: int,
    workers: int,
    min_available_dates: int,
    allow_missing_dates: bool,
    confirm_data_rights: bool,
    output: str | Path,
) -> dict[str, Any]:
    if not confirm_data_rights:
        raise ValueError("explicit rights-review confirmation is required")
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between 1 and 8")
    if max_total_bytes <= 0:
        raise ValueError("max_total_bytes must be positive")
    expected_dates = load_dates(date_list)
    from huggingface_hub import HfApi
    api = HfApi(token=False)
    info = api.dataset_info(repo_id, revision=revision, files_metadata=True, token=False)
    commit_sha = info.sha
    if revision not in {"main", "master"} and commit_sha != revision:
        raise ValueError(f"Hub resolved revision {revision} to unexpected commit {commit_sha}")
    selected, missing_dates, archive_file_count = extract_window_metadata(
        list(info.siblings or []), repo_id, commit_sha, folder, expected_dates
    )
    if missing_dates and not allow_missing_dates:
        raise ValueError("source is missing candidate dates: " + ", ".join(missing_dates))
    if len(selected) < min_available_dates:
        raise ValueError(f"only {len(selected)} files available; minimum required is {min_available_dates}")
    total_bytes = sum(int(row["size_bytes"]) for row in selected)
    if total_bytes > max_total_bytes:
        raise ValueError(f"selected files total {total_bytes} exceeds max_total_bytes {max_total_bytes}")

    acquired = []
    errors = []
    root = Path(raw_root).resolve()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download, row, root, 3): row for row in selected}
        for future in as_completed(futures):
            row = futures[future]
            try:
                acquired.append(future.result())
            except Exception as exc:
                errors.append({"date": row.get("date"), "path": row.get("path"), "error": f"{type(exc).__name__}: {exc}"})
    acquired.sort(key=lambda item: item["date"])
    repository_root = Path.cwd().resolve()
    for item in acquired:
        local_path = Path(item["local_path"]).resolve()
        item["local_path"] = str(local_path)
        item["repository_path"] = local_path.relative_to(repository_root).as_posix()
    report = {
        "repo_id": repo_id,
        "resolved_commit_sha": commit_sha,
        "folder": folder,
        "date_list_path": str(date_list),
        "expected_date_count": len(expected_dates),
        "archive_file_count_in_folder": archive_file_count,
        "available_date_count": len(selected),
        "missing_date_count": len(missing_dates),
        "missing_dates": missing_dates,
        "acquired_file_count": len(acquired),
        "download_error_count": len(errors),
        "expected_download_bytes": total_bytes,
        "downloaded_bytes": sum(int(row.get("downloaded_bytes", 0)) for row in acquired),
        "max_total_bytes": max_total_bytes,
        "files": acquired,
        "errors": errors,
        "rights_review": {
            "dataset_card_license": "MIT",
            "dataset_card_source_claim": "NEPSE public floorsheet and index data",
            "user_requested_source": True,
            "raw_data_redistributed": False,
            "limitations": [
                "MIT is the dataset card's declared license; upstream source rights are not independently verified.",
                "Missing dates are explicitly reported and are not inferred as exchange closures.",
                "Filename date is not promoted to trade date until row-level date and contract checks pass.",
                "Time values are retained as supplied; null times are never synthesized.",
                "Contract numbers and IDs remain strings.",
            ],
        },
        "status": (
            "complete_for_source_available_dates"
            if not errors and len(acquired) == len(selected) and not missing_dates
            else "partial_source_coverage"
            if not errors and len(acquired) == len(selected)
            else "partial_download_failure"
        ),
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--folder", default="floorsheet")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--date-list", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/huggingface"))
    parser.add_argument("--max-total-bytes", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--min-available-dates", type=int, default=1)
    parser.add_argument("--allow-missing-dates", action="store_true")
    parser.add_argument("--confirm-data-rights", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/reports/urek-floorsheet-window.json"))
    args = parser.parse_args()
    report = acquire_window(
        repo_id=args.repo_id,
        folder=args.folder,
        revision=args.revision,
        date_list=args.date_list,
        raw_root=args.raw_root,
        max_total_bytes=args.max_total_bytes,
        workers=args.workers,
        min_available_dates=args.min_available_dates,
        allow_missing_dates=args.allow_missing_dates,
        confirm_data_rights=args.confirm_data_rights,
        output=args.output,
    )
    print(json.dumps({
        "repo_id": report["repo_id"],
        "resolved_commit_sha": report["resolved_commit_sha"],
        "expected_date_count": report["expected_date_count"],
        "available_date_count": report["available_date_count"],
        "missing_date_count": report["missing_date_count"],
        "acquired_file_count": report["acquired_file_count"],
        "download_error_count": report["download_error_count"],
        "downloaded_bytes": report["downloaded_bytes"],
        "status": report["status"],
    }, indent=2))
    if report["download_error_count"]:
        raise SystemExit(2)
    if report["acquired_file_count"] < args.min_available_dates:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
