import unittest
from datetime import date, timedelta

from app.trend_features import minervini_trend_template
from app.relative_strength_features import relative_strength_universe


def price_rows(n, fn=lambda i: 100 + i):
    start = date(2025, 1, 1)
    rows = []
    for i in range(n):
        close = float(fn(i))
        rows.append({
            "session_date": (start + timedelta(days=i)).isoformat(),
            "open": close, "high": close + 2, "low": close - 2,
            "close": close, "volume": 1000,
        })
    return rows


class MinerviniTrendTests(unittest.TestCase):
    def test_insufficient_252_sessions_is_null_not_zero(self):
        result = minervini_trend_template(price_rows(251))
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_strong_rising_series_passes_trend_conditions(self):
        result = minervini_trend_template(price_rows(260))
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["score"], 100)
        self.assertTrue(all(result["checks"].values()))

    def test_duplicate_dates_rejected(self):
        rows = price_rows(252)
        rows.append(dict(rows[-1]))
        with self.assertRaises(ValueError):
            minervini_trend_template(rows)

    def test_invalid_price_rejected(self):
        rows = price_rows(252)
        rows[-1]["close"] = float("nan")
        with self.assertRaises(ValueError):
            minervini_trend_template(rows)


class RelativeStrengthTests(unittest.TestCase):
    def test_weighted_rs_and_percentile(self):
        benchmark = price_rows(130, lambda i: 100 + i * 0.2)
        strong = price_rows(130, lambda i: 100 + i * 0.8)
        weak = price_rows(130, lambda i: 100 + i * 0.05)
        result = relative_strength_universe(
            {"STRONG": strong, "WEAK": weak}, benchmark
        )
        self.assertEqual(result["eligible_symbols"], 2)
        self.assertGreater(
            result["results"]["STRONG"]["weighted_excess_return_pct"],
            result["results"]["WEAK"]["weighted_excess_return_pct"],
        )
        self.assertGreater(result["results"]["STRONG"]["score"], result["results"]["WEAK"]["score"])
        self.assertEqual(result["results"]["STRONG"]["rank"], 1)
        self.assertEqual(result["results"]["WEAK"]["rank"], 2)

    def test_incomplete_history_excluded(self):
        result = relative_strength_universe(
            {"SHORT": price_rows(100)}, price_rows(130)
        )
        self.assertEqual(result["eligible_symbols"], 0)
        self.assertIn("SHORT", result["excluded_symbols"])


    def test_missing_intermediate_benchmark_session_is_not_skipped(self):
        benchmark = price_rows(130)
        stock = price_rows(130, lambda i: 100 + i * 0.5)
        stock = [row for i, row in enumerate(stock) if i != 100]
        result = relative_strength_universe({"AAA": stock}, benchmark)
        self.assertEqual(result["eligible_symbols"], 0)
        self.assertIn("missing_exact_sessions", result["excluded_symbols"]["AAA"])

    def test_stale_stock_endpoint_is_not_used_for_cross_sectional_rs(self):
        benchmark = price_rows(130)
        stock = price_rows(130)[:-1]
        result = relative_strength_universe({"AAA": stock}, benchmark)
        self.assertEqual(result["eligible_symbols"], 0)
        self.assertEqual(result["excluded_symbols"]["AAA"], "missing_latest_benchmark_session")

    def test_duplicate_benchmark_dates_rejected(self):
        benchmark = price_rows(130)
        benchmark.append(dict(benchmark[-1]))
        with self.assertRaises(ValueError):
            relative_strength_universe({"AAA": price_rows(130)}, benchmark)

    def test_stock_benchmark_session_mismatch_not_filled(self):
        stock = price_rows(130)
        stock = stock[:-10]
        result = relative_strength_universe({"AAA": stock}, price_rows(130))
        self.assertEqual(result["eligible_symbols"], 0)
        self.assertIn("AAA", result["excluded_symbols"])


if __name__ == "__main__":
    unittest.main()
