"""Normalize source-specific NEPSE daily sector-index CSV/CSV.GZ files."""
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
SILVER = ROOT / "data" / "silver" / "indices"
QUARANTINE = ROOT / "data" / "quarantine"

ALIASES = {
    "index_date": ("date", "business_date", "calculation_date"),
    "sector": ("sector", "index_name", "sector_name"),
    "open": ("open", "opening"),
    "high": ("high",),
    "low": ("low",),
    "close": ("close", "closing"),
    "absolute_change": ("absolute_change", "change", "point_change"),
    "percentage_change": ("percentage_change", "percent_change", "change_pct"),
    "week52_high": ("number_52_weeks_high", "week52_high", "52_week_high"),
    "week52_low": ("number_52_weeks_low", "week52_low", "52_week_low"),
    "turnover_values": ("turnover_values", "turnover", "turnover_amount"),
    "turnover_volume": ("turnover_volume", "volume"),
    "total_transaction": ("total_transaction", "transactions", "transaction_count"),
    "serial_no": ("sn", "serial_no"),
    "source_id": ("id", "source_id"),
    "created_at": ("created_at",),
}

OUTPUT_FIELDS = [
    "index_date", "sector", "open", "high", "low", "close",
    "absolute_change", "percentage_change_pct", "week52_high", "week52_low",
    "turnover_values", "turnover_volume", "total_transaction",
    "serial_no", "source_id", "created_at", "source", "source_file", "source_line",
]

def _header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")

def _date(value: str) -> date:
    raw = value.strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValueError(f"invalid index date {value!r}") from exc

def _number(value: str, field: str, *, optional: bool = False, nonnegative: bool = False) -> Decimal | None:
    raw = value.strip().replace(",", "")
    if not raw:
        if optional:
            return None
        raise ValueError(f"missing {field}")
    try:
        result = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"non-finite {field}")
    if nonnegative and result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result

def _columns(fieldnames: list[str]) -> dict[str, str]:
    found = {_header(name): name for name in fieldnames if name}
    resolved = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in found:
                resolved[canonical] = found[alias]
                break
    required = {
        "index_date", "sector", "open", "high", "low", "close",
        "absolute_change", "percentage_change", "turnover_values",
        "turnover_volume", "total_transaction",
    }
    missing = required - set(resolved)
    if missing:
        raise ValueError("index CSV missing columns: " + ", ".join(sorted(missing)))
    return resolved

def _value(row: dict[str, Any], cols: dict[str, str], key: str) -> str:
    column = cols.get(key)
    value = row.get(column) if column else ""
    return "" if value is None else str(value).strip()

def _canonical(raw: dict[str, Any], cols: dict[str, str], source: str,
               source_file: str, line_no: int) -> dict[str, str]:
    index_date = _date(_value(raw, cols, "index_date"))
    sector = _value(raw, cols, "sector").strip()
    if not sector:
        raise ValueError("missing sector/index name")

    numbers = {}
    for field in ("open", "high", "low", "close"):
        numbers[field] = _number(_value(raw, cols, field), field)
        if numbers[field] <= 0:
            raise ValueError(f"{field} must be positive")
    if numbers["high"] < max(numbers["open"], numbers["low"], numbers["close"]):
        raise ValueError("high is below open/low/close")
    if numbers["low"] > min(numbers["open"], numbers["high"], numbers["close"]):
        raise ValueError("low is above open/high/close")

    absolute_change = _number(_value(raw, cols, "absolute_change"), "absolute_change")
    pct_text = _value(raw, cols, "percentage_change").replace("%", "").strip()
    percentage_change = _number(pct_text, "percentage_change")
    turnover_values = _number(_value(raw, cols, "turnover_values"), "turnover_values", nonnegative=True)
    turnover_volume = _number(_value(raw, cols, "turnover_volume"), "turnover_volume", nonnegative=True)
    total_transaction = _number(_value(raw, cols, "total_transaction"), "total_transaction", nonnegative=True)

    def optional(field: str) -> str:
        val = _number(_value(raw, cols, field), field, optional=True, nonnegative=True)
        return "" if val is None else format(val, "f")

    serial = _value(raw, cols, "serial_no")
    source_id = _value(raw, cols, "source_id")
    created_at = _value(raw, cols, "created_at")
    return {
        "index_date": index_date.isoformat(),
        "sector": sector,
        **{key: format(val, "f") for key, val in numbers.items()},
        "absolute_change": format(absolute_change, "f"),
        "percentage_change_pct": format(percentage_change, "f"),
        "week52_high": optional("week52_high"),
        "week52_low": optional("week52_low"),
        "turnover_values": format(turnover_values, "f"),
        "turnover_volume": format(turnover_volume, "f"),
        "total_transaction": format(total_transaction, "f"),
        "serial_no": serial,
        "source_id": source_id,
        "created_at": created_at,
        "source": source,
        "source_file": source_file,
        "source_line": str(line_no),
    }

def normalize_sector_index_csv(input_path: str | Path, *, source: str,
                               max_reject_ratio: float = 0.10) -> dict[str, Any]:
    path = Path(input_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    if not 0 <= max_reject_ratio < 1:
        raise ValueError("max_reject_ratio must be in [0, 1)")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    accepted: dict[tuple[str, str], dict[str, str]] = {}
    rejected = []
    seen = 0
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("index CSV has no header")
        cols = _columns(reader.fieldnames)
        for line_no, raw in enumerate(reader, start=2):
            seen += 1
            try:
                record = _canonical(raw, cols, source, path.name, line_no)
                key = (record["index_date"], record["sector"].casefold())
                previous = accepted.get(key)
                if previous:
                    comparable_old = {k:v for k,v in previous.items() if k not in ("source_file", "source_line")}
                    comparable_new = {k:v for k,v in record.items() if k not in ("source_file", "source_line")}
                    if comparable_old != comparable_new:
                        raise ValueError(f"conflicting duplicate index for {record['sector']}")
                    continue
                accepted[key] = record
            except Exception as exc:
                rejected.append({"source_file": path.name, "source_line": line_no,
                                 "raw": raw, "reason": f"{type(exc).__name__}: {exc}"})

    reject_ratio = len(rejected) / seen if seen else 0.0
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    quarantine_path = None
    if rejected:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        quarantine_path = QUARANTINE / f"index_rejects_{stamp}_{digest[:10]}.jsonl"
        with quarantine_path.open("w", encoding="utf-8") as handle:
            for item in rejected:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    if seen and reject_ratio > max_reject_ratio:
        raise ValueError(
            f"Index reject ratio {reject_ratio:.2%} exceeds threshold {max_reject_ratio:.2%}; "
            f"no silver rows written. Quarantine: {quarantine_path}"
        )

    by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in accepted.values():
        by_date[record["index_date"]].append(record)
    sessions = []
    for day, rows in sorted(by_date.items()):
        rows.sort(key=lambda row: row["sector"].casefold())
        out_dir = SILVER / f"date={day}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "indices.csv"
        existing = {}
        if out_path.exists():
            with out_path.open("r", encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    existing[(row["index_date"], row["sector"].casefold())] = row
        for row in rows:
            key = (row["index_date"], row["sector"].casefold())
            if key in existing:
                old = {k:v for k,v in existing[key].items() if k not in ("source_file", "source_line")}
                new = {k:v for k,v in row.items() if k not in ("source_file", "source_line")}
                if old != new:
                    raise ValueError(f"Existing silver conflict for {day} sector {row['sector']}")
            else:
                existing[key] = row
        with out_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(sorted(existing.values(), key=lambda row: row["sector"].casefold()))
        sessions.append({"date": day, "rows": len(existing), "path": str(out_path.relative_to(ROOT))})

    return {
        "source": source, "input_file": path.name, "input_sha256": digest,
        "rows_seen": seen, "unique_rows_accepted": len(accepted),
        "rows_rejected": len(rejected), "reject_ratio": round(reject_ratio, 6),
        "quarantine_path": str(quarantine_path.relative_to(ROOT)) if quarantine_path else None,
        "sessions_written": sessions,
        "status": "normalized" if not rejected else "normalized_with_quarantine",
    }
