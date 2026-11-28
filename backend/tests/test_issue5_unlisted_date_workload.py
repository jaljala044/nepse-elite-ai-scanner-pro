import csv,tempfile,unittest
from pathlib import Path
from build_issue5_unlisted_date_workload import build_workload

class Issue5WorkloadTests(unittest.TestCase):
    def test_groups_by_date_and_preserves_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pairs.csv"
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["symbol","current_date","previous_date"]);w.writeheader()
                w.writerows([
                    {"symbol":"NABIL","current_date":"2026-06-27","previous_date":"2026-06-26"},
                    {"symbol":"NICA","current_date":"2026-06-27","previous_date":"2026-06-26"},
                    {"symbol":"NABIL","current_date":"2026-06-28","previous_date":"2026-06-27"}])
            x=build_workload(p)
            self.assertEqual(x["candidate_count"],3)
            self.assertEqual(x["distinct_current_dates"],2)
            self.assertEqual(x["status"],"UNKNOWN_REVIEW_REQUIRED")
            self.assertFalse(x["rules"]["no_canonical_promotion"] is False)
            self.assertTrue(all(c["disposition"]=="UNKNOWN" and not c["promotion_allowed"] for b in x["batches"] for c in b["candidates"]))
    def test_duplicate_pairs_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pairs.csv"
            p.write_text("symbol,current_date,previous_date\nNABIL,2026-06-27,2026-06-26\nNABIL,2026-06-27,2026-06-26\n")
            with self.assertRaisesRegex(ValueError,"duplicate candidate pair"):build_workload(p)
    def test_invalid_date_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pairs.csv";p.write_text("symbol,current_date,previous_date\nNABIL,not-a-date,2026-06-26\n")
            with self.assertRaisesRegex(ValueError,"invalid ISO date"):build_workload(p)
