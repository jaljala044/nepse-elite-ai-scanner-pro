import unittest

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


class SebonSecurityReconciliationTests(unittest.TestCase):
    def test_normalization_preserves_words_but_ignores_case_punctuation_and_spacing(self):
        self.assertEqual(
            normalize_company_name("  ABC-Bank,   LIMITED "),
            "abc bank limited",
        )

    def test_unique_exact_name_is_only_a_review_candidate_and_preserves_both_refs(self):
        result = reconcile_sebon_company_candidates([candidate()], [security()])
        row = result["exact_match_candidates"][0]
        self.assertEqual(row["reconciliation_status"], "exact_name_match_review_required")
        self.assertEqual(row["identity_status"], "unresolved_pending_review")
        self.assertTrue(row["source_row_ref"].endswith("line:4"))
        self.assertTrue(row["security_candidate"]["source_record_ref"].endswith("row:8"))
        self.assertIsNone(row["classification_effective_date"])
        self.assertFalse(result["identity_verified"])
        self.assertFalse(result["membership_admission_allowed"])

    def test_duplicate_official_company_names_are_ambiguous_not_first_match_wins(self):
        result = reconcile_sebon_company_candidates(
            [candidate()],
            [security(security_id=101, symbol="ABCB"),
             security(security_id=102, symbol="ABCB2")],
        )
        self.assertTrue(result["ambiguous_candidates"][0]["manual_review_required"])
        self.assertEqual(len(result["ambiguous_candidates"][0]["security_candidates"]), 2)
        self.assertEqual(result["exact_match_candidates"], [])

    def test_unmatched_candidate_is_explicit_and_not_fuzzy_matched(self):
        result = reconcile_sebon_company_candidates(
            [candidate("ABC Bank")], [security("ABC Bank Limited")]
        )
        self.assertEqual(result["unmatched_candidates"][0]["identity_status"], "unmatched")

    def test_multiple_candidates_are_partitioned_without_losing_source_references(self):
        result = reconcile_sebon_company_candidates(
            [candidate(ref="row:1"), candidate("Unknown Finance", ref="row:2")],
            [security()],
        )
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["exact_match_candidates"][0]["source_row_ref"], "row:1")
        self.assertEqual(result["unmatched_candidates"][0]["source_row_ref"], "row:2")

    def test_invalid_official_security_ids_are_rejected(self):
        for bad_id in (None, 0, -1, True, "101"):
            with self.subTest(security_id=bad_id):
                record = security()
                record["security_id"] = bad_id
                with self.assertRaisesRegex(ValueError, "invalid_security_id"):
                    reconcile_sebon_company_candidates([], [record])

    def test_missing_official_source_reference_is_rejected(self):
        record = security()
        record["source_record_ref"] = ""
        with self.assertRaisesRegex(ValueError, "source_ref_required"):
            reconcile_sebon_company_candidates([], [record])

    def test_duplicate_candidate_source_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_candidate_source_row_ref"):
            reconcile_sebon_company_candidates(
                [candidate(ref="same"), candidate(ref="same")], [security()]
            )

    def test_duplicate_official_symbol_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate_identity"):
            reconcile_sebon_company_candidates(
                [],
                [security(security_id=101, symbol="ABCB"),
                 security(security_id=102, symbol="ABCB")],
            )


if __name__ == "__main__":
    unittest.main()
