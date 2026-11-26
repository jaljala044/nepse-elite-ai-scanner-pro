#!/usr/bin/env python3
"""Generate a non-promoting audit report for recovered NEPSE session candidates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.session_candidate_audit import audit_session_candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--calendar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True, help="Checkout root for the pinned source archive")
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    report = audit_session_candidates(args.candidates, args.calendar, args.source_root, args.source_repository, args.source_revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
