import hashlib,json,unittest
from datetime import date,timedelta
from app.historical_coverage_validation import validate_120_session_history

def sha(x): return hashlib.sha256(x.encode()).hexdigest()
def fixture():
    sessions=[(date(2026,6,1)+timedelta(days=i)).isoformat() for i in range(120)]
    sources={
      "A":{"available_at":"2026-11-27T10:00:00Z","rights_status":"approved","source_validation_status":"verified","finality_status":"final","raw_sha256":sha("a"),"independence_group":"pub-a","independence_review_status":"approved"},
      "B":{"available_at":"2026-11-27T10:00:00Z","rights_status":"approved","source_validation_status":"verified","finality_status":"final","raw_sha256":sha("b"),"independence_group":"pub-b","independence_review_status":"approved"}}
    reconciled=[]
    for day in sessions:
      reconciled.append({"security_id":"SEC-1","session_date":day,"values":{"open":"100","high":"110","low":"95","close":"108","volume":"1000","turnover":"108000"},
       "source_ids":["A","B"],"evidence_sha256":[sha("a"),sha("b")],"independent_source_count":2,
       "status":"cross_source_reconciled_research_only"})
    body={"production_promotion_allowed":False,"canonical_promotion_allowed":False,"reconciled":reconciled}
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    ledger={**body,"ledger_sha256":digest}
    actions={"SEC-1":{"status":"verified_no_action","adjustment_basis":"raw","source_id":"A","evidence_id":"CA-1","available_at":"2026-11-27T10:00:00Z"}}
    return {"reconciliation_ledger":ledger,"ledger_available_at":"2026-11-27T11:00:00Z",
      "source_evidence":sources,"security_universe":[{"security_id":"SEC-1","symbol":"AAA"}],
      "verified_sessions":sessions,"corporate_action_reviews":actions,"decision_cutoff":"2026-11-27T12:00:00Z",
      "lookback_sessions":120,"adjustment_basis":"raw"}
class HistoryCoverageTests(unittest.TestCase):
 def run_check(self,**overrides):
  args=fixture();args.update(overrides);return validate_120_session_history(**args)
 def test_complete_120_session_history_passes_research_only(self):
  r=self.run_check();self.assertTrue(r["research_review_allowed"]);self.assertFalse(r["production_promotion_allowed"]);self.assertEqual(r["verified_session_count"],120)
 def test_missing_session_is_not_filled(self):
  args=fixture();args["reconciliation_ledger"]["reconciled"].pop(30)
  body={k:v for k,v in args["reconciliation_ledger"].items() if k!="ledger_sha256"}
  args["reconciliation_ledger"]["ledger_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"]);self.assertEqual(r["missing_pair_count"],1)
 def test_under_120_sessions_blocks(self):
  args=fixture();args["verified_sessions"]=args["verified_sessions"][:-1]
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"]);self.assertIn("insufficient_verified_trading_sessions",r["errors"])
 def test_unverified_corporate_actions_block(self):
  args=fixture();args["corporate_action_reviews"]["SEC-1"]["status"]="unknown"
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"])
 def test_action_adjustment_basis_mismatch_blocks(self):
  args=fixture();args["corporate_action_reviews"]["SEC-1"]["adjustment_basis"]="split_adjusted"
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"])
 def test_late_source_blocks_point_in_time(self):
  args=fixture();args["source_evidence"]["A"]["available_at"]="2026-11-27T13:00:00Z"
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"])
 def test_hash_tampering_blocks(self):
  args=fixture();args["reconciliation_ledger"]["ledger_sha256"]="0"*64
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"])
 def test_duplicate_session_date_blocks(self):
  args=fixture();args["verified_sessions"].append(args["verified_sessions"][0])
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"])
 def test_cross_source_hash_lineage_mismatch_blocks(self):
  args=fixture();args["reconciliation_ledger"]["reconciled"][0]["evidence_sha256"]=[sha("a")]
  body={k:v for k,v in args["reconciliation_ledger"].items() if k!="ledger_sha256"}
  args["reconciliation_ledger"]["ledger_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
  r=validate_120_session_history(**args);self.assertFalse(r["research_review_allowed"])
if __name__=="__main__":unittest.main()
