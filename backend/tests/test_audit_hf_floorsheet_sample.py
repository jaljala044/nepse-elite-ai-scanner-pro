import tempfile
import unittest
from pathlib import Path

from audit_hf_floorsheet_sample import (
    audit_floorsheet_rows, compare_index_controls, compare_reference_turnover,
    compare_sector_controls,
    find_nepse_index_row, validate_index_ohlc,
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

    def test_rejects_duplicate_nepse_index_control_rows(self):
        floor = {"total_amount": "9206.00", "total_quantity": 30, "row_count": 2}
        row = {"sector": "NEPSE_index", "turnover_values": "9206.00", "turnover_volume": "30", "total_transaction": "2"}
        result = compare_index_controls(floor, [row, dict(row)], "2026-08-26")
        self.assertFalse(result["matched"])
        self.assertEqual(result["status"], "duplicate_nepse_index_control_rows")
        self.assertEqual(result["nepse_index_row_count"], 2)

    def test_rejects_index_control_date_mismatch(self):
        floor = {"total_amount": "9206.00", "total_quantity": 30, "row_count": 2}
        row = {"date": "2026-08-25", "sector": "NEPSE_index", "turnover_values": "9206.00", "turnover_volume": "30", "total_transaction": "2"}
        result = compare_index_controls(floor, [row], "2026-08-26")
        self.assertFalse(result["matched"])
        self.assertEqual(result["status"], "nepse_index_control_date_mismatch")

    def test_flags_index_high_below_open_and_open_equal_to_previous_close(self):
        row = {
            "open": "2594.27", "high": "2592.12", "low": "2546.94",
            "close": "2558.35", "absolute_change": "-35.92",
        }
        result = validate_index_ohlc(row)
        self.assertFalse(result["valid"])
        self.assertIn("index_high_below_open", {x["reason"] for x in result["errors"]})
        self.assertTrue(result["previous_close_diagnostic"]["open_equals_derived_previous_close"])
        self.assertEqual(result["previous_close_diagnostic"]["derived_previous_close"], "2594.27")

    def test_compares_sector_controls_and_preserves_unmapped_instruments(self):
        floor_rows = [
            {"sector": "Development Banks", "quantity": "10", "amount": "1000.00"},
            {"sector": "Commercial Banks", "quantity": "20", "amount": "2000.00"},
            {"sector": "Non-Convertible Debentures", "quantity": "5", "amount": "500.00"},
        ]
        index_rows = [
            {"sector": "Development Bank Index", "total_transaction": "1", "turnover_volume": "10", "turnover_values": "1000.00"},
            {"sector": "Banking SubIndex", "total_transaction": "1", "turnover_volume": "19", "turnover_values": "1900.00"},
        ]
        result = compare_sector_controls(floor_rows, index_rows)
        self.assertEqual(result["exact_match_sector_count"], 1)
        self.assertEqual(result["different_sector_count"], 1)
        self.assertEqual(result["unmapped_floorsheet_sectors"], ["Non-Convertible Debentures"])
        commercial = next(x for x in result["sector_comparisons"] if x["floorsheet_sector"] == "Commercial Banks")
        self.assertEqual(commercial["status"], "sector_control_difference")
        self.assertEqual(commercial["comparisons"]["share_quantity"]["difference"], "1")

    def test_compares_reference_turnover_without_assuming_exact_equality(self):
        floor = {"total_amount": "4773857657.46"}
        reference = [{
            "date": "2026-08-26",
            "symbol": "NEPSE_index",
            "volume": "4773850987.0",
        }]
        result = compare_reference_turnover(floor, reference, "2026-08-26")
        self.assertEqual(result["status"], "different")
        self.assertEqual(result["difference_floorsheet_minus_reference"], "6670.46")
        self.assertIn("not share volume", result["mapping"])

    def test_rejects_reference_index_date_mismatch(self):
        floor = {"total_amount": "100"}
        reference = [{"date": "2026-08-25", "symbol": "NEPSE_index", "volume": "100"}]
        result = compare_reference_turnover(floor, reference, "2026-08-26")
        self.assertEqual(result["status"], "reference_index_date_mismatch")

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
