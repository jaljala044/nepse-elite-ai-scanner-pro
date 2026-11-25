#!/usr/bin/env python3
"""Build per-security OHLCV coverage against explicit universe and session evidence.

Only evidence-backed open dates enter the expected-session denominator. Unknown
calendar dates remain visible as unresolved candidates, never inferred sessions.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from app.session_calendar import load_calendar, schedule_candidate

UNIVERSE_FIELDS = ("security_id", "symbol", "instrument_type", "valid_from", "valid_to", "target_in_scope")
DATA_FIELDS = ("source_id", "symbol", "date")


def _read_universe(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = set(UNIVERSE_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("universe missing columns: " + ", ".join(sorted(missing)))
        for line, raw in enumerate(reader, 2):
            symbol = (raw.get("symbol") or "").strip().upper()
            security_id = (raw.get("security_id") or "").strip()
            kind = (raw.get("instrument_type") or "").strip()
            scope = (raw.get("target_in_scope") or "").strip().lower()
            if not symbol or not security_id:
                raise ValueError(f"{path}:{line}: security_id and symbol are required")
            if kind not in {"equity", "mutual_fund", "convertible_debenture",
                            "non_convertible_debenture", "preference_share", "other"}:
                raise ValueError(f"{path}:{line}: unsupported instrument_type {kind!r}")
            if scope not in {"true", "false"}:
                raise ValueError(f"{path}:{line}: target_in_scope must be true or false")
            if scope == "true" and kind not in {"equity", "mutual_fund"}:
                raise ValueError(f"{path}:{line}: target universe permits only equity and mutual_fund")
            start = date.fromisoformat(raw["valid_from"].strip())
            end = date.fromisoformat(raw["valid_to"].strip()) if (raw.get("valid_to") or "").strip() else None
            if end is not None and end < start:
                raise ValueError(f"{path}:{line}: valid_to precedes valid_from")
            rows.append({
                "security_id": security_id, "symbol": symbol, "instrument_type": kind,
                "valid_from": start, "valid_to": end, "target_in_scope": scope == "true",
            })
    if not rows:
        raise ValueError("universe snapshot is empty")
    ids = [r["security_id"] for r in rows if r["target_in_scope"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate in-scope security_id in universe snapshot")
    for index, left in enumerate(rows):
        if not left["target_in_scope"]:
            continue
        for right in rows[index + 1:]:
            if not right["target_in_scope"] or left["symbol"] != right["symbol"]:
                continue
            left_end, right_end = left["valid_to"] or date.max, right["valid_to"] or date.max
            if left["valid_from"] <= right_end and right["valid_from"] <= left_end:
                raise ValueError(f"overlapping in-scope symbol {left['symbol']}")
    return rows


def _read_observations(paths: list[str | Path]) -> dict[str, dict[str, Counter]]:
    observed: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for source_path in paths:
        with Path(source_path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = set(DATA_FIELDS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{source_path}: data missing columns: " + ", ".join(sorted(missing)))
            for line, row in enumerate(reader, 2):
                source_id = (row.get("source_id") or "").strip()
                symbol = (row.get("symbol") or "").strip().upper()
                if not source_id or not symbol:
                    raise ValueError(f"{source_path}:{line}: source_id and symbol are required")
                day = date.fromisoformat((row.get("date") or "").strip()).isoformat()
                observed[source_id][symbol][day] += 1
    return observed


def build_security_coverage_report(
    universe_path: str | Path,
    calendar_path: str | Path,
    data_paths: list[str | Path],
    start: date,
    end: date,
) -> dict[str, Any]:
    if end < start:
        raise ValueError("end date must not precede start date")
    universe = _read_universe(universe_path)
    calendar = load_calendar(calendar_path)
    observed_by_source = _read_observations(data_paths)

    sessions = sorted(
        day for day, evidence in calendar.items()
        if start <= day <= end and evidence["status"] in {"verified_open", "verified_exceptional_open"}
    )
    verified_closed = {day for day, evidence in calendar.items()
                       if start <= day <= end and evidence["status"] in {"verified_closed", "verified_exceptional_closed"}}
    target = [row for row in universe if row["target_in_scope"]]
    type_counts = Counter(row["instrument_type"] for row in target)
    per_source = []
    for source_id, observed in sorted(observed_by_source.items()):
        per_security = []
        expected_total = observed_total = 0
        unknown_calendar_candidates = set()
        unexpected_observations = []
        target_symbols = {row["symbol"] for row in target}
        unknown_symbol_observations = []
        for unknown_symbol, day_counts in sorted(observed.items()):
            if unknown_symbol in target_symbols:
                continue
            for observed_day, row_count in sorted(day_counts.items()):
                observed_date = date.fromisoformat(observed_day)
                if start <= observed_date <= end:
                    unknown_symbol_observations.append({
                        "symbol": unknown_symbol, "date": observed_day,
                        "row_count": row_count,
                        "reason": "symbol_not_in_target_universe_snapshot",
                    })
        for security in sorted(target, key=lambda row: (row["instrument_type"], row["symbol"], row["security_id"])):
            expected = [
                day for day in sessions
                if security["valid_from"] <= day and (security["valid_to"] is None or day <= security["valid_to"])
            ]
            found = observed.get(security["symbol"], Counter())
            observed_dates = {date.fromisoformat(day) for day, count in found.items() if count > 0}
            in_range = {day for day in observed_dates if start <= day <= end}
            matched = sorted(day for day in expected if found.get(day.isoformat(), 0) == 1)
            missing = sorted(day.isoformat() for day in expected if found.get(day.isoformat(), 0) == 0)
            duplicates = sorted(day.isoformat() for day in expected if found.get(day.isoformat(), 0) > 1)
            unexpected = sorted(day.isoformat() for day in in_range if day not in set(expected))
            expected_total += len(expected)
            observed_total += len(matched)
            for day in in_range:
                if day not in calendar:
                    unknown_calendar_candidates.add(day.isoformat())
                elif day in verified_closed:
                    unexpected_observations.append({"symbol": security["symbol"], "date": day.isoformat(), "reason": "observation_on_verified_closed_date"})
                elif day not in set(expected):
                    unexpected_observations.append({"symbol": security["symbol"], "date": day.isoformat(), "reason": "outside_security_effective_interval_or_not_verified_open"})
            per_security.append({
                "security_id": security["security_id"],
                "symbol": security["symbol"],
                "instrument_type": security["instrument_type"],
                "valid_from": security["valid_from"].isoformat(),
                "valid_to": security["valid_to"].isoformat() if security["valid_to"] else None,
                "expected_verified_sessions": len(expected),
                "observed_expected_sessions": len(matched),
                "missing_sessions": missing,
                "duplicate_session_rows": duplicates,
                "observed_outside_expected_sessions": unexpected,
                "coverage_ratio": (len(matched) / len(expected)) if expected else None,
            })
        per_source.append({
            "source_id": source_id,
            "expected_security_session_observations": expected_total,
            "matched_security_session_observations": observed_total,
            "coverage_ratio": observed_total / expected_total if expected_total else None,
            "unverified_calendar_observation_dates": sorted(unknown_calendar_candidates),
            "unexpected_observations": unexpected_observations,
            "unknown_symbol_observation_count": sum(row["row_count"] for row in unknown_symbol_observations),
            "unknown_symbol_observations": unknown_symbol_observations,
            "per_security": per_security,
        })

    # Never combine publishers into one coverage numerator/denominator.
    single_source = per_source[0] if len(per_source) == 1 else None
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "target_security_count": len({row["security_id"] for row in target}),
        "target_equity_count": len({row["security_id"] for row in target if row["instrument_type"] == "equity"}),
        "target_mutual_fund_count": len({row["security_id"] for row in target if row["instrument_type"] == "mutual_fund"}),
        "expected_target_equity_count": 281,
        "expected_target_mutual_fund_count": 47,
        "target_universe_counts_match": (
            len({row["security_id"] for row in target if row["instrument_type"] == "equity"}) == 281
            and len({row["security_id"] for row in target if row["instrument_type"] == "mutual_fund"}) == 47
        ),
        "verified_open_session_count": len(sessions),
        "source_count": len(per_source),
        "source_specific_reports": per_source,
        "per_security": single_source["per_security"] if single_source else [],
        "expected_security_session_observations": single_source["expected_security_session_observations"] if single_source else None,
        "matched_security_session_observations": single_source["matched_security_session_observations"] if single_source else None,
        "aggregate_coverage_ratio": single_source["coverage_ratio"] if single_source else None,
        "status": "coverage_diagnostic_only",
        "promotion_allowed": False,
        "limitations": [
            "Expected sessions include only explicit verified_open or verified_exceptional_open dates.",
            "Unknown dates are excluded from the denominator and reported separately; no weekday or file-presence inference is used.",
            "Each publisher is reported separately; coverage ratios from different sources are never merged.",
            "This report measures supplied source rows, not proof of complete market capture or data rights.",
            "Duplicate rows remain anomalies and do not increase matched-session coverage.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--input", action="append", required=True, type=Path, help="normalized symbol/date CSV; repeatable")
    parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    parser.add_argument("--end-date", required=True, type=date.fromisoformat)
    parser.add_argument("--output", type=Path, default=Path("data/reports/security-coverage.json"))
    args = parser.parse_args()
    report = build_security_coverage_report(args.universe, args.calendar, args.input, args.start_date, args.end_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "target_security_count", "target_equity_count", "target_mutual_fund_count",
        "verified_open_session_count", "expected_security_session_observations",
        "matched_security_session_observations", "aggregate_coverage_ratio",
        "status", "promotion_allowed",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
