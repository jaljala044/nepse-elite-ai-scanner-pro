import unittest
from datetime import date, timedelta

from app.idpat_market_structure import analyze_idpat_market_structure


def make_snapshot(count=65):
    start = date(2026, 7, 1)
    bars = []
    for i in range(count):
        # Oscillating but valid bars create confirmed swing structure.
        center = 100 + (i % 8) * (1 if (i // 8) % 2 == 0 else -1)
        bars.append({
            "date": (start + timedelta(days=i)).isoformat(),
            "open": str(center - 0.2),
            "high": str(center + 1.0),
            "low": str(center - 1.0),
            "close": str(center + 0.2),
            "volume": "1000",
        })
    return {
        "symbol": "TEST",
        "price_volume": {
            "status": "verified",
            "source_id": "TEST_OHLCV",
            "coverage": "1",
            "available_at": "2026-11-26T15:00:00+05:45",
            "bars": bars,
        },
    }


class IDPATMarketStructureTests(unittest.TestCase):
    def analyze(self, snapshot, calendar=None):
        return analyze_idpat_market_structure(
            snapshot,
            as_of_date="2026-11-26",
            as_of_timestamp="2026-11-26T16:00:00+05:45",
            session_calendar=calendar,
        )

    def test_uses_existing_structure_engine_and_remains_no_trade(self):
        result = self.analyze(make_snapshot())
        self.assertEqual(result["status"], "partial_research_only")
        self.assertEqual(result["action"], "NO_TRADE")
        self.assertIsNone(result["overall_score"])
        self.assertIn("latest_events", result["market_structure"])
        self.assertIn("equal_highs_buy_side_candidates", result["liquidity_map"])

    def test_missing_calendar_withholds_only_multi_timeframe(self):
        result = self.analyze(make_snapshot())
        self.assertEqual(result["multi_timeframe"]["status"], "withheld")
        self.assertEqual(result["multi_timeframe"]["reason"], "session_calendar_missing")
        self.assertEqual(result["status"], "partial_research_only")

    def test_unverified_calendar_is_not_used(self):
        calendar = {
            "status": "unverified", "source_id": "CAL", "coverage": "1",
            "available_at": "2026-11-26T15:00:00+05:45",
            "sessions": ["2026-07-01"],
        }
        result = self.analyze(make_snapshot(), calendar)
        self.assertEqual(result["multi_timeframe"]["status"], "withheld")
        self.assertEqual(result["multi_timeframe"]["reason"], "session_calendar_not_verified")

    def test_verified_calendar_enables_mtf_with_source_trace(self):
        snap = make_snapshot()
        sessions = [row["date"] for row in snap["price_volume"]["bars"]]
        calendar = {
            "status": "verified", "source_id": "NEPSE_SESSION_CALENDAR",
            "coverage": "1", "available_at": "2026-11-26T15:30:00+05:45",
            "sessions": sessions,
        }
        result = self.analyze(snap, calendar)
        self.assertIn(result["multi_timeframe"]["status"], {"research_only", "unavailable"})
        if result["multi_timeframe"]["status"] == "research_only":
            self.assertEqual(
                result["multi_timeframe"]["calendar_evidence"]["source_id"],
                "NEPSE_SESSION_CALENDAR",
            )

    def test_calendar_future_session_is_withheld(self):
        calendar = {
            "status": "verified", "source_id": "CAL", "coverage": "1",
            "available_at": "2026-11-26T15:00:00+05:45",
            "sessions": ["2026-07-01", "2026-11-27"],
        }
        result = self.analyze(make_snapshot(), calendar)
        self.assertEqual(result["multi_timeframe"]["status"], "withheld")
        self.assertEqual(result["multi_timeframe"]["reason"], "calendar_contains_future_session")

    def test_future_ohlcv_bar_is_withheld(self):
        snap = make_snapshot()
        snap["price_volume"]["bars"][-1]["date"] = "2026-11-27"
        result = self.analyze(snap)
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["reason"], "bar_after_cutoff")

    def test_low_coverage_is_withheld(self):
        snap = make_snapshot()
        snap["price_volume"]["coverage"] = "0.8"
        result = self.analyze(snap)
        self.assertEqual(result["status"], "withheld")
        self.assertEqual(result["reason"], "coverage_below_threshold")


if __name__ == "__main__":
    unittest.main()
