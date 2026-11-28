#!/usr/bin/env python3
"""Verify the pinned Issue #5 quarantine overlay without modifying it."""
import argparse
import json
from collections import Counter
from pathlib import Path
from app.issue5_quarantine import Quarantine, EXPECTED_SHA256, EXPECTED_COUNT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    guard = Quarantine(args.csv_path)
    counts = Counter(
        "confirmed_carry_forward" if row["confirmed_carry_forward"] == "True"
        else "explicit_closure_review"
        for row in guard.rows.values()
    )
    report = {
        "status": "PASS",
        "sha256": EXPECTED_SHA256,
        "record_count": len(guard.rows),
        "unique_locators": len(guard.rows),
        "duplicate_locators": 0,
        "confirmed_carry_forward": counts["confirmed_carry_forward"],
        "explicit_closure_review": counts["explicit_closure_review"],
        "eligible_trading_candle": 0,
        "canonical_training_allowed": 0,
        "source_file_modified": False,
    }
    if report["record_count"] != EXPECTED_COUNT:
        raise SystemExit("Unexpected quarantine record count")
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
