"""Fail-closed reconciliation of SEBON company candidates to NEPSE IDs.

Exact normalized names generate review proposals only. This module never
confirms identity, assigns a production security ID, or admits membership.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from collections import defaultdict
from typing import Any


_CROSSWALK_PATH = "data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_SOURCE_REF = re.compile(r"^pdf-sha256:[0-9a-f]{64}:page:[1-9][0-9]*:line:[1-9][0-9]*$")
_SUFFIX_ALIASES = {
    "ltd": "limited",
    "limited": "limited",
    "co": "company",
    "company": "company",
    "pvt": "private",
    "private": "private",
    "public": "public",
    "plc": "public",
}


def normalize_company_name(value: Any) -> str:
    """Normalize Unicode/case/punctuation and common legal-suffix spellings."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("company_name_required")
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("&", " and ")
    text = "".join(char if char.isalnum() else " " for char in text)
    tokens = [_SUFFIX_ALIASES.get(token, token) for token in text.split()]
    return " ".join(tokens)


def _parse_crosswalk(
    raw_csv: bytes,
    *,
    expected_payload_sha256: str,
    expected_artifact_git_blob_sha: str,
    expected_source_snapshot_blob_sha: str,
    expected_snapshot_date: str,
) -> tuple[list[dict], str]:
    if not isinstance(raw_csv, bytes) or not raw_csv:
        raise ValueError("crosswalk_csv_bytes_required")
    digest = hashlib.sha256(raw_csv).hexdigest()
    if digest != expected_payload_sha256:
        raise ValueError("crosswalk_payload_sha256_mismatch")
    if not isinstance(expected_artifact_git_blob_sha, str) or not _HEX40.fullmatch(expected_artifact_git_blob_sha):
        raise ValueError("crosswalk_artifact_git_blob_sha_invalid")
    if not isinstance(expected_source_snapshot_blob_sha, str) or not _HEX40.fullmatch(expected_source_snapshot_blob_sha):
        raise ValueError("source_snapshot_blob_sha_invalid")
    if not isinstance(expected_snapshot_date, str) or not expected_snapshot_date:
        raise ValueError("crosswalk_snapshot_date_required")
    try:
        text = raw_csv.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text, newline=""))
        required = {
            "symbol", "security_id", "security_name", "snapshot_date",
            "active_status", "crosswalk_status", "source_snapshot_blob_sha",
        }
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("crosswalk_required_columns_missing")
        records = list(reader)
    except (UnicodeDecodeError, csv.Error):
        raise ValueError("crosswalk_csv_invalid") from None
    if not records:
        raise ValueError("crosswalk_records_empty")

    seen_symbols: set[str] = set()
    seen_ids: set[int] = set()
    normalized = []
    for index, row in enumerate(records):
        symbol = row.get("symbol", "")
        name = row.get("security_name", "")
        raw_id = row.get("security_id", "")
        status = row.get("active_status", "")
        if not symbol or symbol != symbol.strip() or symbol.upper() != symbol:
            raise ValueError(f"crosswalk_row_{index}_symbol_invalid")
        if symbol in seen_symbols:
            raise ValueError(f"crosswalk_row_{index}_duplicate_symbol")
        seen_symbols.add(symbol)
        if not raw_id.isdigit() or int(raw_id) <= 0:
            raise ValueError(f"crosswalk_row_{index}_security_id_invalid")
        security_id = int(raw_id)
        if security_id in seen_ids:
            raise ValueError(f"crosswalk_row_{index}_duplicate_security_id")
        seen_ids.add(security_id)
        if not name or not name.strip() or status not in {"A", "S"}:
            raise ValueError(f"crosswalk_row_{index}_identity_fields_invalid")
        if row.get("snapshot_date") != expected_snapshot_date:
            raise ValueError(f"crosswalk_row_{index}_snapshot_date_mismatch")
        if row.get("crosswalk_status") != f"snapshot_id_match_active_status_{status}":
            raise ValueError(f"crosswalk_row_{index}_crosswalk_status_mismatch")
        if row.get("source_snapshot_blob_sha") != expected_source_snapshot_blob_sha:
            raise ValueError(f"crosswalk_row_{index}_source_snapshot_blob_mismatch")
        normalized.append({
            "symbol": symbol,
            "security_id": security_id,
            "security_name": name.strip(),
            "snapshot_date": expected_snapshot_date,
            "active_status": status,
            "normalized_name": normalize_company_name(name),
            "crosswalk_record_ref": f"{_CROSSWALK_PATH}#symbol={symbol}",
        })
    return normalized, digest


def reconcile_sebon_company_candidates(
    candidates: list[dict],
    crosswalk_csv: bytes,
    *,
    expected_crosswalk_payload_sha256: str,
    expected_crosswalk_artifact_git_blob_sha: str,
    expected_source_snapshot_blob_sha: str,
    expected_snapshot_date: str,
) -> dict[str, Any]:
    """Return exact-name identity proposals, ambiguity and unmatched queues.

    A unique match is still review-required. No proposed ID is promoted into
    the candidate's authoritative identity fields.
    """
    if not isinstance(candidates, list):
        raise ValueError("sebon_candidates_must_be_list")
    securities, crosswalk_digest = _parse_crosswalk(
        crosswalk_csv,
        expected_payload_sha256=expected_crosswalk_payload_sha256,
        expected_artifact_git_blob_sha=expected_crosswalk_artifact_git_blob_sha,
        expected_source_snapshot_blob_sha=expected_source_snapshot_blob_sha,
        expected_snapshot_date=expected_snapshot_date,
    )
    by_name: dict[str, list[dict]] = defaultdict(list)
    for security in securities:
        by_name[security["normalized_name"]].append(security)

    results = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"candidate_{index}_must_be_object")
        company = candidate.get("company_name_candidate")
        source_ref = candidate.get("source_row_ref")
        if not isinstance(company, str) or not company.strip():
            raise ValueError(f"candidate_{index}_company_name_required")
        if not isinstance(source_ref, str) or not _SOURCE_REF.fullmatch(source_ref):
            raise ValueError(f"candidate_{index}_source_row_ref_invalid")
        sector = candidate.get("sector_label_candidate")
        if not isinstance(sector, str) or not sector.strip():
            raise ValueError(f"candidate_{index}_sector_label_required")
        normalized_name = normalize_company_name(company)
        matches = by_name.get(normalized_name, [])
        base = {
            "company_name_candidate": company,
            "sector_label_candidate": sector,
            "normalized_company_name": normalized_name,
            "source_row_ref": source_ref,
            "source_page": candidate.get("source_page"),
            "source_line_number": candidate.get("source_line_number"),
            "crosswalk_snapshot_date": expected_snapshot_date,
            "crosswalk_payload_sha256": crosswalk_digest,
            "crosswalk_artifact_git_blob_sha": expected_crosswalk_artifact_git_blob_sha,
            "source_snapshot_blob_sha": expected_source_snapshot_blob_sha,
            "identity_confirmed": False,
            "security_id": None,
            "symbol": None,
            "review_required": True,
            "membership_admission_allowed": False,
        }
        if len(matches) == 1:
            match = matches[0]
            base.update({
                "match_status": "exact_normalized_name_candidate",
                "match_method": "unicode_case_punctuation_and_legal_suffix_normalization",
                "proposed_security_id": match["security_id"],
                "proposed_symbol": match["symbol"],
                "proposed_security_name": match["security_name"],
                "proposed_active_status": match["active_status"],
                "crosswalk_record_ref": match["crosswalk_record_ref"],
                "match_count": 1,
            })
        elif len(matches) > 1:
            base.update({
                "match_status": "ambiguous_multiple_exact_name_matches",
                "match_method": "exact_normalized_name",
                "match_count": len(matches),
                "possible_matches": [
                    {key: match[key] for key in (
                        "security_id", "symbol", "security_name",
                        "active_status", "crosswalk_record_ref",
                    )}
                    for match in matches
                ],
            })
        else:
            base.update({
                "match_status": "unmatched_no_exact_name_candidate",
                "match_method": "exact_normalized_name_only",
                "match_count": 0,
            })
        results.append(base)

    counts = {
        status: sum(row["match_status"] == status for row in results)
        for status in (
            "exact_normalized_name_candidate",
            "ambiguous_multiple_exact_name_matches",
            "unmatched_no_exact_name_candidate",
        )
    }
    return {
        "schema_version": 1,
        "source_crosswalk": {
            "path": _CROSSWALK_PATH,
            "artifact_git_blob_sha": expected_crosswalk_artifact_git_blob_sha,
            "source_snapshot_blob_sha": expected_source_snapshot_blob_sha,
            "payload_sha256": crosswalk_digest,
            "snapshot_date": expected_snapshot_date,
            "security_record_count": len(securities),
        },
        "candidate_count": len(results),
        "match_counts": counts,
        "results": results,
        "reconciliation_status": "review_required",
        "identity_verified": False,
        "membership_admission_allowed": False,
        "production_sector_signals_allowed": False,
    }
