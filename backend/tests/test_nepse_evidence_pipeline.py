import hashlib, unittest
from app.nepse_evidence_pipeline import build_nepse_evidence_pipeline

def digest(x): return hashlib.sha256(x.encode()).hexdigest()
def fixture():
    batches=[]
    for sid,group,raw in [("SRC-A","independent-a","raw-a"),("SRC-B","independent-b","raw-b")]:
        h=digest(raw)
        manifest={"source_id":sid,"available_at":"2026-11-27T10:00:00Z","rights_status":"approved",
          "source_validation_status":"verified","finality_status":"final","raw_sha256":h,
          "independence_group":group,"independence_review_status":"approved"}
        admission={"admission_allowed":True,"production_promotion_allowed":False,"source_id":sid,
          "raw_sha256":h,"rows":[{"line_number":2,"symbol":"AAA","security_id":"SEC-1",
          "session_date":"2026-11-26","values":{"open":"100","high":"110","low":"95",
          "close":"108","volume":"1000","turnover":"108000"},"status":"valid_candidate"}]}
        batches.append({"manifest":manifest,"admission":admission})
    return {"reference_admission":{"status":"reference_evidence_ready_for_research_review","research_review_allowed":True},
      "admitted_batches":batches,"expected_pairs":[{"security_id":"SEC-1","session_date":"2026-11-26"}],
      "decision_cutoff":"2026-11-27T12:00:00Z","ledger_available_at":"2026-11-27T11:00:00Z",
      "security_universe":[{"security_id":"SEC-1","symbol":"AAA"}],"verified_sessions":["2026-11-26"],
      "corporate_action_reviews":{"SEC-1":{"status":"verified_no_action","adjustment_basis":"raw",
      "source_id":"SRC-A","evidence_id":"CA-1","available_at":"2026-11-27T10:00:00Z"}},
      "lookback_sessions":1}
class PipelineTests(unittest.TestCase):
    def test_valid_pipeline_is_research_only(self):
        r=build_nepse_evidence_pipeline(**fixture())
        self.assertTrue(r["research_review_allowed"]); self.assertFalse(r["production_promotion_allowed"])
    def test_reference_gate_blocks(self):
        a=fixture(); a["reference_admission"]={"research_review_allowed":False}
        r=build_nepse_evidence_pipeline(**a); self.assertFalse(r["research_review_allowed"])
    def test_raw_admission_failure_blocks(self):
        a=fixture(); a["admitted_batches"][0]["admission"]["admission_allowed"]=False
        r=build_nepse_evidence_pipeline(**a); self.assertFalse(r["research_review_allowed"])
    def test_duplicate_source_blocks(self):
        a=fixture(); a["admitted_batches"][1]["manifest"]["source_id"]="SRC-A"
        r=build_nepse_evidence_pipeline(**a); self.assertFalse(r["research_review_allowed"])
    def test_non_independent_sources_block(self):
        a=fixture(); a["admitted_batches"][1]["manifest"]["independence_group"]="independent-a"
        r=build_nepse_evidence_pipeline(**a); self.assertFalse(r["research_review_allowed"])
    def test_promotion_claim_blocks(self):
        a=fixture(); a["admitted_batches"][0]["admission"]["production_promotion_allowed"]=True
        r=build_nepse_evidence_pipeline(**a); self.assertFalse(r["research_review_allowed"])
if __name__ == "__main__": unittest.main()
