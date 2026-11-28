import unittest
from datetime import date, timedelta
from app.strategy_horizon_policy import assess_holding_duration

class StrategyHorizonPolicyTests(unittest.TestCase):
    def check(self, horizon, days, protective=False):
        start = date(2026, 6, 1)
        return assess_holding_duration(horizon, start.isoformat(),
            (start + timedelta(days=days)).isoformat(), protective_exit=protective)

    def test_swing_boundaries(self):
        for days, expected in ((2, False), (3, True), (15, True), (16, False)):
            with self.subTest(days=days):
                self.assertEqual(self.check("swing", days)["within_planned_band"], expected)

    def test_positional_boundaries(self):
        for days, expected in ((13, False), (14, True), (56, True), (57, False)):
            with self.subTest(days=days):
                self.assertEqual(self.check("positional", days)["within_planned_band"], expected)

    def test_protective_exit_is_not_blocked(self):
        for horizon in ("swing", "positional"):
            for days in (1, 60):
                r = self.check(horizon, days, True)
                self.assertTrue(r["duration_policy_allows_exit"])
                self.assertFalse(r["within_planned_band"])
                self.assertFalse(r["settlement_and_execution_verified"])

    def test_invalid_dates_and_horizons(self):
        for horizon, days in (("unknown", 5), ("swing", -1)):
            with self.assertRaises(ValueError):
                self.check(horizon, days)

    def test_not_production_eligible(self):
        self.assertFalse(self.check("swing", 5)["production_eligible"])
