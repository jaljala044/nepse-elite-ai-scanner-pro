#!/usr/bin/env python3
"""Read-only CLI that assembles explicit evidence and prints training blockers.

This command never promotes rows, writes canonical tables or starts model
training. It only reads supplied evidence reports and writes a readiness report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.data_readiness_evidence import assemble_training_evidence


def _load_json(path: str | None) -> Any:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_list(path: str | None) -> list[dict] | None:
    value = _load_json(path)
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise ValueError(f"{path}: expected JSON object or list")


def evaluate_from_paths(args: argparse.Namespace) -> dict:
    result = assemble_training_evidence(
        universe_report=_load_json(args.universe_report),
        session_reports=_load_list(args.session_reports),
        provenance_reports=_load_list(args.provenance_reports),
        ohlcv_report=_load_json(args.ohlcv_report),
        broker_report=_load_json(args.broker_report),
        point_in_time_report=_load_json(args.point_in_time_report),
        corporate_action_reviewed=args.corporate_action_reviewed,
        holdout_protocol_id=args.holdout_protocol_id,
        historical_coverage=args.historical_coverage,
        evidence_snapshot_id=args.evidence_snapshot_id,
    )
    result["readiness_report_policy"] = "read_only_no_canonical_promotion_no_training_execution"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-report")
    parser.add_argument("--session-reports")
    parser.add_argument("--provenance-reports")
    parser.add_argument("--ohlcv-report")
    parser.add_argument("--broker-report")
    parser.add_argument("--point-in-time-report")
    parser.add_argument("--corporate-action-reviewed", action="store_true")
    parser.add_argument("--holdout-protocol-id")
    parser.add_argument("--historical-coverage", type=float)
    parser.add_argument("--evidence-snapshot-id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_from_paths(args)
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({
        "training_ready": result["training_readiness"]["training_ready"],
        "model_training_allowed": result["training_readiness"]["model_training_allowed"],
        "blockers": result["training_readiness"]["blockers"],
        "output": str(args.output) if args.output else None,
        "policy": result["readiness_report_policy"],
    }, indent=2))
    return 0 if result["training_readiness"]["training_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
