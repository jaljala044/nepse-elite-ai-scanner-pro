import unittest
from app.p4_34_benh_history_reconciliation import reconcile_benh_first_trade
from app.p4_35_historical_cohort_pipeline import normalize_ohlcv,detect_duplicate_sessions,compare_provider_sessions,find_missing_sessions,validate_security_mapping,build_cohort_quality_report

class Steps100109Tests(unittest.TestCase):
 def row(self,symbol="BENH",day="2024-06-03",provider="sharehub",close=100):
  return {"symbol":symbol,"session_date":day,"open":99,"high":101,"low":98,"close":close,"volume":1000,"provider_id":provider}
 def test_100_normalization_and_bad_ohlcv_rejection(self):
  r=normalize_ohlcv([self.row(),{**self.row(),"high":90}],provider_id="sharehub")
  self.assertEqual(r["accepted_count"],1); self.assertEqual(r["rejected_count"],1)
 def test_101_provider_provenance_is_attached(self):
  r=normalize_ohlcv([self.row()],provider_id="chukul")
  self.assertEqual(r["records"][0]["provider_id"],"chukul")
 def test_102_duplicate_symbol_sessions_detected(self):
  self.assertEqual(len(detect_duplicate_sessions([self.row(),self.row(provider="chukul")])),1)
 def test_103_cross_provider_match_and_conflict(self):
  a=self.row(); b=self.row(provider="chukul")
  self.assertEqual(compare_provider_sessions([a,b])[0]["status"],"MATCHED")
  b["close"]=105
  self.assertEqual(compare_provider_sessions([a,b])[0]["status"],"CONFLICT_REVIEW")
 def test_104_expected_session_gaps(self):
  self.assertEqual(find_missing_sessions([self.row(day="2024-06-03")],["2024-06-03","2024-06-04"],symbol="BENH"),["2024-06-04"])
 def test_105_mapping_requires_effective_date_and_evidence(self):
  self.assertEqual(validate_security_mapping(symbol="BPW",security_id="SEC1",effective_from="2020-01-01",effective_to=None,evidence_refs=["capture:1"])["status"],"EVIDENCE_BACKED_CANDIDATE")
  self.assertEqual(validate_security_mapping(symbol="BPW",security_id=None,effective_from=None,effective_to=None,evidence_refs=[])["status"],"UNRESOLVED")
 def test_106_invalid_mapping_date_order_blocked(self):
  self.assertEqual(validate_security_mapping(symbol="X",security_id="S",effective_from="2022-01-01",effective_to="2021-01-01",evidence_refs=["x"])["status"],"BLOCKED")
 def test_107_cohort_requires_coverage(self):
  r=build_cohort_quality_report(records=[self.row()],expected_sessions=["2024-06-03","2024-06-04"],required_symbols=["BENH"])
  self.assertEqual(r["status"],"BLOCKED")
 def test_108_cohort_reports_conflicts(self):
  a=self.row(); b=self.row(provider="sharesansar",close=110)
  r=build_cohort_quality_report(records=[a,b],expected_sessions=["2024-06-03"],required_symbols=["BENH"])
  self.assertEqual(r["status"],"BLOCKED"); self.assertTrue(r["conflicts"])
 def test_109_research_review_never_auto_admits_production(self):
  r=build_cohort_quality_report(records=[self.row()],expected_sessions=["2024-06-03"],required_symbols=["BENH"])
  self.assertTrue(r["production_admission_allowed"] is False)
  self.assertTrue(r["scanner_activation_allowed"] is False)
 def test_benh_mismatch_not_corroborated_even_if_archive_bounds_exist(self):
  r=reconcile_benh_first_trade(chart_records=[{"symbol":"BENH","session_date":"2024-06-03"}],floorsheet_records=[{"symbol":"BENH","session_date":"2024-06-04","trade_count":2}],floorsheet_coverage_start="2024-06-01",floorsheet_coverage_end="2024-06-10",floorsheet_coverage_verified=True)
  self.assertEqual(r["status"],"PARTIAL_EVIDENCE")
if __name__=="__main__": unittest.main()
