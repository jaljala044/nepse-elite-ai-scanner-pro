"""Regression tests for fail-closed holiday review validation."""
import sys
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_holiday_review_index import validate

def row(**kw):
    r = dict(date="2018-10-01", official_observations="1",
             secondary_observations="0", official_locators="artifact:1/row:0",
             secondary_locators="", existing_calendar_status="project_accepted_open",
             review_disposition="hold_open_conflict", new_promotion_allowed="false")
    r.update(kw)
    return r

class HolidayGuardTests(unittest.TestCase):
    def check(self, rows):
        return validate(rows, {"2018-10-01": "project_accepted_open"}, date(2026,11,28))
    def test_conflict_held(self):
        self.assertEqual(self.check([row()])["new_promotions"], 0)
    def test_duplicate_date(self):
        with self.assertRaises(ValueError):
            self.check([row(), row()])
    def test_promotion_rejected(self):
        with self.assertRaises(ValueError):
            self.check([row(new_promotion_allowed="true")])
    def test_count_mismatch(self):
        with self.assertRaises(ValueError):
            self.check([row(official_observations="2")])
    def test_status_mismatch(self):
        with self.assertRaises(ValueError):
            self.check([row(existing_calendar_status="verified_closed")])
    def test_duplicate_locator(self):
        with self.assertRaises(ValueError):
            self.check([row(), row(date="2018-10-02", existing_calendar_status="unlisted",
                review_disposition="hold_scope_or_evidence_review")])
    def test_no_evidence(self):
        with self.assertRaises(ValueError):
            self.check([row(official_observations="0", official_locators="")])
    def test_future_date(self):
        r = row(date="2026-12-30", existing_calendar_status="unlisted",
                review_disposition="hold_scope_or_evidence_review")
        self.assertEqual(self.check([r])["future_dates"], 1)
    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            self.check([row(date="2018-02-30")])
    def test_empty(self):
        with self.assertRaises(ValueError):
            self.check([])

if __name__ == "__main__":
    unittest.main()
