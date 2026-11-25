import unittest
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

    def test_broker_summary_does_not_assign_unverified_flow(self):
        rows = [
            {"identity_status":"verified","broker_entity_id":"B1","side":"buy","amount":100},
            {"identity_status":"ambiguous","broker_entity_id":None,"side":"buy","amount":900},
        ]
        result = broker_participation_summary(rows)
        self.assertEqual(result["verified_net_amount"], 100)
        self.assertEqual(result["unmapped_or_unverified_rows"], 1)
        self.assertEqual(result["status"], "partial_identity_coverage")

    def test_empty_broker_summary_is_insufficient(self):
        self.assertEqual(broker_participation_summary([])["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
