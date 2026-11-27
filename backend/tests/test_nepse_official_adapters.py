import unittest
from app.nepse_official_adapters import validate_nepse_dataset

ENV={"source_id":"NEPSE-1","publisher":"NEPSE","source_uri":"https://example.invalid/data",
"evidence_id":"EV1","raw_sha256":"a"*64,"available_at":"2026-11-27T10:00:00+05:45",
"rights_status":"approved","source_validation_status":"verified","finality_status":"final","registry_review_id":"REV1"}
CUTOFF="2026-11-27T11:00:00+05:45"

class OfficialAdapterTests(unittest.TestCase):
 def test_valid_ohlcv_research_row(self):
  row={"security_id":"SEC1","session_date":"2026-11-27","open":"100","high":"110","low":"95","close":"105","volume":"1000","turnover":"105000"}
  r=validate_nepse_dataset(dataset_kind="ohlcv",rows=[row],source_envelope=ENV,decision_cutoff=CUTOFF)
  self.assertEqual(r["status"],"validated_for_research")
  self.assertFalse(r["production_promotion_allowed"])
 def test_bad_ohlcv_is_quarantined(self):
  row={"security_id":"SEC1","session_date":"2026-11-27","open":"100","high":"90","low":"95","close":"105","volume":"1000","turnover":"105000"}
  r=validate_nepse_dataset(dataset_kind="ohlcv",rows=[row],source_envelope=ENV,decision_cutoff=CUTOFF)
  self.assertEqual(r["quarantined_count"],1)
 def test_late_or_unverified_envelope_blocks(self):
  env={**ENV,"available_at":"2026-11-27T12:00:00+05:45","source_validation_status":"draft"}
  r=validate_nepse_dataset(dataset_kind="ohlcv",rows=[],source_envelope=env,decision_cutoff=CUTOFF)
  self.assertFalse(r["research_review_allowed"])
  self.assertIn("source_available_after_decision_cutoff",r["envelope_errors"])
 def test_duplicate_security_session_quarantined(self):
  row={"security_id":"SEC1","session_date":"2026-11-27","open":"100","high":"110","low":"95","close":"105","volume":"1000","turnover":"105000"}
  r=validate_nepse_dataset(dataset_kind="ohlcv",rows=[row,row],source_envelope=ENV,decision_cutoff=CUTOFF)
  self.assertEqual(r["accepted_count"],1)
  self.assertEqual(r["quarantined_count"],1)
 def test_unknown_dataset_rejected(self):
  with self.assertRaises(ValueError):
   validate_nepse_dataset(dataset_kind="unknown",rows=[],source_envelope=ENV,decision_cutoff=CUTOFF)

if __name__=="__main__": unittest.main()
