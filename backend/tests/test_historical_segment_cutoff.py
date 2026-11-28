import unittest

from app.historical_segment_eligibility import evaluate_historical_segment


class HistoricalSegmentCutoffTests(unittest.TestCase):
    def test_future_expected_session_is_explicitly_rejected(self):
        result = evaluate_historical_segment(
            segment={},
            expected_sessions=["2026-01-02"],
            session_statuses={},
            session_evidence={},
            records=[],
            required_sessions=1,
            decision_cutoff="2026-01-01T00:00:00+05:45",
        )
        self.assertIn("future_expected_session:2026-01-02", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertFalse(result["approved_backtest_eligible"])
        self.assertFalse(result["production_promotion_allowed"])

    def test_same_kathmandu_calendar_date_is_not_future(self):
        result = evaluate_historical_segment(
            segment={},
            expected_sessions=["2026-01-01"],
            session_statuses={},
            session_evidence={},
            records=[],
            required_sessions=1,
            decision_cutoff="2026-01-01T23:59:59+05:45",
        )
        self.assertNotIn("future_expected_session:2026-01-01", result["reasons"])


if __name__ == "__main__":
    unittest.main()
