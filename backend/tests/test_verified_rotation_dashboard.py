import unittest
from datetime import date, timedelta
from app.index_intelligence import build_verified_rotation_dashboard


class VerifiedRotationDashboardTests(unittest.TestCase):
    def setUp(self):
        self.days = [(date(2026, 1, 1)+timedelta(days=i)).isoformat() for i in range(51)]
        self.kw = dict(verified_session_dates=self.days, expected_indices=["NEPSE","BANK"],
                       decision_time="2026-11-26T18:00:00+05:45")
        self.rows = [dict(index_code=k, session_date=d, close=100+i*m,
                          record_type="index_ohlcv", source_validation_status="verified",
                          finality_status="final", source_id=k, source_payload_sha256="a"*64,
                          available_at=self.kw["decision_time"])
                     for k,m in [("NEPSE",1),("BANK",2)] for i,d in enumerate(self.days)]

    def test_complete(self):
        r = build_verified_rotation_dashboard(self.rows, **self.kw)
        self.assertEqual(r["status"], "research_only")
        self.assertEqual(len(r["indices"]["BANK"]["rotation_trail"]), 6)
        self.assertFalse(r["signals_enabled"])

    def test_late(self):
        self.rows[-1]["available_at"] = "2026-11-27T18:00:00+05:45"
        r = build_verified_rotation_dashboard(self.rows, **self.kw)
        self.assertEqual(r["status"], "insufficient_evidence")
        self.assertIn("BANK", r["missing_indices"])

    def test_duplicate(self):
        with self.assertRaisesRegex(ValueError, "duplicate_index_session"):
            build_verified_rotation_dashboard(self.rows + self.rows[:1], **self.kw)
