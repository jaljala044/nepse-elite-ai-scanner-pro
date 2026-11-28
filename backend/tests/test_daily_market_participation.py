import unittest
from app.daily_market_participation import daily_market_participation


class DailyMarketParticipationTests(unittest.TestCase):
    def setUp(self):
        self.proof = dict(status="verified", source_id="fixture",
                          source_payload_sha256="a"*64,
                          available_at="2026-11-26T15:00:00+05:45")
        self.kw = dict(expected_symbols=["A", "B", "C"],
                       universe=dict(self.proof, as_of_session="2026-11-26",
                                     symbols=["A", "B", "C"]),
                       calendar=dict(self.proof, sessions=["2026-11-25","2026-11-26"]),
                       decision_time="2026-11-26T15:30:00+05:45")
        self.rows = [dict(symbol=s, session_date="2026-11-26",
                          prior_session="2026-11-25", prior_close_verified=True,
                          corporate_action_status="verified_clear",
                          source_validation_status="verified", finality_status="final",
                          source_id="fixture", source_payload_sha256="b"*64,
                          available_at=self.proof["available_at"], prior_close=100,
                          close=p, volume=v, turnover=v*p)
                     for s,p,v in [("A",110,20),("B",90,30),("C",110,20)]]

    def test_pressure_and_stable_rank(self):
        r = daily_market_participation(self.rows, **self.kw)
        self.assertEqual(r["status"], "research_only")
        self.assertAlmostEqual(r["pressure"], 1/3)
        self.assertEqual(r["sentiment"], "positive")
        self.assertEqual([x["symbol"] for x in r["rankings"]["gainers"]], ["A","C"])
        self.assertEqual(r["rankings"]["losers"][0]["symbol"], "B")
        self.assertEqual(r["rankings"]["volume"][0]["symbol"], "B")
        self.assertFalse(r["signals_enabled"])

    def test_missing_or_late_evidence(self):
        for rows in [self.rows[:2], [*self.rows[:2], dict(self.rows[2], available_at="2026-11-27T10:00:00+05:45")]]:
            r = daily_market_participation(rows, **self.kw)
            self.assertIsNone(r["pressure"])
            self.assertIsNone(r["rankings"])
            self.assertEqual(r["missing_symbols"], ["C"])

    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError, "duplicate_symbol"):
            daily_market_participation(self.rows + self.rows[:1], **self.kw)

    def test_unverified_calendar(self):
        self.kw["calendar"]["status"] = "unverified"
        self.assertIsNone(daily_market_participation(self.rows, **self.kw)["rankings"])

    def test_corporate_action_unclear(self):
        self.rows[0]["corporate_action_status"] = "unknown"
        self.assertIsNone(daily_market_participation(self.rows, **self.kw)["rankings"])
