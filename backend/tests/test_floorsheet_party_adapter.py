import hashlib
import unittest
from decimal import Decimal

from app.floorsheet_contract import FloorsheetContract
from app.floorsheet_party_adapter import (
    aggregate_floorsheet_broker_parties,
    build_broker_party_observations,
)


class FloorsheetPartyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.digest = hashlib.sha256(b"floorsheet sample").hexdigest()
        self.contracts = [
            FloorsheetContract(
                source_id="urek@pinned",
                source_payload_sha256=self.digest,
                source_row_number=2,
                trade_date="2026-08-26",
                contract_id="00001",
                symbol="NABIL",
                buyer_broker_code="11",
                seller_broker_code="42",
                quantity=Decimal("10"),
                rate=Decimal("100"),
                amount=Decimal("1000"),
            ),
            FloorsheetContract(
                source_id="urek@pinned",
                source_payload_sha256=self.digest,
                source_row_number=3,
                trade_date="2026-08-26",
                contract_id="00002",
                symbol="NABIL",
                buyer_broker_code="12",
                seller_broker_code="42",
                quantity=Decimal("5"),
                rate=Decimal("110"),
                amount=Decimal("550"),
            ),
        ]

    def test_each_contract_becomes_two_separate_party_observations(self):
        rows = build_broker_party_observations(self.contracts)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["side"] for r in rows], ["buy", "sell", "buy", "sell"])
        self.assertEqual([r["source_broker_code"] for r in rows], ["11", "42", "12", "42"])
        self.assertTrue(all(r["identity_status"] == "unmapped" for r in rows))
        self.assertTrue(all(r["broker_entity_id"] is None for r in rows))

    def test_unresolved_source_broker_codes_remain_separate_aggregates(self):
        result = aggregate_floorsheet_broker_parties(self.contracts)
        buys = [x for x in result["aggregates"] if x["side"] == "buy"]
        self.assertEqual(
            {x["source_broker_code"] for x in buys},
            {"11", "12"},
        )
        self.assertEqual(len(buys), 2)
        self.assertTrue(all(x["broker_entity_id"] is None for x in buys))
        self.assertTrue(all(x["identity_status"] == "unmapped" for x in buys))

    def test_party_amounts_preserve_both_sides_and_do_not_claim_gross_contract_count(self):
        result = aggregate_floorsheet_broker_parties(self.contracts)
        self.assertEqual(result["input_party_observation_rows"], 4)
        self.assertEqual(sum(Decimal(x["amount"]) for x in result["aggregates"]), Decimal("3100"))
        buy_coverage = next(x for x in result["coverage"] if x["side"] == "buy")
        self.assertEqual(buy_coverage["unresolved_amount"], "1550")
        self.assertEqual(buy_coverage["total_amount"], "1550")
        # Gross source turnover is counted once per contract, not once per party.
        self.assertEqual(sum(x.amount for x in self.contracts), Decimal("1550"))

    def test_asymmetric_verified_identity_mapping_only_verifies_reviewed_codes(self):
        result = aggregate_floorsheet_broker_parties(
            self.contracts,
            identity_links={
                ("urek@pinned", "11"): {
                    "status": "verified", "broker_entity_id": "broker-11",
                    "evidence_ids": ["broker-list-review-1"],
                }
            },
        )
        aggregates = result["aggregates"]
        self.assertTrue(any(x["broker_entity_id"] == "broker-11" for x in aggregates))
        self.assertTrue(any(
            x["source_broker_code"] == "12"
            and x["identity_status"] == "unmapped"
            and x["broker_entity_id"] is None
            for x in aggregates
        ))


if __name__ == "__main__":
    unittest.main()
