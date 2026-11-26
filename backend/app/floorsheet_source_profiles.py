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


# The daily SamirWagle capture is sourced from Merolagani's public floorsheet
# page. Its date field is generated with Python date.today() by the scraper;
# it is not an exchange-issued trade-date field and must remain provisional.
SAMIR_REPO_ID = "SamirWagle/Nepse-All-Scraper"
SAMIR_PINNED_COMMIT = "e6160adc6bdf3d19562167388e3d9d4f645c455a"
SAMIR_FLOORSHEET_PATH = "data/floorsheet/floorsheet_2026-11-24.csv"
SAMIR_BLOB_SHA1 = "22eaa891b30aac2fe4cf197053efa014953351c0"
SAMIR_RAW_SHA256 = "2687b7ed6bc5ebd737fa459ca8dd620941bb3ec1da6613fbd620550495018f55"
SAMIR_RAW_SIZE_BYTES = 3538179

SAMIR_DECLARED_HEADERS = (
    "date", "sn", "contract_no", "stock_symbol", "buyer", "seller",
    "quantity", "rate", "amount",
)
SAMIR_CANONICAL_COLUMNS = {
    "trade_date": "date",
    "contract_id": "contract_no",
    "symbol": "stock_symbol",
    "buyer_broker_code": "buyer",
    "seller_broker_code": "seller",
    "quantity": "quantity",
    "rate": "rate",
    "amount": "amount",
}
SAMIR_SOURCE_ONLY_HEADERS = ("sn",)


def samir_merolagani_capture_mapping() -> CsvFloorsheetMapping:
    """Map the nine observed CSV fields; date remains unverified capture date."""
    return CsvFloorsheetMapping(columns=dict(SAMIR_CANONICAL_COLUMNS))


def review_samir_merolagani_headers(headers: Iterable[str]) -> HeaderReview:
    """Compare headers with the exact pinned daily capture's observed header."""
    if isinstance(headers, (str, bytes)):
        raise ValueError("headers must be an iterable of header strings, not text")
    observed = tuple(headers)
    if any(not isinstance(item, str) or not item.strip() for item in observed):
        raise ValueError("headers must contain only nonblank strings")

    duplicates = tuple(sorted({
        item for item in observed if observed.count(item) > 1
    }))
    expected = set(SAMIR_DECLARED_HEADERS)
    actual = set(observed)
    missing = tuple(sorted(expected - actual))
    unexpected = tuple(sorted(actual - expected))
    valid = (
        len(observed) == len(SAMIR_DECLARED_HEADERS)
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
        profile_id=f"{SAMIR_REPO_ID}@{SAMIR_PINNED_COMMIT}:{SAMIR_FLOORSHEET_PATH}",
        evidence_status="raw_header_observed_capture_date_semantics_unverified",
    )


# SocrateAI's pinned 2026-11-24 comparison file uses an explicit date column
# and a transaction identifier. Its publisher/upstream acquisition lineage is
# not independently established; this profile maps syntax only, not trust.
SOCRATEAI_REPO_ID = "socrateai-official/nepse-open-data"
SOCRATEAI_PINNED_COMMIT = "cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3"
SOCRATEAI_FLOORSHEET_PATH = "floorsheet/floorsheet_2026-11-24.csv"
SOCRATEAI_BLOB_SHA1 = "e7150873219d66a21345df2dfbd78f6c5a4b1152"
SOCRATEAI_RAW_SIZE_BYTES = 3058892
SOCRATEAI_DECLARED_HEADERS = (
    "transaction", "symbol", "buyer", "seller",
    "quantity", "rate", "amount", "date",
)
SOCRATEAI_CANONICAL_COLUMNS = {
    "trade_date": "date",
    "contract_id": "transaction",
    "symbol": "symbol",
    "buyer_broker_code": "buyer",
    "seller_broker_code": "seller",
    "quantity": "quantity",
    "rate": "rate",
    "amount": "amount",
}
SOCRATEAI_SOURCE_ONLY_HEADERS: tuple[str, ...] = ()


def socrateai_floorsheet_mapping() -> CsvFloorsheetMapping:
    """Map the pinned comparison CSV; date and lineage remain evidence-qualified."""
    return CsvFloorsheetMapping(columns=dict(SOCRATEAI_CANONICAL_COLUMNS))


def review_socrateai_floorsheet_headers(headers: Iterable[str]) -> HeaderReview:
    """Compare an observed CSV header with the pinned publisher schema."""
    if isinstance(headers, (str, bytes)):
        raise ValueError("headers must be an iterable of header strings, not text")
    observed = tuple(headers)
    if any(not isinstance(item, str) or not item.strip() for item in observed):
        raise ValueError("headers must contain only nonblank strings")
    duplicates = tuple(sorted({item for item in observed if observed.count(item) > 1}))
    expected = set(SOCRATEAI_DECLARED_HEADERS)
    actual = set(observed)
    missing = tuple(sorted(expected - actual))
    unexpected = tuple(sorted(actual - expected))
    valid = (
        len(observed) == len(SOCRATEAI_DECLARED_HEADERS)
        and not missing and not unexpected and not duplicates
    )
    return HeaderReview(
        valid=valid,
        missing_headers=missing,
        unexpected_headers=unexpected,
        duplicate_headers=duplicates,
        observed_headers=observed,
        profile_id=(
            f"{SOCRATEAI_REPO_ID}@{SOCRATEAI_PINNED_COMMIT}:"
            f"{SOCRATEAI_FLOORSHEET_PATH}"
        ),
        evidence_status="pinned_header_profile_lineage_and_completeness_unverified",
    )
