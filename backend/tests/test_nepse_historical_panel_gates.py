import unittest
from app.nepse_historical_panel import assemble_historical_panel

def ds(kind, rows):
    return {"status":"validated_for_research","research_review_allowed":True,
        "available_at":"2024-01-10T00:00:00+00:00","source_id":"SRC-"+kind,
        "evidence_id":"E-"+kind,"accepted_rows":rows}

class HistoricalPanelUniverseGateTests(unittest.TestCase):
    def datasets(self):
        return {
          "session_calendar":ds("calendar",[
            {"session_date":"2024-01-02","session_status":"OPEN"},
            {"session_date":"2024-01-03","session_status":"OPEN"},
            {"session_date":"2024-01-04","session_status":"OPEN"}]),
          "instrument_universe":ds("universe",[
            {"security_id":"SID-A","symbol":"AAA","effective_from":"2020-01-01","listing_status":"ACTIVE"},
            {"security_id":"SID-A","symbol":"AAA","effective_from":"2024-01-04","listing_status":"DELISTED"},
            {"security_id":"SID-B","symbol":"BBB","effective_from":"2024-01-03","listing_status":"ACTIVE"}]),
          "ohlcv":ds("ohlcv",[
            {"security_id":"SID-A","symbol":"AAA","session_date":"2024-01-02","open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000"},
            {"security_id":"SID-A","symbol":"AAA","session_date":"2024-01-03","open":"10","high":"11","low":"9","close":"10","volume":"100","turnover":"1000"},
            {"security_id":"SID-B","symbol":"BBB","session_date":"2024-01-03","open":"20","high":"21","low":"19","close":"20","volume":"100","turnover":"2000"},
            {"security_id":"SID-B","symbol":"BBB","session_date":"2024-01-04","open":"20","high":"21","low":"19","close":"20","volume":"100","turnover":"2000"}]),
          "corporate_actions":ds("actions",[{"security_id":"SID-A","action_type":"dividend","announcement_date":"2023-11-01","effective_date":"2023-12-01","status":"completed"}]) }
    def readiness(self):
        return {"status":"READY","data_quality":"HIGH","strategy_eligibility":{
          "trend_momentum":{"eligible":True,"missing_datasets":[]},
          "idpat_smart_money":{"eligible":True,"missing_datasets":[]},
          "broker_footprint":{"eligible":True,"missing_datasets":[]},
          "smc_ict_liquidity":{"eligible":True,"missing_datasets":[]},
          "hybrid_consensus":{"eligible":True,"missing_datasets":[]},
          "fundamental_investment":{"eligible":True,"missing_datasets":[]}}}
    def test_later_ipo_and_delisted_security_are_kept_point_in_time(self):
        out=assemble_historical_panel(datasets=self.datasets(),start_date="2024-01-02",end_date="2024-01-04",
            decision_cutoff="2024-01-10T00:00:00+00:00",readiness_report=self.readiness())
        self.assertEqual(out["status"],"validated_for_research")
        self.assertEqual(set(out["eligible_symbols"]),{"AAA","BBB"})
        self.assertEqual(out["historical_universe_security_count"],2)
        self.assertEqual(out["panel_rows"],4)
    def test_missing_readiness_blocks_panel(self):
        out=assemble_historical_panel(datasets=self.datasets(),start_date="2024-01-02",end_date="2024-01-04",
            decision_cutoff="2024-01-10T00:00:00+00:00")
        self.assertEqual(out["status"],"blocked")
        self.assertIn("historical_readiness_gate_missing_or_blocked",out["errors"])

if __name__=="__main__": unittest.main()
