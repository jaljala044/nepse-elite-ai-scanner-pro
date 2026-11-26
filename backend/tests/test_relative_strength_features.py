import unittest
from datetime import date, timedelta

from app.relative_strength_features import relative_strength_universe

DIGEST = "c" * 64


def rows_for(symbol, count=127, rate=0.5, *, benchmark=False):
    start = date(2025, 1, 1)
    result = []
    for i in range(count):
        session = (start + timedelta(days=i)).isoformat()
        row = {
            "session_date": session, "close": 100 + i * rate,
            "source_validation_status": "verified", "source_id": "archive-v1",
            "source_payload_sha256": DIGEST,
        }
        if benchmark:
            row.update({"record_type": "index_ohlcv", "index_code": "NEPSE",
                        "finality_status": "final"})
        else:
            row.update({"symbol": symbol, "price_basis_status": "verified_unadjusted_no_actions",
                        "corporate_action_status": "clear"})
        result.append(row)
    return result


class RelativeStrengthTests(unittest.TestCase):
    def test_weighted_excess_returns_and_percentile_rank(self):
        benchmark = rows_for("NEPSE", rate=0.2, benchmark=True)
        securities = {
            "STRONG": rows_for("STRONG", rate=0.8),
            "WEAK": rows_for("WEAK", rate=0.05),
        }
        result = relative_strength_universe(securities, benchmark,
                                            expected_symbols=["STRONG", "WEAK"])
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["eligible_symbols"], 2)
        self.assertGreater(result["results"]["STRONG"]["weighted_excess_return_pct"],
                           result["results"]["WEAK"]["weighted_excess_return_pct"])
        self.assertEqual(result["results"]["STRONG"]["rank"], 1)
        self.assertEqual(result["results"]["WEAK"]["rank"], 2)

    def test_unverified_benchmark_never_enters_rs(self):
        benchmark = rows_for("NEPSE", benchmark=True)
        for row in benchmark:
            row["source_validation_status"] = "provisional"
        result = relative_strength_universe(
            {"AAA": rows_for("AAA"), "BBB": rows_for("BBB")},
            benchmark, expected_symbols=["AAA", "BBB"])
        self.assertEqual(result["reason"], "insufficient_verified_final_nepse_benchmark_history")
        self.assertEqual(result["eligible_symbols"], 0)

    def test_unverified_stock_price_basis_excludes_symbol(self):
        benchmark = rows_for("NEPSE", benchmark=True)
        strong = rows_for("AAA")
        strong[0]["corporate_action_status"] = "unreviewed"
        result = relative_strength_universe(
            {"AAA": strong, "BBB": rows_for("BBB")},
            benchmark, expected_symbols=["AAA", "BBB"])
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("AAA", result["excluded_symbols"])
        self.assertIsNone(result["results"]["BBB"]["score"])

    def test_missing_exact_intermediate_session_excludes_symbol(self):
        benchmark = rows_for("NEPSE", benchmark=True)
        stock = rows_for("AAA")
        stock = [row for row in stock if row["session_date"] != benchmark[-10]["session_date"]]
        result = relative_strength_universe(
            {"AAA": stock, "BBB": rows_for("BBB")},
            benchmark, expected_symbols=["AAA", "BBB"])
        self.assertIn("AAA", result["excluded_symbols"])
        self.assertEqual(result["eligible_symbols"], 1)
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_universe_coverage_gate_withholds_all_scores(self):
        benchmark = rows_for("NEPSE", benchmark=True)
        securities = {"AAA": rows_for("AAA"), "BBB": rows_for("BBB")}
        result = relative_strength_universe(
            securities, benchmark, expected_symbols=["AAA", "BBB", "CCC"])
        self.assertEqual(result["universe_coverage_pct"], 66.67)
        self.assertIsNone(result["results"]["AAA"]["score"])

    def test_duplicate_benchmark_session_rejected(self):
        benchmark = rows_for("NEPSE", benchmark=True)
        benchmark.append(dict(benchmark[-1]))
        with self.assertRaisesRegex(ValueError, "duplicate session_date"):
            relative_strength_universe(
                {"AAA": rows_for("AAA"), "BBB": rows_for("BBB")},
                benchmark, expected_symbols=["AAA", "BBB"])

    def test_bad_digest_excludes_stock(self):
        benchmark = rows_for("NEPSE", benchmark=True)
        stock = rows_for("AAA")
        stock[0]["source_payload_sha256"] = "not-a-hash"
        result = relative_strength_universe(
            {"AAA": stock, "BBB": rows_for("BBB")},
            benchmark, expected_symbols=["AAA", "BBB"])
        self.assertIn("AAA", result["excluded_symbols"])


if __name__ == "__main__":
    unittest.main()
