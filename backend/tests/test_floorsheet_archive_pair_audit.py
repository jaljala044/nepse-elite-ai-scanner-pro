import hashlib
import unittest

from app.floorsheet_archive_pair_audit import audit_floorsheet_archive_pair
from app.floorsheet_csv_adapter import CsvFloorsheetMapping


LEFT = CsvFloorsheetMapping(columns={
    "trade_date": "date", "contract_id": "contract_no", "symbol": "symbol",
    "buyer_broker_code": "buyer", "seller_broker_code": "seller",
    "quantity": "quantity", "rate": "rate", "amount": "amount",
})
RIGHT = CsvFloorsheetMapping(columns={
    "trade_date": "date", "contract_id": "transaction", "symbol": "symbol",
    "buyer_broker_code": "buyer", "seller_broker_code": "seller",
    "quantity": "quantity", "rate": "rate", "amount": "amount",
})


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


class FloorsheetArchivePairAuditTests(unittest.TestCase):
    def setUp(self):
        self.left = (
            b"date,contract_no,symbol,buyer,seller,quantity,rate,amount\n"
            b"2026-11-24,C1,AAA,11,22,10,10,100\n"
            b"2026-11-24,202611240002,BBB,12,23,2,20,40\n"
        )
        self.right = (
            b"date,transaction,symbol,buyer,seller,quantity,rate,amount\n"
            b"2026-11-24,C1,AAA,11,22,10,10,100\n"
            b"2026-11-25,202611240002,BBB,12,23,2,20,40\n"
        )

    def run_audit(self, left=None, right=None):
        left = self.left if left is None else left
        right = self.right if right is None else right
        return audit_floorsheet_archive_pair(
            left, right, left_source_id="left@pin", right_source_id="right@pin",
            left_expected_sha256=digest(left), right_expected_sha256=digest(right),
            left_mapping=LEFT, right_mapping=RIGHT,
        )

    def test_hash_checked_parse_comparison_and_identity_findings(self):
        result = self.run_audit()
        self.assertEqual(result["audit_status"], "review_only_complete_parse")
        self.assertEqual(result["comparison"]["exact_shared_contract_count"], 1)
        self.assertEqual(len(result["identity_audit"]["cross_source_date_disagreements"]), 1)
        self.assertEqual(len(result["identity_audit"]["contract_prefix_date_findings"]), 1)
        self.assertFalse(result["source_rights_verified"])
        self.assertFalse(result["canonical_promotion_allowed"])

    def test_hash_mismatch_rejected_before_parse(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            audit_floorsheet_archive_pair(
                self.left, self.right, left_source_id="left", right_source_id="right",
                left_expected_sha256="0" * 64, right_expected_sha256=digest(self.right),
                left_mapping=LEFT, right_mapping=RIGHT,
            )

    def test_rejected_rows_are_visible_and_lower_audit_status(self):
        malformed = self.left + b"2026-11-24,C3,CCC,11,22,0,10,0\n"
        result = self.run_audit(left=malformed)
        self.assertEqual(result["audit_status"], "review_only_with_rejected_rows")
        self.assertEqual(result["left_file"]["rejected_rows"], 1)
        self.assertEqual(len(result["left_file"]["rejected_row_ledger"]), 1)
        self.assertEqual(result["left_file"]["rejected_row_ledger"][0]["source_row_number"], 4)


    def test_no_valid_rows_on_one_side_is_reported_without_crashing(self):
        invalid = (
            b"date,contract_no,symbol,buyer,seller,quantity,rate,amount\n"
            b"2026-11-24,C3,CCC,11,22,0,10,0\n"
        )
        result = self.run_audit(left=invalid)
        self.assertEqual(result["left_file"]["parsed_rows"], 0)
        self.assertEqual(
            result["comparison"]["comparison_status"],
            "not_run_no_parsed_rows_on_one_or_both_sides",
        )
        self.assertFalse(result["canonical_promotion_allowed"])


    def test_duplicate_contract_keys_are_retained_and_block_comparison(self):
        duplicate_left = self.left + (
            b"2026-11-24,C1,AAA,11,22,10,10,100\n"
        )
        result = self.run_audit(left=duplicate_left)
        self.assertEqual(
            result["comparison"]["comparison_status"],
            "not_run_duplicate_keys_require_adjudication",
        )
        self.assertEqual(
            result["left_file"]["row_reconciliation"]["counts"]["exact_duplicate"],
            2,
        )
        self.assertEqual(
            len(result["left_file"]["row_reconciliation"]["review_rows"]),
            2,
        )


    def test_amount_arithmetic_exceptions_block_cross_source_comparison(self):
        bad_amount = (
            b"date,contract_no,symbol,buyer,seller,quantity,rate,amount\n"
            b"2026-11-24,C1,AAA,11,22,10,10,101\n"
        )
        result = self.run_audit(left=bad_amount)
        self.assertEqual(
            result["comparison"]["comparison_status"],
            "not_run_amount_reconciliation_exceptions_require_adjudication",
        )
        self.assertEqual(
            result["left_file"]["row_reconciliation"]["counts"]["amount_reconciliation_exception"],
            1,
        )

    def test_empty_payload_and_invalid_digest_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-empty bytes"):
            self.run_audit(left=b"")
        with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
            audit_floorsheet_archive_pair(
                self.left, self.right, left_source_id="left", right_source_id="right",
                left_expected_sha256="bad", right_expected_sha256=digest(self.right),
                left_mapping=LEFT, right_mapping=RIGHT,
            )


if __name__ == "__main__":
    unittest.main()
