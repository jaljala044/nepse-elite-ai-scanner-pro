import unittest
from datetime import date,timedelta
from app.index_intelligence import index_intelligence
class IndexIntelligenceTests(unittest.TestCase):
    def fixture(self):
        days=[str(date(2025,1,1)+timedelta(days=i)) for i in range(65)]
        rows=[dict(index=k,date=d,close=100+i*m,reviewed=True,evidence_id="fixture") for k,m in [("NEPSE",1),("BANK",2)] for i,d in enumerate(days)]
        return rows,dict(sessions=days,benchmark="NEPSE",expected_indices=["NEPSE","BANK"],calendar_verified=True)
    def test_trend_rotation(self):
        rows,kw=self.fixture()
        r=index_intelligence(rows,**kw)
        self.assertEqual(r["indices"]["NEPSE"]["trend"],"bullish")
        self.assertGreater(r["indices"]["BANK"]["rotation_trail"][-1]["relative_return_pct"],0)
        self.assertIsNone(r["production_score"])
    def test_missing_session(self):
        rows,kw=self.fixture()
        r=index_intelligence(rows[:-1],**kw)
        self.assertEqual(r["indices"]["BANK"]["status"],"unavailable")
    def test_duplicate(self):
        rows,kw=self.fixture()
        self.assertEqual(index_intelligence(rows+[rows[0]],**kw)["reason"],"duplicate_or_out_of_scope")
    def test_calendar_gate(self):
        rows,kw=self.fixture()
        kw["calendar_verified"]=False
        self.assertEqual(index_intelligence(rows,**kw)["status"],"unavailable")


    def verified_rows(self, count=253):
        rows = []
        start = date(2025, 1, 1)
        for i in range(count):
            rows.append({
                "record_type": "index_ohlcv",
                "index_code": "NEPSE",
                "session_date": (start + timedelta(days=i)).isoformat(),
                "close": 100 + i * 0.5,
                "source_validation_status": "verified",
                "finality_status": "final",
                "source_id": "nepse-index-source-v1",
                "source_payload_sha256": "a" * 64,
                "available_at": "2026-11-26T15:00:00+05:45",
            })
        return rows

    def test_verified_index_metrics_and_trend(self):
        from app.index_intelligence import build_verified_index_intelligence
        result = build_verified_index_intelligence(
            self.verified_rows(), verified_session_dates=[r["session_date"] for r in self.verified_rows()], decision_time="2026-11-26T15:30:00+05:45"
        )
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["regime"], "strong_uptrend")
        self.assertEqual(result["history_sessions"], 253)
        self.assertIsNotNone(result["metrics"]["return_6m_pct"])
        self.assertTrue(result["metrics"]["sma_200_rising"])
        self.assertIsNone(result["production_score"])
        self.assertEqual(result["action"], "NOT_EVALUATED")

    def test_short_history_exposes_partial_metrics_without_full_status(self):
        from app.index_intelligence import build_verified_index_intelligence
        result = build_verified_index_intelligence(
            self.verified_rows(225), verified_session_dates=[r["session_date"] for r in self.verified_rows(225)], decision_time="2026-11-26T15:30:00+05:45"
        )
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNotNone(result["metrics"]["return_6m_pct"])
        self.assertIsNone(result["metrics"]["high_52w"])
        self.assertIn("52w_high", result["missing_metrics"])

    def test_future_available_and_unverified_rows_are_excluded(self):
        from app.index_intelligence import build_verified_index_intelligence
        rows = self.verified_rows()
        rows[0]["available_at"] = "2026-11-26T15:31:00+05:45"
        rows[1]["source_validation_status"] = "provisional"
        result = build_verified_index_intelligence(
            rows, verified_session_dates=[r["session_date"] for r in self.verified_rows()], decision_time="2026-11-26T15:30:00+05:45"
        )
        self.assertEqual(result["excluded_rows"]["not_available_by_cutoff"], 1)
        self.assertEqual(result["excluded_rows"]["unverified_or_nonfinal"], 1)
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_duplicate_verified_index_session_is_rejected(self):
        from app.index_intelligence import build_verified_index_intelligence
        rows = self.verified_rows()
        rows.append(dict(rows[-1]))
        with self.assertRaisesRegex(ValueError, "duplicate_index_session"):
            build_verified_index_intelligence(
                rows, verified_session_dates=[r["session_date"] for r in self.verified_rows()], decision_time="2026-11-26T15:30:00+05:45"
            )

    def test_invalid_ohlc_not_applicable_close_only_but_bad_close_rejected(self):
        from app.index_intelligence import build_verified_index_intelligence
        rows = self.verified_rows()
        rows[0]["close"] = True
        with self.assertRaisesRegex(ValueError, "invalid_session_or_close"):
            build_verified_index_intelligence(
                rows, decision_time="2026-11-26T15:30:00+05:45"
            )
