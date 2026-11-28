#!/usr/bin/env python3
"""Summarize cross-source overlap in the Issue #5 active-equity gap inventory.

This is a descriptive overlap report only. It does not decide whether an absent
bar is a no-trade, suspension, lifecycle boundary, source omission or missing row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

SMC = "jaljala044/nepse-smc-data"
HISTORY = "jaljala044/nepse-history-starter"
REPOSITORIES = {SMC, HISTORY}
REQUIRED = {
    "repository", "symbol", "trade_date", "gap_status",
    "canonical_promotion_allowed", "raw_source_modified",
}
GAP_STATUS = "UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(row: dict, field: str, line: int) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string at line {line}")
    return value.strip()


def summarize(input_csv: Path) -> dict:
    source_rows = Counter()
    pair_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    symbol_dates: dict[str, set[str]] = defaultdict(set)
    symbol_source_dates: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {SMC: set(), HISTORY: set()}
    )
    date_symbols: dict[str, set[str]] = defaultdict(set)
    seen = set()

    with input_csv.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("gap CSV contains duplicate column headers")
        missing = REQUIRED - set(headers)
        if missing:
            raise ValueError("gap CSV missing columns: " + ", ".join(sorted(missing)))
        for line, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"unexpected extra CSV fields at line {line}")
            repository = _required_text(row, "repository", line)
            raw_symbol = _required_text(row, "symbol", line)
            day = _required_text(row, "trade_date", line)
            gap_status = _required_text(row, "gap_status", line)
            promotion = _required_text(row, "canonical_promotion_allowed", line)
            modified = _required_text(row, "raw_source_modified", line)
            symbol = raw_symbol.upper()
            if repository not in REPOSITORIES:
                raise ValueError(f"unknown repository at line {line}: {repository!r}")
            try:
                parsed = date.fromisoformat(day)
            except (TypeError, ValueError):
                raise ValueError(f"invalid trade date at line {line}: {day!r}") from None
            if parsed.isoformat() != day:
                raise ValueError(f"noncanonical trade date at line {line}: {day!r}")
            if gap_status != GAP_STATUS:
                raise ValueError(f"unexpected gap status at line {line}")
            if promotion.casefold() != "false":
                raise ValueError(f"promotion flag must be false at line {line}")
            if modified.casefold() != "false":
                raise ValueError(f"raw-source mutation flag must be false at line {line}")
            key = (repository, symbol, day)
            if key in seen:
                raise ValueError(f"duplicate repository/symbol/date row: {key}")
            seen.add(key)
            source_rows[repository] += 1
            pair_sources[(symbol, day)].add(repository)
            symbol_dates[symbol].add(day)
            symbol_source_dates[symbol][repository].add(day)
            date_symbols[day].add(symbol)

    if not seen:
        raise ValueError("gap inventory must contain at least one row")

    overlap_counts = Counter()
    pair_rows = []
    for (symbol, day), sources in sorted(pair_sources.items()):
        if sources == REPOSITORIES:
            classification = "both_sources_gap"
        elif sources == {SMC}:
            classification = "smc_only_gap"
        elif sources == {HISTORY}:
            classification = "history_starter_only_gap"
        else:
            raise ValueError(f"unexpected source set for {symbol}/{day}: {sources}")
        overlap_counts[classification] += 1
        pair_rows.append({
            "symbol": symbol,
            "trade_date": day,
            "gap_source_count": len(sources),
            "gap_sources": ";".join(sorted(sources)),
            "overlap_classification": classification,
            "adjudication": "UNRESOLVED_NO_TRADE_OR_MISSING_OR_LIFECYCLE",
            "canonical_promotion_allowed": False,
        })

    top_symbols = []
    for symbol, days in symbol_dates.items():
        smc_days = symbol_source_dates[symbol][SMC]
        history_days = symbol_source_dates[symbol][HISTORY]
        top_symbols.append({
            "symbol": symbol,
            "unique_gap_dates": len(days),
            "smc_gap_dates": len(smc_days),
            "history_starter_gap_dates": len(history_days),
            "both_source_gap_dates": len(smc_days & history_days),
        })
    top_symbols.sort(key=lambda x: (-x["unique_gap_dates"], x["symbol"]))

    top_dates = []
    for day, symbols in date_symbols.items():
        smc_count = sum(1 for symbol in symbols if SMC in pair_sources[(symbol, day)])
        history_count = sum(1 for symbol in symbols if HISTORY in pair_sources[(symbol, day)])
        top_dates.append({
            "trade_date": day,
            "unique_symbol_gaps": len(symbols),
            "smc_symbol_gaps": smc_count,
            "history_starter_symbol_gaps": history_count,
            "both_source_symbol_gaps": sum(
                1 for symbol in symbols if pair_sources[(symbol, day)] == REPOSITORIES
            ),
        })
    top_dates.sort(key=lambda x: (-x["unique_symbol_gaps"], x["trade_date"]))

    return {
        "report_type": "issue5_cross_source_gap_overlap_descriptive_only",
        "input_csv_sha256": sha256(input_csv),
        "source_gap_rows": sum(source_rows.values()),
        "source_gap_rows_by_repository": dict(sorted(source_rows.items())),
        "unique_symbol_date_keys": len(pair_sources),
        "overlap_classification_counts": dict(sorted(overlap_counts.items())),
        "top_symbols": top_symbols[:25],
        "top_dates": top_dates[:25],
        "pair_classification_csv": "issue5_cross_source_gap_pair_classification.csv",
        "raw_source_modified": False,
        "gap_adjudication_complete": False,
        "canonical_or_training_promotion": False,
        "interpretation": (
            "A gap in both archives is a shared absence, not proof of no trade. "
            "A one-source gap is a source-coverage difference, not proof the other "
            "source is authoritative. Every pair remains unresolved."
        ),
        "pair_classifications": pair_rows,
    }


def write_report(report: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "issue5_cross_source_gap_overlap.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pair_fields = [
        "symbol", "trade_date", "gap_source_count", "gap_sources",
        "overlap_classification", "adjudication", "canonical_promotion_allowed",
    ]
    with (output_dir / report["pair_classification_csv"]).open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=pair_fields)
        writer.writeheader()
        writer.writerows(report["pair_classifications"])
    for key, filename in (
        ("top_symbols", "issue5_cross_source_gap_top_symbols.csv"),
        ("top_dates", "issue5_cross_source_gap_top_dates.csv"),
    ):
        rows = report[key]
        with (output_dir / filename).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = summarize(args.input)
    write_report(report, args.output_dir)
    print(json.dumps({
        key: value for key, value in report.items()
        if key not in {"pair_classifications", "top_symbols", "top_dates"}
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
