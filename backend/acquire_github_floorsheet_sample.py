#!/usr/bin/env python3
"""Acquire one pinned GitHub floorsheet CSV with Git-blob and SHA-256 verification."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


def select_sample(rows: list[dict[str, Any]], sample_date: str, max_total_bytes: int) -> list[dict[str, Any]]:
    try:
        date.fromisoformat(sample_date)
    except ValueError as exc:
        raise ValueError(f"invalid sample date: {sample_date}") from exc
    if max_total_bytes <= 0:
        raise ValueError("max_total_bytes must be positive")
    selected = [row for row in rows if row.get("date") == sample_date]
    if len(selected) != 1:
        raise ValueError(f"expected exactly one dated file for {sample_date}; found {len(selected)}")
    total = sum(int(row["size_bytes"]) for row in selected)
    if total > max_total_bytes:
        raise ValueError(f"sample size {total} exceeds max_total_bytes {max_total_bytes}")
    if not selected[0].get("git_blob_sha1"):
        raise ValueError("sample file has no Git blob SHA-1")
    return selected


def acquire_sample(
    *,
    owner: str,
    repo: str,
    revision: str,
    prefix: str,
    sample_date: str,
    raw_root: str | Path,
    max_total_bytes: int,
    confirm_data_rights: bool,
    output: str | Path,
) -> dict[str, Any]:
    if not confirm_data_rights:
        raise ValueError("explicit rights-review confirmation is required")
    from acquire_floorsheet_archive import download_one, enumerate_files
    commit_sha, rows = enumerate_files(owner, repo, revision, prefix)
    if revision not in {"main", "master"} and commit_sha != revision:
        raise ValueError(f"GitHub resolved revision {revision} to unexpected commit {commit_sha}")
    selected = select_sample(rows, sample_date, max_total_bytes)
    acquired = [download_one(dict(row), Path(raw_root)) for row in selected]
    report = {
        "repository": f"{owner}/{repo}",
        "resolved_commit_sha": commit_sha,
        "prefix": prefix,
        "sample_date": sample_date,
        "enumerated_archive_files": len(rows),
        "selected_file_count": len(acquired),
        "max_total_bytes": max_total_bytes,
        "acquired_files": acquired,
        "rights_review": {
            "repository_license": "MIT",
            "upstream_data_rights_independently_verified": False,
            "user_requested_source": True,
            "raw_data_redistributed": False,
            "limitations": [
                "Repository MIT license is not treated as independent proof of upstream exchange-data rights.",
                "This is a one-date private technical comparison sample, not canonical promotion or proof of archive completeness.",
                "Preserve source rows and all differences; never auto-merge conflicting transactions.",
            ],
        },
    }
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--revision", required=True, help="Pinned Git commit SHA")
    parser.add_argument("--prefix", default="floorsheet")
    parser.add_argument("--date", required=True, dest="sample_date")
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw/floorsheet"))
    parser.add_argument("--max-total-bytes", type=int, required=True)
    parser.add_argument("--confirm-data-rights", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("data/reports/github-floorsheet-sample.json"))
    args = parser.parse_args()
    report = acquire_sample(
        owner=args.owner,
        repo=args.repo,
        revision=args.revision,
        prefix=args.prefix,
        sample_date=args.sample_date,
        raw_root=args.raw_root,
        max_total_bytes=args.max_total_bytes,
        confirm_data_rights=args.confirm_data_rights,
        output=args.output,
    )
    print(json.dumps({
        "repository": report["repository"],
        "resolved_commit_sha": report["resolved_commit_sha"],
        "sample_date": report["sample_date"],
        "selected_file_count": report["selected_file_count"],
        "downloaded_bytes": sum(x["downloaded_bytes"] for x in report["acquired_files"]),
        "verification": [x["verification"] for x in report["acquired_files"]],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
