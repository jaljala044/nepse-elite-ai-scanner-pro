import unittest
from app.sector_historical_timeline import build_sector_timeline_snapshot
CUTOFF="2026-11-28T12:00:00Z"
BASE={"event_id":"e1","security_id":"SEC-1","symbol":"AAA","event_type":"classify","sector_code":"BANK",
"effective_from":"2026-01-01","effective_to":None,"captured_at":"2026-11-27T10:00:00Z",
"available_at":"2026-11-27T10:01:00Z","source_id":"s1","publisher_id":"pub-a",
"source_class":"secondary_publisher","evidence_ref":"doc:1","payload_sha256":"a"*64}
def event(**changes): return {**BASE,**changes}
class SectorHistoricalTimelineTests(unittest.TestCase):
 def build(self,events,as_of="2026-11-28",cutoff=CUTOFF):
  return build_sector_timeline_snapshot(events,as_of_date=as_of,decision_time=cutoff,
   allowed_sector_codes={"BANK","HYDRO"},known_security_ids={"SEC-1","SEC-2"})
 def test_independent_publishers_corroborate(self):
  r=self.build([event(),event(event_id="e2",source_id="s2",publisher_id="pub-b",evidence_ref="doc:2",payload_sha256="b"*64)])
  self.assertEqual(r["snapshots"]["SEC-1"]["sector_code"],"BANK")
 def test_single_publisher_is_withheld(self):
  self.assertIsNone(self.build([event()])["snapshots"]["SEC-1"]["sector_code"])
 def test_conflicting_sector_claims_are_withheld(self):
  r=self.build([event(),event(event_id="e2",sector_code="HYDRO",source_id="s2",publisher_id="pub-b",evidence_ref="doc:2",payload_sha256="b"*64)])
  self.assertEqual(r["snapshots"]["SEC-1"]["status"],"conflicting_effective_classifications")
 def test_future_available_event_excluded(self):
  r=self.build([event(),event(event_id="e2",source_id="s2",publisher_id="pub-b",evidence_ref="doc:2",payload_sha256="b"*64,captured_at="2026-11-29T10:00:00Z",available_at="2026-11-29T10:01:00Z")])
  self.assertEqual(r["snapshots"]["SEC-1"]["status"],"single_publisher_only")
 def test_future_effective_date_not_applied(self):
  r=self.build([event(effective_from="2026-11-29")])
  self.assertEqual(r["snapshots"]["SEC-1"]["status"],"missing_effective_classification")
 def test_symbol_change_requires_two_publishers(self):
  r=self.build([event(event_type="symbol_change",sector_code=None,symbol="NEW")])
  self.assertEqual(r["snapshots"]["SEC-1"]["symbol_status"],"single_publisher_symbol_alias")
  self.assertIsNone(r["snapshots"]["SEC-1"]["corroborated_symbol"])
 def test_symbol_change_keeps_stable_security_id(self):
  r=self.build([event(event_type="symbol_change",sector_code=None,symbol="NEW")])
  self.assertIn("SEC-1",r["snapshots"]); self.assertNotIn("NEW",r["snapshots"])
 def test_corporate_action_link_is_reference_only(self):
  r=self.build([event(event_type="corporate_action_link",sector_code=None,corporate_action_id="CA-1")])
  self.assertEqual(r["snapshots"]["SEC-1"]["corporate_action_ids"],["CA-1"])
  self.assertIsNone(r["snapshots"]["SEC-1"]["sector_code"])
 def test_unknown_security_id_rejected(self):
  r=self.build([event(security_id="UNVERIFIED")])
  self.assertEqual(r["rejected_events"][0]["reason"],"unknown_or_unverified_security_id")
 def test_duplicate_event_id_rejected(self):
  r=self.build([event(),event()])
  self.assertEqual(r["rejected_events"][0]["reason"],"duplicate_event_id")
 def test_invalid_source_class_rejected(self):
  r=self.build([event(source_class="unknown")])
  self.assertEqual(r["rejected_events"][0]["reason"],"source_class_not_admissible")
 def test_future_as_of_rejected(self):
  with self.assertRaisesRegex(ValueError,"as_of_date_after_decision_time"): self.build([event()],as_of="2026-11-30")
 def test_production_gate_remains_closed(self):
  r=self.build([event()]); self.assertFalse(r["verified"]); self.assertFalse(r["admission_allowed"])
  self.assertEqual(r["score_adjustment"],0); self.assertFalse(r["recommendation_override"])
if __name__=="__main__": unittest.main()
