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
        self.records = [self.row(day) for day in self.sessions]

    def row(self, day):
        return {
            "session_date": day, "symbol": "NABIL", "security_id": "123",
            "open": "100", "high": "105", "low": "95", "close": "102", "volume": "1000",
            "adjustment_basis": "raw", "rights_status": "approved",
            "evidence_sha256": "a" * 64, "available_at": "2025-12-31T15:00:00+05:45",
        }

    def evaluate(self, **overrides):
        args = dict(segment=self.segment, expected_sessions=self.sessions,
                    session_statuses=self.statuses, records=self.records,
                    required_sessions=120, available_warmup_sessions=20,
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


    def test_runtime_requires_pinned_ledger(self):
        from unittest.mock import patch
        from app.historical_segment_eligibility import evaluate_runtime_historical_segment
        with patch("app.historical_segment_eligibility.runtime_quarantine_keys", side_effect=ValueError("missing")):
            result = evaluate_runtime_historical_segment()
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertFalse(result["approved_backtest_eligible"])

    def test_runtime_ledger_cannot_be_overridden_by_empty_caller_keys(self):
        from unittest.mock import patch
        from app.historical_segment_eligibility import evaluate_runtime_historical_segment
        with patch("app.historical_segment_eligibility.runtime_quarantine_keys",
                   return_value=frozenset({("NABIL", self.sessions[0])})):
            result = evaluate_runtime_historical_segment(
                segment=self.segment, expected_sessions=self.sessions,
                session_statuses=self.statuses, records=self.records,
                required_sessions=120, available_warmup_sessions=20,
                decision_cutoff="2026-01-01T00:00:00+05:45", blocked_keys=set())
        self.assertIn("quarantined_bar:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_runtime_cannot_admit_legacy_rows_without_session_evidence(self):
        from unittest.mock import patch
        from app.historical_segment_eligibility import evaluate_runtime_historical_segment
        with patch("app.historical_segment_eligibility.runtime_quarantine_keys",
                   return_value=frozenset()):
            result = evaluate_runtime_historical_segment(
                segment=self.segment, expected_sessions=self.sessions,
                session_statuses=self.statuses, records=self.records,
                required_sessions=120, available_warmup_sessions=20,
                decision_cutoff="2026-01-01T00:00:00+05:45")
        self.assertIn("runtime_session_evidence_required", result["reasons"])
        self.assertEqual(result["eligible_ohlcv_candle_count"], 0)
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_explicit_quarantine_marker_blocks_traded_bar(self):
        records = list(self.records)
        records[0] = dict(records[0], quarantined=True)
        result = self.evaluate(records=records)
        self.assertIn("quarantined_bar:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertEqual(result["verified_traded_session_count"], 119)

    def test_blocked_no_trade_session_cannot_bridge_window(self):
        day = self.sessions[-1]
        result = self.evaluate(session_statuses=dict(self.statuses, **{day: "no_trade_verified"}),
                               records=self.records[:-1], required_sessions=119,
                               blocked_keys={("NABIL", day)})
        self.assertIn("quarantined_session_in_window", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])


if __name__ == "__main__":
    unittest.main()
