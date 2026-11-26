import unittest
from decimal import Decimal
from app.footprint_features import market_breadth, security_footprint, broker_participation_summary, broker_footprint_features


class FootprintFeatureTests(unittest.TestCase):
    def test_market_breadth_reports_denominator_and_coverage(self):
        rows = [
            {"symbol":"AAA","close":11,"previous_close":10},
            {"symbol":"BBB","close":9,"previous_close":10},
        ]
        result = market_breadth(rows, ["AAA","BBB","CCC"])
        self.assertEqual((result["advancing"], result["declining"]), (1,1))
        self.assertAlmostEqual(result["coverage_ratio"], 2/3)
        self.assertEqual(result["status"], "insufficient_coverage")

    def test_out_of_universe_symbols_do_not_inflate_market_breadth(self):
        rows = [
            {"symbol":"AAA","close":11,"previous_close":10},
            {"symbol":"DEBT1","close":20,"previous_close":10},
        ]
        result = market_breadth(rows, ["AAA"])
        self.assertEqual(result["observed_symbols"], 1)
        self.assertEqual(result["eligible_symbols"], 1)
        self.assertEqual(result["coverage_ratio"], 1.0)
        self.assertEqual(result["advancing"], 1)
        self.assertEqual(result["unexpected_symbols"], ["DEBT1"])

    def test_security_footprint_uses_prior_only_volume_baseline(self):
        rows = [{"session_date":f"2026-11-{i:02d}","close":100+i,"previous_close":99+i,"volume":100}
                for i in range(1,7)]
        rows[-1]["volume"] = 300
        result = security_footprint(rows, minimum_history=5)
        self.assertEqual(result["prior_volume_mean"], 100)
        self.assertEqual(result["volume_ratio"], 3)
        self.assertEqual(result["status"], "observed")

    def test_market_breadth_rejects_non_finite_prices(self):
        with self.assertRaisesRegex(ValueError, "finite and positive"):
            market_breadth([{"symbol":"AAA","close":float("nan"),"previous_close":10}])

    def test_market_breadth_rejects_duplicate_expected_symbols(self):
        with self.assertRaisesRegex(ValueError, "must be unique"):
            market_breadth([], ["AAA", "AAA"])

    def test_security_footprint_rejects_duplicate_sessions(self):
        rows = [
            {"session_date":"2026-11-23","close":10,"previous_close":9,"volume":100},
            {"session_date":"2026-11-23","close":11,"previous_close":10,"volume":120},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate session dates"):
            security_footprint(rows)

    def test_security_footprint_rejects_non_finite_volume(self):
        rows = [{"session_date":"2026-11-23","close":10,"previous_close":9,"volume":float("inf")}]
        with self.assertRaisesRegex(ValueError, "finite non-negative"):
            security_footprint(rows)

    def test_broker_summary_does_not_assign_unverified_flow(self):
        rows = [
            {"identity_status":"verified","broker_entity_id":"B1","side":"buy","amount":100},
            {"identity_status":"ambiguous","broker_entity_id":None,"side":"buy","amount":900},
        ]
        result = broker_participation_summary(rows)
        self.assertEqual(Decimal(result["verified_net_amount"]), Decimal("100"))
        self.assertEqual(result["unmapped_or_unverified_rows"], 1)
        self.assertEqual(result["status"], "partial_identity_coverage")

    def test_broker_summary_uses_exact_decimal_amounts(self):
        rows = [
            {"identity_status":"verified","broker_entity_id":"B1","side":"buy","amount":"0.1"},
            {"identity_status":"verified","broker_entity_id":"B2","side":"buy","amount":"0.2"},
        ]
        result = broker_participation_summary(rows)
        self.assertEqual(result["verified_buy_amount"], "0.3")
        self.assertEqual(result["verified_net_amount"], "0.3")

    def test_broker_summary_rejects_unresolved_identity_with_entity_id(self):
        rows = [{"identity_status":"ambiguous","broker_entity_id":"B1","side":"buy","amount":"10"}]
        with self.assertRaisesRegex(ValueError, "unresolved identity"):
            broker_participation_summary(rows)

    def test_broker_summary_rejects_non_finite_amount(self):
        rows = [{"identity_status":"verified","broker_entity_id":"B1","side":"buy","amount":"NaN"}]
        with self.assertRaisesRegex(ValueError, "finite and non-negative"):
            broker_participation_summary(rows)


    def test_broker_footprint_ranks_verified_buyers_and_sellers_by_window(self):
        rows = []
        for day in range(1, 6):
            trade_date = f"2026-11-{day:02d}"
            for contract, buyer, seller, amount in (
                ("A", "BROKER-A", "BROKER-B", "100"),
                ("B", "BROKER-B", "BROKER-A", "20"),
            ):
                rows.extend([
                    {"trade_date": trade_date, "symbol": "NABIL", "side": "buy",
                     "amount": amount, "quantity": "1", "identity_status": "verified",
                     "broker_entity_id": buyer, "source_broker_code": buyer},
                    {"trade_date": trade_date, "symbol": "NABIL", "side": "sell",
                     "amount": amount, "quantity": "1", "identity_status": "verified",
                     "broker_entity_id": seller, "source_broker_code": seller},
                ])
        result = broker_footprint_features(rows)
        daily = result["security_features"]["NABIL"]["1D"]
        self.assertEqual(daily["status"], "observed")
        self.assertEqual(daily["top_net_buyers"][0]["broker_entity_id"], "BROKER-A")
        self.assertEqual(daily["top_net_sellers"][0]["broker_entity_id"], "BROKER-B")
        self.assertEqual(daily["verified_amount_coverage_pct"], 100)
        self.assertEqual(result["market_windows"]["1W"]["observed_sessions"], 5)

    def test_unresolved_broker_amount_remains_in_coverage_and_blocks_score(self):
        rows = [
            {"trade_date": "2026-11-24", "symbol": "NABIL", "side": "buy",
             "amount": "100", "quantity": "1", "identity_status": "verified",
             "broker_entity_id": "BROKER-A", "source_broker_code": "11"},
            {"trade_date": "2026-11-24", "symbol": "NABIL", "side": "sell",
             "amount": "900", "quantity": "9", "identity_status": "unmapped",
             "broker_entity_id": None, "source_broker_code": "99"},
        ]
        result = broker_footprint_features(rows)
        daily = result["security_features"]["NABIL"]["1D"]
        self.assertEqual(daily["verified_amount_coverage_pct"], 10)
        self.assertIsNone(daily["score"])
        self.assertEqual(daily["unresolved_party_observation_count"], 1)
        self.assertEqual(daily["status"], "insufficient_identity_coverage_or_history")

    def test_broker_footprint_refuses_missing_party_schema(self):
        result = broker_footprint_features([{"side": "buy", "amount": "100"}])
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["score"])

    def test_broker_footprint_rejects_unresolved_entity_assignment(self):
        rows = [{
            "trade_date": "2026-11-24", "symbol": "NABIL", "side": "buy",
            "amount": "100", "quantity": "1", "identity_status": "ambiguous",
            "broker_entity_id": "BROKER-A", "source_broker_code": "11",
        }]
        with self.assertRaisesRegex(ValueError, "unresolved identity"):
            broker_footprint_features(rows)

    def test_empty_broker_summary_is_insufficient(self):
        self.assertEqual(broker_participation_summary([])["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
