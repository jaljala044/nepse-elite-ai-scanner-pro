#!/usr/bin/env python3
"""Reconcile source-specific daily OHLCV counts/totals and cross-source rows."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

REQUIRED = {"source_id", "symbol", "date", "open", "high", "low", "close", "volume"}


def _read_rows(paths: list[str | Path]) -> list[dict]:
    rows = []
    for source_path in paths:
        with Path(source_path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = REQUIRED - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{source_path}: missing columns: " + ", ".join(sorted(missing)))
            for line, raw in enumerate(reader, 2):
                try:
                    item = {key: (raw.get(key) or "").strip() for key in REQUIRED}
                    item["source_row_number"] = line
                    if not item["source_id"] or not item["symbol"]:
                        raise ValueError("source_id and symbol are required")
                    item["symbol"] = item["symbol"].upper()
                    from datetime import date
                    date.fromisoformat(item["date"])
                    for field in ("open", "high", "low", "close", "volume"):
                        value = Decimal(item[field].replace(",", ""))
                        if not value.is_finite():
                            raise ValueError(f"{field} must be finite")
                        item[field] = value
                    if item["volume"] < 0 or any(item[field] <= 0 for field in ("open","high","low","close")):
                        raise ValueError("prices must be positive and volume non-negative")
                except (InvalidOperation, ValueError) as exc:
                    raise ValueError(f"{source_path}:{line}: {exc}") from exc
                rows.append(item)
    return rows


def reconcile_ohlcv_sources(paths: list[str | Path], control_path: str | Path | None = None) -> dict[str, Any]:
    rows = _read_rows(paths)
    by_source_day = defaultdict(list)
    by_day_symbol = defaultdict(list)
    for row in rows:
        by_source_day[(row["source_id"], row["date"])].append(row)
        by_day_symbol[(row["date"], row["symbol"])].append(row)

    daily = []
    duplicates = []
    for (source_id, day), group in sorted(by_source_day.items()):
        symbols = [row["symbol"] for row in group]
        duplicate_symbols = sorted(symbol for symbol, count in __import__("collections").Counter(symbols).items() if count > 1)
        for symbol in duplicate_symbols:
            duplicates.append({"source_id": source_id, "date": day, "symbol": symbol,
                               "row_count": symbols.count(symbol)})
        daily.append({
            "source_id": source_id, "date": day,
            "row_count": len(group), "unique_symbol_count": len(set(symbols)),
            "total_volume": str(sum((row["volume"] for row in group), Decimal("0"))),
            "duplicate_symbols": duplicate_symbols,
        })

    cross_source = []
    for (day, symbol), group in sorted(by_day_symbol.items()):
        by_source = defaultdict(list)
        for row in group:
            by_source[row["source_id"]].append(row)
        if len(by_source) < 2:
            continue
        source_ids = sorted(by_source)
        if any(len(by_source[source_id]) != 1 for source_id in source_ids):
            classification = "duplicate_within_source"
        else:
            signatures = {
                source_id: tuple(str(by_source[source_id][0][field])
                                 for field in ("open","high","low","close","volume"))
                for source_id in source_ids
            }
            classification = "exact_cross_source_match" if len(set(signatures.values())) == 1 else "cross_source_conflict"
        cross_source.append({
            "date": day, "symbol": symbol, "classification": classification,
            "source_ids": source_ids,
            "source_values": {
                source_id: [
                    {field: str(row[field]) for field in ("open","high","low","close","volume")}
                    for row in by_source[source_id]
                ] for source_id in source_ids
            },
        })

    control_results = []
    if control_path:
        with Path(control_path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"source_id", "date", "row_count", "total_volume"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError("control file missing columns: " + ", ".join(sorted(missing)))
            controls = {}
            for line, row in enumerate(reader, 2):
                key = (row["source_id"].strip(), row["date"].strip())
                if key in controls:
                    raise ValueError(f"control line {line}: duplicate source/date")
                controls[key] = (int(row["row_count"]), Decimal(row["total_volume"]))
        for item in daily:
            key = (item["source_id"], item["date"])
            expected = controls.get(key)
            differences = []
            if expected is None:
                differences.append("missing_control_total")
            else:
                if item["row_count"] != expected[0]:
                    differences.append("row_count")
                if Decimal(item["total_volume"]) != expected[1]:
                    differences.append("total_volume")
            control_results.append({"source_id": key[0], "date": key[1],
                                    "differences": differences,
                                    "status": "passed" if not differences else "failed"})
    return {
        "source_date_count": len(daily),
        "daily_source_totals": daily,
        "duplicate_source_symbol_dates": duplicates,
        "cross_source_comparison_count": len(cross_source),
        "cross_source_comparisons": cross_source,
        "control_total_results": control_results,
        "promotion_allowed": False,
        "policy": "source_specific_totals_and_row_comparisons_no_auto_repair_or_source_selection",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--control-totals", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/reports/ohlcv-source-daily-reconciliation.json"))
    args = parser.parse_args()
    report = reconcile_ohlcv_sources(args.input, args.control_totals)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    print(json.dumps({
        "source_date_count": report["source_date_count"],
        "duplicate_source_symbol_date_count": len(report["duplicate_source_symbol_dates"]),
        "cross_source_comparison_count": report["cross_source_comparison_count"],
        "cross_source_conflict_count": sum(x["classification"] == "cross_source_conflict" for x in report["cross_source_comparisons"]),
        "control_total_failure_count": sum(x["status"] == "failed" for x in report["control_total_results"]),
        "promotion_allowed": report["promotion_allowed"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
