import unittest
from app.p4_38_public_export_intake import (
 parse_csv_bytes, build_import_manifest, normalize_ohlcv_rows,
 normalize_close_only_rows, reconcile_provider_rows, normalize_floorsheet_rows,
 find_session_gaps, evaluate_first_trade_evidence, assess_identity_evidence,
 build_no_api_readiness,
)

class PublicExportIntakeTests(unittest.TestCase):
 def test_csv_utf8_bom_and_rows(self):
  self.assertEqual(parse_csv_bytes(b"\xef\xbb\xbfdate,close\n2026-11-27,10\n")[0]["close"],"10")
 def test_empty_or_invalid_csv_rejected(self):
  with self.assertRaises(ValueError): parse_csv_bytes(b"")
  with self.assertRaises(ValueError): parse_csv_bytes(b"")
 def test_manifest_hash_and_manual_mode(self):
  raw=b"date,close\n"
  m=build_import_manifest(provider="sharehub",symbol="BENH",filename="export.csv",raw=raw,source_url=None,captured_at="2026-11-28T12:00:00+04:00")
  self.assertEqual(m["raw_sha256"],__import__("hashlib").sha256(raw).hexdigest())
  self.assertFalse(m["subscription_bypass"]); self.assertFalse(m["production_admission_allowed"])
 def test_naive_timestamp_rejected(self):
  with self.assertRaises(ValueError):
   build_import_manifest(provider="chukul",symbol="BENH",filename="x.csv",raw=b"x",source_url=None,captured_at="2026-11-28T12:00:00")
 def row(self, close=100):
  return {"date":"2026-11-27","open":99,"high":101,"low":98,"close":close,"volume":1000}
 def test_ohlcv_normalization_and_duplicate_quarantine(self):
  r=normalize_ohlcv_rows(provider="sharehub",symbol="BENH",rows=[self.row(),self.row()])
  self.assertEqual(len(r["records"]),1); self.assertEqual(r["rejected"][0]["reason"],"duplicate_symbol_session")
 def test_invalid_ohlc_rejected(self):
  r=normalize_ohlcv_rows(provider="sharehub",symbol="BENH",rows=[{**self.row(),"high":98}])
  self.assertEqual(len(r["records"]),0)
 def test_chukul_alias_precedence_and_provider_conflict(self):
  a=normalize_ohlcv_rows(provider="sharehub",symbol="BENH",rows=[self.row(100)])
  b=normalize_ohlcv_rows(provider="chukul",symbol="BENH",rows=[{"trading_date":"2026-11-27","openPrice":99,"highPrice":106,"lowPrice":98,"closePrice":105,"totalVolume":1000}])
  self.assertEqual(reconcile_provider_rows([a,b])[0]["status"],"CONFLICT_REVIEW")
 def test_single_provider_not_mislabeled_as_match(self):
  a=normalize_ohlcv_rows(provider="sharehub",symbol="BENH",rows=[self.row()])
  self.assertEqual(reconcile_provider_rows([a])[0]["status"],"SINGLE_PROVIDER")
 def test_close_only_never_ohlcv(self):
  r=normalize_close_only_rows(provider="public",symbol="BENH",rows=[{"date":"2026-11-27","close":10}])
  self.assertFalse(r["ohlcv_eligible"]); self.assertEqual(r["field_scope"],"daily_close_only")
 def test_floorsheet_aggregation_and_broker_semantics(self):
  r=normalize_floorsheet_rows(symbol="BENH",rows=[
   {"date":"2026-11-27","symbol":"BENH","qty":10,"rate":100,"buyer_broker_no":1},
   {"date":"2026-11-27","symbol":"BENH","qty":5,"rate":110,"seller_broker_no":2}])
  self.assertEqual(r["records"][0]["trade_count"],2)
  self.assertTrue(r["broker_numbers_are_execution_channels_not_owners"])
  self.assertFalse(r["coverage_verified"])
 def test_foreign_symbol_ignored(self):
  r=normalize_floorsheet_rows(symbol="BENH",rows=[{"date":"2026-11-27","symbol":"NABIL","qty":1,"rate":1}])
  self.assertEqual(r["records"],[])
 def test_session_gap_detection(self):
  self.assertEqual(find_session_gaps(expected_sessions=["2026-11-26","2026-11-27"],observed_sessions=["2026-11-26"]),["2026-11-27"])
 def test_first_trade_requires_primary_and_complete_archive(self):
  good=evaluate_first_trade_evidence(listing_date="2026-10-13",scheduled_trade_date="2026-10-14",first_observed_trade_date="2026-10-14",archive_complete_from="2026-10-14",archive_complete_through="2026-11-27",primary_exchange_evidence=True)
  self.assertTrue(good["first_trade_date_verified"])
  bad=evaluate_first_trade_evidence(listing_date="2026-10-13",scheduled_trade_date="2026-10-14",first_observed_trade_date="2026-10-15",archive_complete_from="2026-10-14",archive_complete_through="2026-11-27",primary_exchange_evidence=True)
  self.assertFalse(bad["first_trade_date_verified"])
 def test_identity_remains_unapproved(self):
  r=assess_identity_evidence(symbol="BPW",security_id="id1",effective_from="2024-01-01",effective_to=None,evidence_refs=["notice"],primary_evidence=True)
  self.assertEqual(r["status"],"PRIMARY_EVIDENCE_REVIEW"); self.assertFalse(r["production_identity_approved"])
 def test_no_api_is_supported(self):
  self.assertFalse(build_no_api_readiness()["api_required"])

if __name__=="__main__": unittest.main()
