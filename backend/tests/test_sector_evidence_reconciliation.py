import unittest

from app.sector_evidence_reconciliation import reconcile_sector_evidence

CUTOFF = "2026-11-28T12:00:00Z"
BASE = {
    "symbol": "AAA", "sector_code": "BANK", "source_id": "s1",
    "publisher_id": "publisher-a", "source_class": "secondary_publisher",
    "payload_sha256": "a" * 64, "source_record_ref": "page:1",
    "captured_at": "2026-11-27T10:00:00Z",
    "available_at": "2026-11-27T10:01:00Z",
    "effective_from": "2026-01-01", "effective_to": None,
}


def row(**changes):
    return {**BASE, **changes}


class SectorEvidenceReconciliationTests(unittest.TestCase):
    def reconcile(self, observations, symbols=("AAA",), cutoff=CUTOFF, as_of="2026-11-28"):
        return reconcile_sector_evidence(
            observations, symbols=list(symbols),
            allowed_sector_codes={"BANK", "HYDRO", "FINANCE"},
            as_of_date=as_of, decision_time=cutoff,
        )

    def test_two_independent_publishers_corroborate_secondary_membership(self):
        result = self.reconcile([row(), row(
            source_id="s2", publisher_id="publisher-b",
            payload_sha256="b" * 64, source_record_ref="page:2",
        )])
        item = result["results"]["AAA"]
        self.assertEqual(item["status"], "corroborated_secondary")
        self.assertEqual(item["sector_code"], "BANK")
        self.assertFalse(item["official_membership_verified"])

    def test_primary_plus_independent_secondary_is_labeled_primary_corroborated(self):
        result = self.reconcile([row(source_class="primary_nepse"), row(
            source_id="s2", publisher_id="publisher-b",
            payload_sha256="b" * 64, source_record_ref="page:2",
        )])
        self.assertEqual(result["results"]["AAA"]["status"], "corroborated_primary")

    def test_same_publisher_does_not_count_as_independent(self):
        result = self.reconcile([row(), row(source_id="s2", source_record_ref="page:2")])
        item = result["results"]["AAA"]
        self.assertEqual(item["status"], "single_source_only")
        self.assertIsNone(item["sector_code"])

    def test_conflicting_publishers_withhold_sector(self):
        result = self.reconcile([row(), row(
            source_id="s2", publisher_id="publisher-b", sector_code="HYDRO",
            payload_sha256="b" * 64, source_record_ref="page:2",
        )])
        item = result["results"]["AAA"]
        self.assertEqual(item["status"], "conflicting_sources")
        self.assertIsNone(item["sector_code"])

    def test_future_available_evidence_is_excluded(self):
        result = self.reconcile([
            row(), row(source_id="s2", publisher_id="publisher-b",
                       payload_sha256="b" * 64, source_record_ref="page:2",
                       captured_at="2026-11-29T10:00:00Z",
                       available_at="2026-11-29T10:01:00Z"),
        ])
        self.assertEqual(result["results"]["AAA"]["status"], "single_source_only")

    def test_historical_effective_date_excludes_future_reclassification(self):
        result = self.reconcile([
            row(effective_from="2026-11-27", effective_to="2026-11-27"),
            row(source_id="s2", publisher_id="publisher-b",
                payload_sha256="b" * 64, source_record_ref="page:2",
                effective_from="2026-11-29"),
        ], as_of="2026-11-27")
        self.assertEqual(result["results"]["AAA"]["status"], "single_source_only")

    def test_historical_reclassification_is_detected_as_two_timelines(self):
        old = self.reconcile([
            row(effective_from="2026-01-01", effective_to="2026-11-27"),
            row(source_id="s2", publisher_id="publisher-b",
                payload_sha256="b" * 64, source_record_ref="page:2",
                effective_from="2026-01-01", effective_to="2026-11-27"),
        ], as_of="2026-11-27")
        new = self.reconcile([
            row(effective_from="2026-11-28"),
            row(source_id="s2", publisher_id="publisher-b",
                payload_sha256="b" * 64, source_record_ref="page:2",
                effective_from="2026-11-28"),
        ])
        self.assertEqual(old["results"]["AAA"]["sector_code"], "BANK")
        self.assertEqual(new["results"]["AAA"]["sector_code"], "BANK")

    def test_expired_evidence_is_withheld(self):
        result = self.reconcile([row(effective_to="2026-11-27")])
        self.assertEqual(result["results"]["AAA"]["status"], "missing_evidence")
        self.assertIsNone(result["results"]["AAA"]["sector_code"])

    def test_missing_symbol_is_reported_not_neutral(self):
        result = self.reconcile([], symbols=("AAA", "BBB"))
        self.assertEqual(result["results"]["BBB"]["status"], "missing_evidence")
        self.assertEqual(result["corroborated_coverage_pct"], 0.0)

    def test_invalid_payload_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "payload_hash_invalid"):
            self.reconcile([row(payload_sha256="not-a-hash")])

    def test_capture_after_availability_rejected(self):
        with self.assertRaisesRegex(ValueError, "available_before_capture"):
            self.reconcile([row(captured_at="2026-11-28T10:00:00Z",
                                available_at="2026-11-27T10:00:00Z")])

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone_aware"):
            self.reconcile([row(captured_at="2026-11-27T10:00:00")])

    def test_no_recommendation_or_production_admission(self):
        result = self.reconcile([row(), row(
            source_id="s2", publisher_id="publisher-b",
            payload_sha256="b" * 64, source_record_ref="page:2",
        )])
        self.assertFalse(result["verified"])
        self.assertFalse(result["admission_allowed"])
        self.assertFalse(result["production_recommendations_enabled"])


if __name__ == "__main__":
    unittest.main()
