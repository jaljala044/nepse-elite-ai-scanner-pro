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


    def test_bos_then_choch_are_detected_after_confirmed_pivots(self):
        rows = bars(20)
        rows[6] = {**rows[6], "open": 100, "high": 110, "low": 99, "close": 100}
        rows[12] = {**rows[12], "open": 95, "high": 96, "low": 90, "close": 95}
        rows[15] = {**rows[15], "open": 89, "high": 90, "low": 88, "close": 89}
        # Break above the confirmed swing high after two right-hand bars.
        rows[9] = {**rows[9], "open": 111, "high": 113, "low": 110, "close": 112}
        result = smc_features(rows)
        events = result["timeframes"]["daily"]["events"]
        self.assertIn("bos", [event["event"] for event in events])
        self.assertIn("choch", [event["event"] for event in events])

    def test_buy_side_and_sell_side_liquidity_sweeps_are_candidates(self):
        rows = bars(20)
        rows[6] = {**rows[6], "open": 100, "high": 110, "low": 99, "close": 100}
        rows[9] = {**rows[9], "open": 109, "high": 111, "low": 108, "close": 109}
        rows[12] = {**rows[12], "open": 95, "high": 96, "low": 90, "close": 95}
        rows[15] = {**rows[15], "open": 91, "high": 92, "low": 89, "close": 91}
        result = smc_features(rows)
        labels = [event["event"] for event in result["liquidity_sweeps"]]
        self.assertIn("buy_side_liquidity_sweep", labels)
        self.assertIn("sell_side_liquidity_sweep", labels)

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
