#!/usr/bin/env python3
"""Run or audit the scheduled bronze evidence backup operator."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.evidence_backup_scheduler import audit_backup_schedule, run_scheduled_backup  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("run", "audit"), required=True)
    parser.add_argument("--config", help="JSON file with quiesce_argv, backup_argv and resume_argv")
    parser.add_argument("--receipts", required=True, help="Append-only JSONL receipt ledger")
    parser.add_argument("--lock", help="OS lock file used to serialize backup runs")
    parser.add_argument("--run-id", help="Unique scheduler invocation ID")
    parser.add_argument("--expected-interval-hours", type=float, default=26)
    parser.add_argument("--grace-hours", type=float, default=2)
    args = parser.parse_args()

    if args.mode == "run":
        if not args.config or not args.lock or not args.run_id:
            parser.error("--mode run requires --config, --lock and --run-id")
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = run_scheduled_backup(
            config=config, receipt_path=args.receipts,
            lock_path=args.lock, run_id=args.run_id,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("status") == "backup_verified" else 2

    result = audit_backup_schedule(
        args.receipts,
        expected_interval_hours=args.expected_interval_hours,
        grace_hours=args.grace_hours,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "healthy" else 2


if __name__ == "__main__":
    raise SystemExit(main())
