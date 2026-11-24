import unittest

from compare_floorsheet_samples import compare_samples


def urek(contract="2026082601000001", **overrides):
    row = {
        "contract_no": contract,
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


def soc(contract="2026082601000001", **overrides):
    row = {
        "transaction": contract,
        "date": "2026-08-26",
        "symbol": "NABIL",
        "buyer": "58",
        "seller": "26",
        "quantity": "10.0",
        "rate": "540.6",
        "amount": "5406.0",
    }
    row.update(overrides)
    return row


class FloorsheetSampleComparisonTests(unittest.TestCase):
    def test_exact_shared_transactions_match_across_schema_variants(self):
        result = compare_samples([urek()], [soc()], "2026-08-26")
        self.assertTrue(result["cross_source_match_pass"])
        self.assertEqual(result["cross_source_status"], "EXACT_MATCH_ON_SHARED_TRANSACTION_FIELDS")
        self.assertEqual(result["contract_number_comparison"]["shared_contracts"], 1)
        self.assertEqual(result["urek_only_fields_not_cross_checked"], ["time", "sector", "id"])

    def test_numeric_formatting_differences_are_normalized_as_decimal(self):
        result = compare_samples([urek()], [soc()], "2026-08-26")
        self.assertEqual(result["shared_field_mismatch_count"], 0)

    def test_detects_missing_contracts(self):
        result = compare_samples([urek()], [soc("2026082601000002")], "2026-08-26")
        self.assertFalse(result["cross_source_match_pass"])
        self.assertEqual(result["contract_number_comparison"]["urek_only_contracts"], 1)
        self.assertEqual(result["contract_number_comparison"]["socrateai_only_contracts"], 1)

    def test_detects_shared_field_mismatch(self):
        result = compare_samples([urek()], [soc(amount="5407.0")], "2026-08-26")
        self.assertEqual(result["shared_field_mismatch_count"], 1)
        self.assertEqual(result["shared_field_mismatches_preview"][0]["field_differences"][0]["field"], "amount")

    def test_detects_duplicate_contracts(self):
        result = compare_samples([urek(), urek()], [soc()], "2026-08-26")
        self.assertFalse(result["cross_source_match_pass"])
        self.assertEqual(result["contract_number_comparison"]["urek_duplicate_contract_numbers"], ["2026082601000001"])

    def test_rejects_wrong_date(self):
        result = compare_samples([urek(calculation_date="2026-08-25")], [soc()], "2026-08-26")
        self.assertEqual(result["date_error_count"], 1)


if __name__ == "__main__":
    unittest.main()
