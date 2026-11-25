import unittest
from datetime import date
from decimal import Decimal

from app.broker_identity import BrokerIdentityLink
from app.floorsheet_contract import FloorsheetContract
from app.floorsheet_broker_join import resolve_contract_brokers


class FloorsheetBrokerJoinTests(unittest.TestCase):
    def contract(self, line=1, buyer="11", seller="42"):
        return FloorsheetContract(
            source_id="fixture", source_payload_sha256="a" * 64,
            source_row_number=line, trade_date="2024-06-03", contract_id=f"C{line}",
            symbol="NABIL", buyer_broker_code=buyer, seller_broker_code=seller,
            quantity=Decimal("10"), rate=Decimal("100"), amount=Decimal("1000"),
        )

    def test_resolves_both_sides_using_trade_date(self):
        links = [
            BrokerIdentityLink("fixture", "11", "B11", "verified", "e11",
                               valid_from=date(2020, 1, 1), valid_to=date(2024, 12, 31)),
            BrokerIdentityLink("fixture", "42", "B42", "verified", "e42",
                               valid_from=date(2020, 1, 1), valid_to=date(2024, 12, 31)),
        ]
        result = resolve_contract_brokers([self.contract()], links, source_id="fixture")
        self.assertEqual(result["party_observation_rows"], 2)
        self.assertEqual([r["broker_entity_id"] for r in result["rows"]], ["B11", "B42"])
        self.assertEqual([r["side"] for r in result["rows"]], ["buy", "sell"])

    def test_unmapped_and_ambiguous_codes_are_retained(self):
        links = [BrokerIdentityLink("fixture", "42", None, "ambiguous", "review")]
        result = resolve_contract_brokers([self.contract()], links, source_id="fixture")
        self.assertEqual(result["party_observation_rows"], 2)
        self.assertEqual(result["unresolved_rows_retained"], 2)
        self.assertEqual([r["broker_entity_id"] for r in result["rows"]], [None, None])

    def test_historical_mapping_change_uses_contract_date(self):
        links = [
            BrokerIdentityLink("fixture", "11", "OLD", "verified", "old",
                               valid_from=date(2020, 1, 1), valid_to=date(2023, 12, 31)),
            BrokerIdentityLink("fixture", "11", "NEW", "verified", "new",
                               valid_from=date(2024, 1, 1)),
        ]
        result = resolve_contract_brokers([self.contract(seller="99")], links, source_id="fixture")
        self.assertEqual(result["rows"][0]["broker_entity_id"], "NEW")

    def test_source_row_and_payload_lineage_preserved(self):
        result = resolve_contract_brokers([self.contract(line=7)], [], source_id="fixture")
        row = result["rows"][0]
        self.assertEqual(row["source_row_number"], 7)
        self.assertEqual(row["source_payload_sha256"], "a" * 64)
        self.assertEqual(result["input_contract_rows"], 1)

    def test_blank_source_rejected(self):
        with self.assertRaises(ValueError):
            resolve_contract_brokers([self.contract()], [], source_id=" ")


if __name__ == "__main__":
    unittest.main()
