"""Expected-session OHLCV coverage and cross-source reconciliation report."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation


def build_historical_coverage_report(records: list[dict], *,
                                    expected_sessions: list[str],
                                    expected_symbols: list[str]) -> dict:
    """Audit a caller-supplied verified session/symbol grid; infer no missing sessions."""
    sessions = sorted({date.fromisoformat(x).isoformat() for x in expected_sessions})
    symbols = sorted({x.strip().upper() for x in expected_symbols if x.strip()})
    if not sessions or not symbols:
        raise ValueError("verified expected_sessions and expected_symbols are required")
    expected = {(d, s) for d in sessions for s in symbols}
    by_key_source = defaultdict(list)
    source_rows = defaultdict(int)
    for index, row in enumerate(records):
        try:
            key = (date.fromisoformat(row["session_date"]).isoformat(), row["symbol"].strip().upper())
            source = row["source_id"]
            if not source:
                raise ValueError("blank source_id")
            Decimal(str(row["close"]))
        except (KeyError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"invalid coverage input row {index}: {exc}") from exc
        by_key_source[(key, source)].append(row)
        source_rows[source] += 1

    source_ids = sorted(source_rows)
    per_source = {}
    for source in source_ids:
        present, missing, duplicates = set(), [], []
        for key in sorted(expected):
            rows = by_key_source.get((key, source), [])
            if not rows:
                missing.append({"session_date": key[0], "symbol": key[1]})
            else:
                present.add(key)
                if len(rows) > 1:
                    duplicates.append({"session_date": key[0], "symbol": key[1], "row_count": len(rows)})
        per_source[source] = {
            "input_rows": source_rows[source], "covered_keys": len(present),
            "expected_keys": len(expected), "missing_keys": missing,
            "duplicate_keys": duplicates,
            "coverage_ratio": str(Decimal(len(present)) / Decimal(len(expected))),
        }

    conflicts = []
    for key in sorted(expected):
        observed = []
        for source in source_ids:
            rows = by_key_source.get((key, source), [])
            for row in rows:
                observed.append((source, str(Decimal(str(row["close"])))))
        by_source_values = defaultdict(set)
        for source, value in observed:
            by_source_values[source].add(value)
        source_distinct = {value for values in by_source_values.values() for value in values}
        if len(by_source_values) > 1 and len(source_distinct) > 1:
            conflicts.append({"session_date": key[0], "symbol": key[1],
                              "source_values": [{"source_id": s, "close": v} for s, v in observed]})
    union_covered = sum(1 for key in expected if any(by_key_source.get((key, src)) for src in source_ids))
    return {
        "expected_session_count": len(sessions), "expected_symbol_count": len(symbols),
        "expected_symbol_session_keys": len(expected), "source_reports": per_source,
        "union_covered_keys": union_covered, "union_missing_keys": len(expected) - union_covered,
        "cross_source_close_conflict_count": len(conflicts), "cross_source_conflicts": conflicts,
        "calendar_source": "caller_supplied_verified_sessions",
        "unverified_weekday_inference_used": False,
        "canonical_promotion_allowed": False,
        "policy": "coverage_and_conflicts_reported_without_source_preference",
    }
