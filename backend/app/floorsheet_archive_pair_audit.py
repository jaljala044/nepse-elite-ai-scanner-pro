"""Reproducible two-file floorsheet archive audit from caller-supplied raw bytes.

The caller must supply expected SHA-256 values obtained from independently
pinned acquisition evidence. This module does not fetch data or certify rights.
Rejected CSV rows remain in the report's exception ledger.
"""
from __future__ import annotations

import hashlib
import re

from app.floorsheet_csv_adapter import CsvFloorsheetMapping, parse_floorsheet_csv
from app.floorsheet_cross_source import compare_floorsheet_sources
from app.floorsheet_identity_audit import audit_contract_date_identity


def audit_floorsheet_archive_pair(
    left_payload: bytes,
    right_payload: bytes,
    *,
    left_source_id: str,
    right_source_id: str,
    left_expected_sha256: str,
    right_expected_sha256: str,
    left_mapping: CsvFloorsheetMapping,
    right_mapping: CsvFloorsheetMapping,
) -> dict:
    """Hash-check, parse, compare and identity-audit two pinned CSV payloads."""
    for label, payload, expected in (
        ("left", left_payload, left_expected_sha256),
        ("right", right_payload, right_expected_sha256),
    ):
        if not isinstance(payload, bytes) or not payload:
            raise ValueError(f"{label} payload must be non-empty bytes")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            raise ValueError(f"{label} expected SHA-256 must be 64 hexadecimal characters")
        actual = hashlib.sha256(payload).hexdigest()
        if actual.lower() != expected.lower():
            raise ValueError(f"{label} payload SHA-256 does not match pinned expected digest")

    left = parse_floorsheet_csv(
        left_payload, source_id=left_source_id, mapping=left_mapping
    )
    right = parse_floorsheet_csv(
        right_payload, source_id=right_source_id, mapping=right_mapping
    )
    rejected = left["rejected_rows"] + right["rejected_rows"]

    if left["rows"] and right["rows"]:
        comparison = compare_floorsheet_sources(left["rows"], right["rows"])
        identity = audit_contract_date_identity(left["rows"], right["rows"])
    else:
        comparison = {
            "comparison_status": "not_run_no_parsed_rows_on_one_or_both_sides",
            "source_independence_verified": False,
            "canonical_promotion_allowed": False,
            "coverage_admission_allowed": False,
        }
        identity = {
            "audit_status": "not_run_no_parsed_rows_on_one_or_both_sides",
            "source_independence_verified": False,
            "trade_date_authority_verified": False,
            "coverage_admission_allowed": False,
            "canonical_promotion_allowed": False,
        }

    def file_report(parsed, source_id):
        return {
            "source_id": source_id,
            "sha256": parsed["source_payload_sha256"],
            "input_rows": parsed["input_data_rows"],
            "parsed_rows": parsed["parsed_rows"],
            "rejected_rows": parsed["rejected_rows"],
            "rejected_row_ledger": parsed["errors"],
        }

    return {
        "audit_status": (
            "review_only_complete_parse" if rejected == 0
            else "review_only_with_rejected_rows"
        ),
        "left_file": file_report(left, left_source_id),
        "right_file": file_report(right, right_source_id),
        "comparison": comparison,
        "identity_audit": identity,
        "source_independence_verified": False,
        "daily_capture_completeness_verified": False,
        "source_rights_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "hash_pinned_parse_and_compare_only_no_source_trust_inference",
    }
