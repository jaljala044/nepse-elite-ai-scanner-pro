import unittest
from app.feature_pipeline import build_feature_snapshot


class FeaturePipelineTests(unittest.TestCase):
    def test_future_rows_are_excluded_before_feature_calculation(self):
        rows = [
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-23",
             "available_at":"2026-11-23T16:00:00Z","close":11,"previous_close":10,"volume":100},
            {"record_type":"ohlcv","symbol":"AAA","session_date":"2026-11-24",
             "available_at":"2026-11-25T16:00:00Z","close":99,"previous_close":11,"volume":9999},
            {"record_type":"broker","available_at":"2026-11-23T16:00:00Z",
             "identity_status":"unmapped","amount":500,"side":"buy"},
        ]
        result = build_feature_snapshot(rows, "2026-11-24T12:00:00Z", ["AAA","BBB"])
        self.assertEqual(result["excluded_input_count"], 1)
        self.assertEqual(result["security_features"]["AAA"]["close"], 11)
        self.assertEqual(result["market_breadth"]["observed_symbols"], 1)
        self.assertEqual(result["relative_strength"]["status"], "insufficient_evidence")
        self.assertTrue(result["point_in_time_eligible"])
        self.assertEqual(result["interpretation"], "descriptive_only_not_a_trading_signal")



    def test_verified_broker_party_rows_feed_point_in_time_footprint_and_component(self):
        from datetime import date, timedelta
        start = date(2026, 11, 16)
        rows = []
        for i in range(5):
            day = start + timedelta(days=i)
            session = day.isoformat()
            available = session + "T16:00:00Z"
            rows.append({
                "record_type": "ohlcv", "symbol": "AAA", "session_date": session,
                "available_at": available, "open": 100, "high": 102, "low": 99,
                "close": 101, "previous_close": 100, "volume": 1000,
            })
            for buyer, seller, amount in (("B1", "B2", "100"), ("B2", "B1", "20")):
                rows.extend([
                    {"record_type": "broker", "available_at": available,
                     "trade_date": session, "symbol": "AAA", "side": "buy",
                     "amount": amount, "quantity": "1", "identity_status": "verified",
                     "broker_entity_id": buyer, "source_broker_code": buyer},
                    {"record_type": "broker", "available_at": available,
                     "trade_date": session, "symbol": "AAA", "side": "sell",
                     "amount": amount, "quantity": "1", "identity_status": "verified",
                     "broker_entity_id": seller, "source_broker_code": seller},
                ])
        result = build_feature_snapshot(rows, "2026-11-21T12:00:00Z", ["AAA"])
        footprint = result["broker_footprint"]["security_features"]["AAA"]["1W"]
        self.assertEqual(footprint["status"], "observed")
        self.assertEqual(footprint["top_net_buyers"][0]["broker_entity_id"], "B1")
        self.assertIsNotNone(result["component_candidates"]["AAA"]["broker"])
        self.assertEqual(result["broker_footprint"]["as_of_trade_date"], "2026-11-20")


    def test_relative_strength_uses_only_verified_final_nepse_index_rows(self):
        from datetime import date, timedelta
        start = date(2026, 1, 1)
        rows = []
        benchmark_digest = "a" * 64
        for i in range(130):
            day = start + timedelta(days=i)
            session = day.isoformat()
            available = session + "T16:00:00Z"
            rows.append({
                "record_type": "index_ohlcv", "index_code": "NEPSE",
                "session_date": session, "available_at": available,
                "close": 1000 + i * 0.2,
                "source_validation_status": "verified", "finality_status": "final",
                "source_id": "exchange-index-audit", "source_payload_sha256": benchmark_digest,
            })
            for symbol, multiplier in (("AAA", 0.8), ("BBB", 0.05)):
                close = 100 + i * multiplier
                rows.append({
                    "record_type": "ohlcv", "symbol": symbol,
                    "session_date": session, "available_at": available,
                    "open": close, "high": close + 1, "low": close - 1,
                    "close": close, "previous_close": close - multiplier,
                    "volume": 1000,
                })
        provisional_day = (start + timedelta(days=130)).isoformat()
        rows.append({
            "record_type": "index_ohlcv", "index_code": "NEPSE",
            "session_date": provisional_day, "available_at": provisional_day + "T11:00:00Z",
            "close": 0, "source_validation_status": "verified",
            "finality_status": "provisional", "source_id": "exchange-index-audit",
            "source_payload_sha256": benchmark_digest,
        })
        decision_time = provisional_day + "T12:00:00Z"
        result = build_feature_snapshot(rows, decision_time, ["AAA", "BBB"])
        rs = result["relative_strength"]
        self.assertEqual(rs["status"], "observed")
        self.assertEqual(rs["withheld_unverified_or_provisional_index_rows"], 1)
        self.assertEqual(rs["results"]["AAA"]["as_of_session"], (start + timedelta(days=129)).isoformat())
        self.assertGreater(rs["results"]["AAA"]["score"], rs["results"]["BBB"]["score"])
        self.assertIsNotNone(result["component_candidates"]["AAA"]["relative_strength"])

    def test_unverified_index_rows_never_populate_relative_strength_component(self):
        from datetime import date, timedelta
        start = date(2026, 1, 1)
        rows = []
        for i in range(130):
            day = start + timedelta(days=i)
            session = day.isoformat()
            rows.append({
                "record_type": "ohlcv", "symbol": "AAA", "session_date": session,
                "available_at": session + "T16:00:00Z", "open": 100 + i,
                "high": 102 + i, "low": 99 + i, "close": 101 + i,
                "previous_close": 100 + i, "volume": 1000,
            })
            rows.append({
                "record_type": "index_ohlcv", "index_code": "NEPSE",
                "session_date": session, "available_at": session + "T16:00:00Z",
                "close": 1000 + i, "source_validation_status": "provisional",
                "finality_status": "provisional", "source_id": "unverified-source",
                "source_payload_sha256": "b" * 64,
            })
        result = build_feature_snapshot(rows, "2026-05-12T12:00:00Z", ["AAA"])
        self.assertEqual(result["relative_strength"]["status"], "insufficient_evidence")
        self.assertIsNone(result["component_candidates"]["AAA"]["relative_strength"])

    def test_point_in_time_snapshot_includes_minervini_template(self):
        from datetime import date, timedelta
        start = date(2025, 1, 1)
        rows = []
        for i in range(260):
            session = start + timedelta(days=i)
            close = 100.0 + i
            rows.append({
                "record_type": "ohlcv", "symbol": "AAA",
                "session_date": session.isoformat(),
                "available_at": session.isoformat() + "T16:00:00Z",
                "open": close, "high": close + 2, "low": close - 2,
                "close": close, "previous_close": close - 1,
                "volume": 1000,
            })
        result = build_feature_snapshot(
            rows, (start + timedelta(days=260)).isoformat() + "T12:00:00Z", ["AAA"]
        )
        trend = result["trend_features"]["AAA"]
        self.assertEqual(trend["status"], "observed")
        self.assertEqual(trend["score"], 100)
        self.assertEqual(trend["history_sessions"], 260)
        volume = result["volume_features"]["AAA"]
        self.assertEqual(volume["status"], "observed")
        self.assertEqual(volume["relative_volume"], 1.0)
        wyckoff = result["wyckoff_features"]["AAA"]
        self.assertEqual(wyckoff["status"], "observed")
        self.assertEqual(wyckoff["history_sessions"], 260)
        smc = result["smc_features"]["AAA"]
        self.assertEqual(smc["status"], "observed")
        self.assertEqual(smc["timeframes"]["daily"]["status"], "observed")
        candidates = result["component_candidates"]["AAA"]
        self.assertIsNotNone(candidates["wyckoff"])
        self.assertIsNotNone(candidates["trend"])
        self.assertIsNotNone(candidates["volume"])
        self.assertIsNotNone(candidates["smc"])
        self.assertIsNone(candidates["relative_strength"])
        self.assertIsNone(candidates["broker"])


if __name__ == "__main__":
    unittest.main()
