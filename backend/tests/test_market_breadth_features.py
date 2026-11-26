import unittest
from datetime import date, timedelta

from app.market_breadth_features import market_breadth_component

DIGEST = "a" * 64
DECISION = "2026-11-26T16:00:00+05:45"


def calendar(count=200):
    start = date(2025, 1, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(count)]


def rows_for(symbols=("AAA", "BBB", "CCC"), count=200, *, rising=True):
    dates = calendar(count)
    output = []
    for symbol_index, symbol in enumerate(symbols):
        for index, session in enumerate(dates):
            base = 1000 + index if rising else 1200 - index
            close = base + symbol_index
            output.append({
                "record_type": "ohlcv", "symbol": symbol, "session_date": session,
                "open": close - 1, "high": close + 2, "low": close - 2, "close": close,
                "source_validation_status": "verified", "finality_status": "final",
                "source_id": "nepse-official-reviewed", "source_payload_sha256": DIGEST,
                "available_at": "2026-11-25T15:00:00+05:45",
            })
    return output


def provenance(dates):
    return {"status": "verified", "source_id": "nepse-security-universe",
            "source_payload_sha256": DIGEST, "as_of_session": dates[-1]}


class MarketBreadthTests(unittest.TestCase):
    def run_component(self, rows=None, symbols=("AAA", "BBB", "CCC"), dates=None, **kwargs):
        dates = dates or calendar()
        rows = rows if rows is not None else rows_for(symbols, len(dates))
        return market_breadth_component(
            rows, expected_symbols=list(symbols), universe_provenance=provenance(dates),
            session_dates=dates, decision_time=DECISION, **kwargs
        )

    def test_verified_rising_universe_returns_full_breadth_component(self):
        result = self.run_component()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["coverage_pct"], 100)
        self.assertEqual(result["metrics"]["pct_above_sma200"], 100)

    def test_incomplete_symbol_coverage_withholds_score(self):
        rows = rows_for()
        rows = [row for row in rows if row["symbol"] != "CCC"]
        result = self.run_component(rows=rows)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_provisional_row_withholds_affected_symbol(self):
        rows = rows_for()
        rows[0]["source_validation_status"] = "provisional"
        result = self.run_component(rows=rows)
        self.assertIsNone(result["score"])
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_future_available_at_is_not_admitted(self):
        rows = rows_for()
        rows[-1]["available_at"] = "2026-11-27T10:00:00+05:45"
        result = self.run_component(rows=rows)
        self.assertIsNone(result["score"])

    def test_bad_hash_is_not_admitted(self):
        rows = rows_for()
        rows[0]["source_payload_sha256"] = "invalid"
        result = self.run_component(rows=rows)
        self.assertIsNone(result["score"])

    def test_duplicate_symbol_session_fails(self):
        rows = rows_for()
        rows.append(dict(rows[-1]))
        with self.assertRaisesRegex(ValueError, "duplicate OHLCV session"):
            self.run_component(rows=rows)

    def test_missing_exact_session_is_not_filled(self):
        rows = rows_for()
        rows = [row for row in rows if not (row["symbol"] == "AAA" and row["session_date"] == calendar()[4])]
        result = self.run_component(rows=rows)
        self.assertIsNone(result["score"])

    def test_calendar_below_200_sessions_is_unavailable(self):
        dates = calendar(199)
        result = self.run_component(dates=dates)
        self.assertEqual(result["reason"], "canonical_calendar_below_200_sessions")

    def test_unverified_universe_is_not_accepted(self):
        dates = calendar()
        p = provenance(dates)
        p["status"] = "provisional"
        result = market_breadth_component(
            rows_for(), expected_symbols=["AAA", "BBB", "CCC"], universe_provenance=p,
            session_dates=dates, decision_time=DECISION
        )
        self.assertIsNone(result["score"])


if __name__ == "__main__":
    unittest.main()
