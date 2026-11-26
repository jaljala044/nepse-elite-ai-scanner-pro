"""Reproducible two-file floorsheet archive audit from caller-supplied raw bytes.

The caller must supply expected SHA-256 values obtained from independently
pinned acquisition evidence. This module does not fetch data or certify rights.
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
    comparison = compare_floorsheet_sources(left["rows"], right["rows"])
    identity = audit_contract_date_identity(left["rows"], right["rows"])
    rejected = left["rejected_rows"] + right["rejected_rows"]
    return {
        "audit_status": "review_only_complete_parse" if rejected == 0
                        else "review_only_with_rejected_rows",
        "left_file": {
            "source_id": left_source_id,
            "sha256": left["source_payload_sha256"],
            "input_rows": left["input_data_rows"],
            "parsed_rows": left["parsed_rows"],
            "rejected_rows": left["rejected_rows"],
        },
        "right_file": {
            "source_id": right_source_id,
            "sha256": right["source_payload_sha256"],
            "input_rows": right["input_data_rows"],
            "parsed_rows": right["parsed_rows"],
            "rejected_rows": right["rejected_rows"],
        },
        "comparison": comparison,
        "identity_audit": identity,
        "source_independence_verified": False,
        "daily_capture_completeness_verified": False,
        "source_rights_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "hash_pinned_parse_and_compare_only_no_source_trust_inference",
    }
