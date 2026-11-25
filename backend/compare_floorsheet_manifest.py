#!/usr/bin/env python3
"""Run reproducible contract-level comparisons for a manifest of dated CSV pairs."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from compare_floorsheet_source_csvs import HEADERS, compare_sources


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_file(base: Path, item: dict[str, Any], side: str) -> tuple[Path, str]:
    path_key = f"{side}_path"
    format_key = f"{side}_format"
    hash_key = f"{side}_sha256"
    relative = item.get(path_key)
    source_format = item.get(format_key)
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError(f"{path_key} must be a non-empty relative path")
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"{path_key} must stay inside the manifest directory") from exc
    if not candidate.is_file():
        raise ValueError(f"{path_key} does not exist: {relative}")
    if source_format not in HEADERS:
        raise ValueError(f"{format_key} must be one of {sorted(HEADERS)}")
    expected_hash = item.get(hash_key)
    actual_hash = _sha256(candidate)
    if expected_hash is not None:
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ValueError(f"{hash_key} must be a 64-character SHA-256 hex digest")
        if any(char not in "0123456789abcdefABCDEF" for char in expected_hash):
            raise ValueError(f"{hash_key} must be hexadecimal")
        if actual_hash.lower() != expected_hash.lower():
            raise ValueError(f"{hash_key} mismatch for {relative}")
    return candidate, source_format


def compare_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("pairs"), list):
        raise ValueError("manifest must be an object containing a pairs array")
    if not payload["pairs"]:
        raise ValueError("manifest pairs array must not be empty")

    seen_dates: set[str] = set()
    results = []
    for index, item in enumerate(payload["pairs"]):
        if not isinstance(item, dict):
            raise ValueError(f"pairs[{index}] must be an object")
        trade_date = item.get("trade_date")
        if not isinstance(trade_date, str):
            raise ValueError(f"pairs[{index}].trade_date must be YYYY-MM-DD")
        try:
            if date.fromisoformat(trade_date).isoformat() != trade_date:
                raise ValueError
        except ValueError as exc:
            raise ValueError(f"pairs[{index}].trade_date must be a real YYYY-MM-DD date") from exc
        if trade_date in seen_dates:
            raise ValueError(f"duplicate trade_date in manifest: {trade_date}")
        seen_dates.add(trade_date)

        left, left_format = _resolve_file(manifest_file.parent, item, "left")
        right, right_format = _resolve_file(manifest_file.parent, item, "right")
        control = item.get("independent_control")
        if control is not None:
            if not isinstance(control, dict) or control.get("trade_date") != trade_date:
                raise ValueError(f"pairs[{index}].independent_control trade_date must match pair date")
        comparison = compare_sources(
            left, right,
            left_format=left_format,
            right_format=right_format,
            independent_control=control,
        )
        results.append({
            "trade_date": trade_date,
            "left_file": left.name,
            "left_sha256": _sha256(left),
            "right_file": right.name,
            "right_sha256": _sha256(right),
            "comparison": comparison,
        })

    exact_dates = sum(
        result["comparison"]["comparison"]["status"] == "exact_contract_set_and_row_match"
        for result in results
    )
    conflict_dates = sum(
        result["comparison"]["comparison"]["conflicting_shared_contract_count"] > 0
        for result in results
    )
    control_failures = sum(
        1 for result in results
        if result["comparison"]["independent_control"] is not None
        and any(
            side["status"] != "passed"
            for side in result["comparison"]["independent_control"].values()
        )
    )
    return {
        "schema_version": "1.0",
        "manifest_file": manifest_file.name,
        "date_count": len(results),
        "exact_contract_set_and_row_match_dates": exact_dates,
        "dates_with_contract_set_or_row_differences": len(results) - exact_dates,
        "dates_with_shared_contract_conflicts": conflict_dates,
        "dates_with_independent_control_failures": control_failures,
        "readiness_status": (
            "review_required"
            if exact_dates != len(results) or conflict_dates or control_failures
            else "review_only_exact_comparison_no_canonical_promotion"
        ),
        "canonical_source_selected": False,
        "training_eligible": False,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = compare_manifest(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "date_count": report["date_count"],
        "exact_dates": report["exact_contract_set_and_row_match_dates"],
        "difference_dates": report["dates_with_contract_set_or_row_differences"],
        "readiness_status": report["readiness_status"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
