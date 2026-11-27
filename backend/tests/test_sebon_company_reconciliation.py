import csv
import hashlib
import io
import unittest

from app.sebon_company_reconciliation import (
    normalize_company_name,
    reconcile_sebon_company_candidates,
)


ARTIFACT_BLOB = "d" * 40
SOURCE_SNAPSHOT_BLOB = "a" * 40
SNAPSHOT_DATE = "2026-11-25"
SOURCE_HASH = "b" * 64


def make_crosswalk(rows=None):
    rows = rows or [
        {"symbol": "AAA", "security_id": "101",
         "security_name": "Himalayan Example Hydropower Limited",
         "snapshot_date": SNAPSHOT_DATE, "active_status": "A",
         "crosswalk_status": "snapshot_id_match_active_status_A",
         "source_snapshot_blob_sha": SOURCE_SNAPSHOT_BLOB},
        {"symbol": "BBB", "security_id": "102",
         "security_name": "Other Example Finance Company Ltd.",
         "snapshot_date": SNAPSHOT_DATE, "active_status": "A",
         "crosswalk_status": "snapshot_id_match_active_status_A",
         "source_snapshot_blob_sha": SOURCE_HASH},
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def candidate(name="Himalayan Example Hydropower Ltd.", line=2):
    return {
        "company_name_candidate": name,
        "sector_label_candidate": "Hydropower",
        "source_row_ref": f"pdf-sha256:{'c' * 64}:page:1:line:{line}",
        "source_page": 1,
        "source_line_number": line,
    }


class SebonCompanyReconciliationTests(unittest.TestCase):
    def run_reconcile(self, candidates, payload=None, **kwargs):
        raw = payload or make_crosswalk()
        return reconcile_sebon_company_candidates(
            candidates, raw,
            expected_crosswalk_payload_sha256=hashlib.sha256(raw).hexdigest(),
            expected_crosswalk_artifact_git_blob_sha=ARTIFACT_BLOB,
            expected_source_snapshot_blob_sha=SOURCE_SNAPSHOT_BLOB,
            expected_snapshot_date=SNAPSHOT_DATE,
            **kwargs,
        )

    def test_normalizes_common_legal_suffix_variants(self):
        self.assertEqual(
            normalize_company_name("A & B Co. Ltd."),
            "a and b company limited",
        )
        self.assertEqual(
            normalize_company_name("A and B Company Limited"),
            "a and b company limited",
        )

    def test_unique_exact_normalized_match_is_only_a_proposal(self):
        result = self.run_reconcile([candidate()])
        row = result["results"][0]
        self.assertEqual(row["match_status"], "exact_normalized_name_candidate")
        self.assertEqual(row["proposed_symbol"], "AAA")
        self.assertEqual(row["proposed_security_id"], 101)
        self.assertIsNone(row["security_id"])
        self.assertFalse(row["identity_confirmed"])
        self.assertTrue(row["review_required"])
        self.assertFalse(result["membership_admission_allowed"])

    def test_unmatched_company_is_not_fuzzy_matched(self):
        result = self.run_reconcile([candidate("Himalayan Example Hydropower Company")])
        row = result["results"][0]
        self.assertEqual(row["match_status"], "unmatched_no_exact_name_candidate")
        self.assertIsNone(row["proposed_symbol"])

    def test_duplicate_normalized_names_are_ambiguous(self):
        rows = [
            {"symbol": "AAA", "security_id": "101", "security_name": "Same Company Limited",
             "snapshot_date": SNAPSHOT_DATE, "active_status": "A",
             "crosswalk_status": "snapshot_id_match_active_status_A",
             "source_snapshot_blob_sha": SOURCE_HASH},
            {"symbol": "BBB", "security_id": "102", "security_name": "Same Company Ltd.",
             "snapshot_date": SNAPSHOT_DATE, "active_status": "A",
             "crosswalk_status": "snapshot_id_match_active_status_A",
             "source_snapshot_blob_sha": SOURCE_HASH},
        ]
        result = self.run_reconcile([candidate("Same Company Limited")], make_crosswalk(rows))
        row = result["results"][0]
        self.assertEqual(row["match_status"], "ambiguous_multiple_exact_name_matches")
        self.assertEqual(row["match_count"], 2)
        self.assertIsNone(row["proposed_symbol"])

    def test_rejects_crosswalk_payload_hash_mismatch(self):
        raw = make_crosswalk()
        with self.assertRaisesRegex(ValueError, "payload_sha256_mismatch"):
            reconcile_sebon_company_candidates(
                [candidate()], raw,
                expected_crosswalk_payload_sha256="0" * 64,
                expected_crosswalk_git_blob_sha=GIT_BLOB,
                expected_snapshot_date=SNAPSHOT_DATE,
            )

    def test_rejects_duplicate_crosswalk_symbols(self):
        rows = [
            {"symbol": "AAA", "security_id": "101", "security_name": "First Ltd",
             "snapshot_date": SNAPSHOT_DATE, "active_status": "A",
             "crosswalk_status": "snapshot_id_match_active_status_A",
             "source_snapshot_blob_sha": SOURCE_HASH},
            {"symbol": "AAA", "security_id": "102", "security_name": "Second Ltd",
             "snapshot_date": SNAPSHOT_DATE, "active_status": "A",
             "crosswalk_status": "snapshot_id_match_active_status_A",
             "source_snapshot_blob_sha": SOURCE_HASH},
        ]
        raw = make_crosswalk(rows)
        with self.assertRaisesRegex(ValueError, "duplicate_symbol"):
            self.run_reconcile([candidate()], raw)

    def test_rejects_crosswalk_snapshot_date_mismatch(self):
        raw = make_crosswalk()
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        rows[0]["snapshot_date"] = "2026-11-24"
        raw = make_crosswalk(rows)
        with self.assertRaisesRegex(ValueError, "snapshot_date_mismatch"):
            self.run_reconcile([candidate()], raw)

    def test_rejects_bad_source_row_reference(self):
        bad = candidate()
        bad["source_row_ref"] = "page:1"
        with self.assertRaisesRegex(ValueError, "source_row_ref_invalid"):
            self.run_reconcile([bad])

    def test_rejects_invalid_security_id(self):
        rows = list(csv.DictReader(io.StringIO(make_crosswalk().decode())))
        rows[0]["security_id"] = "0"
        raw = make_crosswalk(rows)
        with self.assertRaisesRegex(ValueError, "security_id_invalid"):
            self.run_reconcile([candidate()], raw)

    def test_empty_candidates_is_valid_audit(self):
        result = self.run_reconcile([])
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(result["reconciliation_status"], "review_required")


if __name__ == "__main__":
    unittest.main()
