import unittest
from datetime import date, datetime

from app.market_scan import run_market_scan


class MarketScanOrchestrationTests(unittest.TestCase):
    def test_scans_every_candidate_in_deterministic_order(self):
        called = []
        def scan(symbol, rows, as_of):
            called.append(symbol)
            return {"status": "screened", "signals": [], "metrics": {}}

        result = run_market_scan(
            ["ZZZ", "AAA"],
            {"AAA": [{"date": "2026-01-02"}], "ZZZ": [{"date": "2026-01-01"}]},
            as_of=None,
            scan_symbol=scan,
        )
        self.assertEqual(called, ["AAA", "ZZZ"])
        self.assertEqual([row["symbol"] for row in result["results"]], ["AAA", "ZZZ"])
        self.assertEqual(result["candidate_universe_count"], 2)
        self.assertEqual(result["observation_coverage_pct"], 100.0)
        self.assertFalse(result["ranking_enabled"])

    def test_as_of_excludes_future_rows_before_scanner_callback(self):
        seen = []
        def scan(symbol, rows, as_of):
            seen.extend(row["date"] for row in rows)
            return {"status": "screened"}

        result = run_market_scan(
            ["AAA"],
            {"AAA": [
                {"date": "2026-01-01"},
                {"date": "2026-01-03"},
                {"date": "2026-01-02"},
            ]},
            as_of=date(2026, 1, 2),
            scan_symbol=scan,
        )
        self.assertEqual(seen, ["2026-01-01", "2026-01-02"])
        self.assertEqual(result["results"][0]["latest_available_observation"], "2026-01-02")

    def test_missing_ohlcv_is_explicit_and_never_scanned(self):
        called = []
        result = run_market_scan(
            ["AAA", "BBB"],
            {"AAA": [{"date": "2026-01-01"}]},
            as_of=date(2026, 1, 2),
            scan_symbol=lambda *args: called.append(args) or {"status": "screened"},
        )
        self.assertEqual(len(called), 1)
        missing = result["results"][1]
        self.assertEqual(missing["symbol"], "BBB")
        self.assertEqual(missing["status"], "insufficient_data")
        self.assertEqual(missing["freshness_status"], "no_observation")
        self.assertIsNone(missing["latest_observation_calendar_age_days"])
        self.assertEqual(missing["requested_as_of"], "2026-01-02")
        self.assertEqual(missing["as_of"], "2026-01-02")
        self.assertFalse(missing["ranking_eligible"])
        self.assertEqual(result["symbols_without_observations"], 1)
        self.assertEqual(result["status_counts"]["insufficient_data"], 1)

    def test_callback_cannot_enable_ranking_or_buy_eligibility(self):
        result = run_market_scan(
            ["AAA"],
            {"AAA": [{"date": "2026-01-01"}]},
            as_of=date(2026, 1, 2),
            scan_symbol=lambda *args: {
                "status": "screened",
                "ranking_eligible": True,
                "buy_list_eligible": True,
                "signals": [],
                "metrics": {},
            },
        )
        row = result["results"][0]
        self.assertFalse(row["ranking_eligible"])
        self.assertFalse(row["buy_list_eligible"])
        self.assertFalse(result["ranking_enabled"])

    def test_calendar_age_is_reported_without_session_staleness_claim(self):
        result = run_market_scan(
            ["AAA"],
            {"AAA": [{"date": "2026-01-01"}]},
            as_of=date(2026, 1, 5),
            scan_symbol=lambda *args: {"status": "screened"},
        )
        row = result["results"][0]
        self.assertEqual(row["latest_observation_calendar_age_days"], 4)
        self.assertEqual(
            row["freshness_status"],
            "calendar_age_only_session_status_unverified",
        )
        self.assertIn("no stale-session judgment", result["disclaimer"])

    def test_duplicate_or_noncanonical_universe_is_rejected(self):
        for symbols in (["AAA", "AAA"], ["aaa"], [""]):
            with self.subTest(symbols=symbols):
                with self.assertRaises(ValueError):
                    run_market_scan(symbols, {}, as_of=None, scan_symbol=lambda *args: {})

    def test_bad_datetime_row_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be a datetime"):
            run_market_scan(
                ["AAA"], {"AAA": [{"date": datetime(2026, 1, 1)}]},
                as_of=None, scan_symbol=lambda *args: {},
            )

    def test_empty_universe_is_safe(self):
        result = run_market_scan([], {}, as_of=None, scan_symbol=lambda *args: {})
        self.assertEqual(result["candidate_universe_count"], 0)
        self.assertEqual(result["observation_coverage_pct"], 0.0)
        self.assertEqual(result["results"], [])
        self.assertFalse(result["ranking_enabled"])


if __name__ == "__main__":
    unittest.main()
