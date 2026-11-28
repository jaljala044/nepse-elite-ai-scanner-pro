#!/usr/bin/env python3
"""Build a read-only per-equity OHLCV coverage and exception ledger.

Input universe CSV must contain a Symbol column and only approved equity
instruments. Historical files are <SYMBOL>_OHLCV.csv with Date, Open, High,
Low, Close, Volume columns (optional Symbol column). No source files are changed.
"""
import argparse
import csv
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = ("Date", "Open", "High", "Low", "Close", "Volume")


def parse_date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("noncanonical_date")
    return parsed


def dec(value):
    try:
        n = Decimal(value)
        return n if n.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def inspect(symbol, root):
    path = root / f"{symbol}_OHLCV.csv"
    if not path.is_file():
        return {"symbol": symbol, "file": str(path), "status": "MISSING_FILE",
                "rows": 0, "unique_sessions": 0, "duplicates": 0,
                "invalid_ohlcv": 0, "first_date": "", "last_date": ""}
    seen, dates = Counter(), []
    invalid = 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(REQUIRED).issubset(reader.fieldnames):
            return {"symbol": symbol, "file": str(path), "status": "INVALID_SCHEMA",
                    "rows": 0, "unique_sessions": 0, "duplicates": 0,
                    "invalid_ohlcv": 0, "first_date": "", "last_date": ""}
        for row in reader:
            try:
                d = parse_date((row.get("Date") or "").strip())
            except ValueError:
                invalid += 1
                continue
            if row.get("Symbol") and row["Symbol"].strip().upper() != symbol:
                invalid += 1
                continue
            nums = {k: dec(row.get(k, "")) for k in ("Open", "High", "Low", "Close", "Volume")}
            o, h, l, c, v = (nums[k] for k in ("Open", "High", "Low", "Close", "Volume"))
            if (any(x is None for x in nums.values()) or
                any(x <= 0 for x in (o, h, l, c, v)) or
                v != v.to_integral_value() or
                h < max(o, c, l) or l > min(o, c, h)):
                invalid += 1
            seen[d] += 1
            dates.append(d)
    duplicates = sum(n - 1 for n in seen.values() if n > 1)
    status = "REVIEW_REQUIRED" if duplicates or invalid else "OBSERVED_COVERAGE_ONLY"
    return {"symbol": symbol, "file": str(path), "status": status,
            "rows": len(dates), "unique_sessions": len(seen), "duplicates": duplicates,
            "invalid_ohlcv": invalid,
            "first_date": min(seen).isoformat() if seen else "",
            "last_date": max(seen).isoformat() if seen else ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", required=True, type=Path)
    ap.add_argument("--data-dir", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    with args.universe.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "Symbol" not in reader.fieldnames:
            raise SystemExit("Universe CSV requires a Symbol column")
        symbols = [r["Symbol"].strip().upper() for r in reader]
    if len(symbols) != 281 or any(not re.fullmatch(r"[A-Z0-9]+", s) for s in symbols):
        raise SystemExit(f"Expected exactly 281 valid equity symbols; received {len(symbols)}")
    if len(set(symbols)) != len(symbols):
        raise SystemExit("Duplicate symbols in universe; refusing to produce ledger")
    rows = [inspect(s, args.data_dir) for s in sorted(symbols)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"universe_count": len(rows),
               "files_missing": sum(r["status"] == "MISSING_FILE" for r in rows),
               "invalid_schemas": sum(r["status"] == "INVALID_SCHEMA" for r in rows),
               "review_required": sum(r["status"] == "REVIEW_REQUIRED" for r in rows),
               "observed_coverage_only": sum(r["status"] == "OBSERVED_COVERAGE_ONLY" for r in rows),
               "ledger": str(args.output),
               "acceptance": "NOT_GRANTED; session calendar, source lineage, corporate actions and cross-source reconciliation remain separate gates"}
    print(json.dumps(summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
