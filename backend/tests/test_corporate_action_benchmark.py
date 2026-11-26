import unittest
from app.corporate_action_benchmark import (
    adjust_ohlcv_for_corporate_actions, compare_portfolio_to_benchmark,
)


class CorporateActionAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"date": "2025-01-01", "open": 100, "high": 110, "low": 90, "close": 100, "volume": 1000},
            {"date": "2025-01-02", "open": 50, "high": 55, "low": 45, "close": 50, "volume": 2000},
            {"date": "2025-01-03", "open": 51, "high": 56, "low": 46, "close": 52, "volume": 2100},
        ]
        self.base = {"status": "verified", "source_id": "cdsc-record-1",
                     "available_at": "2025-01-01T10:00:00+05:45", "ex_date": "2025-01-02"}

    def adjust(self, action):
        return adjust_ohlcv_for_corporate_actions(
            rows=self.rows, actions=[action], as_of_date="2025-01-03",
            evidence_cutoff="2025-01-03T15:00:00+05:45")

    def test_bonus_and_split_adjust_pre_ex_date_prices_and_volume(self):
        for kind in ("bonus", "split"):
            action = dict(self.base, action_type=kind, ratio=1)
            result = self.adjust(action)
            self.assertEqual(result["rows"][0]["close"], 50)
            self.assertEqual(result["rows"][0]["volume"], 2000)
            self.assertEqual(result["rows"][1]["close"], 50)

    def test_cash_dividend_adjustment(self):
        action = dict(self.base, action_type="dividend", cash_per_share=10)
        result = self.adjust(action)
        self.assertEqual(result["rows"][0]["close"], 90)
        self.assertEqual(result["rows"][1]["close"], 50)

    def test_rights_theoretical_ex_rights_adjustment(self):
        action = dict(self.base, action_type="rights", ratio=1, subscription_price=50)
        result = self.adjust(action)
        self.assertEqual(result["rows"][0]["close"], 75)

    def test_future_action_is_not_applied(self):
        action = dict(self.base, action_type="bonus", ratio=1, ex_date="2025-01-04")
        result = self.adjust(action)
        self.assertEqual(result["rows"][0]["close"], 100)
        self.assertEqual(result["action_audit"], [])

    def test_unverified_or_lookahead_action_rejected(self):
        action = dict(self.base, action_type="bonus", ratio=1, status="unverified")
        with self.assertRaisesRegex(ValueError, "not_verified"):
            self.adjust(action)
        action = dict(self.base, action_type="bonus", ratio=1,
                      available_at="2025-01-04T10:00:00+05:45")
        with self.assertRaisesRegex(ValueError, "lookahead"):
            self.adjust(action)

    def test_duplicate_ohlcv_dates_rejected(self):
        with self.assertRaisesRegex(ValueError, "unique_and_ordered"):
            adjust_ohlcv_for_corporate_actions(
                rows=[self.rows[0], self.rows[0]], actions=[],
                as_of_date="2025-01-03", evidence_cutoff="2025-01-03T15:00:00+05:45")


class BenchmarkComparisonTests(unittest.TestCase):
    def test_exact_date_aligned_excess_return(self):
        result = compare_portfolio_to_benchmark(
            portfolio_curve=[{"date": "2025-01-01", "equity": 1000},
                             {"date": "2025-01-02", "equity": 1100},
                             {"date": "2025-01-03", "equity": 1050}],
            benchmark_rows=[{"date": "2025-01-01", "close": 2000},
                            {"date": "2025-01-03", "close": 2100}],
            as_of_date="2025-01-03")
        self.assertEqual(result["aligned_observations"], 2)
        self.assertEqual(result["portfolio_return_pct"], 5.0)
        self.assertEqual(result["benchmark_return_pct"], 5.0)
        self.assertEqual(result["excess_return_pct"], 0.0)

    def test_no_interpolation_or_future_benchmark_data(self):
        with self.assertRaisesRegex(ValueError, "two_aligned"):
            compare_portfolio_to_benchmark(
                portfolio_curve=[{"date": "2025-01-01", "equity": 1000}],
                benchmark_rows=[{"date": "2025-01-01", "close": 2000}],
                as_of_date="2025-01-01")


if __name__ == "__main__":
    unittest.main()
