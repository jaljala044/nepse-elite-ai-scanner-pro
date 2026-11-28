import unittest
from unittest.mock import patch
from datetime import date
from app.continuity_manifest import assess_manifest_segment

class ManifestIntegrationTests(unittest.TestCase):
    day = "2026-11-19"

    def run_review(self, calendar, reviewed=None, lifecycle=None):
        with patch("app.continuity_manifest.load_reviewed_rows", return_value=reviewed or {}), patch("app.continuity_manifest.load_calendar", return_value=calendar):
            return assess_manifest_segment("TEST", self.day, self.day,
                reviewed_path="unused", calendar_path="unused",
                lifecycle=lifecycle or {}, minimum_bars=1)

    def calendar(self, scope="all_securities", status="verified_open"):
        return {date.fromisoformat(self.day): {"scope":scope,"status":status,"raw_evidence_sha256":"a"*64}}

    def test_empty_manifest_blocks(self):
        r = self.run_review(self.calendar())
        self.assertEqual(r["manifest_rows_in_segment"], 0)
        self.assertFalse(r["continuity_preflight_passed"])
        self.assertFalse(r["backtest_promotion_allowed"])

    def test_sample_scope_is_not_market_scope(self):
        r = self.run_review(self.calendar("security_id_8108_only"))
        self.assertEqual(r["calendar_evidence_days_in_segment"], 0)
        self.assertIn(self.day+":calendar_unverified", r["reasons"])

    def test_exceptional_closure_normalized(self):
        r = self.run_review(self.calendar(status="verified_exceptional_closed"))
        self.assertEqual(r["counts"]["closed"], 1)

    def test_reviewed_row_and_lifecycle_bridge(self):
        row = dict(date=self.day,symbol="TEST",security_id="1",open=10,high=12,low=9,close=11,volume=100,evidence_id="row",price_basis="raw",canonical_promotion_allowed=True)
        life = {self.day:dict(symbol="TEST",security_id="1",instrument_type="equity",status="active",boundary=False,evidence_id="life")}
        r = self.run_review(self.calendar(), {("TEST",self.day):row}, life)
        self.assertTrue(r["continuity_preflight_passed"])
        self.assertFalse(r["backtest_promotion_allowed"])

    def test_other_symbol_not_used(self):
        r = self.run_review(self.calendar(), {("OTHER",self.day):{}})
        self.assertEqual(r["manifest_rows_in_segment"], 0)
