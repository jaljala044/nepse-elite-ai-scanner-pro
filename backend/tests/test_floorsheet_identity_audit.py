from decimal import Decimal
import unittest

from app.floorsheet_contract import FloorsheetContract
from app.floorsheet_identity_audit import audit_contract_date_identity


HASH = "b" * 64


def row(source, contract, trade_date, symbol="AAA"):
    return FloorsheetContract(
        source_id=source, source_payload_sha256=HASH, source_row_number=2,
        trade_date=trade_date, contract_id=contract, symbol=symbol,
        buyer_broker_code="11", seller_broker_code="22",
        quantity=Decimal("10"), rate=Decimal("10"), amount=Decimal("100"),
    )


class FloorsheetIdentityAuditTests(unittest.TestCase):
    def test_cross_source_date_disagreement_is_reported(self):
        result = audit_contract_date_identity(
            [row("left", "C100", "2026-11-24")],
            [row("right", "C100", "2026-11-25")],
        )
        self.assertEqual(len(result["cross_source_date_disagreements"]), 1)
        self.assertEqual(
            result["cross_source_date_disagreements"][0]["left_dates"],
            ["2026-11-24"],
        )
        self.assertFalse(result["coverage_admission_allowed"])

    def test_same_source_contract_reused_on_multiple_dates_is_reported(self):
        result = audit_contract_date_identity(
            [
                row("left", "C100", "2026-11-24"),
                row("left", "C100", "2026-11-25"),
            ],
            [row("right", "C200", "2026-11-24")],
        )
        self.assertEqual(
            result["left_within_source_date_collisions"][0]["dates"],
            ["2026-11-24", "2026-11-25"],
        )

    def test_eight_digit_date_prefix_is_diagnostic_not_authoritative(self):
        result = audit_contract_date_identity(
            [row("left", "202611240001", "2026-11-25")],
            [row("right", "OTHER", "2026-11-25")],
        )
        finding = result["contract_prefix_date_findings"][0]
        self.assertEqual(finding["diagnostic_prefix_date"], "2026-11-24")
        self.assertFalse(finding["prefix_semantics_verified"])

    def test_non_date_prefix_and_invalid_date_prefix_are_ignored(self):
        result = audit_contract_date_identity(
            [row("left", "202613990001", "2026-11-24")],
            [row("right", "ABC001", "2026-11-24")],
        )
        self.assertEqual(result["contract_prefix_date_findings"], [])

    def test_empty_or_untyped_inputs_rejected(self):
        with self.assertRaisesRegex(ValueError, "source must contain"):
            audit_contract_date_identity([], [row("right", "C1", "2026-11-24")])
        with self.assertRaisesRegex(ValueError, "FloorsheetContract"):
            audit_contract_date_identity(
                [object()], [row("right", "C1", "2026-11-24")]
            )


if __name__ == "__main__":
    unittest.main()
