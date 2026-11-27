import unittest
from app.nepse_source_bundle import acquire_historical_dataset_bundle

def reg():
    def rec(sid,pub,kind):
        return {"source_id":sid,"publisher_id":pub,"publisher_group":pub,
            "publisher_name":pub,"canonical_uri":"https://"+sid+".example.org/",
            "authority_type":"exchange_official","dataset_kinds":[kind],"status":"approved",
            "review_id":"review-"+sid,"reviewed_at":"2025-01-01T00:00:00+05:45"}
    return [rec("ohlcv","p1","ohlcv"),rec("cal","p2","session_calendar"),
        rec("universe","p3","instrument_universe"),rec("actions","p4","corporate_actions")]

def csv_transport(body):
    return lambda uri,**kwargs:{"status":200,"final_url":uri,
        "headers":{"Content-Length":str(len(body)),"Content-Type":"text/csv"},"body":body}

class HistoricalBundleTests(unittest.TestCase):
    def test_bundle_captures_manifest_and_readiness_gate(self):
        datasets={
        "ohlcv":b"security_id,session_date,open,high,low,close,volume,turnover\nS1,2025-01-02,10,11,9,10,100,1000\n",
        "session_calendar":b"session_date,session_status\n2025-01-02,OPEN\n",
        "instrument_universe":b"security_id,symbol,effective_from,listing_status\nS1,ABC,2025-01-01,ACTIVE\n",
        "corporate_actions":b"security_id,action_type,announcement_date,effective_date,status\nS1,bonus,2025-01-01,2025-01-02,FINAL\n"}
        requests=[]; transports={}
        for kind,body in datasets.items():
            sid={"session_calendar":"cal","instrument_universe":"universe","corporate_actions":"actions"}.get(kind,kind)
            requests.append({"request_id":"req-"+kind,"dataset_kind":kind,"source_id":sid,
                "endpoint_uri":"https://"+sid+".example.org/"+kind+".csv",
                "evidence_id":"e-"+kind,"captured_at":"2025-01-03T00:00:00+05:45",
                "rights_status":"approved"})
            transports[sid]=csv_transport(body)
        result=acquire_historical_dataset_bundle(registry=reg(),requests=requests,
            decision_cutoff="2025-01-04T00:00:00+05:45",start_date="2025-01-02",
            end_date="2025-01-02",transport_by_source=transports)
        self.assertEqual(result["capture_count"],4,result["manifest"]["failures"])
        self.assertEqual(result["readiness"]["status"],"PARTIAL")
        self.assertFalse(result["historical_panel_promotion_allowed"])
        self.assertEqual(result["promotion_block_reason"],"independent corporate-action reconciliation evidence must be supplied and verified separately")
        self.assertEqual(len(result["manifest"]["manifest_sha256"]),64)

    def test_missing_required_dataset_blocks_promotion(self):
        result=acquire_historical_dataset_bundle(registry=reg(),requests=[] if False else [{
            "request_id":"only-calendar","dataset_kind":"session_calendar","source_id":"cal",
            "endpoint_uri":"https://cal.example.org/cal.csv","evidence_id":"e1",
            "captured_at":"2025-01-03T00:00:00+05:45","rights_status":"approved"}],
            decision_cutoff="2025-01-04T00:00:00+05:45",start_date="2025-01-02",
            end_date="2025-01-02",transport_by_source={"cal":csv_transport(
                b"session_date,session_status\n2025-01-02,OPEN\n")})
        self.assertEqual(result["readiness"]["status"],"BLOCKED")
        self.assertFalse(result["historical_panel_promotion_allowed"])

if __name__=="__main__": unittest.main()
