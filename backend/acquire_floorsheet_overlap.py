#!/usr/bin/env python3
"""Acquire a bounded, pinned overlap sample from two public floorsheet archives."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SAMIR_REPO = "SamirWagle/Nepse-All-Scraper"
SAMIR_COMMIT = "e6160adc6bdf3d19562167388e3d9d4f645c455a"
SOCRATE_REPO = "socrateai-official/nepse-open-data"
SOCRATE_COMMIT = "cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3"
SAMIR_PATTERN = re.compile(r"^data/floorsheet/floorsheet_(\d{4}-\d{2}-\d{2})\.csv$")
SOCRATE_PATTERN = re.compile(r"^floorsheet/floorsheet_(\d{4}-\d{2}-\d{2})\.csv$")


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "NEPSE-ELITE-AI-audit/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected HTTP status {response.status}: {url}")
        return response.read()


def tree_files(repository: str, commit: str, pattern: re.Pattern[str]) -> dict[str, dict[str, Any]]:
    url = f"https://api.github.com/repos/{repository}/git/trees/{commit}?recursive=1"
    payload = json.loads(fetch(url).decode("utf-8"))
    if payload.get("truncated"):
        raise RuntimeError(f"Git tree response was truncated for {repository}@{commit}")
    files = {}
    for entry in payload.get("tree", []):
        match = pattern.fullmatch(entry.get("path", ""))
        if match and entry.get("type") == "blob":
            try:
                date.fromisoformat(match.group(1))
            except ValueError:
                continue
            files[match.group(1)] = entry
    return files


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--end-date", default="2026-11-25")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 30:
        parser.error("--limit must be between 1 and 30")
    if args.days < 1 or args.days > 366:
        parser.error("--days must be between 1 and 366")
    try:
        end_date = date.fromisoformat(args.end_date)
    except ValueError:
        parser.error("--end-date must be a real YYYY-MM-DD date")

    samir = tree_files(SAMIR_REPO, SAMIR_COMMIT, SAMIR_PATTERN)
    socrate = tree_files(SOCRATE_REPO, SOCRATE_COMMIT, SOCRATE_PATTERN)
    start_date = end_date - timedelta(days=args.days - 1)
    overlap = sorted(
        d for d in set(samir) & set(socrate)
        if start_date <= date.fromisoformat(d) <= end_date
    )[-args.limit:]
    if not overlap:
        raise RuntimeError("no overlapping dated floorsheet files found in requested window")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    pairs = []
    for trade_date in overlap:
        left_entry, right_entry = samir[trade_date], socrate[trade_date]
        left_url = (
            f"https://raw.githubusercontent.com/{SAMIR_REPO}/{SAMIR_COMMIT}/"
            f"{left_entry['path']}"
        )
        right_url = (
            f"https://raw.githubusercontent.com/{SOCRATE_REPO}/{SOCRATE_COMMIT}/"
            f"{right_entry['path']}"
        )
        left_bytes, right_bytes = fetch(left_url), fetch(right_url)
        if git_blob_sha1(left_bytes) != left_entry["sha"]:
            raise RuntimeError(f"Samir Git blob SHA-1 mismatch for {trade_date}")
        if git_blob_sha1(right_bytes) != right_entry["sha"]:
            raise RuntimeError(f"SocrateAI Git blob SHA-1 mismatch for {trade_date}")
        left_name = f"samir-{trade_date}.csv"
        right_name = f"socrate-{trade_date}.csv"
        (args.output_dir / left_name).write_bytes(left_bytes)
        (args.output_dir / right_name).write_bytes(right_bytes)
        pairs.append({
            "trade_date": trade_date,
            "left_path": left_name,
            "left_format": "samir",
            "left_sha256": hashlib.sha256(left_bytes).hexdigest(),
            "right_path": right_name,
            "right_format": "socrate",
            "right_sha256": hashlib.sha256(right_bytes).hexdigest(),
        })

    manifest = {
        "schema_version": "1.0",
        "source_revisions": {
            "samir": {"repository": SAMIR_REPO, "commit": SAMIR_COMMIT},
            "socrateai": {"repository": SOCRATE_REPO, "commit": SOCRATE_COMMIT},
        },
        "date_window": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "selected_dates": overlap,
        "pairs": pairs,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({
        "selected_date_count": len(overlap),
        "first_selected_date": overlap[0],
        "last_selected_date": overlap[-1],
        "manifest": str(args.manifest),
        "raw_csvs_retained_only_in_runner_workspace": True,
    }, indent=2))


if __name__ == "__main__":
    main()
