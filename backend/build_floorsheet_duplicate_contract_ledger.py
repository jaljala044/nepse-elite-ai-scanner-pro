#!/usr/bin/env python3
"""Extract physical rows for duplicate contract IDs without resolving them."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from compare_floorsheet_source_csvs import HEADERS


def duplicate_ledger(manifest_path: str | Path) -> dict[str, Any]:
    manifest_file = Path(manifest_path).resolve()
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("manifest must contain a non-empty pairs array")
    revisions = manifest.get("source_revisions", {})
    source_configs = (
        ("samir", "left_path", "left_format", "left_sha256", revisions.get("samir", {})),
        ("socrateai", "right_path", "right_format", "right_sha256", revisions.get("socrateai", {})),
    )
    entries: list[dict[str, Any]] = []
    per_source_date = []
    for pair in pairs:
        trade_date = pair.get("trade_date")
        if not isinstance(trade_date, str):
            raise ValueError("manifest trade_date must be a string")
        for source_name, path_key, format_key, hash_key, revision in source_configs:
            candidate = (manifest_file.parent / pair[path_key]).resolve()
            try:
                candidate.relative_to(manifest_file.parent)
            except ValueError as exc:
                raise ValueError("manifest source path escapes its directory") from exc
            source_format = pair[format_key]
            if source_format not in HEADERS:
                raise ValueError(f"unsupported source format: {source_format}")
            payload = candidate.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != pair[hash_key]:
                raise ValueError(f"source SHA-256 mismatch: {candidate.name}")

            import io
            text = payload.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text, newline=""))
            if tuple(reader.fieldnames or ()) != HEADERS[source_format]:
                raise ValueError(f"source header mismatch: {candidate.name}")
            counts: Counter[str] = Counter()
            for row in reader:
                cid = (row.get("contract_no") if source_format == "samir" else row.get("transaction")) or ""
                cid = cid.strip()
                if cid:
                    counts[cid] += 1
            duplicate_ids = {cid for cid, count in counts.items() if count > 1}
            captured: dict[str, list[dict[str, str]]] = defaultdict(list)
            reader = csv.DictReader(io.StringIO(text, newline=""))
            for row in reader:
                cid = (row.get("contract_no") if source_format == "samir" else row.get("transaction")) or ""
                cid = cid.strip()
                if cid in duplicate_ids:
                    captured[cid].append({
                        "physical_csv_line_number": reader.line_num,
                        "raw_row": {key: value for key, value in row.items() if key is not None},
                    })
            for cid in sorted(duplicate_ids):
                rows = captured[cid]
                variants = {
                    json.dumps(item["raw_row"], sort_keys=True, separators=(",", ":"))
                    for item in rows
                }
                for occurrence, item in enumerate(rows, start=1):
                    row = item["raw_row"]
                    entries.append({
                        "trade_date": trade_date,
                        "source": source_name,
                        "source_repository": revision.get("repository", source_name),
                        "source_commit": revision.get("commit"),
                        "source_file": candidate.name,
                        "source_sha256": digest,
                        "contract_id": cid,
                        "occurrence_index": occurrence,
                        "occurrence_count": len(rows),
                        "physical_csv_line_number": item["physical_csv_line_number"],
                        "duplicate_rows_identical": len(variants) == 1,
                        "row_variant_count": len(variants),
                        "raw_row": row,
                        "disposition": "unresolved_duplicate_contract_id_no_auto_deduplication",
                    })
            per_source_date.append({
                "trade_date": trade_date,
                "source": source_name,
                "file": candidate.name,
                "sha256": digest,
                "row_count": sum(counts.values()),
                "unique_contract_count": len(counts),
                "duplicate_contract_id_count": len(duplicate_ids),
                "duplicate_physical_row_count": sum(counts[cid] for cid in duplicate_ids),
                "duplicate_extra_row_count": sum(counts[cid] - 1 for cid in duplicate_ids),
            })
    entries.sort(key=lambda item: (
        item["trade_date"], item["source"], item["contract_id"], item["occurrence_index"],
    ))
    duplicate_ids = {
        (item["trade_date"], item["source"], item["contract_id"])
        for item in entries
    }
    return {
        "schema_version": "1.0",
        "source_revisions": revisions,
        "date_count": len(pairs),
        "duplicate_contract_id_count": len(duplicate_ids),
        "duplicate_physical_row_count": len(entries),
        "duplicate_extra_row_count": sum(
            item["occurrence_count"] - 1
            for item in entries
            if item["occurrence_index"] == 1
        ),
        "source_date_summaries": per_source_date,
        "canonical_source_selected": False,
        "training_eligible": False,
        "disposition_policy": "preserve_all_duplicate_physical_rows_for_manual_review",
        "entries": entries,
    }


def write_csv(path: Path, report: dict[str, Any]) -> None:
    fields = (
        "trade_date", "source", "source_repository", "source_commit",
        "source_file", "source_sha256", "contract_id", "occurrence_index",
        "occurrence_count", "physical_csv_line_number", "duplicate_rows_identical", "row_variant_count",
        "raw_row", "disposition",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in report["entries"]:
            row = dict(item)
            row["raw_row"] = json.dumps(row["raw_row"], ensure_ascii=False, separators=(",", ":"))
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--csv-output", required=True, type=Path)
    args = parser.parse_args()
    report = duplicate_ledger(args.manifest)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv(args.csv_output, report)
    print(json.dumps({
        "duplicate_contract_id_count": report["duplicate_contract_id_count"],
        "duplicate_physical_row_count": report["duplicate_physical_row_count"],
        "duplicate_extra_row_count": report["duplicate_extra_row_count"],
        "canonical_source_selected": False,
        "training_eligible": False,
    }, indent=2))


if __name__ == "__main__":
    main()
