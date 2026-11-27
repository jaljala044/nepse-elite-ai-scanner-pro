import unittest
from app.historical_pilot_verification import validate_official_first_trade_evidence


class OfficialFirstTradeVerificationTests(unittest.TestCase):
    def setUp(self):
        self.cohort = [{"symbol":"SAIL","security_id":"SEC-1","reported_first_trade_date":"2025-11-23"}]
        self.record = {
            "symbol":"SAIL","source_type":"nepse_official_floorsheet","contract_id":"C-1",
            "security_id":"SEC-1","source_record_id":"R-1:line-2","raw_sha256":"a"*64,
            "trade_date":"2025-11-23","available_at":"2025-11-23T15:00:00+05:45",
            "captured_at":"2025-11-23T15:10:00+05:45","quantity":10,"price":100,
            "finality":"final","record_status":"verified","capture_complete":True,
            "capture_id":"CAP-1","source_id":"SRC-1","publisher_id":"PUB-1",
            "payload_id":"P1","page_number":1,
        }
        self.captures = {"capture": {
            "status":"CAPTURE_VALIDATED","capture_id":"CAP-1","source_id":"SRC-1",
            "publisher_id":"PUB-1","window_start":"2025-11-23T00:00:00+05:45",
            "window_end":"2025-11-23T23:59:59+05:45",
            "verified_pages":[{"page_number":1,"payload_id":"P1","raw_sha256":"a"*64}],
        }}

    def run_check(self, record):
        return validate_official_first_trade_evidence(
            self.cohort, [record], decision_cutoff="2025-11-24T00:00:00+05:45",
            validated_capture_reports=self.captures,
        )

    def test_official_contract_resolves_date_when_bound_to_validated_page(self):
        report = self.run_check(self.record)
        self.assertEqual(report["verified_count"], 1)
        self.assertFalse(report["backtest_admission_allowed"])

    def test_secondary_source_rejected(self):
        report = self.run_check(dict(self.record, source_type="secondary_provider"))
        self.assertEqual(report["rejected_evidence"][0]["reason"], "source_not_official")

    def test_future_evidence_rejected(self):
        report = self.run_check(dict(self.record, available_at="2025-11-25T00:00:00+05:45"))
        self.assertEqual(report["rejected_evidence"][0]["reason"], "evidence_available_after_decision_cutoff")

    def test_official_date_conflict_remains_unresolved(self):
        report = self.run_check(dict(self.record, trade_date="2025-11-24"))
        self.assertEqual(report["unresolved"][0]["status"], "official_boundary_conflicts_with_reported_date")

    def test_page_hash_mismatch_rejected(self):
        report = self.run_check(dict(self.record, raw_sha256="b"*64))
        self.assertEqual(report["rejected_evidence"][0]["reason"], "first_trade_evidence_not_bound_to_validated_page_hash")


if __name__ == "__main__":
    unittest.main()
