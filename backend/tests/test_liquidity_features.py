import unittest
from datetime import date, timedelta

from app.liquidity_features import liquidity_tradability_features

DIGEST = "b" * 64


def fixture():
    dates = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(20)]
    rows = []
    for symbol, scale in (("AAA", 4.0), ("BBB", 2.0), ("CCC", 1.0)):
        for day in dates:
            rows.append({"symbol": symbol, "session_date": day,
                "turnover": 10000 * scale, "trade_count": 100 * scale,
                "best_bid": 99.0, "best_ask": 101.0 + (4 - scale),
                "bid_depth": 500 * scale, "ask_depth": 400 * scale,
                "source_validation_status": "verified", "source_id": "book-eod",
                "source_payload_sha256": DIGEST})
    return dates, rows


class LiquidityFeatureTests(unittest.TestCase):
    def test_complete_verified_universe_scores(self):
        dates, rows = fixture()
        result = liquidity_tradability_features(rows, expected_symbols=["AAA", "BBB", "CCC"],
                                                session_dates=dates)
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["symbols"]["AAA"]["score_status"], "observed")
        self.assertGreater(result["symbols"]["AAA"]["score"], result["symbols"]["CCC"]["score"])
        self.assertFalse(result["execution_approval"])

    def test_unverified_rows_are_not_counted(self):
        dates, rows = fixture()
        for row in rows:
            if row["symbol"] == "AAA":
                row["source_validation_status"] = "provisional"
        result = liquidity_tradability_features(rows, expected_symbols=["AAA", "BBB", "CCC"],
                                                session_dates=dates)
        self.assertEqual(result["symbols"]["AAA"]["status"], "insufficient_evidence")
        self.assertEqual(result["observed_symbols"], 2)
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_missing_session_blocks_symbol_score(self):
        dates, rows = fixture()
        rows = [row for row in rows if not (row["symbol"] == "AAA" and row["session_date"] == dates[5])]
        result = liquidity_tradability_features(rows, expected_symbols=["AAA", "BBB", "CCC"],
                                                session_dates=dates)
        self.assertIsNone(result["symbols"]["AAA"]["score"])
        self.assertEqual(result["symbols"]["AAA"]["observed_sessions"], 19)

    def test_duplicate_symbol_session_rejected(self):
        dates, rows = fixture()
        rows.append(dict(rows[0]))
        with self.assertRaisesRegex(ValueError, "duplicate symbol/session"):
            liquidity_tradability_features(rows, expected_symbols=["AAA", "BBB", "CCC"],
                                            session_dates=dates)

    def test_crossed_book_rejected(self):
        dates, rows = fixture()
        rows[0]["best_bid"], rows[0]["best_ask"] = 102, 101
        with self.assertRaisesRegex(ValueError, "crossed order book"):
            liquidity_tradability_features(rows, expected_symbols=["AAA", "BBB", "CCC"],
                                            session_dates=dates)

    def test_short_calendar_fails_closed(self):
        result = liquidity_tradability_features([], expected_symbols=["AAA", "BBB"],
                                                session_dates=["2026-01-01"])
        self.assertEqual(result["reason"], "canonical_calendar_below_20_sessions")


if __name__ == "__main__":
    unittest.main()
