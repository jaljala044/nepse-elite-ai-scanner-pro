"""Expected-session OHLCV coverage and cross-source reconciliation report."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation


def _canonical_iso_date(value, field_name: str) -> str:
    """Require an exact YYYY-MM-DD string; reject permissive ISO variants."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field_name} must be canonical YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field_name} must be canonical YYYY-MM-DD")
    return value


def build_historical_coverage_report(records: list[dict], *,
                                    expected_sessions: list[str],
                                    expected_symbols: list[str]) -> dict:
    """Audit a caller-supplied verified session/symbol grid; infer no missing sessions."""
    sessions = sorted({_canonical_iso_date(x, "expected session") for x in expected_sessions})
    if any(not isinstance(x, str) or not x.strip() for x in expected_symbols):
        raise ValueError("expected symbols must be non-empty strings")
    symbols = sorted({x.strip().upper() for x in expected_symbols})
    if not sessions or not symbols:
        raise ValueError("verified expected_sessions and expected_symbols are required")
    expected = {(d, s) for d in sessions for s in symbols}
    by_key_source = defaultdict(list)
    source_rows = defaultdict(int)
    unexpected_rows = defaultdict(list)
    for index, row in enumerate(records):
        try:
            session_date = _canonical_iso_date(row["session_date"], "session_date")
            symbol = str(row["symbol"]).strip().upper()
            source = str(row["source_id"]).strip()
            close = Decimal(str(row["close"]))
            if not source or not symbol:
                raise ValueError("blank source_id or symbol")
            if not close.is_finite() or close <= 0:
                raise ValueError("close must be a finite positive decimal")
            key = (session_date, symbol)
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise ValueError(f"invalid coverage input row {index}: {exc}") from exc
        by_key_source[(key, source)].append(row)
        source_rows[source] += 1
        if key not in expected:
            unexpected_rows[source].append({
                "session_date": key[0], "symbol": key[1],
                "reason": ("session_not_in_verified_expected_grid" if key[0] not in sessions
                           else "symbol_not_in_expected_universe"),
            })

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
            "unexpected_rows": sorted(unexpected_rows[source],
                                      key=lambda item: (item["session_date"], item["symbol"])),
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


def build_cached_historical_coverage_report(path, *, expected_sessions, expected_symbols,
                                           load_records, registry):
    """Reuse an exact-file coverage report without re-running deterministic parsing.

    The expected session/symbol grid is fingerprinted into the schema-version key,
    because changing the audit grid changes the report even when file bytes do not.
    ``load_records(path)`` must return the same row shape accepted by
    ``build_historical_coverage_report``. Source authorization, lineage, calendar
    verification and promotion remain caller-owned gates and are never cached here.
    """
    import hashlib
    import json
    from pathlib import Path
    from nepse_shared_validation import run_cached_validation

    sessions = sorted({_canonical_iso_date(x, "expected session") for x in expected_sessions})
    if any(not isinstance(x, str) or not x.strip() for x in expected_symbols):
        raise ValueError("expected symbols must be non-empty strings")
    symbols = sorted({x.strip().upper() for x in expected_symbols})
    if not sessions or not symbols:
        raise ValueError("verified expected_sessions and expected_symbols are required")
    grid = json.dumps({"sessions": sessions, "symbols": symbols},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")
    grid_sha256 = hashlib.sha256(grid).hexdigest()

    def validate_file(file_path):
        report = build_historical_coverage_report(
            load_records(Path(file_path)), expected_sessions=sessions,
            expected_symbols=symbols)
        return {"valid": True, "coverage_report": report}

    return run_cached_validation(
        registry, path, dataset_kind="historical_ohlcv_coverage",
        schema_version=f"coverage-grid-v1:{grid_sha256}",
        validator_version="historical-coverage-v1", validator=validate_file)
