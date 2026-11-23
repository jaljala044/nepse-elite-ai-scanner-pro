"""Inventory public Hugging Face NEPSE dataset files and summarize coverage/size.

Inventory-only: this script does not download source data. Full file metadata and hashes
are not required for inventory; file path, size and repository revision are retained.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.hf_dataset_collector import DATASETS, _extract_date, collect_hf_datasets

ROOT = Path(__file__).resolve().parents[1]

def summarize_dataset(key: str, info: dict[str, Any]) -> dict[str, Any]:
    files = info.get("records", [])
    dates = sorted({day for item in files if (day := _extract_date(str(item.get("path", ""))))})
    folder_counts: dict[str, int] = {}
    extension_counts: dict[str, int] = {}
    by_date: dict[str, int] = {}
    dated_files = 0
    unpartitioned = 0
    for item in files:
        path = str(item.get("path", ""))
        folder = path.split("/", 1)[0] if "/" in path else "(root)"
        folder_counts[folder] = folder_counts.get(folder, 0) + 1
        lower = path.lower()
        extension = ".csv.gz" if lower.endswith(".csv.gz") else Path(lower).suffix or "(none)"
        extension_counts[extension] = extension_counts.get(extension, 0) + 1
        day = _extract_date(path)
        if day:
            dated_files += 1
            by_date[day.isoformat()] = by_date.get(day.isoformat(), 0) + 1
        else:
            unpartitioned += 1

    gaps = []
    for previous, current in zip(dates, dates[1:]):
        days = (current - previous).days
        if days > 7:
            gaps.append({"from": previous.isoformat(), "to": current.isoformat(),
                         "calendar_days_apart": days,
                         "note": "Review only; calendar gaps are not automatically missing trading sessions."})
    gaps.sort(key=lambda item: item["calendar_days_apart"], reverse=True)

    largest = sorted(files, key=lambda item: int(item.get("size") or 0), reverse=True)[:10]
    total_bytes = sum(int(item.get("size") or 0) for item in files)
    return {
        "dataset_key": key,
        "repo": info.get("repo"),
        "revision": info.get("revision"),
        "files_found": len(files),
        "estimated_total_bytes": total_bytes,
        "estimated_total_mib": round(total_bytes / (1024 * 1024), 3),
        "dated_files": dated_files,
        "unpartitioned_files": unpartitioned,
        "unique_path_dates": len(dates),
        "first_path_date": dates[0].isoformat() if dates else None,
        "last_path_date": dates[-1].isoformat() if dates else None,
        "files_per_folder": dict(sorted(folder_counts.items())),
        "files_by_extension": dict(sorted(extension_counts.items())),
        "largest_calendar_gaps_over_7_days": gaps[:20],
        "largest_files": [
            {"path": item.get("path"), "bytes": int(item.get("size") or 0),
             "oid": item.get("oid")}
            for item in largest
        ],
        "publisher_notes": info.get("notes"),
    }

def summarize_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    datasets = {
        key: summarize_dataset(key, info)
        for key, info in inventory.get("datasets", {}).items()
    }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "inventory_only_no_bulk_download",
        "dataset_count": len(datasets),
        "datasets": datasets,
        "limitations": [
            "Path dates and file sizes describe the public repository inventory, not row-level coverage.",
            "Calendar gaps are review flags only; exchange holidays and historical trading-week changes matter.",
            "File inventory does not validate row schemas, completeness, corporate-action adjustments or licensing.",
            "The same source may publish multiple tables with distinct source provenance; do not merge them automatically."
        ],
        "source_inventory_manifest": inventory.get("manifest_path"),
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory all or selected public NEPSE Hugging Face datasets")
    parser.add_argument("--dataset", action="append", choices=sorted(DATASETS),
                        help="Repeat to select datasets; defaults to all registered Hugging Face datasets")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "reports" / "hf-dataset-inventory-summary.json")
    args = parser.parse_args()
    inventory = collect_hf_datasets(args.dataset, download=False)
    summary = summarize_inventory(inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
