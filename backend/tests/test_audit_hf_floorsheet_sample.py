import tempfile
import unittest
from pathlib import Path

from audit_hf_floorsheet_sample import (
    audit_floorsheet_rows, compare_index_controls, find_nepse_index_row,
)


def sample_row(**overrides):
    row = {
        "contract_no": "2026082601000001",
        "calculation_date": "2026-08-26",
        "time": "10:46:00",
        "stock_symbol": "NABIL",
        "sector": "Commercial Banks",
        "buyer": "58",
        "seller": "26",
        "quantity": "10",
        "rate": "540.60",
        "amount": "5406.00",
        "id": "20260826059442",
    }
    row.update(overrides)
    return row


class HFFloorsheetSampleAuditTests(unittest.TestCase):
    def test_valid_rows_and_null_time_are_preserved(self):
        rows = [sample_row(), sample_row(
            contract_no="2026082601000002", id="20260826059441",
            time="", stock_symbol="HBL", buyer="4", seller="62",
            quantity="20", rate="190.00", amount="3800.00",
        )]
        result = audit_floorsheet_rows(rows, "2026-08-26")
        self.assertTrue(result["row_validation_pass"])
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["null_execution_time_count"], 1)
        self.assertEqual(result["total_quantity"], 30)
        self.assertEqual(result["total_amount"], "9206.00")
        self.assertEqual(result["unique_symbols"], 2)

    def test_flags_calculation_date_and_contract_prefix_mismatch(self):
        result = audit_floorsheet_rows([
            sample_row(calculation_date="2026-08-25", contract_no="2026082501000001")
        ], "2026-08-26")
        self.assertFalse(result["row_validation_pass"])
        reasons = {x["reason"] for x in result["row_validation_errors"]}
        self.assertIn("calculation_date_mismatch", reasons)
        self.assertIn("contract_date_prefix_mismatch", reasons)

    def test_flags_quantity_rate_amount_mismatch(self):
        result = audit_floorsheet_rows([sample_row(amount="5407.00")], "2026-08-26")
        self.assertFalse(result["row_validation_pass"])
        self.assertIn("quantity_rate_amount_mismatch", {x["reason"] for x in result["row_validation_errors"]})

    def test_flags_exact_duplicate_contract_without_deduplicating(self):
        rows = [
            sample_row(),
            sample_row(id="20260826059443"),
        ]
        result = audit_floorsheet_rows(rows, "2026-08-26")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(len(result["exact_duplicate_contracts"]), 1)
        self.assertEqual(len(result["conflicting_duplicate_contracts"]), 0)
        self.assertFalse(result["row_validation_pass"])

    def test_flags_conflicting_duplicate_contract(self):
        rows = [sample_row(), sample_row(id="20260826059443", amount="6000.00")]
        result = audit_floorsheet_rows(rows, "2026-08-26")
        self.assertEqual(len(result["conflicting_duplicate_contracts"]), 1)

    def test_flags_duplicate_ids(self):
        rows = [sample_row(), sample_row(contract_no="2026082601000002")]
        result = audit_floorsheet_rows(rows, "2026-08-26")
        self.assertEqual(len(result["duplicate_ids"]), 1)

    def test_finds_nepse_index_control_row(self):
        rows = [{"sector": "Banking"}, {"sector": "NEPSE_index", "turnover_values": "9206.00"}]
        self.assertEqual(find_nepse_index_row(rows)["turnover_values"], "9206.00")

    def test_compares_daily_control_totals_exactly(self):
        floor = {"total_amount": "9206.00", "total_quantity": 30, "row_count": 2}
        index_rows = [{
            "sector": "NEPSE",
            "turnover_values": "9206.00",
            "turnover_volume": "30",
            "total_transaction": "2",
        }]
        result = compare_index_controls(floor, index_rows)
        self.assertTrue(result["matched"])
        self.assertEqual(result["status"], "exact_control_total_match")

    def test_preserves_control_total_differences(self):
        floor = {"total_amount": "9206.01", "total_quantity": 30, "row_count": 2}
        index_rows = [{
            "sector": "NEPSE_index",
            "turnover_values": "9206.00",
            "turnover_volume": "30",
            "total_transaction": "2",
        }]
        result = compare_index_controls(floor, index_rows)
        self.assertFalse(result["matched"])
        self.assertEqual(result["comparisons"]["turnover_amount"]["difference_floorsheet_minus_index"], "0.01")


if __name__ == "__main__":
    unittest.main()
