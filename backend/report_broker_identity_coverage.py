#!/usr/bin/env python3
"""Create source-hashed broker identity coverage by date/security/side."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from app.broker_aggregation import aggregate_broker_observations


def build_broker_identity_coverage(path: Path) -> dict:
    raw = path.read_bytes()
    rows = []
    required = {"trade_date","symbol","side","amount","quantity","identity_status",
                "broker_entity_id","source_id","contract_id","source_payload_sha256",
                "source_row_number","identity_evidence_ids"}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("broker observation file missing columns: " + ", ".join(sorted(missing)))
        for line, raw_row in enumerate(reader, 2):
            row = dict(raw_row)
            row["source_row_number"] = int(row["source_row_number"])
            row["identity_evidence_ids"] = json.loads(row["identity_evidence_ids"] or "[]")
            row["broker_entity_id"] = row["broker_entity_id"] or None
            rows.append(row)
    result = aggregate_broker_observations(rows)
    return {
        "source_file": str(path),
        "source_file_sha256": hashlib.sha256(raw).hexdigest(),
        "source_file_byte_count": len(raw),
        "input_party_observation_count": len(rows),
        "coverage": result["coverage"],
        "aggregate_rows": result["aggregate_rows"],
        "coverage_rows": result["coverage_rows"],
        "policy": result["policy"],
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_broker_identity_coverage(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output.exists() and args.output.read_text(encoding="utf-8") != encoded:
        raise RuntimeError("broker coverage output exists with different content")
    if not args.output.exists():
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    print(json.dumps({
        "input_party_observation_count": report["input_party_observation_count"],
        "coverage_rows": report["coverage_rows"],
        "source_file_sha256": report["source_file_sha256"],
        "promotion_allowed": report["promotion_allowed"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
