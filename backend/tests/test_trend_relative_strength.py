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
            "source_validation_status": "verified",
            "source_id": "equity-test-source",
            "source_payload_sha256": "e" * 64,
            "price_basis_status": "verified_unadjusted_no_actions",
            "corporate_action_status": "clear",
        })
    return rows



def benchmark_rows(n, fn=lambda i: 100 + i):
    rows = price_rows(n, fn)
    for row in rows:
        row.update({
            "record_type": "index_ohlcv", "index_code": "NEPSE",
            "finality_status": "final", "source_validation_status": "verified",
            "source_id": "nepse-final-test-source", "source_payload_sha256": "f" * 64,
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
        benchmark = benchmark_rows(130, lambda i: 100 + i * 0.2)
        strong = price_rows(130, lambda i: 100 + i * 0.8)
        weak = price_rows(130, lambda i: 100 + i * 0.05)
        result = relative_strength_universe(
            {"STRONG": strong, "WEAK": weak}, benchmark, expected_symbols=["STRONG", "WEAK"]
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
            {"SHORT": price_rows(100)}, benchmark_rows(130), expected_symbols=["SHORT"]
        )
        self.assertEqual(result["eligible_symbols"], 0)
        self.assertIn("SHORT", result["excluded_symbols"])

    def test_duplicate_benchmark_dates_rejected(self):
        benchmark = benchmark_rows(130)
        benchmark.append(dict(benchmark[-1]))
        with self.assertRaises(ValueError):
            relative_strength_universe({"AAA": price_rows(130)}, benchmark, expected_symbols=["AAA"])

    def test_stock_benchmark_session_mismatch_not_filled(self):
        stock = price_rows(130)
        stock = stock[:-10]
        result = relative_strength_universe({"AAA": stock}, benchmark_rows(130), expected_symbols=["AAA"])
        self.assertEqual(result["eligible_symbols"], 0)
        self.assertIn("AAA", result["excluded_symbols"])


if __name__ == "__main__":
    unittest.main()
