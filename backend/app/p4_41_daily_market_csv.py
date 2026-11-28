"""Steps 160-169: validate daily market-wide ShareSansar CSV archive rows."""
from __future__ import annotations

import csv
import hashlib
import math
import re
from datetime import date
from io import StringIO
from typing import Any

REQUIRED = ("Symbol", "Open", "High", "Low", "Close", "Vol", "Turnover", "Trans.")
PARSER_VERSION = "p4.41-csv-integrity-v2"
_NUMBER = re.compile(r"^-?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?$")


def _number(value: Any) -> float:
    if value is None:
        raise ValueError("missing_numeric")
    raw = str(value).strip()
    if raw.lower() in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        raise ValueError("non_finite_numeric")
    if not _NUMBER.fullmatch(raw):
        raise ValueError("malformed_numeric")
    parsed = float(raw.replace(",", ""))
    if not math.isfinite(parsed):
        raise ValueError("non_finite_numeric")
    return parsed


def _quarantine(line: int, symbol: str, row: dict, reason: str) -> dict:
    return {"source_line": line, "symbol": symbol, "reasons": [reason], "raw_row": row}


def parse_daily_market_csv(text: str, *, session_date: str, source_url: str, retrieved_at: str) -> dict[str, Any]:
    """Parse UTF-8 CSV text, retain a digest, and quarantine malformed/ambiguous rows."""
    try:
        session = date.fromisoformat(session_date).isoformat()
    except (TypeError, ValueError):
        return {"status": "REJECTED", "errors": ["invalid_session_date"], "records": [],
                "quarantined_rows": [], "production_admission_allowed": False}
    if not isinstance(text, str):
        return {"status": "REJECTED", "errors": ["invalid_csv_text"], "records": [],
                "quarantined_rows": [], "production_admission_allowed": False}

    raw_bytes = text.encode("utf-8")
    artifact = {
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "byte_count": len(raw_bytes),
        "encoding": "utf-8",
        "source_url": source_url,
        "retrieved_at": retrieved_at,
        "parser_version": PARSER_VERSION,
    }
    errors: list[str] = []
    warnings: list[str] = []
    records: list[dict] = []
    quarantined: list[dict] = []
    seen: dict[str, int] = {}
    reader = csv.DictReader(StringIO(text, newline=""), restkey="__extra_fields__", strict=True)
    headers = reader.fieldnames or []
    missing = [column for column in REQUIRED if column not in headers]
    if missing:
        return {"status": "REJECTED", "errors": ["missing_columns:" + ",".join(missing)],
                "records": [], "quarantined_rows": [], "source_artifact": artifact,
                "production_admission_allowed": False}

    try:
        for line, row in enumerate(reader, start=2):
            raw_row = dict(row)
            symbol = (row.get("Symbol") or "").strip().upper()
            if not symbol:
                errors.append(f"line_{line}_missing_symbol")
                quarantined.append(_quarantine(line, symbol, raw_row, "missing_symbol"))
                continue
            if row.get("__extra_fields__") is not None:
                quarantined.append(_quarantine(line, symbol, raw_row, "extra_csv_fields"))
                warnings.append(f"line_{line}_quarantined_{symbol}:extra_csv_fields")
                continue
            missing_values = [column for column in REQUIRED if row.get(column) in (None, "")]
            if missing_values:
                quarantined.append(_quarantine(line, symbol, raw_row, "missing_row_fields:" + ",".join(missing_values)))
                warnings.append(f"line_{line}_quarantined_{symbol}:missing_row_fields")
                continue
            if symbol in seen:
                previous_line = seen[symbol]
                previous = next((item for item in records if item["symbol"] == symbol), None)
                if previous is not None:
                    records.remove(previous)
                    quarantined.append(_quarantine(previous_line, symbol, previous["raw_row"], "duplicate_symbol"))
                quarantined.append(_quarantine(line, symbol, raw_row, "duplicate_symbol"))
                errors.append(f"line_{line}_duplicate_symbol_{symbol}")
                warnings.append(f"symbol_{symbol}_ambiguous_duplicate_rows")
                continue
            seen[symbol] = line
            try:
                o, h, low, close = (_number(row[key]) for key in ("Open", "High", "Low", "Close"))
                volume = _number(row["Vol"])
                turnover = _number(row["Turnover"])
                transactions = _number(row["Trans."])
                reasons = []
                if min(o, h, low, close) <= 0 or low > min(o, close) or h < max(o, close) or low > h:
                    reasons.append("invalid_ohlc")
                if min(volume, turnover, transactions) < 0:
                    reasons.append("negative_activity")
                if reasons:
                    quarantined.append(_quarantine(line, symbol, raw_row, ",".join(reasons)))
                    warnings.append(f"line_{line}_quarantined_{symbol}:" + ",".join(reasons))
                    continue
                records.append({
                    "symbol": symbol, "session_date": session, "open": o, "high": h, "low": low, "close": close,
                    "volume": volume, "turnover": turnover, "transactions": transactions,
                    "provider": "sharesansar_scraper_public_archive", "source_url": source_url,
                    "retrieved_at": retrieved_at, "source_class": "UNOFFICIAL_THIRD_PARTY_ARCHIVE",
                    "scope": "DAILY_MARKET_WIDE_CSV", "quality": "RESEARCH_ONLY",
                    "source_artifact_sha256": artifact["sha256"], "parser_version": PARSER_VERSION,
                    "source_line": line, "raw_row": raw_row, "production_admission_allowed": False,
                })
            except (TypeError, ValueError) as exc:
                reason = str(exc) if str(exc) in {"missing_numeric", "malformed_numeric", "non_finite_numeric"} else "invalid_numeric"
                quarantined.append(_quarantine(line, symbol, raw_row, reason))
                warnings.append(f"line_{line}_quarantined_{symbol}:{reason}")
    except csv.Error as exc:
        errors.append("malformed_csv:" + str(exc))

    status = "REJECTED" if errors else ("RESEARCH_ONLY_WITH_QUARANTINE" if quarantined else "RESEARCH_ONLY_VALIDATED")
    return {
        "status": status, "errors": errors, "warnings": warnings, "records": records,
        "quarantined_rows": quarantined, "row_count": len(records),
        "source_row_count": len(records) + len(quarantined), "quarantined_row_count": len(quarantined),
        "unique_symbols": len(seen), "session_date": session, "source_artifact": artifact,
        "file_scope": "MARKET_WIDE_DAILY_SNAPSHOT", "production_admission_allowed": False,
    }


def find_symbol_record(parsed: dict[str, Any], symbol: str) -> dict[str, Any]:
    key = symbol.strip().upper()
    matches = [record for record in parsed.get("records", []) if record["symbol"] == key]
    quarantined = [record for record in parsed.get("quarantined_rows", []) if record["symbol"] == key]
    if quarantined:
        return {"status": "QUARANTINED_ROW", "record": None, "evidence": quarantined}
    if len(matches) == 1:
        return {"status": "FOUND", "record": matches[0]}
    if not matches:
        return {"status": "NOT_PRESENT_IN_ARCHIVE_FILE", "record": None}
    return {"status": "AMBIGUOUS_DUPLICATE", "record": None}
