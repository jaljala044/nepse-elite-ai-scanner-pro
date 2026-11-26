"""Reconcile floorsheet-observed symbols to dated scanner instrument scope.

This is a symbol-scope audit, not a session-completeness or NO_TRADE audit.
Unmatched symbols remain UNKNOWN; source rows are never promoted.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


SAMIR_HEADERS = {
    "contract_no", "stock_symbol", "quantity", "rate", "amount", "date"
}
SOCRATEAI_HEADERS = {
    "transaction", "symbol", "quantity", "rate", "amount", "date"
}
SCOPE_CLASSES = {
    "IN_SCOPE_EQUITY_CANDIDATE",
    "OUT_OF_SCOPE_MUTUAL_FUND",
    "OUT_OF_SCOPE_PROMOTER_SHARE",
    "OUT_OF_SCOPE_DEBENTURE",
    "OUT_OF_SCOPE_BOND",
    "EQUITY_CANDIDATE_NOT_IN_CROSSWALK",
    "UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY",
    "UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH",
}


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or ())
        missing = sorted(required - headers)
        if missing:
            raise ValueError(f"{path} missing required columns: {missing}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def _decimal(value: str, field: str) -> Decimal:
    text = value.strip()
    if "," in text:
        import re
        if not re.fullmatch(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", text):
            raise ValueError(f"invalid thousands grouping in {field}: {value!r}")
        text = text.replace(",", "")
    try:
        result = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"non-finite or negative {field}: {value!r}")
    return result


def audit_floorsheet_symbol_scope(
    samir_path: str | Path,
    socrateai_path: str | Path,
    equity_crosswalk_path: str | Path,
    target_candidates_path: str | Path,
    security_snapshot_path: str | Path,
    expected_trade_date: str,
    expected_snapshot_date: str,
) -> dict:
    try:
        expected_trade_date = date.fromisoformat(expected_trade_date).isoformat()
        expected_snapshot_date = date.fromisoformat(expected_snapshot_date).isoformat()
    except ValueError as exc:
        raise ValueError("expected trade/snapshot dates must be ISO YYYY-MM-DD") from exc

    samir = _read_csv(Path(samir_path), SAMIR_HEADERS)
    socrateai = _read_csv(Path(socrateai_path), SOCRATEAI_HEADERS)
    crosswalk_rows = _read_csv(Path(equity_crosswalk_path), {
        "symbol", "security_id", "security_name", "snapshot_date",
        "active_status", "crosswalk_status",
    })
    candidate_rows = _read_csv(Path(target_candidates_path), {
        "symbol", "instrument_class_from_rendered_list", "official_snapshot_id",
        "official_snapshot_status",
    })
    snapshot_rows = _read_csv(Path(security_snapshot_path), {
        "symbol", "security_id", "security_name", "active_status", "snapshot_date",
    })

    def unique_index(rows, label):
        index = {}
        duplicates = []
        for row in rows:
            symbol = row["symbol"].strip().upper()
            if not symbol:
                raise ValueError(f"{label} contains a blank symbol")
            if symbol in index:
                duplicates.append(symbol)
            index[symbol] = row
        if duplicates:
            raise ValueError(f"{label} contains duplicate symbols: {sorted(set(duplicates))}")
        return index

    crosswalk = unique_index(crosswalk_rows, "equity crosswalk")
    candidates = unique_index(candidate_rows, "target candidates")
    snapshot = unique_index(snapshot_rows, "security snapshot")
    for symbol, row in crosswalk.items():
        security = snapshot.get(symbol)
        if row["snapshot_date"] != expected_snapshot_date or row["active_status"] != "A" or row["crosswalk_status"] != "snapshot_id_match_active_status_A":
            raise ValueError(f"equity crosswalk row for {symbol} is not a verified active row for {expected_snapshot_date}")
        if security is None:
            raise ValueError(f"equity crosswalk symbol {symbol} missing from dated security snapshot")
        if (row["security_id"] != security["security_id"]
                or row["active_status"] != security["active_status"]
                or row["snapshot_date"] != security["snapshot_date"]
                or row["security_name"] != security["security_name"]):
            raise ValueError(f"equity crosswalk/security snapshot conflict for {symbol}")

    observed = defaultdict(lambda: {
        "samir_contracts": 0, "socrateai_contracts": 0,
        "samir_quantity": Decimal("0"), "socrateai_quantity": Decimal("0"),
        "samir_amount": Decimal("0"), "socrateai_amount": Decimal("0"),
    })

    def collect(rows, symbol_field, source):
        seen = set()
        for line, row in enumerate(rows, 2):
            symbol = row[symbol_field].strip().upper()
            contract_id = row["contract_no" if source == "samir" else "transaction"]
            trade_date = row["date"]
            if not symbol or not contract_id or not trade_date:
                raise ValueError(f"{source} row {line} missing date, contract or symbol")
            try:
                parsed_trade_date = date.fromisoformat(trade_date).isoformat()
            except ValueError as exc:
                raise ValueError(f"{source} row {line} has invalid ISO trade date: {trade_date!r}") from exc
            if parsed_trade_date != expected_trade_date:
                raise ValueError(f"{source} row {line} trade date {parsed_trade_date} differs from expected {expected_trade_date}")
            key = (trade_date, contract_id)
            if key in seen:
                raise ValueError(f"{source} duplicate date/contract key at row {line}: {key}")
            seen.add(key)
            item = observed[symbol]
            item[f"{source}_contracts"] += 1
            item[f"{source}_quantity"] += _decimal(row["quantity"], "quantity")
            item[f"{source}_amount"] += _decimal(row["amount"], "amount")

    collect(samir, "stock_symbol", "samir")
    collect(socrateai, "symbol", "socrateai")

    symbol_reports = []
    class_counts = Counter()
    for symbol in sorted(observed):
        cross = crosswalk.get(symbol)
        candidate = candidates.get(symbol)
        security = snapshot.get(symbol)
        candidate_class = (candidate or {}).get("instrument_class_from_rendered_list", "")
        security_name = (security or {}).get("security_name", "")
        normalized_name = security_name.casefold()

        if cross:
            scope_class = "IN_SCOPE_EQUITY_CANDIDATE"
            security_id = cross["security_id"]
            evidence = "dated_2026-11-26_equity_crosswalk"
        elif candidate_class.casefold() == "mutual fund":
            scope_class = "OUT_OF_SCOPE_MUTUAL_FUND"
            security_id = (candidate or {}).get("official_snapshot_id") or (security or {}).get("security_id")
            evidence = "dated_target_candidate_instrument_class"
        elif "promoter" in normalized_name:
            scope_class = "OUT_OF_SCOPE_PROMOTER_SHARE"
            security_id = (security or {}).get("security_id")
            evidence = "dated_security_snapshot_name_identifies_promoter_share"
        elif "debenture" in normalized_name:
            scope_class = "OUT_OF_SCOPE_DEBENTURE"
            security_id = (security or {}).get("security_id")
            evidence = "dated_security_snapshot_name_identifies_debenture"
        elif "bond" in normalized_name.split():
            scope_class = "OUT_OF_SCOPE_BOND"
            security_id = (security or {}).get("security_id")
            evidence = "dated_security_snapshot_name_identifies_bond"
        elif candidate_class.casefold() == "equity":
            scope_class = "EQUITY_CANDIDATE_NOT_IN_CROSSWALK"
            security_id = (candidate or {}).get("official_snapshot_id") or (security or {}).get("security_id")
            evidence = "target_candidate_equity_missing_from_equity_crosswalk"
        elif security:
            scope_class = "UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY"
            security_id = security.get("security_id")
            evidence = "dated_security_snapshot_only_no_approved_scope_class"
        else:
            scope_class = "UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH"
            security_id = None
            evidence = "no_dated_snapshot_or_crosswalk_match"

        if scope_class not in SCOPE_CLASSES:
            raise AssertionError(f"unsupported scope class: {scope_class}")
        class_counts[scope_class] += 1
        metrics = observed[symbol]
        symbol_reports.append({
            "symbol": symbol,
            "scope_class": scope_class,
            "security_id": security_id,
            "security_name": (cross or security or {}).get("security_name", ""),
            "candidate_instrument_class": candidate_class or None,
            "snapshot_active_status": (security or cross or {}).get("active_status"),
            "snapshot_date": (security or cross or {}).get("snapshot_date"),
            "evidence": evidence,
            **{key: str(value) if isinstance(value, Decimal) else value
               for key, value in metrics.items()},
        })

    return {
        "schema_version": "1.1",
        "expected_trade_date": expected_trade_date,
        "expected_security_snapshot_date": expected_snapshot_date,
        "audit_status": "review_only_symbol_scope_reconciliation",
        "source_rows": {
            "samir": len(samir),
            "socrateai": len(socrateai),
        },
        "unique_symbols_observed": len(symbol_reports),
        "registry_rows": {
            "equity_crosswalk": len(crosswalk_rows),
            "target_candidates": len(candidate_rows),
            "security_snapshot": len(snapshot_rows),
        },
        "scope_class_counts": dict(sorted(class_counts.items())),
        "symbols": symbol_reports,
        "unobserved_equity_crosswalk_symbols": sorted(set(crosswalk) - set(observed)),
        "policy": {
            "mutual_funds_in_equity_scanner": False,
            "promoter_shares_in_ordinary_equity_scanner": False,
            "debentures_in_equity_scanner": False,
            "unknown_scope_promoted": False,
            "absence_from_archive_means_no_trade": False,
            "canonical_promotion_allowed": False,
            "coverage_admission_allowed": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samir", type=Path, required=True)
    parser.add_argument("--socrateai", type=Path, required=True)
    parser.add_argument("--equity-crosswalk", type=Path, required=True)
    parser.add_argument("--target-candidates", type=Path, required=True)
    parser.add_argument("--security-snapshot", type=Path, required=True)
    parser.add_argument("--expected-trade-date", required=True)
    parser.add_argument("--expected-snapshot-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_floorsheet_symbol_scope(
        args.samir, args.socrateai, args.equity_crosswalk,
        args.target_candidates, args.security_snapshot,
        args.expected_trade_date, args.expected_snapshot_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "unique_symbols_observed": report["unique_symbols_observed"],
        "scope_class_counts": report["scope_class_counts"],
        "canonical_promotion_allowed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
