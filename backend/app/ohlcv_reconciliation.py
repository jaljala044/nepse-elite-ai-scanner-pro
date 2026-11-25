"""Conservative row-level OHLCV reconciliation for two local source archives.

Compares same-named CSV files by explicit date and OHLCV fields. It never
selects a winning source, infers exchange sessions, adjusts prices, or drops
duplicate-date rows. Input files and source revisions are recorded in output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

ALIASES = {
    "date": ("date", "trading_date", "business_date", "trade_date"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c", "ltp"),
    "volume": ("volume", "vol", "total_traded_quantity", "quantity"),
}
NUMERIC_FIELDS = ("open", "high", "low", "close", "volume")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _header_map(headers: list[str], path: Path) -> dict[str, str]:
    normalized = {str(h).strip().lower(): str(h) for h in headers if h is not None}
    mapping: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        matches = [normalized[a] for a in aliases if a in normalized]
        if len(matches) != 1:
            raise ValueError(
                f"{path}: expected exactly one recognized {field} column; "
                f"found {matches or 'none'}"
            )
        mapping[field] = matches[0]
    return mapping


def _canonical_number(raw: Any, *, field: str, path: Path, row_number: int) -> str:
    value = str(raw if raw is not None else "").strip().replace(",", "")
    if not value:
        raise ValueError(f"{path}:{row_number}: empty {field}")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{path}:{row_number}: invalid {field} value {value!r}") from exc
    if not number.is_finite():
        raise ValueError(f"{path}:{row_number}: non-finite {field} value")
    return format(number.normalize(), "f")


def read_ohlcv(path: Path) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    errors: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path}: missing CSV header")
        columns = _header_map(reader.fieldnames, path)
        for row_number, row in enumerate(reader, start=2):
            raw_date = str(row.get(columns["date"]) or "").strip()
            try:
                # Strict ISO calendar date; no locale-dependent parsing.
                day = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
            except ValueError:
                errors.append({"row": row_number, "date": raw_date, "error": "invalid_or_non_iso_date"})
                continue
            try:
                values = {
                    field: _canonical_number(row.get(columns[field]), field=field,
                                             path=path, row_number=row_number)
                    for field in NUMERIC_FIELDS
                }
            except ValueError as exc:
                errors.append({"row": row_number, "date": day, "error": str(exc)})
                continue
            grouped[day].append(values)
    return dict(grouped), errors


def _compare_symbol(left_path: Path | None, right_path: Path | None,
                    left_root: Path, right_root: Path) -> dict[str, Any]:
    left_rows, left_errors = read_ohlcv(left_path) if left_path else ({}, [])
    right_rows, right_errors = read_ohlcv(right_path) if right_path else ({}, [])
    left_dates, right_dates = set(left_rows), set(right_rows)
    duplicates = {
        "left": {d: len(v) for d, v in left_rows.items() if len(v) > 1},
        "right": {d: len(v) for d, v in right_rows.items() if len(v) > 1},
    }
    mismatches = []
    for day in sorted(left_dates & right_dates):
        # Duplicate dates are ambiguous; compare all rows as multisets and retain
        # the duplicate flag rather than arbitrarily choosing a row.
        l_values = sorted(tuple(row[f] for f in NUMERIC_FIELDS) for row in left_rows[day])
        r_values = sorted(tuple(row[f] for f in NUMERIC_FIELDS) for row in right_rows[day])
        if l_values != r_values:
            mismatches.append({
                "date": day,
                "left_rows": [dict(zip(NUMERIC_FIELDS, row)) for row in l_values],
                "right_rows": [dict(zip(NUMERIC_FIELDS, row)) for row in r_values],
            })
    return {
        "left_file": str(left_path.relative_to(left_root)) if left_path else None,
        "right_file": str(right_path.relative_to(right_root)) if right_path else None,
        "left_sha256": sha256_file(left_path) if left_path else None,
        "right_sha256": sha256_file(right_path) if right_path else None,
        "left_only_dates": sorted(left_dates - right_dates),
        "right_only_dates": sorted(right_dates - left_dates),
        "field_value_mismatches": mismatches,
        "duplicate_dates": duplicates,
        "invalid_rows": {"left": left_errors, "right": right_errors},
        "left_row_count": sum(map(len, left_rows.values())),
        "right_row_count": sum(map(len, right_rows.values())),
        "status": (
            "source_missing_left" if left_path is None else
            "source_missing_right" if right_path is None else
            "conflict" if (mismatches or duplicates["left"] or duplicates["right"]
                           or left_errors or right_errors) else
            "date_coverage_differs" if left_dates != right_dates else
            "identical_ohlcv_rows"
        ),
    }


def reconcile_roots(left_root: Path, right_root: Path, *,
                    left_source: str, right_source: str,
                    left_revision: str, right_revision: str) -> dict[str, Any]:
    left_files = {p.relative_to(left_root).as_posix(): p
                  for p in left_root.rglob("*.csv") if p.is_file()}
    right_files = {p.relative_to(right_root).as_posix(): p
                   for p in right_root.rglob("*.csv") if p.is_file()}
    # Match by relative path first; same ticker basename in different folder
    # layouts is not silently treated as the same instrument.
    keys = sorted(set(left_files) | set(right_files))
    symbols = {
        key: _compare_symbol(left_files.get(key), right_files.get(key),
                             left_root, right_root)
        for key in keys
    }
    counts = Counter(item["status"] for item in symbols.values())
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_type": "source_to_source_row_level_ohlcv_reconciliation",
        "left_source": {"label": left_source, "revision": left_revision},
        "right_source": {"label": right_source, "revision": right_revision},
        "matching_rule": "identical relative CSV path; no ticker-name inference",
        "symbol_file_count": len(symbols),
        "status_counts": dict(sorted(counts.items())),
        "symbols": symbols,
        "limitations": [
            "A missing row is not proof of a missing exchange session.",
            "Only explicit ISO YYYY-MM-DD dates and OHLCV columns are compared.",
            "No corporate-action adjustment, winner selection, or source merge is performed.",
            "CSV files with different relative paths are not matched by basename.",
            "Source revisions are supplied labels and must be verified by the operator.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-root", required=True, type=Path)
    parser.add_argument("--right-root", required=True, type=Path)
    parser.add_argument("--left-source", required=True)
    parser.add_argument("--right-source", required=True)
    parser.add_argument("--left-revision", required=True)
    parser.add_argument("--right-revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = reconcile_roots(
        args.left_root, args.right_root, left_source=args.left_source,
        right_source=args.right_source, left_revision=args.left_revision,
        right_revision=args.right_revision,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "symbol_file_count": report["symbol_file_count"],
                      "status_counts": report["status_counts"]}, indent=2))


if __name__ == "__main__":
    main()
