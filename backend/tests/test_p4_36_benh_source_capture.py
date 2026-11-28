import unittest
from app.p4_36_benh_source_capture import (
 parse_sharehub_chart, parse_chukul_chart, parse_sharesansar_chart,
 aggregate_floorsheet, reconcile_history_sources, assess_predecessor_identity,
)

class Steps110119Tests(unittest.TestCase):
 def row(self, **kw):
  return {"date":"2024-06-03","open":99,"high":101,"low":98,"close":100,"volume":1200,**kw}
 def capture(self, parser, provider_row=None):
  return parser(symbol="BENH",rows=[provider_row or self.row()],raw_payload='{"raw":true}',
   source_url="https://example.invalid/capture",captured_at="2026-11-28T08:00:00+00:00")
 def test_110_sharehub_chart_capture_hash_and_provenance(self):
  c=self.capture(parse_sharehub_chart)
  self.assertEqual(c["provider_id"],"sharehub"); self.assertEqual(len(c["raw_payload_sha256"]),64)
  self.assertEqual(c["records"][0]["symbol"],"BENH")
 def test_111_chukul_adapter(self):
  c=self.capture(parse_chukul_chart,{"trading_date":"2024-06-03","openPrice":99,"highPrice":101,"lowPrice":98,"closePrice":100,"totalVolume":1200})
  self.assertEqual(c["records"][0]["provider_id"],"chukul")
 def test_112_sharesansar_adapter(self):
  c=self.capture(parse_sharesansar_chart,{"trade_date":"2024-06-03","open":99,"high":101,"low":98,"closing_price":100,"quantity":1200})
  self.assertEqual(c["records"][0]["close"],100)
 def test_113_invalid_chart_rows_quarantined(self):
  c=self.capture(parse_sharehub_chart,{"date":"bad","open":1,"high":2,"low":0.5,"close":1,"volume":10})
  self.assertEqual(c["status"],"NO_VALID_ROWS"); self.assertEqual(len(c["rejected"]),1)
 def test_114_floorsheet_daily_aggregation(self):
  f=aggregate_floorsheet(symbol="BENH",trades=[{"trade_date":"2024-06-03","quantity":10,"rate":100},{"trade_date":"2024-06-03","qty":5,"price":110}],
   raw_payload="trades",source_url="https://example.invalid/floorsheet",captured_at="2026-11-28T08:00:00+00:00")
  self.assertEqual(f["records"][0]["trade_count"],2); self.assertEqual(f["records"][0]["volume"],15)
  self.assertFalse(f["coverage_verified"])
 def test_115_earliest_date_mismatch_is_partial(self):
  c=self.capture(parse_sharehub_chart)
  f={"records":[{"session_date":"2024-06-04","trade_count":2}],"coverage_verified":True}
  self.assertEqual(reconcile_history_sources(chart_captures=[c],floorsheet=f)["status"],"PARTIAL_EVIDENCE")
 def test_116_cross_provider_field_conflict(self):
  a=self.capture(parse_sharehub_chart)
  brow={"trading_date":"2024-06-03","openPrice":99,"highPrice":101,"lowPrice":98,"closePrice":105,"totalVolume":1200}
  b=self.capture(parse_chukul_chart,brow)
  r=reconcile_history_sources(chart_captures=[a,b],floorsheet=None)
  self.assertEqual(r["provider_comparisons"][0]["status"],"CONFLICT_REVIEW")
 def test_117_bpw_identity_requires_authoritative_evidence(self):
  r=assess_predecessor_identity(symbol="BPW",security_id="S1",effective_from="2001-01-01",effective_to=None,evidence_refs=["chart"],evidence_type="chart")
  self.assertEqual(r["status"],"UNRESOLVED")
 def test_118_jalpa_identity_accepts_evidence_backed_candidate_only(self):
  r=assess_predecessor_identity(symbol="JALPA",security_id="S2",effective_from="2002-01-01",effective_to=None,evidence_refs=["issuer:notice:1"],evidence_type="issuer_notice")
  self.assertEqual(r["status"],"EVIDENCE_BACKED_CANDIDATE"); self.assertFalse(r["production_identity_approved"])
 def test_119_klbsl_and_mklb_remain_separate_unresolved_records(self):
  a=assess_predecessor_identity(symbol="KLBSL",security_id=None,effective_from=None,effective_to=None,evidence_refs=[],evidence_type=None)
  b=assess_predecessor_identity(symbol="MKLB",security_id=None,effective_from=None,effective_to=None,evidence_refs=[],evidence_type=None)
  self.assertEqual((a["status"],b["status"]),("UNRESOLVED","UNRESOLVED"))
if __name__=="__main__": unittest.main()
