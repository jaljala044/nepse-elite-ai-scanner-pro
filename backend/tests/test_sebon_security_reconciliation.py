import pytest

from app.sebon_security_reconciliation import (
    normalize_company_name,
    reconcile_sebon_company_candidates,
)


def candidate(name="ABC Bank Limited", ref="pdf-sha256:abc:page:1:line:4", sector="Commercial Banks"):
    return {
        "company_name_candidate": name,
        "sector_label_candidate": sector,
        "source_row_ref": ref,
    }


def security(name="ABC Bank Limited", security_id=101, symbol="ABCB"):
    return {
        "security_id": security_id,
        "symbol": symbol,
        "company_name": name,
        "source_record_ref": "nepse-snapshot:sha256:def:row:8",
    }


def test_normalization_preserves_words_but_ignores_case_punctuation_and_spacing():
    assert normalize_company_name("  ABC-Bank,   LIMITED ") == "abc bank limited"


def test_unique_exact_name_is_only_a_review_candidate_and_preserves_both_refs():
    result = reconcile_sebon_company_candidates(
        [candidate()], [security()]
    )
    row = result["exact_match_candidates"][0]
    assert row["reconciliation_status"] == "exact_name_match_review_required"
    assert row["identity_status"] == "unresolved_pending_review"
    assert row["source_row_ref"].endswith("line:4")
    assert row["security_candidate"]["source_record_ref"].endswith("row:8")
    assert row["classification_effective_date"] is None
    assert result["identity_verified"] is False
    assert result["membership_admission_allowed"] is False


def test_duplicate_official_company_names_are_ambiguous_not_first_match_wins():
    result = reconcile_sebon_company_candidates(
        [candidate()], [security(security_id=101, symbol="ABCB"),
                        security(security_id=102, symbol="ABCB2")]
    )
    assert result["ambiguous_candidates"][0]["manual_review_required"] is True
    assert len(result["ambiguous_candidates"][0]["security_candidates"]) == 2
    assert result["exact_match_candidates"] == []


def test_unmatched_candidate_is_explicit_and_not_fuzzy_matched():
    result = reconcile_sebon_company_candidates(
        [candidate("ABC Bank")], [security("ABC Bank Limited")]
    )
    assert result["unmatched_candidates"][0]["identity_status"] == "unmatched"


def test_multiple_candidates_are_partitioned_without_losing_source_references():
    result = reconcile_sebon_company_candidates(
        [candidate(ref="row:1"), candidate("Unknown Finance", ref="row:2")],
        [security()],
    )
    assert result["candidate_count"] == 2
    assert result["exact_match_candidates"][0]["source_row_ref"] == "row:1"
    assert result["unmatched_candidates"][0]["source_row_ref"] == "row:2"


@pytest.mark.parametrize("bad_id", [None, 0, -1, True, "101"])
def test_rejects_invalid_official_security_ids(bad_id):
    record = security()
    record["security_id"] = bad_id
    with pytest.raises(ValueError, match="invalid_security_id"):
        reconcile_sebon_company_candidates([], [record])


def test_rejects_missing_official_source_reference():
    record = security()
    record["source_record_ref"] = ""
    with pytest.raises(ValueError, match="source_ref_required"):
        reconcile_sebon_company_candidates([], [record])


def test_rejects_duplicate_candidate_source_reference():
    with pytest.raises(ValueError, match="duplicate_candidate_source_row_ref"):
        reconcile_sebon_company_candidates(
            [candidate(ref="same"), candidate(ref="same")], [security()]
        )


def test_rejects_duplicate_official_symbol():
    with pytest.raises(ValueError, match="duplicate_identity"):
        reconcile_sebon_company_candidates(
            [], [security(security_id=101, symbol="ABCB"),
                security(security_id=102, symbol="ABCB")]
        )
