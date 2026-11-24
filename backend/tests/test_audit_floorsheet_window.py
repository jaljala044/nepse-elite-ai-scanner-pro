import unittest

from audit_floorsheet_window import audit_socrateai_rows


def row(**overrides):
    value = {
        "transaction": "2026082601000001",
        "date": "2026-08-26",
        "symbol": "NABIL",
        "buyer": "58",
        "seller": "26",
        "quantity": "10.0",
        "rate": "540.6",
        "amount": "5406.0",
    }
    value.update(overrides)
    return value


class FloorsheetWindowAuditTests(unittest.TestCase):
    def test_validates_socrateai_rows_and_totals(self):
        result = audit_socrateai_rows([
            row(),
            row(transaction="2026082601000002", symbol="HBL", quantity="20", rate="190", amount="3800"),
        ], "2026-08-26")
        self.assertTrue(result["row_validation_pass"])
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["total_quantity"], 30)
        self.assertEqual(result["total_amount"], "9206.0")
        self.assertFalse(result["execution_time_available"])

    def test_flags_wrong_date_and_amount_arithmetic(self):
        result = audit_socrateai_rows([row(date="2026-08-25", amount="5407")], "2026-08-26")
        self.assertFalse(result["row_validation_pass"])
        reasons = {x["reason"] for x in result["row_validation_errors"]}
        self.assertIn("date_mismatch", reasons)
        self.assertIn("quantity_rate_amount_mismatch", reasons)

    def test_flags_duplicate_contract_numbers(self):
        result = audit_socrateai_rows([row(), row()], "2026-08-26")
        self.assertFalse(result["row_validation_pass"])
        self.assertEqual(len(result["duplicate_contracts"]), 1)


if __name__ == "__main__":
    unittest.main()
