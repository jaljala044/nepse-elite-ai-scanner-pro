"""CLI: python audit_v3_coverage.py --input data.csv --universe symbols.csv"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from app.data_coverage_v3 import audit_ohlcv


def read_rows(paths: list[Path]):
    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError(f"{path}: missing CSV header")
            for row in reader:
                yield row


def read_symbols(path: Path | None):
    if path is None:
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("universe CSV must have a symbol header")
        field = next((f for f in reader.fieldnames if f.strip().lower() == "symbol"), None)
        if field is None:
            raise ValueError("universe CSV must contain a symbol column")
        return [row[field] for row in reader]


def main():
    parser = argparse.ArgumentParser(description="Audit NEPSE daily OHLCV coverage without fabricating sessions.")
    parser.add_argument("--input", nargs="+", required=True, help="One or more combined OHLCV CSV files")
    parser.add_argument("--universe", help="Optional CSV with a symbol column for exact missing-symbol checks")
    parser.add_argument("--sessions", help="Optional CSV with a date column listing authoritative exchange sessions")
    parser.add_argument("--as-of", help="Optional YYYY-MM-DD cutoff")
    parser.add_argument("--target-count", type=int, default=309)
    parser.add_argument("--output", default="reports/v3_coverage_audit.json")
    args = parser.parse_args()

    paths = [Path(p) for p in args.input]
    for path in paths:
        if not path.is_file():
            parser.error(f"input file not found: {path}")
    session_dates = None
    if args.sessions:
        with Path(args.sessions).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            field = next((f for f in (reader.fieldnames or []) if f.strip().lower() == "date"), None)
            if field is None:
                parser.error("sessions CSV must contain a date column")
            session_dates = [row[field] for row in reader]

    report = audit_ohlcv(
        read_rows(paths),
        expected_symbols=read_symbols(Path(args.universe)) if args.universe else None,
        expected_sessions=session_dates,
        target_universe_size=args.target_count,
        as_of=args.as_of,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("per_symbol", "errors", "limitations")}, indent=2))
    print(f"Full report: {output}")


if __name__ == "__main__":
    main()
