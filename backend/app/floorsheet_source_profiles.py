"""Declared source profiles for explicitly mapping public NEPSE floorsheet CSVs.

Profiles describe publisher-declared headers. They do not replace verification
against the exact raw CSV bytes being ingested.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.floorsheet_csv_adapter import CsvFloorsheetMapping


UREK_REPO_ID = "urekmazino69/Nepse-floorsheet-and-indices"
UREK_PINNED_REVISION = "11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0"
UREK_FOLDER = "floorsheet"

UREK_DECLARED_HEADERS = (
    "contract_no",
    "calculation_date",
    "time",
    "stock_symbol",
    "sector",
    "buyer",
    "seller",
    "quantity",
    "rate",
    "amount",
    "id",
)

UREK_CANONICAL_COLUMNS = {
    "trade_date": "calculation_date",
    "contract_id": "contract_no",
    "symbol": "stock_symbol",
    "buyer_broker_code": "buyer",
    "seller_broker_code": "seller",
    "quantity": "quantity",
    "rate": "rate",
    "amount": "amount",
}

# These source fields are not part of FloorsheetContract. They remain available
# in the immutable raw CSV and must not be fabricated into canonical fields.
UREK_SOURCE_ONLY_HEADERS = ("time", "sector", "id")


@dataclass(frozen=True)
class HeaderReview:
    valid: bool
    missing_headers: tuple[str, ...]
    unexpected_headers: tuple[str, ...]
    duplicate_headers: tuple[str, ...]
    observed_headers: tuple[str, ...]
    profile_id: str
    evidence_status: str = "publisher_schema_declared_raw_header_not_yet_reviewed"


def urek_floorsheet_mapping() -> CsvFloorsheetMapping:
    """Return the explicit Urek header map; caller must verify it on raw bytes."""
    return CsvFloorsheetMapping(columns=dict(UREK_CANONICAL_COLUMNS))


def review_urek_floorsheet_headers(headers: Iterable[str]) -> HeaderReview:
    """Compare a real CSV header row with the exact publisher-declared schema."""
    if isinstance(headers, (str, bytes)):
        raise ValueError("headers must be an iterable of header strings, not text")
    observed = tuple(headers)
    if any(not isinstance(item, str) or not item.strip() for item in observed):
        raise ValueError("headers must contain only nonblank strings")

    duplicates = tuple(sorted({
        item for item in observed if observed.count(item) > 1
    }))
    expected = set(UREK_DECLARED_HEADERS)
    actual = set(observed)
    missing = tuple(sorted(expected - actual))
    unexpected = tuple(sorted(actual - expected))
    valid = (
        len(observed) == len(UREK_DECLARED_HEADERS)
        and not missing
        and not unexpected
        and not duplicates
    )
    return HeaderReview(
        valid=valid,
        missing_headers=missing,
        unexpected_headers=unexpected,
        duplicate_headers=duplicates,
        observed_headers=observed,
        profile_id=f"{UREK_REPO_ID}@{UREK_PINNED_REVISION}:{UREK_FOLDER}",
    )
