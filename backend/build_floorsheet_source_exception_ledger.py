#!/usr/bin/env python3
"""Build a hash-linked, review-only ledger of cross-source floorsheet exceptions."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

CSV_FIELDS = (
    "trade_date", "exception_type", "source_repository", "source_commit",
    "source_file", "source_sha256", "other_source_repository", "other_source_commit",
    "other_source_file", "other_source_sha256", "contract_id", "symbol", "buyer",
    "seller", "quantity", "rate", "amount", "different_fields", "left_record",
    "right_record", "disposition",
)


def build_ledger(report_path: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    report_file, manifest_file = Path(report_path), Path(manifest_path)
    report = json.loads(report_file.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(report.get("results"), list) or not isinstance(manifest.get("pairs"), list):
        raise ValueError("report and manifest must contain results and pairs arrays")

    pairs = {item.get("trade_date"): item for item in manifest["pairs"] if isinstance(item, dict)}
    if len(pairs) != len(manifest["pairs"]):
        raise ValueError("manifest contains invalid or duplicate date pairs")
    if set(pairs) != {item.get("trade_date") for item in report["results"]}:
        raise ValueError("report dates do not exactly match manifest dates")

    revisions = manifest.get("source_revisions", {})
    left_revision = revisions.get("samir", {})
    right_revision = revisions.get("socrateai", {})
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add(record: dict[str, Any]) -> None:
        key = (
            record["trade_date"], record["exception_type"],
            record["source_repository"], record["contract_id"],
        )
        if key in seen:
            raise ValueError(f"duplicate exception ledger identity: {key}")
        seen.add(key)
        entries.append(record)

    for date_result in report["results"]:
        trade_date = date_result.get("trade_date")
        pair = pairs[trade_date]
        comparison = date_result.get("comparison", {})
        left = comparison.get("left_source", {})
        right = comparison.get("right_source", {})
        expected = (
            pair.get("left_sha256"), pair.get("right_sha256")
        )
        observed = (left.get("sha256"), right.get("sha256"))
        if expected != observed:
            raise ValueError(f"source hash linkage mismatch for {trade_date}")
        detail = comparison.get("comparison", {})
        left_only = detail.get("left_only_contracts", [])
        right_only = detail.get("right_only_contracts", [])
        conflicts = detail.get("conflicts", [])

        for side, rows, source, other, source_revision, other_revision, source_key, other_key in (
            ("left", left_only, left, right, left_revision, right_revision, "samir", "socrateai"),
            ("right", right_only, right, left, right_revision, left_revision, "socrateai", "samir"),
        ):
            for row in rows:
                add({
                    "trade_date": trade_date,
                    "exception_type": f"{side}_source_only",
                    "source_repository": source_revision.get("repository", source_key),
                    "source_commit": source_revision.get("commit"),
                    "source_file": source.get("source_path"),
                    "source_sha256": source.get("sha256"),
                    "other_source_repository": other_revision.get("repository", other_key),
                    "other_source_commit": other_revision.get("commit"),
                    "other_source_file": other.get("source_path"),
                    "other_source_sha256": other.get("sha256"),
                    "contract_id": row.get("contract_id"),
                    "symbol": row.get("symbol"),
                    "buyer": row.get("buyer"),
                    "seller": row.get("seller"),
                    "quantity": row.get("quantity"),
                    "rate": row.get("rate"),
                    "amount": row.get("amount"),
                    "different_fields": [],
                    "left_record": row if side == "left" else None,
                    "right_record": row if side == "right" else None,
                    "disposition": "unresolved_source_only_no_auto_selection",
                })

        for conflict in conflicts:
            cid = conflict.get("contract_id")
            add({
                "trade_date": trade_date,
                "exception_type": "shared_contract_field_conflict",
                "source_repository": left_revision.get("repository", "samir"),
                "source_commit": left_revision.get("commit"),
                "source_file": left.get("source_path"),
                "source_sha256": left.get("sha256"),
                "other_source_repository": right_revision.get("repository", "socrateai"),
                "other_source_commit": right_revision.get("commit"),
                "other_source_file": right.get("source_path"),
                "other_source_sha256": right.get("sha256"),
                "contract_id": cid,
                "symbol": conflict.get("left", {}).get("symbol"),
                "buyer": None, "seller": None, "quantity": None, "rate": None, "amount": None,
                "different_fields": conflict.get("different_fields", []),
                "left_record": conflict.get("left"),
                "right_record": conflict.get("right"),
                "disposition": "unresolved_shared_field_conflict_no_auto_selection",
            })

    entries.sort(key=lambda item: (
        item["trade_date"], item["exception_type"], item["contract_id"],
    ))
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["exception_type"]] = counts.get(entry["exception_type"], 0) + 1
    return {
        "schema_version": "1.0",
        "source_revisions": revisions,
        "date_count": len(report["results"]),
        "exception_count": len(entries),
        "exception_counts_by_type": counts,
        "canonical_source_selected": False,
        "training_eligible": False,
        "disposition_policy": "all_cross_source_exceptions_remain_unresolved",
        "entries": entries,
    }


def write_csv(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for entry in ledger["entries"]:
            row = dict(entry)
            row["different_fields"] = json.dumps(row.get("different_fields", []), separators=(",", ":"))
            row["left_record"] = json.dumps(row.get("left_record"), ensure_ascii=False, separators=(",", ":"))
            row["right_record"] = json.dumps(row.get("right_record"), ensure_ascii=False, separators=(",", ":"))
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    args = parser.parse_args()
    ledger = build_ledger(args.report, args.manifest)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    args.json_output.write_text(payload, encoding="utf-8")
    write_csv(args.csv_output, ledger)
    print(json.dumps({
        "date_count": ledger["date_count"],
        "exception_count": ledger["exception_count"],
        "exception_counts_by_type": ledger["exception_counts_by_type"],
        "json_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "canonical_source_selected": False,
        "training_eligible": False,
    }, indent=2))


if __name__ == "__main__":
    main()
