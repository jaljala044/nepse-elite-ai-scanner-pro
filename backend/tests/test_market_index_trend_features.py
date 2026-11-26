import unittest
from datetime import date, timedelta

from app.market_index_trend_features import nepse_index_trend_component

DIGEST = "d" * 64
DECISION_TIME = "2026-11-26T16:00:00+05:45"


def fixture_rows(count=220, *, rising=True):
    start = date(2025, 1, 1)
    result = []
    for index in range(count):
        close = 1000 + index if rising else 1000 - index * 0.5
        session = (start + timedelta(days=index)).isoformat()
        result.append({
            "record_type": "index_ohlcv",
            "index_code": "NEPSE",
            "session_date": session,
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "source_validation_status": "verified",
            "finality_status": "final",
            "source_id": "exchange-reviewed-index-v1",
            "source_payload_sha256": DIGEST,
            "available_at": "2026-11-25T15:00:00+05:45",
        })
    return result


def session_dates(rows):
    return [row["session_date"] for row in rows]


class MarketIndexTrendTests(unittest.TestCase):
    def test_verified_rising_index_produces_component_contract(self):
        rows = fixture_rows()
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(rows), decision_time=DECISION_TIME
        )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["as_of_session"], rows[-1]["session_date"])
        self.assertTrue(result["metrics"]["sma200_rising_over_20_sessions"])
        self.assertEqual(result["source_id"], rows[-1]["source_id"])

    def test_insufficient_history_returns_null_score(self):
        rows = fixture_rows(219)
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(rows), decision_time=DECISION_TIME
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_unverified_finality_is_not_promoted(self):
        rows = fixture_rows()
        rows[0]["source_validation_status"] = "provisional"
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(rows), decision_time=DECISION_TIME
        )
        self.assertIsNone(result["score"])
        self.assertEqual(result["reason"], "unverified_or_missing_exact_index_sessions")

    def test_future_available_at_is_withheld(self):
        rows = fixture_rows()
        rows[-1]["available_at"] = "2026-11-27T10:00:00+05:45"
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(rows), decision_time=DECISION_TIME
        )
        self.assertIsNone(result["score"])
        self.assertIn("future_available_at", [x["reason"] for x in result["rejected_rows"]])

    def test_bad_digest_is_withheld(self):
        rows = fixture_rows()
        rows[4]["source_payload_sha256"] = "bad"
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(rows), decision_time=DECISION_TIME
        )
        self.assertIsNone(result["score"])

    def test_duplicate_session_is_rejected(self):
        rows = fixture_rows()
        rows.append(dict(rows[-1]))
        calendar = session_dates(fixture_rows())
        with self.assertRaisesRegex(ValueError, "duplicate NEPSE index session"):
            nepse_index_trend_component(
                rows, session_dates=calendar, decision_time=DECISION_TIME
            )

    def test_missing_exact_session_is_not_filled(self):
        rows = fixture_rows()
        missing = rows.pop(10)
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(fixture_rows()), decision_time=DECISION_TIME
        )
        self.assertIsNone(result["score"])
        self.assertIn(missing["session_date"], result["missing_sessions"])

    def test_third_party_or_provisional_row_is_not_accepted(self):
        rows = fixture_rows()
        rows[3]["finality_status"] = "provisional"
        result = nepse_index_trend_component(
            rows, session_dates=session_dates(rows), decision_time=DECISION_TIME
        )
        self.assertIsNone(result["score"])


if __name__ == "__main__":
    unittest.main()
