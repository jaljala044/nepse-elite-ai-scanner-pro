import unittest
from decimal import Decimal
from app.floorsheet_contract import FloorsheetContract, reconcile_floorsheet_rows


class FloorsheetContractTests(unittest.TestCase):
    digest = "a" * 64

    def row(self, contract_id="C1", amount="1000", buyer="11", line=1):
        return FloorsheetContract.from_mapping({
            "trade_date":"2026-11-24", "contract_id":contract_id, "symbol":"NABIL",
            "buyer_broker_code":buyer, "seller_broker_code":"42",
            "quantity":"10", "rate":"100", "amount":amount,
        }, source_id="fixture", payload_sha256=self.digest, row_number=line)


    def test_strict_thousands_grouping_is_normalized_without_precision_loss(self):
        row = FloorsheetContract.from_mapping({
            "trade_date": "2026-11-24", "contract_id": "C-GROUPED",
            "symbol": "NABIL", "buyer_broker_code": "11",
            "seller_broker_code": "42", "quantity": "14,670,177",
            "rate": "3,878.00", "amount": "56,878,545,126.00",
        }, source_id="fixture", payload_sha256=self.digest, row_number=1)
        self.assertEqual(row.quantity, Decimal("14670177"))
        self.assertEqual(row.rate, Decimal("3878.00"))
        self.assertEqual(row.amount, Decimal("56878545126.00"))

    def test_malformed_thousands_grouping_is_rejected_not_guessed(self):
        for value in ("38,78.00", "1,23,456", "1234,567", "1,000,00"):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "valid decimals"
            ):
                FloorsheetContract.from_mapping({
                    "trade_date": "2026-11-24", "contract_id": "C-BAD",
                    "symbol": "NABIL", "buyer_broker_code": "11",
                    "seller_broker_code": "42", "quantity": "10",
                    "rate": value, "amount": "1000",
                }, source_id="fixture", payload_sha256=self.digest, row_number=1)

    def test_unique_contract_and_amount_check(self):
        result = reconcile_floorsheet_rows([self.row()])
        self.assertEqual(result["counts"]["unique"], 1)
        self.assertFalse(result["rows"][0]["amount_reconciliation_exception"])
        self.assertEqual(result["rows_discarded"], 0)

    def test_exact_duplicates_are_classified_and_retained(self):
        result = reconcile_floorsheet_rows([self.row(line=1), self.row(line=2)])
        self.assertEqual(result["counts"]["exact_duplicate"], 2)
        self.assertEqual(result["output_rows"], 2)
        self.assertEqual(result["rows_discarded"], 0)

    def test_conflicting_contract_id_is_not_silently_merged(self):
        result = reconcile_floorsheet_rows([self.row(line=1), self.row(buyer="99", line=2)])
        self.assertEqual(result["counts"]["conflicting_duplicate"], 2)
        self.assertTrue(all(x["retained_for_review"] for x in result["rows"]))

    def test_invalid_amount_tolerance_is_rejected(self):
        for tolerance in (Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity")):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                reconcile_floorsheet_rows([self.row()], amount_tolerance=tolerance)

    def test_amount_mismatch_is_flagged(self):
        result = reconcile_floorsheet_rows([self.row(amount="999")])
        self.assertEqual(result["counts"]["amount_reconciliation_exception"], 1)
        self.assertTrue(result["rows"][0]["amount_reconciliation_exception"])

    def test_non_finite_decimals_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.row(amount=value)

    def test_missing_required_text_fields_are_rejected(self):
        row = {"trade_date":"2026-11-24","contract_id":None,"symbol":"NABIL",
               "buyer_broker_code":"11","seller_broker_code":"42",
               "quantity":"10","rate":"100","amount":"1000"}
        with self.assertRaisesRegex(ValueError, "nonblank strings"):
            FloorsheetContract.from_mapping(row, source_id="fixture",
                payload_sha256=self.digest, row_number=1)

    def test_invalid_iso_trade_date_is_rejected(self):
        row = {"trade_date":"not-a-date","contract_id":"C1","symbol":"NABIL",
               "buyer_broker_code":"11","seller_broker_code":"42",
               "quantity":"10","rate":"100","amount":"1000"}
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            FloorsheetContract.from_mapping(row, source_id="fixture",
                payload_sha256=self.digest, row_number=1)

    def test_non_string_identifiers_and_boolean_row_number_rejected(self):
        row = {"trade_date":"2026-11-24","contract_id":"C1","symbol":"NABIL",
               "buyer_broker_code":"11","seller_broker_code":"42",
               "quantity":"10","rate":"100","amount":"1000"}
        with self.assertRaisesRegex(ValueError, "nonblank strings"):
            FloorsheetContract.from_mapping({**row, "symbol": 123},
                source_id="fixture", payload_sha256=self.digest, row_number=1)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            FloorsheetContract.from_mapping(row, source_id="fixture",
                payload_sha256=self.digest, row_number=True)

    def test_lowercase_symbol_and_noncanonical_date_rejected(self):
        row = {"trade_date":"20261124","contract_id":"C1","symbol":"nabil",
               "buyer_broker_code":"11","seller_broker_code":"42",
               "quantity":"10","rate":"100","amount":"1000"}
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            FloorsheetContract.from_mapping(row, source_id="fixture",
                payload_sha256=self.digest, row_number=1)
        row["trade_date"] = "2026-11-24"
        with self.assertRaisesRegex(ValueError, "uppercase"):
            FloorsheetContract.from_mapping(row, source_id="fixture",
                payload_sha256=self.digest, row_number=1)

    def test_invalid_values_and_lineage_rejected(self):
        with self.assertRaises(ValueError):
            self.row(amount="-1")
        with self.assertRaises(ValueError):
            FloorsheetContract.from_mapping({"trade_date":"2026-11-24"},
                source_id="fixture", payload_sha256=self.digest, row_number=1)
        with self.assertRaises(ValueError):
            self.row(line=0)


if __name__ == "__main__":
    unittest.main()
