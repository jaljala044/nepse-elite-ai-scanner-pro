import unittest
from datetime import date, timedelta
from app.historical_segment_eligibility import evaluate_historical_segment


class HistoricalSegmentEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.sessions = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(120)]
        self.segment = {
            "symbol": "NABIL", "security_id": "123", "identity_verified": True,
            "effective_from": self.sessions[0], "effective_to": None,
            "boundary_reviewed": True, "suspension_overlap": False,
            "merger_or_successor_boundary": False, "adjustment_basis": "raw",
            "minimum_warmup_sessions": 20,
        }
        self.statuses = {day: "traded" for day in self.sessions}
        self.session_evidence = {
            day: {
                "status": "traded", "source_id": "fixture-calendar-v1",
                "source_record_ref": f"fixture:{day}",
                "source_url": "https://example.invalid/calendar/2025",
                "evidence_sha256": "b" * 64, "rights_status": "approved",
                "retrieved_at": "2025-12-31T15:00:00+05:45",
                "available_at": "2025-12-31T15:00:00+05:45",
            }
            for day in self.sessions
        }
        self.records = [self.row(day) for day in self.sessions]

    def row(self, day):
        return {
            "session_date": day, "symbol": "NABIL", "security_id": "123",
            "open": "100", "high": "105", "low": "95", "close": "102", "volume": "1000",
            "adjustment_basis": "raw", "rights_status": "approved",
            "evidence_sha256": "a" * 64, "available_at": "2025-12-31T15:00:00+05:45",
        }

    def evaluate(self, **overrides):
        statuses = overrides.get("session_statuses", self.statuses)
        evidence = {
            day: dict(item, status=statuses.get(day, item["status"]))
            for day, item in self.session_evidence.items()
        }
        args = dict(segment=self.segment, expected_sessions=self.sessions,
                    session_statuses=self.statuses, session_evidence=evidence,
                    records=self.records, required_sessions=120,
                    available_warmup_sessions=20,
                    decision_cutoff="2026-01-01T00:00:00+05:45")
        args.update(overrides)
        return evaluate_historical_segment(**args)

    def test_complete_verified_segment_is_exploratory_only(self):
        result = self.evaluate()
        self.assertTrue(result["exploratory_replay_eligible"])
        self.assertFalse(result["approved_backtest_eligible"])
        self.assertFalse(result["production_promotion_allowed"])

    def test_missing_bar_fails_closed(self):
        result = self.evaluate(records=self.records[:-1])
        self.assertIn("missing_bar:" + self.sessions[-1], result["reasons"])

    def test_verified_no_trade_is_not_missing_or_zero_filled(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "no_trade_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertEqual(result["verified_no_trade_count"], 1)
        self.assertEqual(result["verified_traded_session_count"], 119)
        self.assertIn("insufficient_traded_sessions", result["reasons"])

    def test_unverified_session_status_fails_closed(self):
        statuses = dict(self.statuses)
        del statuses[self.sessions[0]]
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("session_status_unverified:" + self.sessions[0], result["reasons"])

    def test_lifecycle_or_identity_unknown_fails_closed(self):
        segment = dict(self.segment, identity_verified=False, merger_or_successor_boundary=None)
        result = self.evaluate(segment=segment)
        self.assertIn("instrument_identity_not_verified", result["reasons"])
        self.assertIn("merger_or_successor_boundary_unknown_or_crossed", result["reasons"])

    def test_late_available_data_is_lookahead(self):
        records = list(self.records)
        records[0] = dict(records[0], available_at="2026-01-02T00:00:00+05:45")
        result = self.evaluate(records=records)
        self.assertIn("lookahead_available_after_cutoff:" + self.sessions[0], result["reasons"])

    def test_rights_and_hash_are_required(self):
        records = list(self.records)
        records[0] = dict(records[0], rights_status="unknown", evidence_sha256="bad")
        result = self.evaluate(records=records)
        self.assertIn("source_rights_not_approved:" + self.sessions[0], result["reasons"])
        self.assertIn("evidence_hash_missing_or_invalid:" + self.sessions[0], result["reasons"])

    def test_duplicate_bars_fail_closed(self):
        result = self.evaluate(records=self.records + [self.records[0]])
        self.assertIn("duplicate_bar:" + self.sessions[0], result["reasons"])

    def test_insufficient_warmup_fails_closed(self):
        result = self.evaluate(available_warmup_sessions=5)
        self.assertIn("insufficient_causal_warmup", result["reasons"])

    def test_no_trade_does_not_count_toward_required_traded_sessions(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "no_trade_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertIn("insufficient_traded_sessions", result["reasons"])
        self.assertEqual(result["verified_traded_session_count"], 119)

    def test_session_outside_effective_lifecycle_fails_closed(self):
        segment = dict(self.segment, effective_to=self.sessions[-2])
        result = self.evaluate(segment=segment)
        self.assertIn("session_outside_instrument_effective_interval:" + self.sessions[-1], result["reasons"])

    def test_no_trade_session_with_bar_is_conflict(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "no_trade_verified"})
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("bar_present_on_verified_no_trade_session:" + day, result["reasons"])


    def test_closed_session_is_distinct_from_verified_no_trade(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "closed_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertEqual(result["verified_closed_session_count"], 1)
        self.assertEqual(result["verified_no_trade_count"], 0)
        self.assertIn("closed_session_in_expected_sessions:" + day, result["reasons"])

    def test_explicit_unknown_session_is_not_assumed_closed(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "unknown"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertEqual(result["unknown_session_count"], 1)
        self.assertEqual(result["verified_closed_session_count"], 0)
        self.assertIn("session_status_unverified:" + day, result["reasons"])

    def test_adjustment_basis_mismatch_fails_closed(self):
        records = list(self.records)
        records[0] = dict(records[0], adjustment_basis="verified_adjusted")
        result = self.evaluate(records=records)
        self.assertIn("adjustment_basis_mismatch:" + self.sessions[0], result["reasons"])

    def test_record_outside_verified_session_grid_is_reported(self):
        records = list(self.records) + [self.row("2025-06-01")]
        result = self.evaluate(records=records)
        self.assertIn("unexpected_bar:2025-06-01", result["reasons"])

    def test_unavailable_or_naive_timestamp_fails_closed(self):
        records = list(self.records)
        records[0] = dict(records[0], available_at="2025-12-31T15:00:00")
        result = self.evaluate(records=records)
        self.assertIn("available_at_unverified:" + self.sessions[0], result["reasons"])

    def test_zero_volume_bar_is_invalid_for_traded_session(self):
        records = list(self.records)
        records[0] = dict(records[0], volume="0")
        result = self.evaluate(records=records)
        self.assertIn("invalid_ohlcv:" + self.sessions[0], result["reasons"])

    def test_expected_session_outside_lifecycle_fails_even_without_bar(self):
        segment = dict(self.segment, effective_to=self.sessions[-2])
        result = self.evaluate(segment=segment, records=self.records[:-1])
        self.assertIn(
            "expected_session_outside_instrument_effective_interval:" + self.sessions[-1],
            result["reasons"],
        )

    def test_status_for_date_outside_expected_grid_fails_closed(self):
        statuses = dict(self.statuses, **{"2025-06-01": "traded"})
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("unexpected_session_status:2025-06-01", result["reasons"])

    def test_expected_sessions_must_be_a_date_list(self):
        with self.assertRaisesRegex(ValueError, "expected_sessions must be a verified date list"):
            self.evaluate(expected_sessions="2025-01-01")

    def test_session_source_url_requires_https_host(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], source_url="https://")
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])
        self.assertEqual(result["unknown_session_count"], 1)

    def test_missing_session_source_provenance_fails_closed(self):
        evidence = dict(self.session_evidence)
        del evidence[self.sessions[0]]
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_missing:" + self.sessions[0], result["reasons"])
        self.assertEqual(result["unknown_session_count"], 1)

    def test_session_source_provenance_must_match_classification(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], status="no_trade_verified")
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_status_mismatch:" + self.sessions[0], result["reasons"])

    def test_late_session_source_evidence_fails_point_in_time_gate(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(
            evidence[self.sessions[0]], available_at="2026-01-02T00:00:00+05:45"
        )
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_lookahead:" + self.sessions[0], result["reasons"])


    def test_expected_sessions_must_be_an_explicit_date_list(self):
        with self.assertRaisesRegex(ValueError, "expected_sessions must be a verified date list"):
            self.evaluate(expected_sessions={"2025-01-01": True})

    def test_session_evidence_url_requires_https_authority(self):
        for bad_url in ("http://example.invalid/calendar", "https:///calendar", "https://[broken"):
            with self.subTest(url=bad_url):
                evidence = dict(self.session_evidence)
                evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], source_url=bad_url)
                result = self.evaluate(session_evidence=evidence)
                self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])


if __name__ == "__main__":
    unittest.main()
