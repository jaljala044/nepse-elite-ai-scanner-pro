import unittest
from app.p4_39_web_evidence_reconciliation import validate_web_evidence_record,compare_close_observations,classify_first_trade,classify_snapshot,normalize_merger_candidate
class WebEvidenceTests(unittest.TestCase):
 def row(self,**kw): return {"session_date":"2026-11-27","open":800,"high":840,"low":771,"close":785,"volume":33244,**kw}
 def test_valid_research_record(self): self.assertEqual(validate_web_evidence_record(self.row())["status"],"RESEARCH_ONLY_VALIDATED")
 def test_invalid_ohlc_rejected(self): self.assertIn("invalid_ohlc_relationship",validate_web_evidence_record(self.row(high=780))["errors"])
 def test_missing_volume_not_ohlcv(self): self.assertFalse(validate_web_evidence_record(self.row(volume=None))["ohlcv_complete"])
 def test_intraday_not_eod(self): self.assertIn("intraday_snapshot_cannot_be_eod",validate_web_evidence_record(self.row(scope="INTRADAY_SNAPSHOT",admit_to_eod=True))["errors"])
 def test_18_nov_close_conflict(self):
  r=compare_close_observations(session_date="2026-11-18",close_observations=[{"provider":"nepsedata","close":837},{"provider":"sharegyan","close":856.4}]); self.assertEqual(r["status"],"CONFLICT_REVIEW")
 def test_27_nov_close_match(self):
  r=compare_close_observations(session_date="2026-11-27",close_observations=[{"provider":"nepsedata","close":785},{"provider":"sharesansar","close":785},{"provider":"sharegyan","close":785}]); self.assertEqual(r["status"],"MATCHED")
 def test_first_observed_after_scheduled_date_not_verified(self):
  r=classify_first_trade(scheduled_date="2026-10-14",first_observed_date="2026-10-15",complete_archive_covers_scheduled_date=False,primary_exchange_evidence=True); self.assertEqual(r["status"],"SCHEDULED_SESSION_NOT_OBSERVED"); self.assertFalse(r["first_trade_date_verified"])
 def test_first_trade_requires_complete_primary_archive(self):
  r=classify_first_trade(scheduled_date="2026-10-15",first_observed_date="2026-10-15",complete_archive_covers_scheduled_date=True,primary_exchange_evidence=True); self.assertEqual(r["status"],"VERIFIED")
 def test_intraday_classification(self): self.assertEqual(classify_snapshot("INTRADAY_SNAPSHOT")["status"],"INTRADAY_NOT_EOD")
 def test_empty_floorsheet_nonzero_summary_conflict(self): self.assertEqual(classify_snapshot("SUMMARY_ONLY",source_table_rows_present=False,summary_volume=27640)["status"],"SOURCE_INTERNAL_CONFLICT")
 def test_merger_is_candidate_not_approved(self):
  r=normalize_merger_candidate({"predecessors":["MKLB"],"successor":"SMATA","event_type":"acquisition","source_urls":["notice"]}); self.assertEqual(r["status"],"SECONDARY_EVIDENCE_CANDIDATE"); self.assertFalse(r["production_identity_approved"])
if __name__=="__main__": unittest.main()
