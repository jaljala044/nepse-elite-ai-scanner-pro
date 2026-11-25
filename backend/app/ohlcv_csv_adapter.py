"""Explicit-mapping OHLCV CSV adapter with row-level exception retention."""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping


FIELDS = ("symbol", "session_date", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class OhlcvCsvMapping:
    columns: Mapping[str, str]
    delimiter: str = ","
    encoding: str = "utf-8-sig"

    def __post_init__(self):
        missing = sorted(set(FIELDS) - set(self.columns))
        if missing:
            raise ValueError(f"OHLCV mapping missing fields: {missing}")
        if len(set(self.columns[f] for f in FIELDS)) != len(FIELDS):
            raise ValueError("OHLCV source headers must be distinct")
        if len(self.delimiter) != 1:
            raise ValueError("delimiter must be one character")


def parse_ohlcv_csv(payload: bytes, *, source_id: str, mapping: OhlcvCsvMapping) -> dict:
    if not source_id.strip():
        raise ValueError("source_id is required")
    digest = hashlib.sha256(payload).hexdigest()
    try:
        decoded = payload.decode(mapping.encoding)
    except (UnicodeDecodeError, LookupError) as exc:
        raise ValueError("payload cannot be decoded with declared encoding") from exc
    reader = csv.DictReader(io.StringIO(decoded, newline=""), delimiter=mapping.delimiter)
    if not reader.fieldnames:
        raise ValueError("OHLCV CSV header is required")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("duplicate OHLCV source headers")
    missing_headers = sorted(set(mapping.columns.values()) - set(reader.fieldnames))
    if missing_headers:
        raise ValueError(f"mapped OHLCV headers absent: {missing_headers}")

    output, exceptions = [], []
    for line, raw in enumerate(reader, start=2):
        if None in raw:
            exceptions.append({"source_row_number": line, "status": "rejected", "reason": "extra_unmapped_columns",
                               "raw_row": raw})
            continue
        values = {key: raw[header] for key, header in mapping.columns.items()}
        try:
            symbol = values["symbol"].strip().upper()
            if not symbol:
                raise ValueError("blank_symbol")
            session = date.fromisoformat(values["session_date"].strip())
            numbers = {key: Decimal(values[key].strip()) for key in ("open", "high", "low", "close", "volume")}
            if any(not x.is_finite() for x in numbers.values()):
                raise ValueError("non_finite_numeric_value")
            if any(x <= 0 for x in numbers.values()):
                raise ValueError("non_positive_ohlcv_value")
            flags = []
            if numbers["high"] < max(numbers["open"], numbers["low"], numbers["close"]):
                flags.append("high_bound_violation")
            if numbers["low"] > min(numbers["open"], numbers["high"], numbers["close"]):
                flags.append("low_bound_violation")
            record = {
                "source_id": source_id, "source_payload_sha256": digest,
                "source_row_number": line, "symbol": symbol,
                "session_date": session.isoformat(),
                **{key: str(value) for key, value in numbers.items()},
                "status": "quarantined_exception" if flags else "parsed_review_required",
                "exception_flags": flags, "raw_mapped_values": values,
            }
            output.append(record)
            if flags:
                exceptions.append(record)
        except (ValueError, InvalidOperation) as exc:
            exceptions.append({"source_id": source_id, "source_payload_sha256": digest,
                               "source_row_number": line, "status": "rejected",
                               "reason": str(exc), "raw_mapped_values": values})
    return {
        "source_id": source_id, "source_payload_sha256": digest,
        "input_rows": len(output) + sum(1 for x in exceptions if x.get("status") == "rejected" and "raw_row" in x),
        "parsed_rows": len(output), "exception_rows": len(exceptions),
        "rows": output, "exceptions": exceptions,
        "source_specific_mapping_verified": False,
        "promotion_allowed": False,
        "policy": "explicit_mapping_and_retain_all_invalid_or_unverified_rows",
    }
