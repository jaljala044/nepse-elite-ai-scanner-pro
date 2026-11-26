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
