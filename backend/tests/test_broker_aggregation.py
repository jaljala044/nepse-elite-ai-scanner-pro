import unittest
from app.broker_aggregation import aggregate_broker_observations, reconcile_source_control_totals


def row(code="B11", status="verified", side="buy", amount="100.10", quantity="1.5", line=1):
    return {
        "trade_date": "2026-11-24", "symbol": "NABIL", "broker_entity_id": code,
        "identity_status": status, "side": side, "amount": amount, "quantity": quantity,
        "source_id": "src", "contract_id": f"C{line}", "source_payload_sha256": "a" * 64,
        "source_row_number": line, "identity_evidence_ids": ["e1"] if status == "verified" else [],
    }


class BrokerAggregationTests(unittest.TestCase):
    def test_exact_decimal_aggregation_and_side_separation(self):
        result = aggregate_broker_observations([row(line=1), row(line=2, amount="0.20", quantity="2.5"),
                                                row(side="sell", line=3)])
        buy = next(x for x in result["aggregates"] if x["side"] == "buy")
        self.assertEqual(buy["amount"], "100.30")
        self.assertEqual(buy["quantity"], "4.0")
        self.assertEqual(buy["contract_count"], 2)

    def test_unresolved_amount_remains_in_coverage_denominator(self):
        result = aggregate_broker_observations([row(line=1), row(code=None, status="unmapped",
                                                                   amount="50", line=2)])
        c = result["coverage"][0]
        self.assertEqual(c["total_amount"], "150.10")
        self.assertEqual(c["verified_amount"], "100.10")
        self.assertEqual(c["unresolved_amount"], "50")
        self.assertEqual(c["unresolved_observation_count"], 1)

    def test_identity_status_and_entity_consistency(self):
        with self.assertRaisesRegex(ValueError, "unresolved identity"):
            aggregate_broker_observations([row(code="B11", status="unmapped")])

    def test_duplicate_lineage_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate party observation"):
            aggregate_broker_observations([row(line=1), row(line=1)])

    def test_invalid_decimal_rejected(self):
        with self.assertRaisesRegex(ValueError, "amount and quantity"):
            aggregate_broker_observations([row(amount="NaN")])

    def test_invalid_source_payload_hash_rejected(self):
        item = row(line=1)
        item["source_payload_sha256"] = "not-a-sha"
        with self.assertRaisesRegex(ValueError, "64-character hex digest"):
            aggregate_broker_observations([item])

    def test_verified_identity_requires_evidence_ids(self):
        item = row(line=1)
        item["identity_evidence_ids"] = []
        with self.assertRaisesRegex(ValueError, "requires identity evidence IDs"):
            aggregate_broker_observations([item])

    def test_invalid_trade_date_rejected(self):
        item = row(line=1)
        item["trade_date"] = "not-a-date"
        with self.assertRaisesRegex(ValueError, "trade_date must be ISO date"):
            aggregate_broker_observations([item])

    def test_aggregation_is_independent_of_input_order(self):
        rows = [row(line=1), row(line=2, amount="0.20", quantity="2.5"),
                row(side="sell", line=3)]
        first = aggregate_broker_observations(rows)
        second = aggregate_broker_observations(list(reversed(rows)))
        self.assertEqual(first, second)

    def test_source_control_totals_count_contract_once(self):
        buyer = row(line=1)
        seller = row(line=1)
        seller["side"] = "sell"
        controls = [{"source_id":"src","trade_date":"2026-11-24",
                     "contract_count":1,"gross_amount":"100.10","party_observation_count":2}]
        result = reconcile_source_control_totals([buyer, seller], controls)
        self.assertEqual(result["passed_source_dates"], 1)
        self.assertEqual(result["results"][0]["observed_gross_amount"], "100.10")
        self.assertEqual(result["results"][0]["observed_contract_count"], 1)

    def test_source_control_mismatch_is_reported(self):
        buyer = row(line=1)
        seller = row(line=1)
        seller["side"] = "sell"
        seller["amount"] = "100.11"
        controls = [{"source_id":"src","trade_date":"2026-11-24",
                     "contract_count":1,"gross_amount":"100.10","party_observation_count":2}]
        result = reconcile_source_control_totals([buyer, seller], controls)
        self.assertEqual(result["failed_source_dates"], 1)
        self.assertIn("contract_party_anomalies", result["results"][0]["differences"])

    def test_missing_buyer_or_seller_side_is_anomaly(self):
        controls = [{"source_id":"src","trade_date":"2026-11-24",
                     "contract_count":1,"gross_amount":"100.10","party_observation_count":2}]
        result = reconcile_source_control_totals([row(line=1)], controls)
        self.assertEqual(result["failed_source_dates"], 1)
        self.assertEqual(result["results"][0]["contract_anomalies"][0]["party_count"], 1)

    def test_unverified_broker_does_not_merge_into_entity_bucket(self):
        result = aggregate_broker_observations([row(line=1), row(code=None, status="ambiguous", line=2)])
        self.assertEqual(len(result["aggregates"]), 2)
        self.assertEqual(sum(x["contract_count"] for x in result["aggregates"]), 2)


if __name__ == "__main__":
    unittest.main()
