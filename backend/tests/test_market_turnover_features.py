import unittest
from datetime import date, timedelta

from app.market_turnover_features import nepse_market_turnover_component

DIGEST = "b" * 64
DECISION = "2026-11-26T16:00:00+05:45"


def calendar(count=21):
    start = date(2026, 10, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(count)]


def rows_for(values=None, dates=None):
    dates = dates or calendar()
    values = values or [100.0] * len(dates)
    return [{
        "record_type": "market_summary",
        "market_code": "NEPSE",
        "session_date": session,
        "total_turnover": value,
        "source_validation_status": "verified",
        "finality_status": "final",
        "source_id": "nepse-market-summary-reviewed-v1",
        "source_payload_sha256": DIGEST,
        "available_at": "2026-11-25T15:00:00+05:45",
    } for session, value in zip(dates, values)]


class MarketTurnoverTests(unittest.TestCase):
    def run_component(self, rows=None, dates=None):
        dates = dates or calendar()
        rows = rows if rows is not None else rows_for(dates=dates)
        return nepse_market_turnover_component(
            rows, session_dates=dates, decision_time=DECISION
        )

    def test_flat_turnover_produces_midrange_participation_score(self):
        result = self.run_component()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["score"], 57.5)
        self.assertEqual(result["metrics"]["latest_vs_trailing_median_ratio"], 1.0)

    def test_expanding_turnover_is_scored_and_flagged_as_not_directional(self):
        values = [100.0] * 16 + [150.0] * 5
        result = self.run_component(rows=rows_for(values))
        self.assertEqual(result["status"], "verified")
        self.assertGreater(result["score"], 70)
        self.assertIn("recent_five_session_turnover_expanding_sharply_confirm_with_breadth_and_price",
                      result["warnings"])
        self.assertIn("not_directional", result["interpretation"])

    def test_contracting_turnover_is_flagged(self):
        values = [100.0] * 11 + [60.0] * 10
        result = self.run_component(rows=rows_for(values))
        self.assertIn("recent_five_session_turnover_contracting", result["warnings"])

    def test_provisional_record_withholds_score(self):
        rows = rows_for()
        rows[0]["source_validation_status"] = "provisional"
        self.assertIsNone(self.run_component(rows=rows)["score"])

    def test_future_available_at_withholds_score(self):
        rows = rows_for()
        rows[-1]["available_at"] = "2026-11-27T10:00:00+05:45"
        self.assertIsNone(self.run_component(rows=rows)["score"])

    def test_bad_hash_withholds_score(self):
        rows = rows_for()
        rows[0]["source_payload_sha256"] = "bad"
        self.assertIsNone(self.run_component(rows=rows)["score"])

    def test_missing_session_is_not_imputed(self):
        rows = rows_for()
        rows.pop(3)
        result = self.run_component(rows=rows)
        self.assertIsNone(result["score"])
        self.assertEqual(len(result["missing_sessions"]), 1)

    def test_duplicate_session_fails(self):
        rows = rows_for()
        rows.append(dict(rows[-1]))
        with self.assertRaisesRegex(ValueError, "duplicate NEPSE market summary session"):
            self.run_component(rows=rows)

    def test_source_change_within_window_withholds_score(self):
        rows = rows_for()
        rows[-1]["source_id"] = "other-source"
        result = self.run_component(rows=rows)
        self.assertEqual(result["reason"], "market_turnover_source_changed_within_window")

    def test_short_history_is_unavailable(self):
        dates = calendar(20)
        result = self.run_component(dates=dates)
        self.assertEqual(result["reason"], "market_turnover_history_below_21_sessions")


if __name__ == "__main__":
    unittest.main()
