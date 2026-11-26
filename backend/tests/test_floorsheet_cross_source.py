from decimal import Decimal
import unittest

from app.floorsheet_contract import FloorsheetContract
from app.floorsheet_cross_source import compare_floorsheet_sources


HASH = "a" * 64


def row(source, contract, *, symbol="AAA", quantity="10", amount="100"):
    return FloorsheetContract(
        source_id=source, source_payload_sha256=HASH, source_row_number=2,
        trade_date="2026-11-24", contract_id=contract, symbol=symbol,
        buyer_broker_code="11", seller_broker_code="22",
        quantity=Decimal(quantity), rate=Decimal("10"), amount=Decimal(amount),
    )


class FloorsheetCrossSourceTests(unittest.TestCase):
    def test_exact_overlap_and_one_sided_rows_are_reported(self):
        left = [row("left", "C1"), row("left", "C2")]
        right = [row("right", "C1"), row("right", "C3")]
        result = compare_floorsheet_sources(left, right)
        self.assertEqual(result["shared_contract_count"], 1)
        self.assertEqual(result["exact_shared_contract_count"], 1)
        self.assertEqual(result["conflicting_shared_contract_count"], 0)
        self.assertEqual(result["left_only_contract_keys"][0]["contract_id"], "C2")
        self.assertEqual(result["right_only_contract_keys"][0]["contract_id"], "C3")
        self.assertEqual(result["right_only_contracts"][0]["symbol"], "AAA")
        self.assertEqual(result["right_only_contracts"][0]["quantity"], "10")
        self.assertEqual(result["right_only_contracts"][0]["amount"], "100")
        self.assertEqual(result["right_only_contracts"][0]["source_row_number"], 2)
        self.assertEqual(result["left_only_contracts"][0]["contract_id"], "C2")
        self.assertFalse(result["source_independence_verified"])
        self.assertFalse(result["coverage_admission_allowed"])

    def test_shared_contract_field_conflict_is_explicit(self):
        result = compare_floorsheet_sources(
            [row("left", "C1")],
            [row("right", "C1", symbol="BBB")],
        )
        self.assertEqual(result["conflicting_shared_contract_count"], 1)
        self.assertIn("symbol", result["conflicts"][0]["differing_fields"])
        self.assertEqual(result["conflicts"][0]["left_record"]["symbol"], "AAA")
        self.assertEqual(result["conflicts"][0]["right_record"]["symbol"], "BBB")

    def test_source_totals_use_contract_rows_once(self):
        result = compare_floorsheet_sources(
            [row("left", "C1"), row("left", "C2", quantity="2", amount="20")],
            [row("right", "C1")],
        )
        self.assertEqual(result["left_totals"]["contract_count"], 2)
        self.assertEqual(result["left_totals"]["quantity"], "12")
        self.assertEqual(result["left_totals"]["gross_amount"], "120")

    def test_duplicate_keys_rejected_in_each_source(self):
        with self.assertRaisesRegex(ValueError, "duplicate date/contract key"):
            compare_floorsheet_sources(
                [row("left", "C1"), row("left", "C1")],
                [row("right", "C1")],
            )

    def test_empty_or_untyped_source_rejected(self):
        with self.assertRaisesRegex(ValueError, "both sources"):
            compare_floorsheet_sources([], [row("right", "C1")])
        with self.assertRaisesRegex(ValueError, "FloorsheetContract"):
            compare_floorsheet_sources([object()], [row("right", "C1")])


if __name__ == "__main__":
    unittest.main()
