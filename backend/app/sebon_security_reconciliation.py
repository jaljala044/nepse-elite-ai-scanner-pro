"""Conservative reconciliation of SEBON company candidates to NEPSE securities.

Only unique normalized exact-name matches are proposed. No fuzzy match, alias
guess, sector admission, or effective-date inference is performed. Even an
exact match remains a review candidate until independently approved.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize_company_name(value: str) -> str:
    """Normalize Unicode, case, punctuation and whitespace without dropping words."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("company_name_must_be_nonempty_string")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(
        char if char.isalnum() else " " for char in normalized
    )
    return re.sub(r"\s+", " ", normalized).strip()


def reconcile_sebon_company_candidates(
    row_candidates: list[dict[str, Any]],
    official_securities: list[dict[str, Any]],
) -> dict[str, Any]:
    """Produce exact-name match candidates, ambiguous records and unmatched rows.

    Expected official security fields: security_id (positive integer), symbol,
    company_name, source_record_ref. These records must originate from a
    separately validated official NEPSE security snapshot.
    """
    if not isinstance(row_candidates, list):
        raise ValueError("row_candidates_must_be_list")
    if not isinstance(official_securities, list):
        raise ValueError("official_securities_must_be_list")

    indexed: dict[str, list[dict[str, Any]]] = {}
    seen_security_ids: set[int] = set()
    seen_symbols: set[str] = set()
    for index, security in enumerate(official_securities):
        if not isinstance(security, dict):
            raise ValueError(f"official_security_{index}_must_be_object")
        security_id = security.get("security_id")
        symbol = security.get("symbol")
        company_name = security.get("company_name")
        source_ref = security.get("source_record_ref")
        if (isinstance(security_id, bool) or not isinstance(security_id, int)
                or security_id <= 0):
            raise ValueError(f"official_security_{index}_invalid_security_id")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(f"official_security_{index}_invalid_symbol")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError(f"official_security_{index}_source_ref_required")
        if security_id in seen_security_ids or symbol.strip().upper() in seen_symbols:
            raise ValueError("official_security_duplicate_identity")
        seen_security_ids.add(security_id)
        seen_symbols.add(symbol.strip().upper())
        key = normalize_company_name(company_name)
        indexed.setdefault(key, []).append({
            "security_id": security_id,
            "symbol": symbol.strip().upper(),
            "company_name": company_name.strip(),
            "source_record_ref": source_ref,
        })

    exact_matches = []
    ambiguous = []
    unmatched = []
    seen_candidate_refs: set[str] = set()
    for index, candidate in enumerate(row_candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"row_candidate_{index}_must_be_object")
        company_name = candidate.get("company_name_candidate")
        source_ref = candidate.get("source_row_ref")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise ValueError(f"row_candidate_{index}_source_row_ref_required")
        if source_ref in seen_candidate_refs:
            raise ValueError("duplicate_candidate_source_row_ref")
        seen_candidate_refs.add(source_ref)
        key = normalize_company_name(company_name)
        base = {
            "company_name_candidate": company_name.strip(),
            "normalized_company_name": key,
            "source_row_ref": source_ref,
            "sector_label_candidate": candidate.get("sector_label_candidate"),
            "classification_effective_date": None,
            "identity_verified": False,
            "membership_admission_allowed": False,
        }
        matches = indexed.get(key, [])
        if len(matches) == 1:
            exact_matches.append({
                **base,
                "reconciliation_status": "exact_name_match_review_required",
                "identity_status": "unresolved_pending_review",
                "security_candidate": matches[0],
            })
        elif len(matches) > 1:
            ambiguous.append({
                **base,
                "reconciliation_status": "ambiguous_duplicate_official_names",
                "identity_status": "ambiguous",
                "security_candidates": matches,
                "manual_review_required": True,
            })
        else:
            unmatched.append({
                **base,
                "reconciliation_status": "unmatched",
                "identity_status": "unmatched",
                "security_candidates": [],
            })

    return {
        "schema_version": 1,
        "reconciliation_method": "unicode_normalized_exact_name_only",
        "official_security_count": len(official_securities),
        "candidate_count": len(row_candidates),
        "exact_match_candidates": exact_matches,
        "ambiguous_candidates": ambiguous,
        "unmatched_candidates": unmatched,
        "identity_verified": False,
        "membership_verified": False,
        "membership_admission_allowed": False,
        "production_sector_signals_allowed": False,
        "limitations": [
            "Exact normalized name equality is a candidate match, not identity proof.",
            "No fuzzy matching, aliases, symbol inference, or beneficial ownership inference is performed.",
            "Official security inputs must have independent source validation and point-in-time provenance.",
            "Sector labels remain source candidates and are not admitted as official membership.",
            "Classification effective dates remain unknown unless separately established by primary evidence.",
        ],
    }
