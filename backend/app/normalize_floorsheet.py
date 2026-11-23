"""Normalize a source-specific NEPSE trade-level floorsheet CSV into silver partitions.

The parser preserves broker codes as execution-channel IDs and never infers investor identity.
Raw source files remain untouched; rejected rows are quarantined with reasons.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SILVER = ROOT / "data" / "silver" / "floorsheet"
QUARANTINE = ROOT / "data" / "quarantine"

ALIASES = {
    "contract_no": ("contract_no", "contractno", "contract_id", "contractid", "contract_number"),
    "trade_date": ("calculation_date", "business_date", "trade_date", "date"),
    "execution_time": ("time", "trade_time", "tradetime", "execution_time"),
    "symbol": ("stock_symbol", "symbol", "security_symbol"),
    "sector": ("sector", "sector_name", "industry"),
    "buyer_broker_code": ("buyer", "buyer_broker", "buyer_broker_id", "buyer_id"),
    "seller_broker_code": ("seller", "seller_broker", "seller_broker_id", "seller_id"),
    "quantity": ("quantity", "qty", "trade_quantity"),
    "price": ("rate", "price", "trade_price"),
    "amount": ("amount", "turnover", "trade_amount"),
}

OUTPUT_FIELDS = [
    "trade_date", "execution_time", "contract_no", "symbol", "sector",
    "buyer_broker_code", "seller_broker_code", "quantity", "price", "amount",
    "source", "source_file", "source_line",
]

def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")

def _parse_date(value: str) -> date:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValueError(f"unrecognized trade date {value!r}") from exc

def _decimal(value: str, field: str) -> Decimal:
    raw = value.strip().replace(",", "")
    try:
        result = Decimal(raw)
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"non-finite {field}: {value!r}")
    return result

def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {_normalize_header(name): name for name in fieldnames if name}
    result: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                result[canonical] = normalized[alias]
                break
    required = {
        "contract_no", "trade_date", "symbol", "quantity", "price", "amount"
    }
    missing = required - set(result)
    if missing:
        raise ValueError("floorsheet CSV missing columns: " + ", ".join(sorted(missing)))
    return result

def _get(row: dict[str, Any], columns: dict[str, str], key: str) -> str:
    source_column = columns.get(key)
    if not source_column:
        return ""
    value = row.get(source_column)
    return "" if value is None else str(value).strip()

def _canonical_row(
    raw: dict[str, Any], columns: dict[str, str], source: str,
    source_file: str, line_no: int,
) -> dict[str, str]:
    trade_date = _parse_date(_get(raw, columns, "trade_date"))
    contract = _get(raw, columns, "contract_no")
    symbol = _get(raw, columns, "symbol").upper()
    if not contract:
        raise ValueError("missing contract number")
    if not symbol or len(symbol) > 20:
        raise ValueError("invalid or missing stock symbol")

    qty_decimal = _decimal(_get(raw, columns, "quantity"), "quantity")
    if qty_decimal <= 0 or qty_decimal != qty_decimal.to_integral_value():
        raise ValueError("quantity must be a positive whole number")
    qty = int(qty_decimal)

    price = _decimal(_get(raw, columns, "price"), "price")
    amount = _decimal(_get(raw, columns, "amount"), "amount")
    if price <= 0 or amount <= 0:
        raise ValueError("price and amount must be positive")
    difference = abs((qty_decimal * price) - amount)
    # Allow <= NPR 1.00 rounding discrepancy, and preserve original reported amount.
    if difference > Decimal("1.00"):
        raise ValueError(f"quantity × price differs from amount by {difference}")

    execution_time = _get(raw, columns, "execution_time")
    if execution_time.lower() in ("none", "null", "nan", "nat"):
        execution_time = ""

    buyer = _get(raw, columns, "buyer_broker_code")
    seller = _get(raw, columns, "seller_broker_code")
    return {
        "trade_date": trade_date.isoformat(),
        "execution_time": execution_time,
        "contract_no": contract,
        "symbol": symbol,
        "sector": _get(raw, columns, "sector"),
        "buyer_broker_code": buyer,
        "seller_broker_code": seller,
        "quantity": str(qty),
        "price": format(price, "f"),
        "amount": format(amount, "f"),
        "source": source,
        "source_file": source_file,
        "source_line": str(line_no),
    }

def _key(row: dict[str, str]) -> tuple[str, str]:
    return row["trade_date"], row["contract_no"]

def normalize_floorsheet_csv(
    input_path: str | Path,
    *,
    source: str,
    max_reject_ratio: float = 0.10,
) -> dict[str, Any]:
    path = Path(input_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if not 0 <= max_reject_ratio < 1:
        raise ValueError("max_reject_ratio must be in [0, 1)")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    accepted: dict[tuple[str, str], dict[str, str]] = {}
    rejected: list[dict[str, Any]] = []
    row_count = 0

    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        columns = _resolve_columns(reader.fieldnames)
        for line_no, raw in enumerate(reader, start=2):
            row_count += 1
            try:
                record = _canonical_row(raw, columns, source, path.name, line_no)
                key = _key(record)
                previous = accepted.get(key)
                if previous is not None:
                    comparable_prev = {k: v for k, v in previous.items() if k not in ("source_file", "source_line")}
                    comparable_now = {k: v for k, v in record.items() if k not in ("source_file", "source_line")}
                    if comparable_prev != comparable_now:
                        raise ValueError(f"conflicting duplicate contract {key[1]}")
                    continue
                accepted[key] = record
            except Exception as exc:
                rejected.append({"source_file": path.name, "source_line": line_no,
                                 "raw": raw, "reason": f"{type(exc).__name__}: {exc}"})

    reject_ratio = len(rejected) / row_count if row_count else 0.0
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    quarantine_path = None
    if rejected:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        quarantine_path = QUARANTINE / f"floorsheet_rejects_{stamp}_{digest[:10]}.jsonl"
        with quarantine_path.open("w", encoding="utf-8") as handle:
            for item in rejected:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    if row_count and reject_ratio > max_reject_ratio:
        raise ValueError(
            f"Reject ratio {reject_ratio:.2%} exceeds threshold {max_reject_ratio:.2%}; "
            f"accepted rows were not written. Quarantine: {quarantine_path}"
        )

    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in accepted.values():
        by_date[record["trade_date"]].append(record)

    written = []
    for trade_day, rows in sorted(by_date.items()):
        rows.sort(key=lambda row: (row["contract_no"], row["symbol"]))
        day_dir = SILVER / f"date={trade_day}"
        day_dir.mkdir(parents=True, exist_ok=True)
        out_path = day_dir / "floorsheet.csv"
        # Idempotent upsert by (trade_date, contract_no); keep source provenance of first import.
        existing: dict[tuple[str, str], dict[str, str]] = {}
        if out_path.exists():
            with out_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    existing[_key(row)] = row
        for row in rows:
            key = _key(row)
            if key in existing:
                old = {k: v for k, v in existing[key].items() if k not in ("source_file", "source_line")}
                new = {k: v for k, v in row.items() if k not in ("source_file", "source_line")}
                if old != new:
                    raise ValueError(f"Existing silver conflict for {trade_day} contract {key[1]}")
            else:
                existing[key] = row
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(sorted(existing.values(), key=lambda r: (r["contract_no"], r["symbol"])))
        written.append({
            "trade_date": trade_day, "source_rows": len(rows),
            "silver_rows": len(existing), "path": str(out_path.relative_to(ROOT)),
        })

    return {
        "source": source, "input_file": path.name, "input_sha256": digest,
        "rows_seen": row_count, "unique_rows_accepted": len(accepted),
        "rows_rejected": len(rejected), "reject_ratio": round(reject_ratio, 6),
        "quarantine_path": str(quarantine_path.relative_to(ROOT)) if quarantine_path else None,
        "sessions_written": written,
        "status": "normalized" if not rejected else "normalized_with_quarantine",
        "warning": "Broker codes identify exchange execution channels; they do not identify beneficial owners or prove institutional accumulation/distribution.",
    }
