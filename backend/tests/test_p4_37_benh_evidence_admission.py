import unittest
from app.p4_37_benh_evidence_admission import (
 validate_close_only_capture, detect_expected_date_gaps, classify_benh_history_coverage,
 assess_predecessor_lineage, build_acquisition_readiness
)

class Steps120129Tests(unittest.TestCase):
 def payload(self):
  return {"symbol":"BENH","source_url":"https://nepsedata.com/stock/BENH","raw_excerpt_sha256":"a"*64,
   "data_scope":"daily_close_only","record_count":2,"records":[
    {"symbol":"BENH","session_date":"2026-10-15","close":313.9,"field_coverage":["close"]},
    {"symbol":"BENH","session_date":"2026-10-16","close":353.0,"field_coverage":["close"]}]}
 def test_120_close_only_capture_is_research_only_not_ohlcv(self):
  r=validate_close_only_capture(self.payload())
  self.assertEqual(r["status"],"RESEARCH_ONLY_CLOSE_SERIES"); self.assertFalse(r["ohlcv_eligible"])
 def test_121_duplicate_or_invalid_close_rows_rejected(self):
  p=self.payload(); p["records"].append(p["records"][0]); p["record_count"]=3
  self.assertEqual(validate_close_only_capture(p)["status"],"REJECTED")
 def test_122_expected_first_session_gap_detected(self):
  self.assertEqual(detect_expected_date_gaps(observed_dates=["2026-10-15"],expected_dates=["2026-10-14","2026-10-15"]),["2026-10-14"])
 def test_123_listing_and_first_observed_dates_kept_separate(self):
  r=classify_benh_history_coverage(listing_date="2026-10-13",scheduled_first_trade_date="2026-10-14",
   first_observed_close_date="2026-10-15",observed_sessions=22,floorsheet_coverage_verified=False)
  self.assertIn("scheduled_first_trade_session_missing_from_close_capture",r["errors"])
  self.assertFalse(r["first_trade_date_verified"])
 def test_124_floorsheet_not_complete_without_explicit_verification(self):
  r=classify_benh_history_coverage(listing_date="2026-10-13",scheduled_first_trade_date="2026-10-14",
   first_observed_close_date="2026-10-14",observed_sessions=22,floorsheet_coverage_verified=False)
  self.assertEqual(r["status"],"PARTIAL_EVIDENCE")
 def test_125_bpw_mapping_stays_secondary_until_primary_pdf_readable(self):
  r=assess_predecessor_lineage(predecessor="BPW",successor="SLBSL",event_date=None,
   evidence_refs=["nepse:notice:2024-02-22","laganilab:BPW"],primary_evidence_acquired=False)
  self.assertEqual(r["status"],"SECONDARY_CANDIDATE"); self.assertFalse(r["production_identity_approved"])
 def test_126_jalpa_and_klbsl_merge_candidate(self):
  for symbol in ("JALPA","KLBSL"):
   r=assess_predecessor_lineage(predecessor=symbol,successor="MATRI",event_date=None,
    evidence_refs=["sharesansar:2024-08-12"],primary_evidence_acquired=False)
   self.assertEqual(r["status"],"SECONDARY_CANDIDATE")
 def test_127_mklb_is_not_assigned_an_unproven_successor(self):
  r=assess_predecessor_lineage(predecessor="MKLB",successor=None,event_date=None,
   evidence_refs=["nepse:company-list"],primary_evidence_acquired=True)
  self.assertEqual(r["status"],"UNRESOLVED")
 def test_128_sharehub_requires_licensed_api_access(self):
  self.assertEqual(build_acquisition_readiness()["sharehub"]["status"],"ACCESS_REQUIRED")
 def test_129_chukul_and_floorsheet_fail_closed(self):
  r=build_acquisition_readiness()
  self.assertEqual(r["chukul"]["status"],"FETCH_BLOCKED")
  self.assertEqual(r["floorsheet_archive"]["status"],"NOT_ACQUIRED")
if __name__=="__main__": unittest.main()
