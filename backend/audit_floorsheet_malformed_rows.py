#!/usr/bin/env python3
"""Extract malformed and formula-mismatch floorsheet rows with physical provenance."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from compare_floorsheet_source_csvs import HEADERS


def inspect_manifest(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("manifest must contain a non-empty pairs array")
    revisions = manifest.get("source_revisions", {})
    entries: list[dict[str, Any]] = []
    summaries = []
    reason_counts: Counter[str] = Counter()

    for pair in pairs:
        trade_date = pair.get("trade_date")
        for source_name, path_key, format_key, hash_key, revision_key in (
            ("samir", "left_path", "left_format", "left_sha256", "samir"),
            ("socrateai", "right_path", "right_format", "right_sha256", "socrateai"),
        ):
            path = (manifest_file.parent / pair[path_key]).resolve()
            try:
                path.relative_to(manifest_file.parent)
            except ValueError as exc:
                raise ValueError("manifest source path escapes its directory") from exc
            source_format = pair[format_key]
            if source_format not in HEADERS:
                raise ValueError(f"unsupported source format: {source_format}")
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != pair[hash_key]:
                raise ValueError(f"source SHA-256 mismatch: {path.name}")
            import io
            reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig"), newline=""))
            if tuple(reader.fieldnames or ()) != HEADERS[source_format]:
                raise ValueError(f"source header mismatch: {path.name}")
            row_count = 0
            malformed_count = 0
            formula_count = 0
            for row in reader:
                row_count += 1
                line_number = reader.line_num
                reasons: list[str] = []
                if None in row:
                    reasons.append("extra_columns")
                if any(row.get(header) is None for header in HEADERS[source_format]):
                    reasons.append("missing_columns")
                raw = {
                    (key if key is not None else "__extra_fields__"): (value or "").strip()
                    for key, value in row.items()
                }
                blank_fields = [key for key, value in raw.items() if value == ""]
                if blank_fields:
                    reasons.append("blank_fields:" + ",".join(blank_fields))
                canonical_date = raw.get("date", "")
                try:
                    date.fromisoformat(canonical_date)
                except ValueError:
                    reasons.append("invalid_trade_date")
                contract_id = raw.get("contract_no") if source_format == "samir" else raw.get("transaction")
                if not contract_id:
                    reasons.append("blank_contract_id")
                numeric = {}
                for field in ("quantity", "rate", "amount"):
                    try:
                        value = Decimal(raw.get(field, "").replace(",", "").strip())
                        if not value.is_finite() or value <= 0:
                            raise ValueError
                        numeric[field] = value
                    except (InvalidOperation, TypeError, ValueError):
                        reasons.append("invalid_" + field)
                if "quantity" in numeric and numeric["quantity"] != numeric["quantity"].to_integral_value():
                    reasons.append("fractional_quantity")
                if reasons:
                    malformed_count += 1
                    for reason in reasons:
                        reason_counts[reason] += 1
                    entries.append({
                        "trade_date": trade_date,
                        "source": source_name,
                        "source_repository": revisions.get(revision_key, {}).get("repository", source_name),
                        "source_commit": revisions.get(revision_key, {}).get("commit"),
                        "source_file": path.name,
                        "source_sha256": digest,
                        "physical_csv_line_number": line_number,
                        "exception_type": "malformed_row",
                        "reasons": reasons,
                        "raw_row": raw,
                        "disposition": "unresolved_malformed_source_row_no_auto_repair",
                    })
                elif all(field in numeric for field in ("quantity", "rate", "amount")):
                    if numeric["quantity"] * numeric["rate"] != numeric["amount"]:
                        formula_count += 1
                        entries.append({
                            "trade_date": trade_date,
                            "source": source_name,
                            "source_repository": revisions.get(revision_key, {}).get("repository", source_name),
                            "source_commit": revisions.get(revision_key, {}).get("commit"),
                            "source_file": path.name,
                            "source_sha256": digest,
                            "physical_csv_line_number": line_number,
                            "exception_type": "quantity_rate_amount_formula_mismatch",
                            "reasons": ["quantity_times_rate_does_not_equal_amount"],
                            "raw_row": raw,
                            "disposition": "unresolved_formula_mismatch_no_auto_repair",
                        })
            summaries.append({
                "trade_date": trade_date,
                "source": source_name,
                "file": path.name,
                "sha256": digest,
                "row_count": row_count,
                "malformed_row_count": malformed_count,
                "formula_mismatch_count": formula_count,
            })
    return {
        "schema_version": "1.0",
        "date_count": len(pairs),
        "exception_count": len(entries),
        "malformed_row_count": sum(x["exception_type"] == "malformed_row" for x in entries),
        "formula_mismatch_count": sum(x["exception_type"] == "quantity_rate_amount_formula_mismatch" for x in entries),
        "reason_counts": dict(sorted(reason_counts.items())),
        "source_date_summaries": summaries,
        "canonical_source_selected": False,
        "training_eligible": False,
        "entries": entries,
    }


def write_csv(path: Path, report: dict[str, Any]) -> None:
    fields = (
        "trade_date", "source", "source_repository", "source_commit", "source_file",
        "source_sha256", "physical_csv_line_number", "exception_type", "reasons",
        "raw_row", "disposition",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for entry in report["entries"]:
            row = dict(entry)
            row["reasons"] = json.dumps(row["reasons"], separators=(",", ":"))
            row["raw_row"] = json.dumps(row["raw_row"], ensure_ascii=False, separators=(",", ":"))
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    args = parser.parse_args()
    report = inspect_manifest(args.manifest)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(args.csv_output, report)
    print(json.dumps({
        "exception_count": report["exception_count"],
        "malformed_row_count": report["malformed_row_count"],
        "formula_mismatch_count": report["formula_mismatch_count"],
        "reason_counts": report["reason_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
