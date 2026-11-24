"""Cross-source daily NEPSE floorsheet reconciliation.

Reads immutable local source CSVs, normalizes schema aliases, validates contract
identity/date/arithmetic, and compares contract-level sets and fields. It never
chooses a canonical source or imports into the database.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ALIASES = {
    "date": ("date", "trading_date", "calculation_date"),
    "contract": ("contract_no", "contract", "transaction", "contractno"),
    "symbol": ("symbol", "stock_symbol", "security"),
    "buyer": ("buyer", "buyer_broker", "buyer_broker_code"),
    "seller": ("seller", "seller_broker", "seller_broker_code"),
    "quantity": ("quantity", "qty", "shares"),
    "rate": ("rate", "price", "trade_price"),
    "amount": ("amount", "turnover", "value"),
}
COMPARISON_FIELDS = ("symbol", "buyer", "seller", "quantity", "rate")


def _decimal(value: Any) -> Decimal:
    text = str(value).strip().replace(",", "")
    if not text:
        raise ValueError("empty numeric field")
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(K|LAC\.?|LAKH|CR)?", text, re.I)
    if not match:
        return Decimal(text)
    number = Decimal(match.group(1))
    suffix = (match.group(2) or "").upper().rstrip(".")
    factor = {"": 1, "K": 1000, "LAC": 100000, "LAKH": 100000, "CR": 10000000}[suffix]
    return number * factor


def _canonical(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f") if normalized else "0"


def _field_map(headers: list[str]) -> dict[str, str]:
    normalized = {header.strip().lower().replace(" ", "_"): header for header in headers}
    mapping = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[canonical] = normalized[alias]
                break
    missing = [name for name in ("contract", "symbol", "buyer", "seller", "quantity", "rate") if name not in mapping]
    if missing:
        raise ValueError(f"missing required floorsheet columns: {', '.join(missing)}")
    return mapping


def audit_source(name: str, path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    records: dict[str, dict[str, Any]] = {}
    seen_contracts: set[str] = set()
    duplicates: list[str] = []
    invalid: list[dict[str, Any]] = []
    date_mismatches: list[dict[str, str]] = []
    qty_total = 0
    turnover_total = Decimal("0")
    symbol_totals: Counter[str] = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path}: missing CSV header")
        mapping = _field_map(reader.fieldnames)
        for line, row in enumerate(reader, start=2):
            try:
                contract = str(row[mapping["contract"]]).strip()
                symbol = str(row[mapping["symbol"]]).strip().upper()
                buyer = str(row[mapping["buyer"]]).strip()
                seller = str(row[mapping["seller"]]).strip()
                quantity = _decimal(row[mapping["quantity"]])
                rate = _decimal(row[mapping["rate"]])
                if not contract or not symbol or not buyer or not seller:
                    raise ValueError("missing contract, symbol or broker code")
                if contract in seen_contracts:
                    duplicates.append(contract)
                    continue
                seen_contracts.add(contract)
                if quantity <= 0 or quantity != quantity.to_integral_value():
                    raise ValueError("quantity must be a positive integer")
                if rate <= 0:
                    raise ValueError("rate must be positive")
                amount = _decimal(row[mapping["amount"]]) if "amount" in mapping and row.get(mapping["amount"]) else quantity * rate
                if abs(quantity * rate - amount) > Decimal("1.00"):
                    raise ValueError("amount differs from quantity × rate by more than NPR 1")
                trade_date = str(row.get(mapping.get("date", ""), "")).strip() if "date" in mapping else ""
                contract_date = contract[:8] if re.fullmatch(r"\d{8}\d+", contract) else ""
                if not trade_date and contract_date:
                    trade_date = f"{contract_date[:4]}-{contract_date[4:6]}-{contract_date[6:8]}"
                if trade_date and contract_date and trade_date.replace("-", "")[:8] != contract_date:
                    date_mismatches.append({"line": line, "contract": contract, "date": trade_date})
                records[contract] = {
                    "contract": contract, "date": trade_date, "symbol": symbol,
                    "buyer": buyer, "seller": seller,
                    "quantity": _canonical(quantity), "rate": _canonical(rate),
                    "amount": _canonical(amount),
                }
                qty_total += int(quantity)
                turnover_total += quantity * rate
                symbol_totals[symbol] += int(quantity)
            except (ValueError, InvalidOperation, TypeError, KeyError) as exc:
                invalid.append({"line": line, "error": str(exc), "row": row})
    dates = sorted({r["date"] for r in records.values() if r["date"]})
    return {
        "name": name, "path": str(path), "sha256": digest,
        "rows": sum(1 for _ in path.open("r", encoding="utf-8-sig")) - 1,
        "valid_contracts": len(records), "duplicate_contracts": duplicates,
        "invalid_rows": invalid, "date_mismatches": date_mismatches,
        "dates": dates, "shares": qty_total,
        "turnover_npr": _canonical(turnover_total),
        "symbols": len(symbol_totals),
        "records": records,
    }


def reconcile_sources(sources: list[tuple[str, Path]]) -> dict[str, Any]:
    audited = [audit_source(name, path) for name, path in sources]
    all_dates = sorted({day for source in audited for day in source["dates"]})
    sessions = []
    for day in all_dates:
        daily = []
        for source in audited:
            records = {key: row for key, row in source["records"].items() if row["date"] == day}
            if records:
                daily.append((source["name"], records))
        if len(daily) < 2:
            continue
        base_name, base = daily[0]
        comparisons = []
        for other_name, other in daily[1:]:
            base_ids, other_ids = set(base), set(other)
            only_base = sorted(base_ids - other_ids)
            only_other = sorted(other_ids - base_ids)
            common = sorted(base_ids & other_ids)
            field_conflicts = []
            for contract in common:
                left, right = base[contract], other[contract]
                differing = {field: {"left": left[field], "right": right[field]}
                             for field in COMPARISON_FIELDS if left[field] != right[field]}
                if differing:
                    field_conflicts.append({"contract": contract, "differences": differing})
            comparisons.append({
                "left_source": base_name, "right_source": other_name,
                "left_contracts": len(base), "right_contracts": len(other),
                "common_contracts": len(common),
                "left_only_count": len(only_base), "right_only_count": len(only_other),
                "left_only_contracts": only_base, "right_only_contracts": only_other,
                "field_conflict_count": len(field_conflicts),
                "field_conflicts": field_conflicts,
            })
        sessions.append({"date": day, "sources": [name for name, _ in daily], "comparisons": comparisons})
    quality_failures = sum(
        len(s["duplicate_contracts"]) + len(s["invalid_rows"]) + len(s["date_mismatches"])
        for s in audited
    )
    completeness_conflicts = sum(
        c["left_only_count"] + c["right_only_count"] + c["field_conflict_count"]
        for session in sessions for c in session["comparisons"]
    )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_multi_source_contract_reconciliation",
        "sources": [{k: v for k, v in source.items() if k != "records"} for source in audited],
        "sessions": sessions,
        "quality_failure_count": quality_failures,
        "cross_source_difference_count": completeness_conflicts,
        "gate": "FAIL" if quality_failures or completeness_conflicts else "PASS",
        "limitations": [
            "A matching contract ID is not proof of exchange-origin authenticity.",
            "Different source snapshots can be incomplete or corrected; no canonical source is auto-selected.",
            "Broker codes are execution-channel identifiers, not beneficial-owner identities.",
            "No execution time is inferred from contract sequence numbers.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, metavar="NAME=CSV")
    parser.add_argument("--output", type=Path, default=Path("data/reports/floorsheet-source-reconciliation.json"))
    args = parser.parse_args()
    sources = []
    for item in args.source:
        if "=" not in item:
            parser.error("--source must be NAME=CSV")
        name, filename = item.split("=", 1)
        path = Path(filename)
        if not name.strip() or not path.is_file():
            parser.error(f"invalid source specification: {item}")
        sources.append((name.strip(), path))
    result = reconcile_sources(sources)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output), "gate": result["gate"],
        "quality_failure_count": result["quality_failure_count"],
        "cross_source_difference_count": result["cross_source_difference_count"],
        "sessions": result["sessions"],
    }, indent=2))
    if result["gate"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
