#!/usr/bin/env python3
"""Persist an immutable, source-hashed broker party/control reconciliation report."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from app.broker_aggregation import reconcile_source_control_totals


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_party_rows(paths: list[Path]) -> list[dict]:
    rows = []
    required = {"source_id", "trade_date", "contract_id", "side", "amount", "quantity"}
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path}: missing columns: " + ", ".join(sorted(missing)))
            rows.extend(dict(row) for row in reader)
    return rows


def _read_controls(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"source_id", "trade_date", "contract_count", "gross_amount", "party_observation_count"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns: " + ", ".join(sorted(missing)))
        return [dict(row) for row in reader]


def build_immutable_report(party_paths: list[Path], controls_path: Path, output: Path) -> dict:
    rows = _read_party_rows(party_paths)
    controls = _read_controls(controls_path)
    reconciliation = reconcile_source_control_totals(rows, controls)
    body = {
        "schema_version": 1,
        "party_input_files": [
            {"path": str(path), "sha256": _sha256(path), "byte_count": path.stat().st_size}
            for path in sorted(party_paths)
        ],
        "control_input_file": {
            "path": str(controls_path), "sha256": _sha256(controls_path),
            "byte_count": controls_path.stat().st_size,
        },
        "reconciliation": reconciliation,
        "canonical_promotion_allowed": False,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    report = {**body, "report_sha256": digest}
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if output.exists():
        if output.read_text(encoding="utf-8") != encoded:
            raise RuntimeError("immutable broker report path already contains different content")
    else:
        with output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--party-rows", action="append", required=True, type=Path)
    parser.add_argument("--controls", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_immutable_report(args.party_rows, args.controls, args.output)
    print(json.dumps({
        "report_sha256": report["report_sha256"],
        "source_date_count": report["reconciliation"]["source_date_count"],
        "failed_source_dates": report["reconciliation"]["failed_source_dates"],
        "output": str(args.output),
        "canonical_promotion_allowed": False,
    }, indent=2))
    return 0 if report["reconciliation"]["failed_source_dates"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
