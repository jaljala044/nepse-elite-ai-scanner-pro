import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import main


class GenericUnknownScanPolicyTests(unittest.TestCase):
    def test_candidate_with_no_validated_rows_is_unknown_not_no_trade(self):
        with patch.object(main, "DATA", {"ADBL": []}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={"symbols": ["ADBL"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["status"], "unknown_result")
        self.assertEqual(result["data_status"], "UNKNOWN")
        self.assertEqual(result["data_quality"], "LOW_CONFIDENCE")
        self.assertEqual(result["overall_rating"], "NOT_RATED")
        self.assertEqual(result["horizon_actions"], {
            "t_plus_2": "UNKNOWN", "swing": "UNKNOWN",
            "positional": "UNKNOWN", "investment": "UNKNOWN",
        })
        self.assertFalse(result["eligibility"]["eligible"])
        self.assertIn("no_rows", result["eligibility"]["reasons"])
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["metrics"], {})
        self.assertEqual(result["market_structure"]["status"], "unknown")
        self.assertEqual(result["signal_confirmation"]["status"], "unknown")
        self.assertEqual(result["signal_confirmation"]["classification"], "UNKNOWN")
        self.assertIn("NO_TRADE requires verified", result["scan_note"])


    def test_unknowns_are_visible_but_never_ranked_or_buy_candidates(self):
        with patch.object(main, "DATA", {"ADBL": []}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={
                    "symbols": ["UNL", "ADBL", "NICEF"]
                })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        by_symbol = {item["symbol"]: item for item in payload["results"]}
        self.assertEqual(set(item["symbol"] for item in payload["unknown_results"]), {"UNL", "ADBL"})
        self.assertEqual(payload["ranked_results"], [])
        self.assertEqual(payload["buy_candidates"], [])
        self.assertEqual(payload["out_of_scope_results"][0]["symbol"], "NICEF")
        for symbol in ("UNL", "ADBL"):
            self.assertEqual(by_symbol[symbol]["result_bucket"], "unknown_results")
            self.assertFalse(by_symbol[symbol]["ranking_eligible"])
            self.assertFalse(by_symbol[symbol]["buy_list_eligible"])
            self.assertEqual(by_symbol[symbol]["overall_rating"], "NOT_RATED")



    def test_valid_research_observations_are_not_mislabeled_no_trade_or_ranked(self):
        from datetime import date
        from contextlib import ExitStack
        row = {"date": date(2025, 1, 1), "open": 10, "high": 12,
               "low": 9, "close": 11, "volume": 100}
        reviewed = {("ADBL", "2025-01-01"): dict(row, evidence_id="fixture")}
        with ExitStack() as stack:
            stack.enter_context(patch.object(main, "DATA", {"ADBL": [row]}))
            stack.enter_context(patch.object(main, "REVIEWED_ROWS", reviewed))
            stack.enter_context(patch.object(main, "assess", return_value=[]))
            stack.enter_context(patch.object(main, "analyze", return_value={"symbol": "ADBL", "status": "screened", "signals": [], "metrics": {}}))
            stack.enter_context(patch.object(main, "detect_structure", return_value={"status": "observed", "bias": "neutral", "events": []}))
            stack.enter_context(patch.object(main, "add_event_evidence"))
            stack.enter_context(patch.object(main, "evaluate_idpat_v3", return_value={"status": "unavailable", "score": None}))
            stack.enter_context(patch.object(main, "evaluate_provisional", return_value={"status": "unavailable", "score": None}))
            stack.enter_context(patch.object(main, "evaluate_timeframes", return_value={"t_plus_2": {"recent_events": []}}))
            stack.enter_context(patch.object(main, "evaluate_confluence", return_value={"status": "unavailable", "score": None}))
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={"symbols": ["ADBL"]})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        result = payload["results"][0]
        self.assertEqual(result["status"], "screened")
        self.assertEqual(result["signal_confirmation"]["status"], "insufficient_data")
        self.assertEqual(result["signal_confirmation"]["classification"], "UNKNOWN")
        self.assertEqual(result["result_bucket"], "research_only")
        self.assertEqual(result["horizon_actions"], {
            "t_plus_2": "NOT_ASSESSED", "swing": "NOT_ASSESSED",
            "positional": "NOT_ASSESSED", "investment": "NOT_ASSESSED",
        })
        self.assertFalse(result["ranking_eligible"])
        self.assertFalse(result["buy_list_eligible"])
        self.assertEqual(payload["unknown_results"], [])
        self.assertEqual(payload["ranked_results"], [])
        self.assertEqual(payload["buy_candidates"], [])

    def test_api_keeps_synthetic_history_unknown_when_server_manifest_is_empty(self):
        from datetime import date, timedelta
        rows = []
        start = date(2025, 1, 1)
        for i in range(60):
            close = 100 + i
            rows.append({"date": start + timedelta(days=i), "open": close - 1,
                         "high": close + 1, "low": close - 2,
                         "close": close, "volume": 1000})
        rows[-1].update(open=159, high=165, low=158, close=164, volume=2500)
        with patch.object(main, "DATA", {"ADBL": rows}), \
             patch.object(main, "REVIEWED_ROWS", {}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={"symbols": ["ADBL"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertFalse(result["eligibility"]["eligible"])
        self.assertTrue(result["eligibility"]["reasons"])
        self.assertEqual(result["signal_confirmation"]["status"], "unknown")
        self.assertEqual(result["signal_confirmation"]["classification"], "UNKNOWN")
        self.assertFalse(result["ranking_eligible"])
        self.assertFalse(result["buy_list_eligible"])

    def test_api_emits_bullish_research_confirmation_only_after_eligibility_gate(self):
        from datetime import date, timedelta
        from contextlib import ExitStack
        rows = []
        start = date(2025, 1, 1)
        for i in range(60):
            close = 100 + i
            rows.append({"date": start + timedelta(days=i), "open": close - 1,
                         "high": close + 1, "low": close - 2,
                         "close": close, "volume": 1000})
        rows[-1].update(open=159, high=165, low=158, close=164, volume=2500)
        reviewed = {("ADBL", str(row["date"])): dict(row, evidence_id="synthetic-test")
                    for row in rows}
        with ExitStack() as stack:
            stack.enter_context(patch.object(main, "DATA", {"ADBL": rows}))
            stack.enter_context(patch.object(main, "REVIEWED_ROWS", reviewed))
            stack.enter_context(patch.object(main, "assess", return_value=[]))
            stack.enter_context(patch.object(main, "analyze", return_value={"symbol": "ADBL", "status": "screened", "signals": [], "metrics": {}}))
            stack.enter_context(patch.object(main, "detect_structure", return_value={"status": "observed", "bias": "neutral", "events": []}))
            stack.enter_context(patch.object(main, "add_event_evidence"))
            stack.enter_context(patch.object(main, "evaluate_idpat_v3", return_value={"status": "unavailable", "score": None}))
            stack.enter_context(patch.object(main, "evaluate_provisional", return_value={"status": "unavailable", "score": None}))
            stack.enter_context(patch.object(main, "evaluate_timeframes", return_value={"t_plus_2": {"recent_events": []}}))
            stack.enter_context(patch.object(main, "evaluate_confluence", return_value={"status": "unavailable", "score": None}))
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={"symbols": ["ADBL"]})
        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["signal_confirmation"]["classification"], "bullish_confirmation")
        self.assertEqual(result["signal_confirmation"]["status"], "research_confirmed")
        self.assertFalse(result["ranking_eligible"])
        self.assertFalse(result["buy_list_eligible"])
        self.assertEqual(result["result_bucket"], "research_only")

    def test_default_scan_includes_unloaded_candidate_unl_as_unknown(self):
        with patch.object(main, "DATA", {"ADBL": []}):
            with TestClient(main.app) as client:
                response = client.post("/v1/scan", json={})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        by_symbol = {item["symbol"]: item for item in payload["results"]}
        self.assertIn("UNL", by_symbol)
        self.assertEqual(by_symbol["UNL"]["status"], "unknown_result")
        self.assertIn("UNL", {item["symbol"] for item in payload["unknown_results"]})
        self.assertEqual(payload["ranked_results"], [])
        self.assertEqual(payload["buy_candidates"], [])


if __name__ == "__main__":
    unittest.main()
