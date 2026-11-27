import unittest
from datetime import date, timedelta
from app.historical_quarantine import QUARANTINE
from app.training_dataset_quarantine import audit_training_windows

class TrainingDatasetQuarantineTests(unittest.TestCase):
    def test_all_keys_direct_and_omitted(self):
        for symbol, day in sorted(QUARANTINE):
            d = date.fromisoformat(day)
            for start, end in [(day,day),(str(d-timedelta(days=1)),str(d+timedelta(days=1)))]:
                result = audit_training_windows([{"record_id":"r1","symbol":symbol,
                    "history_start":start,"observation_date":start,"outcome_end":end}])
                self.assertIn(f"historical_quarantine:0:{symbol}:{day}",result["reasons"])
                self.assertFalse(result["model_training_allowed"])

    def test_missing_duplicate_invalid_and_clean(self):
        row = {"record_id":"r1","symbol":"TEST","history_start":"2026-01-01",
               "observation_date":"2026-01-02","outcome_end":"2026-01-03"}
        self.assertEqual(audit_training_windows([])["status"],"blocked")
        self.assertIn("duplicate_record:1",audit_training_windows([row,row])["reasons"])
        self.assertIn("invalid_window_lineage:0",audit_training_windows([{**row,"outcome_end":"bad"}])["reasons"])
        result = audit_training_windows([row])
        self.assertEqual(result["status"],"declared_windows_clear")
        self.assertFalse(result["independent_dataset_clearance"])
        self.assertFalse(result["model_training_allowed"])
        self.assertEqual(len(result["declared_windows_sha256"]),64)
