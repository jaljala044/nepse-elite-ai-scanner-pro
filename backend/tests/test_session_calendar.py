import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.session_calendar import audit_ohlcv, classify_date, load_calendar, schedule_candidate


class SessionCalendarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calendar = self.root / "calendar.csv"
        self.data = self.root / "prices.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write_calendar(self, rows):
        with self.calendar.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "status", "source_id", "evidence_uri", "raw_evidence_sha256", "published_at", "retrieved_at_utc", "verified_at_utc", "scope", "notes"])
            w.writeheader()
            w.writerows(rows)

    def row(self, day="2026-11-23", **kw):
        r = {"symbol": "NABIL", "date": day, "open": "500", "high": "515", "low": "495", "close": "510", "volume": "100"}
        r.update(kw)
        return r

    def write_prices(self, rows):
        with self.data.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["symbol", "date", "open", "high", "low", "close", "volume"])
            w.writeheader()
            w.writerows(rows)

    def evidence(self, day="2026-11-23", status="verified_open"):
        return {"date": day, "status": status, "source_id": "exchange_notice_001",
                "evidence_uri": "https://example.invalid/notice", "raw_evidence_sha256": "a" * 64,
                "published_at": "2026-11-23T09:00:00+05:45",
                "retrieved_at_utc": "2026-11-24T00:00:00Z",
                "verified_at_utc": "2026-11-24T00:00:00Z", "scope": "all securities",
                "notes": "test fixture"}

    def test_weekday_rules_are_candidates_not_verified_sessions(self):
        self.assertTrue(schedule_candidate(date(2026, 11, 23))[0])
        self.assertEqual(classify_date(date(2026, 11, 23), {})["classification"],
                         "unverified_session_candidate")

    def test_weekly_regime_transitions_are_explicit(self):
        self.assertFalse(schedule_candidate(date(2022, 4, 29))[0]) # Friday odd-lot period
        self.assertFalse(schedule_candidate(date(2022, 5, 6))[0]) # Before two-day weekend starts
        self.assertTrue(schedule_candidate(date(2022, 5, 8))[0])  # Sunday still open before May 15
        self.assertFalse(schedule_candidate(date(2022, 5, 15))[0]) # Sunday closed after weekend starts
        self.assertTrue(schedule_candidate(date(2022, 5, 16))[0])  # Monday-Friday period
        self.assertTrue(schedule_candidate(date(2022, 6, 15))[0])  # Sunday-Friday period starts
        self.assertTrue(schedule_candidate(date(2022, 6, 17))[0])  # Friday open in six-day period
        self.assertTrue(schedule_candidate(date(2022, 9, 16))[0])  # Last Friday before closure
        self.assertTrue(schedule_candidate(date(2022, 9, 18))[0])  # Sunday-Thursday regime
        self.assertFalse(schedule_candidate(date(2022, 9, 23))[0]) # Friday closed from Ashoj
        self.assertFalse(schedule_candidate(date(2026, 4, 3))[0])   # Friday before 2026 transition
        self.assertTrue(schedule_candidate(date(2026, 4, 5))[0])    # Last Sunday-Thursday regime session candidate
        self.assertTrue(schedule_candidate(date(2026, 4, 6))[0])    # Monday under new regime
        self.assertTrue(schedule_candidate(date(2026, 4, 10))[0])   # First Friday under new regime
        self.assertFalse(schedule_candidate(date(2026, 4, 12))[0])  # Sunday under new regime

    def test_calendar_requires_evidence_fields(self):
        row = self.evidence()
        row["raw_evidence_sha256"] = ""
        self.write_calendar([row])
        with self.assertRaisesRegex(ValueError, "require source, URI, raw hash"):
            load_calendar(self.calendar)

    def test_calendar_rejects_invalid_raw_evidence_hash(self):
        row = self.evidence()
        row["raw_evidence_sha256"] = "not-a-hash"
        self.write_calendar([row])
        with self.assertRaisesRegex(ValueError, "64-character hex digest"):
            load_calendar(self.calendar)

    def test_calendar_requires_utc_retrieval_timestamp(self):
        row = self.evidence()
        row["retrieved_at_utc"] = "2026-11-24T00:00:00"
        self.write_calendar([row])
        with self.assertRaisesRegex(ValueError, "retrieved_at_utc must include UTC"):
            load_calendar(self.calendar)

    def test_verification_cannot_precede_retrieval(self):
        row = self.evidence()
        row["verified_at_utc"] = "2026-11-23T00:00:00Z"
        row["retrieved_at_utc"] = "2026-11-24T00:00:00Z"
        self.write_calendar([row])
        with self.assertRaisesRegex(ValueError, "verified_at_utc cannot precede"):
            load_calendar(self.calendar)

    def test_publication_cannot_follow_retrieval(self):
        row = self.evidence()
        row["published_at"] = "2026-11-25T00:00:00Z"
        row["retrieved_at_utc"] = "2026-11-24T00:00:00Z"
        row["verified_at_utc"] = "2026-11-25T01:00:00Z"
        self.write_calendar([row])
        with self.assertRaisesRegex(ValueError, "published_at cannot follow"):
            load_calendar(self.calendar)

    def test_exceptional_open_session_is_accepted_with_evidence(self):
        self.write_calendar([self.evidence(status="verified_exceptional_open")])
        self.write_prices([self.row()])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertEqual(report["rows_accepted"], 1)
        self.assertTrue(report["gate_pass"])

    def test_verification_timestamp_must_be_utc_aware(self):
        row = self.evidence()
        row["verified_at_utc"] = "2026-11-24T00:00:00"
        self.write_calendar([row])
        with self.assertRaisesRegex(ValueError, "must include UTC timezone"):
            load_calendar(self.calendar)

    def test_unsupported_calendar_status_is_rejected(self):
        self.write_calendar([self.evidence(status="candidate_open")])
        with self.assertRaisesRegex(ValueError, "unsupported evidence-backed"):
            load_calendar(self.calendar)

    def test_only_explicit_open_dates_pass(self):
        self.write_calendar([self.evidence()])
        self.write_prices([self.row()])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertEqual(report["rows_accepted"], 1)
        self.assertTrue(report["gate_pass"])

    def test_unverified_date_is_quarantined_not_inferred_from_weekday(self):
        self.write_calendar([])
        self.write_prices([self.row()])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertEqual(report["rows_accepted"], 0)
        self.assertEqual(report["rows_quarantined"], 1)
        self.assertFalse(report["gate_pass"])

    def test_explicit_closure_rejects_row(self):
        self.write_calendar([self.evidence(status="verified_closed")])
        self.write_prices([self.row()])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertIn("date_not_verified_open", report["quarantine"][0]["reason"])

    def test_conflicting_duplicate_is_quarantined(self):
        self.write_calendar([self.evidence()])
        self.write_prices([self.row(), self.row(close="511")])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertEqual(report["rows_accepted"], 1)
        self.assertIn("conflicting_duplicate", report["quarantine"][0]["reason"])

    def test_ohlc_bounds_are_checked(self):
        self.write_calendar([self.evidence()])
        self.write_prices([self.row(high="490")])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertEqual(report["rows_accepted"], 0)
        self.assertIn("invalid_ohlc_bounds", report["quarantine"][0]["reason"])

    def test_non_finite_numeric_values_are_rejected(self):
        self.write_calendar([self.evidence()])
        self.write_prices([self.row(close="NaN")])
        report = audit_ohlcv([self.data], self.calendar)
        self.assertEqual(report["rows_accepted"], 0)
        self.assertIn("non_finite_numeric_value", report["quarantine"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
