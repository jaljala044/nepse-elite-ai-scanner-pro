#!/usr/bin/env python3
"""Export a reviewable, explicitly unverified NEPSE session-candidate register."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

FIELDS = [
    "date",
    "candidate_classification",
    "calendar_verified_status",
    "socrateai_index_row_status",
    "socrateai_validation_errors",
    "yonepse_comparison_status",
    "yonepse_finality",
    "yonepse_updated_at",
    "ohlcv_source_count",
    "ohlcv_sources",
    "ohlcv_symbol_counts",
    "floorsheet_source_count",
    "floorsheet_sources",
    "floorsheet_file_counts",
    "socrateai_index_commit",
    "yonepse_commit",
]


def build_candidate_rows(
    market_report: dict[str, Any],
    yonepse_report: dict[str, Any],
) -> list[dict[str, Any]]:
    market_rows = {str(row["date"]): row for row in market_report.get("dates", [])}
    mirror_rows = {str(row["date"]): row for row in yonepse_report.get("dates", [])}
    all_dates = sorted(set(market_rows) | set(mirror_rows))
    result = []
    for day in all_dates:
        market = market_rows.get(day, {})
        mirror = mirror_rows.get(day, {})
        index_row = market.get("index_row") or {}
        comparison = mirror.get("comparison") or {}
        yonepse = comparison.get("yonepse") or {}
        finality = (
            comparison.get("yonepse_finality")
            or yonepse.get("finality_status")
            or "unmarked"
        )
        updated_at = comparison.get("yonepse_updated_at") or yonepse.get("updated_at") or ""
        if finality == "provisional":
            classification = "provisional_latest_not_final"
        elif not index_row:
            classification = "index_file_without_parsed_row"
        elif not index_row.get("nepse_index_row_valid"):
            classification = "observed_candidate_with_socrateai_row_anomaly"
        elif comparison.get("status") == "yonepse_row_missing":
            classification = "observed_candidate_yonepse_row_missing"
        else:
            classification = "observed_session_candidate_unverified"
        ohlcv = market.get("ohlcv_sources") or {}
        floorsheet = market.get("floorsheet_sources_file_count") or {}
        symbol_counts = {
            source: int(details.get("unique_symbols", 0))
            for source, details in ohlcv.items()
        }
        result.append({
            "date": day,
            "candidate_classification": classification,
            "calendar_verified_status": "not_verified_primary_exchange_evidence_missing",
            "socrateai_index_row_status": index_row.get("index_row_status", "missing"),
            "socrateai_validation_errors": ";".join(index_row.get("validation_errors", [])),
            "yonepse_comparison_status": comparison.get("status", "missing"),
            "yonepse_finality": finality,
            "yonepse_updated_at": updated_at,
            "ohlcv_source_count": len(ohlcv),
            "ohlcv_sources": ";".join(sorted(ohlcv)),
            "ohlcv_symbol_counts": json.dumps(symbol_counts, sort_keys=True),
            "floorsheet_source_count": len(floorsheet),
            "floorsheet_sources": ";".join(sorted(floorsheet)),
            "floorsheet_file_counts": json.dumps(floorsheet, sort_keys=True),
            "socrateai_index_commit": market_report.get("index_commit_sha", ""),
            "yonepse_commit": yonepse_report.get("yonepse_commit_sha", ""),
        })
    return result


def write_candidate_csv(
    market_report: dict[str, Any],
    yonepse_report: dict[str, Any],
    output: str | Path,
) -> list[dict[str, Any]]:
    rows = build_candidate_rows(market_report, yonepse_report)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market-report", type=Path, required=True)
    parser.add_argument("--yonepse-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/reports/nepse-session-candidates.csv"))
    args = parser.parse_args()
    rows = write_candidate_csv(
        json.loads(args.market_report.read_text(encoding="utf-8")),
        json.loads(args.yonepse_report.read_text(encoding="utf-8")),
        args.output,
    )
    counts = {}
    for row in rows:
        status = row["candidate_classification"]
        counts[status] = counts.get(status, 0) + 1
    print(json.dumps({
        "output": str(args.output),
        "candidate_dates": len(rows),
        "calendar_verified": 0,
        "classifications": counts,
    }, indent=2))


if __name__ == "__main__":
    main()
