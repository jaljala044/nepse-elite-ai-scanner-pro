import math
import unittest
from datetime import date, timedelta

from app.market_volatility_features import nepse_index_volatility_component

DIGEST = "c" * 64
DECISION = "2026-11-26T16:00:00+05:45"


def calendar(count=271):
    start = date(2025, 1, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(count)]


def rows_for_closes(closes, dates=None):
    dates = dates or calendar(len(closes))
    return [{
        "record_type": "index_ohlcv",
        "index_code": "NEPSE",
        "session_date": session,
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "source_validation_status": "verified",
        "finality_status": "final",
        "source_id": "nepse-index-reviewed-v1",
        "source_payload_sha256": DIGEST,
        "available_at": "2026-11-25T15:00:00+05:45",
    } for session, close in zip(dates, closes)]


class MarketVolatilityTests(unittest.TestCase):
    def run_component(self, rows=None, dates=None):
        dates = dates or calendar()
        if rows is None:
            rows = rows_for_closes([100.0] * len(dates), dates)
        return nepse_index_volatility_component(
            rows, session_dates=dates, decision_time=DECISION
        )

    def test_flat_market_uses_midrank_for_tied_volatility(self):
        result = self.run_component()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["metrics"]["realized_volatility_20_session_annualized_pct"], 0.0)
        self.assertEqual(result["score"], 50.0)

    def test_low_current_volatility_ranks_as_stability(self):
        returns = [0.01 if i % 2 else -0.01 for i in range(250)] + [0.0001] * 20
        closes = [100.0]
        for change in returns:
            closes.append(closes[-1] * math.exp(change))
        result = self.run_component(rows=rows_for_closes(closes))
        self.assertGreater(result["score"], 90)
        self.assertIn("realized_volatility_in_bottom_decile_compression_watch_for_regime_expansion",
                      result["warnings"])

    def test_high_current_volatility_is_penalized(self):
        returns = [0.0001] * 250 + [0.05 if i % 2 else -0.05 for i in range(20)]
        closes = [100.0]
        for change in returns:
            closes.append(closes[-1] * math.exp(change))
        result = self.run_component(rows=rows_for_closes(closes))
        self.assertLess(result["score"], 10)
        self.assertIn("realized_volatility_in_top_decile_of_rolling_history", result["warnings"])

    def test_provisional_row_withholds_score(self):
        rows = rows_for_closes([100.0] * 271)
        rows[0]["source_validation_status"] = "provisional"
        self.assertIsNone(self.run_component(rows=rows)["score"])

    def test_future_available_at_withholds_score(self):
        rows = rows_for_closes([100.0] * 271)
        rows[-1]["available_at"] = "2026-11-27T10:00:00+05:45"
        self.assertIsNone(self.run_component(rows=rows)["score"])

    def test_bad_hash_withholds_score(self):
        rows = rows_for_closes([100.0] * 271)
        rows[0]["source_payload_sha256"] = "bad"
        self.assertIsNone(self.run_component(rows=rows)["score"])

    def test_missing_session_is_not_imputed(self):
        rows = rows_for_closes([100.0] * 271)
        rows.pop(4)
        result = self.run_component(rows=rows)
        self.assertIsNone(result["score"])
        self.assertEqual(len(result["missing_sessions"]), 1)

    def test_duplicate_session_fails(self):
        rows = rows_for_closes([100.0] * 271)
        rows.append(dict(rows[-1]))
        with self.assertRaisesRegex(ValueError, "duplicate NEPSE index session"):
            self.run_component(rows=rows)

    def test_source_change_withholds_score(self):
        rows = rows_for_closes([100.0] * 271)
        rows[-1]["source_id"] = "another-source"
        result = self.run_component(rows=rows)
        self.assertEqual(result["reason"], "index_volatility_source_changed_within_window")

    def test_short_history_is_unavailable(self):
        dates = calendar(270)
        result = self.run_component(dates=dates)
        self.assertEqual(result["reason"], "index_volatility_history_below_271_sessions")


if __name__ == "__main__":
    unittest.main()
