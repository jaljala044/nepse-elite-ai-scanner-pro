#!/usr/bin/env python3
"""Measure broker-code presence and activity without inferring broker identities."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from compare_floorsheet_source_csvs import HEADERS


def _load_counts(path: Path, source_format: str, expected_hash: str, trade_date: str) -> dict[str, Any]:
    payload = path.read_bytes()
    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"source SHA-256 mismatch: {path.name}")
    if source_format not in HEADERS:
        raise ValueError(f"unsupported source format: {source_format}")
    import io
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
    if tuple(reader.fieldnames or ()) != HEADERS[source_format]:
        raise ValueError(f"source header mismatch: {path.name}")
    buyer_counts: Counter[str] = Counter()
    seller_counts: Counter[str] = Counter()
    row_count = 0
    for row in reader:
        row_count += 1
        if None in row or any(row.get(key) is None for key in HEADERS[source_format]):
            raise ValueError(f"malformed CSV row in {path.name} at data row {row_count}")
        date_value = (row.get("date") or "").strip()
        buyer = (row.get("buyer") or "").strip()
        seller = (row.get("seller") or "").strip()
        if date_value != trade_date:
            raise ValueError(f"source trade date mismatch in {path.name}: {date_value!r}")
        if not buyer or not seller:
            raise ValueError(f"blank broker code in {path.name} at data row {row_count}")
        buyer_counts[buyer] += 1
        seller_counts[seller] += 1
    codes = set(buyer_counts) | set(seller_counts)
    return {
        "file": path.name,
        "sha256": actual_hash,
        "row_count": row_count,
        "buyer_code_count": len(buyer_counts),
        "seller_code_count": len(seller_counts),
        "unique_code_count": len(codes),
        "buyer_counts": dict(sorted(buyer_counts.items())),
        "seller_counts": dict(sorted(seller_counts.items())),
        "code_union": sorted(codes),
    }


def analyze_broker_coverage(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("manifest must contain a non-empty pairs array")
    seen_dates: set[str] = set()
    results = []
    all_codes = {"samir": set(), "socrateai": set()}
    for item in pairs:
        trade_date = item.get("trade_date")
        if not isinstance(trade_date, str) or trade_date in seen_dates:
            raise ValueError(f"invalid or duplicate manifest date: {trade_date!r}")
        seen_dates.add(trade_date)
        source_results = {}
        for side, format_key, path_key, hash_key, source_key in (
            ("samir", "left_format", "left_path", "left_sha256", "samir"),
            ("socrateai", "right_format", "right_path", "right_sha256", "socrateai"),
        ):
            candidate = (manifest_file.parent / item[path_key]).resolve()
            try:
                candidate.relative_to(manifest_file.parent)
            except ValueError as exc:
                raise ValueError("manifest source path escapes its directory") from exc
            source_results[side] = _load_counts(
                candidate, item[format_key], item[hash_key], trade_date,
            )
            all_codes[source_key].update(source_results[side]["code_union"])
        left_codes = set(source_results["samir"]["code_union"])
        right_codes = set(source_results["socrateai"]["code_union"])
        results.append({
            "trade_date": trade_date,
            "samir": source_results["samir"],
            "socrateai": source_results["socrateai"],
            "shared_codes": sorted(left_codes & right_codes),
            "samir_only_codes": sorted(left_codes - right_codes),
            "socrateai_only_codes": sorted(right_codes - left_codes),
            "code_set_exact_match": left_codes == right_codes,
        })
    return {
        "schema_version": "1.0",
        "date_count": len(results),
        "samir_distinct_codes_across_window": sorted(all_codes["samir"]),
        "socrateai_distinct_codes_across_window": sorted(all_codes["socrateai"]),
        "shared_distinct_codes_across_window": sorted(all_codes["samir"] & all_codes["socrateai"]),
        "samir_only_distinct_codes_across_window": sorted(all_codes["samir"] - all_codes["socrateai"]),
        "socrateai_only_distinct_codes_across_window": sorted(all_codes["socrateai"] - all_codes["samir"]),
        "broker_legal_identity_verified": False,
        "policy": "raw_broker_code_coverage_only_no_legal_identity_inference",
        "results": results,
    }


def write_activity_csv(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ("trade_date", "source", "side", "broker_code", "contract_side_observations")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for day in report["results"]:
            for source in ("samir", "socrateai"):
                for side in ("buyer", "seller"):
                    counts = day[source][f"{side}_counts"]
                    for code, count in sorted(counts.items()):
                        writer.writerow({
                            "trade_date": day["trade_date"], "source": source,
                            "side": side, "broker_code": code,
                            "contract_side_observations": count,
                        })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    args = parser.parse_args()
    report = analyze_broker_coverage(args.manifest)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_activity_csv(args.csv_output, report)
    print(json.dumps({
        "date_count": report["date_count"],
        "samir_distinct_codes": len(report["samir_distinct_codes_across_window"]),
        "socrateai_distinct_codes": len(report["socrateai_distinct_codes_across_window"]),
        "shared_codes": len(report["shared_distinct_codes_across_window"]),
        "broker_legal_identity_verified": False,
    }, indent=2))


if __name__ == "__main__":
    main()
