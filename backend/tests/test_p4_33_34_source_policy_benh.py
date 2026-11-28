import unittest
from app.p4_33_nepse_distributed_source_policy import classify_source_record
from app.p4_34_benh_history_reconciliation import reconcile_benh_first_trade

class DistributedSourcePolicyTests(unittest.TestCase):
 def test_sharehub_trusted_distribution_pending_crosscheck(self):
  r=classify_source_record(provider_id="sharehub",captured_at="2026-11-28T10:00:00+05:45",published_at="2026-11-28T09:00:00+05:45",raw_sha256="a"*64,symbol="BENH",session_date="2026-11-20",fields_present=["open","high","low","close","volume"],expected_fields=["open","high","low","close","volume"])
  self.assertEqual(r["status"],"TRUSTED_DISTRIBUTION_PENDING_CROSSCHECK")
  self.assertTrue(r["eligible_for_research"])
  self.assertFalse(r["eligible_for_production_signal"])
 def test_matching_independent_check_corroborates(self):
  r=classify_source_record(provider_id="chukul",captured_at="2026-11-28T10:00:00+05:45",published_at=None,raw_sha256="b"*64,symbol="BENH",session_date="2026-11-20",fields_present=["close"],expected_fields=["close"],independent_check_status="match")
  self.assertEqual(r["status"],"CORROBORATED")
  self.assertTrue(r["eligible_for_production_signal"])
 def test_unknown_provider_quarantined(self):
  r=classify_source_record(provider_id="unknown",captured_at="x",published_at=None,raw_sha256="c"*64,symbol="BENH",session_date="2026-11-20",fields_present=["close"],expected_fields=["close"])
  self.assertEqual(r["status"],"QUARANTINED")
 def test_missing_required_fields_quarantined(self):
  r=classify_source_record(provider_id="sharesansar",captured_at="x",published_at=None,raw_sha256="d"*64,symbol="BENH",session_date="2026-11-20",fields_present=["close"],expected_fields=["close","volume"])
  self.assertEqual(r["status"],"QUARANTINED")

class BenhReconciliationTests(unittest.TestCase):
 def test_matching_dates_and_verified_coverage_corroborate_first_trade(self):
  chart=[{"symbol":"BENH","session_date":"2024-06-03"}]; floor=[{"symbol":"BENH","session_date":"2024-06-03","trade_count":5}]
  r=reconcile_benh_first_trade(chart_records=chart,floorsheet_records=floor,floorsheet_coverage_start="2024-06-01",floorsheet_coverage_end="2024-06-10",floorsheet_coverage_verified=True,official_listing_date="2024-06-01")
  self.assertEqual(r["status"],"FIRST_TRADE_CORROBORATED")
  self.assertFalse(r["listing_date_verified"])
 def test_mismatch_blocks_corroboration(self):
  r=reconcile_benh_first_trade(chart_records=[{"symbol":"BENH","session_date":"2024-06-03"}],floorsheet_records=[{"symbol":"BENH","session_date":"2024-06-04","trade_count":2}],floorsheet_coverage_start="2024-06-01",floorsheet_coverage_end="2024-06-10",floorsheet_coverage_verified=True)
  self.assertEqual(r["status"],"PARTIAL_EVIDENCE")
  self.assertFalse(r["first_trade_date_verified"])
 def test_bounds_without_verified_archive_completeness_are_not_enough(self):
  r=reconcile_benh_first_trade(chart_records=[{"symbol":"BENH","session_date":"2024-06-03"}],floorsheet_records=[{"symbol":"BENH","session_date":"2024-06-03","trade_count":1}],floorsheet_coverage_start="2024-06-01",floorsheet_coverage_end="2024-06-10")
  self.assertEqual(r["status"],"PARTIAL_EVIDENCE")
 def test_wrong_symbol_ignored(self):
  r=reconcile_benh_first_trade(chart_records=[{"symbol":"OTHER","session_date":"2024-01-01"}],floorsheet_records=[],floorsheet_coverage_start=None,floorsheet_coverage_end=None)
  self.assertEqual(r["status"],"NO_EVIDENCE")
if __name__=="__main__": unittest.main()
