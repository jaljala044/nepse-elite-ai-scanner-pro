import csv
import tempfile
import unittest
from pathlib import Path

from validate_security_lifecycle_event_ledger import validate_security_lifecycle_event_ledger


class SecurityLifecycleEventLedgerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.ledger = self.root / "data/reference/nepse_security_lifecycle_events_2026-11-26.csv"
        self.crosswalk = self.root / "data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv"

    def test_current_typed_event_ledger_is_valid_but_not_promotable(self):
        report = validate_security_lifecycle_event_ledger(self.ledger, self.crosswalk, 52)
        self.assertEqual(report["status"], "valid_event_ledger_with_uncaptured_raw_sources")
        self.assertEqual(report["event_count"], 52)
        self.assertEqual(report["unique_event_ids"], 52)
        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["errors"], [])

    def _mutated_report(self, mutate):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.csv"
            with self.ledger.open(encoding="utf-8", newline="") as source:
                rows = list(csv.DictReader(source))
            mutate(rows)
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return validate_security_lifecycle_event_ledger(path, self.crosswalk)

    def test_duplicate_event_id_fails(self):
        report = self._mutated_report(lambda rows: rows[1].update(event_id=rows[0]["event_id"]))
        self.assertTrue(any("duplicate_event_id" in error for error in report["errors"]))

    def test_wrong_current_security_id_fails(self):
        report = self._mutated_report(lambda rows: rows[0].update(security_id="999999"))
        self.assertTrue(any("security_id_does_not_match_current_crosswalk" in error
                            for error in report["errors"]))

    def test_listing_event_does_not_accept_invalid_date(self):
        report = self._mutated_report(lambda rows: rows[0].update(event_date="2024-02-30"))
        self.assertTrue(any("invalid_event_date" in error for error in report["errors"]))

    def test_secondary_source_cannot_claim_primary_verification(self):
        report = self._mutated_report(lambda rows: rows[0].update(
            evidence_tier="secondary_notice", review_status="primary_notice_verified"
        ))
        self.assertTrue(any("secondary_source_cannot_claim_primary_notice_verified" in error
                            for error in report["errors"]))

    def test_invalid_source_url_fails(self):
        report = self._mutated_report(lambda rows: rows[0].update(source_url="not-a-url"))
        self.assertTrue(any("invalid_source_url" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
