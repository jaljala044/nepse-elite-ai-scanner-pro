"""Explicit-mapping CSV adapter for normalized floorsheet contract rows.

No vendor/NEPSE column names are assumed. A caller must supply a reviewed
header mapping from a real source sample. The adapter preserves physical CSV
line numbers and the SHA-256 of the exact input bytes.
"""
from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Mapping

from app.floorsheet_contract import FloorsheetContract


REQUIRED_FIELDS = (
    "trade_date", "contract_id", "symbol", "buyer_broker_code",
    "seller_broker_code", "quantity", "rate", "amount",
)


@dataclass(frozen=True)
class CsvFloorsheetMapping:
    """Map normalized field names to exact source header strings."""
    columns: Mapping[str, str]
    delimiter: str = ","
    encoding: str = "utf-8-sig"

    def __post_init__(self):
        missing = sorted(set(REQUIRED_FIELDS) - set(self.columns))
        extra = sorted(set(self.columns) - set(REQUIRED_FIELDS))
        if missing:
            raise ValueError(f"mapping missing normalized fields: {missing}")
        if extra:
            raise ValueError(f"mapping contains unsupported normalized fields: {extra}")
        if any(not isinstance(self.columns[k], str) or not self.columns[k].strip() for k in REQUIRED_FIELDS):
            raise ValueError("mapped source headers must be nonblank strings")
        if len(set(self.columns[k] for k in REQUIRED_FIELDS)) != len(REQUIRED_FIELDS):
            raise ValueError("each normalized field must map to a distinct source header")
        if len(self.delimiter) != 1:
            raise ValueError("delimiter must be exactly one character")


def parse_floorsheet_csv(
    payload: bytes,
    *,
    source_id: str,
    mapping: CsvFloorsheetMapping,
) -> dict:
    """Parse only explicitly mapped CSV headers; never infer unknown columns."""
    if not source_id.strip():
        raise ValueError("source_id is required")
    digest = hashlib.sha256(payload).hexdigest()
    try:
        text = payload.decode(mapping.encoding)
    except (UnicodeDecodeError, LookupError) as exc:
        raise ValueError("payload cannot be decoded with declared encoding") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=mapping.delimiter)
    if reader.fieldnames is None:
        raise ValueError("CSV header row is required")
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("duplicate source headers are not allowed")
    missing_headers = sorted(set(mapping.columns.values()) - set(reader.fieldnames))
    if missing_headers:
        raise ValueError(f"mapped source headers absent from CSV: {missing_headers}")

    rows = []
    errors = []
    for physical_line, source_row in enumerate(reader, start=2):
        if None in source_row:
            errors.append({
                "source_row_number": physical_line,
                "error": "extra_unmapped_columns",
                "raw_source_row": dict(source_row),
            })
            continue
        mapped = {field: source_row[header] for field, header in mapping.columns.items()}
        try:
            contract = FloorsheetContract.from_mapping(
                mapped, source_id=source_id, payload_sha256=digest,
                row_number=physical_line,
            )
        except (KeyError, ValueError, InvalidOperation) as exc:
            errors.append({
                "source_row_number": physical_line,
                "error": str(exc),
                "raw_source_row": dict(source_row),
            })
            continue
        rows.append(contract)
    return {
        "source_id": source_id,
        "source_payload_sha256": digest,
        "encoding": mapping.encoding,
        "delimiter": mapping.delimiter,
        "header_mapping": dict(mapping.columns),
        "input_data_rows": len(rows) + len(errors),
        "parsed_rows": len(rows),
        "rejected_rows": len(errors),
        "rows": rows,
        "errors": errors,
        "source_specific_mapping_verified": False,
        "policy": "explicit_mapping_no_header_guessing",
    }
