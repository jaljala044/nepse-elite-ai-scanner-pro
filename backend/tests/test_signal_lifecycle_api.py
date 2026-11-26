import os
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


class SignalLifecycleAPITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "api.duckdb")
        self.client = TestClient(app)

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_freeze_store_and_list_buy_as_research_only(self):
        payload = {
            "symbol":"TEST", "decision_time":"2025-01-02T12:00:00Z",
            "horizon":"swing", "action":"BUY", "methodology":"p4.41_v1",
            "evidence":[{"evidence_id":"source-row-1","available_at":"2025-01-02T11:00:00Z"}],
            "details":{"plan":{"entry":"100","stop":"95","targets":["110"]}},
        }
        response = self.client.post("/v1/research/signals", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["record"]["classification"], "research_only_not_execution")
        self.assertEqual(data["storage"]["status"], "stored")
        listed = self.client.get("/v1/research/signals?horizon=swing")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["signals"][0]["action"], "BUY")

    def test_future_evidence_rejected(self):
        payload = {
            "symbol":"TEST", "decision_time":"2025-01-02T12:00:00Z",
            "horizon":"swing", "action":"BUY", "methodology":"p4.41_v1",
            "evidence":[{"evidence_id":"late","available_at":"2025-01-03T11:00:00Z"}],
            "details":{},
        }
        response = self.client.post("/v1/research/signals", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_performance_is_explicitly_research_reference(self):
        response = self.client.get("/v1/research/performance")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["classification"],
                         "gross_price_reference_statistics_not_backtest")



    def test_early_signal_endpoint_auto_freezes_each_horizon(self):
        stamp = "2025-01-02T10:00:00+05:45"
        def ev(source, **values):
            return {"status":"verified","source_id":source,"coverage":"1","available_at":stamp,**values}
        plan = {"setup":"momentum_breakout","entry_type":"breakout_retest",
            "confirmation":"confirmed","entry":"100","stop":"94",
            "targets":["112","118","125"],"invalidation_condition":"close_below_stop",
            "level_status":"inferred_chart_level","evidence_dates":["2025-01-01","2025-01-02"]}
        snapshot = {"symbol":"TEST","as_of_date":"2025-01-02","available_at":stamp,
            "market":ev("MARKET",regime="bull"),
            "sector":ev("SECTOR",alignment="leading_or_improving",excess_return_1m="2"),
            "liquidity":ev("LIQ",median_turnover="5000000",median_spread_pct="0.5",
                median_trade_count="50",median_displayed_depth="500000"),
            "broker":ev("BROKER",net_amount="100000",positive_net_session_ratio="0.7"),
            "price_volume":ev("OHLCV",structure="bullish_bos"),
            "candidate":ev("CANDIDATE",classification="early_accumulation_candidate"),
            "plans":{"t_plus_2":plan,"swing":plan,"positional":plan}}
        payload = {"as_of_date":"2025-01-02","as_of_timestamp":"2025-01-02T12:00:00+05:45",
                   "snapshot":snapshot}
        response = self.client.post("/v1/research/early-signals", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(set(response.json()["signal_tracking"]),
                         {"t_plus_2","swing","positional"})
        listed = self.client.get("/v1/research/signals")
        self.assertEqual(len(listed.json()["signals"]), 3)

if __name__ == "__main__":
    unittest.main()
