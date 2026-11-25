#!/usr/bin/env python3
"""Detect adjusted/unadjusted OHLCV basis mixing without applying adjustments."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED = {"source_id","symbol","date","open","high","low","close","volume","adjustment_basis"}
ALLOWED_BASIS = {"adjusted","unadjusted","unknown"}


def audit_adjustment_basis(paths: list[str | Path]) -> dict[str, Any]:
    rows = []
    for source_path in paths:
        with Path(source_path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = REQUIRED - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{source_path}: missing columns: " + ", ".join(sorted(missing)))
            for line, raw in enumerate(reader, 2):
                source_id = (raw.get("source_id") or "").strip()
                symbol = (raw.get("symbol") or "").strip().upper()
                day = (raw.get("date") or "").strip()
                basis = (raw.get("adjustment_basis") or "").strip().lower()
                if not source_id or not symbol:
                    raise ValueError(f"{source_path}:{line}: source_id and symbol are required")
                date.fromisoformat(day)
                if basis not in ALLOWED_BASIS:
                    raise ValueError(f"{source_path}:{line}: unsupported adjustment_basis {basis!r}")
                rows.append({"source_id":source_id,"symbol":symbol,"date":day,
                             "adjustment_basis":basis,"path":str(source_path),"line":line})

    by_source_symbol = defaultdict(set)
    by_symbol_date = defaultdict(set)
    for row in rows:
        by_source_symbol[(row["source_id"],row["symbol"])].add(row["adjustment_basis"])
        by_symbol_date[(row["symbol"],row["date"])].add(row["adjustment_basis"])

    source_mixing = [
        {"source_id":key[0],"symbol":key[1],"basis_values":sorted(values)}
        for key,values in sorted(by_source_symbol.items())
        if len(values) > 1 or "unknown" in values
    ]
    cross_source_basis_conflicts = [
        {"symbol":key[0],"date":key[1],"basis_values":sorted(values)}
        for key,values in sorted(by_symbol_date.items())
        if len(values) > 1 or "unknown" in values
    ]
    return {
        "input_row_count": len(rows),
        "source_symbol_basis_issue_count": len(source_mixing),
        "cross_source_basis_conflict_count": len(cross_source_basis_conflicts),
        "source_symbol_basis_issues": source_mixing,
        "cross_source_basis_conflicts": cross_source_basis_conflicts,
        "adjustments_applied": False,
        "promotion_allowed": False,
        "policy": "adjusted_and_unadjusted_series_are_not_mixed_or_rebased_without_verified_corporate_action_policy",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/reports/ohlcv-adjustment-basis-audit.json"))
    args = parser.parse_args()
    report = audit_adjustment_basis(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k:report[k] for k in (
        "input_row_count","source_symbol_basis_issue_count","cross_source_basis_conflict_count",
        "adjustments_applied","promotion_allowed")}, indent=2))
    return 0 if not report["source_symbol_basis_issue_count"] and not report["cross_source_basis_conflict_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
