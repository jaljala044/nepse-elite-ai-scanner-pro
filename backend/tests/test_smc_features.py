import unittest
from datetime import date, timedelta

from app.smc_features import smc_features


def bars(count=30):
    start = date(2026, 1, 1)
    result = []
    for i in range(count):
        close = 100 + (i % 5) - 2
        result.append({
            "session_date": (start + timedelta(days=i)).isoformat(),
            "open": close, "high": close + 1, "low": close - 1, "close": close,
        })
    return result


class SMCFeatureTests(unittest.TestCase):
    def test_insufficient_history_is_unscored(self):
        result = smc_features(bars(9))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_bullish_fvg_detected_and_mitigation_tracked(self):
        rows = bars(12)
        rows[5] = {**rows[5], "open": 103, "high": 104, "low": 102, "close": 103.5}
        rows[6] = {**rows[6], "open": 104, "high": 106, "low": 103, "close": 105}
        rows[7] = {**rows[7], "open": 107, "high": 109, "low": 105, "close": 108}
        result = smc_features(rows)
        gaps = [g for g in result["fvg"] if g["formed_session"] == rows[7]["session_date"]]
        self.assertTrue(gaps)
        self.assertEqual(gaps[0]["direction"], "bullish")
        self.assertEqual(gaps[0]["status"], "open")

    def test_fvg_mitigation_is_marked_from_later_bar_overlap(self):
        rows = bars(13)
        rows[5] = {**rows[5], "open": 103, "high": 104, "low": 102, "close": 103.5}
        rows[6] = {**rows[6], "open": 104, "high": 106, "low": 103, "close": 105}
        rows[7] = {**rows[7], "open": 107, "high": 109, "low": 105, "close": 108}
        rows[12] = {**rows[12], "open": 104, "high": 106, "low": 103, "close": 105}
        result = smc_features(rows)
        gap = next(g for g in result["fvg"] if g["formed_session"] == rows[7]["session_date"])
        self.assertEqual(gap["status"], "mitigated")

    def test_pivot_confirmation_uses_right_hand_bars(self):
        rows = bars(12)
        rows[4] = {**rows[4], "high": 110, "low": 98}
        result = smc_features(rows)
        pivot = result["timeframes"]["daily"]["latest_confirmed_swing_high"]
        if pivot and pivot["pivot_session"] == rows[4]["session_date"]:
            self.assertEqual(pivot["confirmed_session"], rows[6]["session_date"])

    def test_weekly_and_monthly_mark_latest_bucket_as_excluded(self):
        rows = bars(80)
        result = smc_features(rows)
        self.assertIn("latest calendar week excluded", result["timeframes"]["weekly"]["period_note"])
        self.assertIn("latest calendar month excluded", result["timeframes"]["monthly"]["period_note"])

    def test_duplicate_dates_rejected(self):
        rows = bars()
        rows[-1] = dict(rows[-2])
        with self.assertRaisesRegex(ValueError, "duplicate session_date"):
            smc_features(rows)

    def test_invalid_ohlc_rejected(self):
        rows = bars()
        rows[-1]["low"] = rows[-1]["high"] + 1
        with self.assertRaisesRegex(ValueError, "inconsistent high"):
            smc_features(rows)


if __name__ == "__main__":
    unittest.main()
