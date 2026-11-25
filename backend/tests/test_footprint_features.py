import unittest
from decimal import Decimal
from app.footprint_features import market_breadth, security_footprint, broker_participation_summary


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

    def test_empty_broker_summary_is_insufficient(self):
        self.assertEqual(broker_participation_summary([])["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
