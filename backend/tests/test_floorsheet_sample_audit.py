import hashlib
import unittest
from decimal import Decimal

from app.floorsheet_contract import FloorsheetContract, reconcile_floorsheet_rows
from app.floorsheet_sample_audit import build_floorsheet_sample_acceptance_report


class FloorsheetSampleAuditTests(unittest.TestCase):
    def setUp(self):
        self.payload_hash = hashlib.sha256(b"sample").hexdigest()
        self.row = FloorsheetContract(
            source_id="sample-source",
            source_payload_sha256=self.payload_hash,
            source_row_number=2,
            trade_date="2026-11-24",
            contract_id="C-1",
            symbol="NABIL",
            buyer_broker_code="11",
            seller_broker_code="42",
            quantity=Decimal("10"),
            rate=Decimal("100"),
            amount=Decimal("1000"),
        )
        self.parsed = {
            "source_id": "sample-source",
            "source_payload_sha256": self.payload_hash,
            "input_data_rows": 1,
            "parsed_rows": 1,
            "rows": [self.row],
            "errors": [],
        }
        self.reconciled = reconcile_floorsheet_rows([self.row])

    def test_clean_sample_only_passes_quality_gate_after_mapping_and_calendar_review(self):
        result = build_floorsheet_sample_acceptance_report(
            self.parsed, self.reconciled, mapping_reviewed=True,
            verified_session_dates=["2026-11-24"],
        )
        self.assertEqual(result["sample_quality_gate"], "passed_for_rights_review")
        self.assertFalse(result["promotion_allowed"])
        self.assertFalse(result["training_eligible"])
        self.assertEqual(result["unique_symbol_count"], 1)
        self.assertEqual(result["unique_broker_code_count"], 2)
        self.assertEqual(result["total_amount"], "1000")

    def test_mapping_not_reviewed_keeps_sample_in_review(self):
        result = build_floorsheet_sample_acceptance_report(
            self.parsed, self.reconciled, verified_session_dates=["2026-11-24"]
        )
        self.assertEqual(result["sample_quality_gate"], "review_required")

    def test_unverified_calendar_date_is_exposed(self):
        result = build_floorsheet_sample_acceptance_report(
            self.parsed, self.reconciled, mapping_reviewed=True
        )
        self.assertEqual(result["calendar_unverified_dates"], ["2026-11-24"])
        self.assertEqual(result["sample_quality_gate"], "review_required")

    def test_rejected_rows_affect_ratio_and_gate(self):
        parsed = dict(self.parsed)
        parsed["input_data_rows"] = 2
        parsed["errors"] = [{"source_row_number": 3, "error": "bad row", "raw_source_row": {"bad": "row"}}]
        result = build_floorsheet_sample_acceptance_report(
            parsed, self.reconciled, mapping_reviewed=True,
            verified_session_dates=["2026-11-24"],
        )
        self.assertEqual(result["rejected_row_ratio"], 0.5)
        self.assertEqual(result["sample_quality_gate"], "review_required")

    def test_tampered_reconciliation_rows_rejected(self):
        altered = dict(self.reconciled)
        altered["rows"] = [dict(self.reconciled["rows"][0], amount_reconciliation_exception=True)]
        with self.assertRaisesRegex(ValueError, "recomputed source-row evidence"):
            build_floorsheet_sample_acceptance_report(self.parsed, altered)

    def test_rejected_row_without_raw_evidence_rejected(self):
        parsed = dict(self.parsed)
        parsed["input_data_rows"] = 2
        parsed["errors"] = [{"source_row_number": 3, "error": "bad row"}]
        with self.assertRaisesRegex(ValueError, "raw source row"):
            build_floorsheet_sample_acceptance_report(parsed, self.reconciled)

    def test_duplicate_verified_session_dates_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be unique"):
            build_floorsheet_sample_acceptance_report(
                self.parsed, self.reconciled, verified_session_dates=["2026-11-24", "2026-11-24"]
            )

    def test_source_lineage_mismatch_rejected(self):
        parsed = dict(self.parsed)
        parsed["source_id"] = "different-source"
        with self.assertRaisesRegex(ValueError, "source lineage"):
            build_floorsheet_sample_acceptance_report(parsed, self.reconciled)

    def test_non_list_verified_dates_rejected(self):
        with self.assertRaisesRegex(ValueError, "must be a list"):
            build_floorsheet_sample_acceptance_report(
                self.parsed, self.reconciled, verified_session_dates=("2026-11-24",)
            )

    def test_invalid_verified_calendar_date_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid calendar dates"):
            build_floorsheet_sample_acceptance_report(
                self.parsed, self.reconciled, verified_session_dates=["2026-99-99"]
            )


if __name__ == "__main__":
    unittest.main()
