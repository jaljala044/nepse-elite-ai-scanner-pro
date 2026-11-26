import unittest
from datetime import date
import tempfile
import json
from pathlib import Path

from app.scanner_eligibility import assess, load_reviewed_rows
from app.storage import DATA, IMPORTS, store_rows


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(date=date(2025, 1, 1), open=10, high=12, low=9, close=11, volume=100)
        self.record = dict(
            symbol="TEST", date="2025-01-01", open=10, high=12, low=9, close=11, volume=100,
            security_id="1001", instrument_type="equity", security_status="active",
            lifecycle_evidence_id="lifecycle-doc", session_status="verified_open",
            session_evidence_id="session-doc", source_id="sharehub", evidence_id="ohlcv-doc",
            source_payload_sha256="a" * 64, price_basis_reviewed=True,
            price_basis_status="verified_unadjusted_no_actions",
            corporate_action_status="clear", corporate_action_evidence_id="action-review",
            available_at="2025-01-01T12:00:00Z",
        )
        self.cutoff = "2025-01-02T00:00:00Z"
        self.key = ("TEST", "2025-01-01")

    def test_complete_evidence_passes_runtime_gate(self):
        self.assertEqual(assess("TEST", [self.row], self.cutoff, {self.key: self.record}), [])

    def test_missing_evidence_blocks_runtime_gate(self):
        cases = [
            ("instrument_type", "mutual_fund", "equity_lifecycle_unverified"),
            ("security_status", "suspended", "equity_lifecycle_unverified"),
            ("lifecycle_evidence_id", "", "equity_lifecycle_unverified"),
            ("security_id", "", "security_identity_unverified"),
            ("symbol", "OTHER", "security_identity_unverified"),
            ("session_status", "candidate", "session_unverified"),
            ("session_evidence_id", "", "session_unverified"),
            ("source_id", "unknown", "source_provenance_unverified"),
            ("evidence_id", "", "source_provenance_unverified"),
            ("source_payload_sha256", "not-a-digest", "source_provenance_unverified"),
            ("price_basis_reviewed", False, "price_basis_unverified"),
            ("price_basis_status", "unknown", "price_basis_unverified"),
            ("corporate_action_status", "unreviewed", "corporate_action_clearance_unverified"),
            ("corporate_action_evidence_id", "", "corporate_action_clearance_unverified"),
            ("available_at", "2025-01-03T00:00:00Z", "availability_unverified_or_future"),
            ("close", 10, "reviewed_values_mismatch"),
        ]
        for field, value, reason in cases:
            with self.subTest(field=field):
                record = dict(self.record, **{field: value})
                errors = assess("TEST", [self.row], self.cutoff, {self.key: record})
                self.assertTrue(any(reason in error for error in errors), errors)

    def test_missing_manifest_record_blocks(self):
        self.assertTrue(assess("TEST", [self.row], self.cutoff, {}))

    def test_loader_requires_all_stage1_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.json"
            record = dict(self.record, canonical_promotion_allowed=True)
            path.write_text(json.dumps({"schema_version": 1, "records": [record]}))
            self.assertEqual(len(load_reviewed_rows(path)), 1)
            for field, value in [
                ("security_id", ""), ("lifecycle_evidence_id", ""),
                ("session_evidence_id", ""), ("price_basis_reviewed", False),
                ("price_basis_status", "unknown"), ("corporate_action_status", "unreviewed"),
                ("corporate_action_evidence_id", ""), ("source_payload_sha256", "bad"),
            ]:
                with self.subTest(field=field):
                    invalid = dict(record, **{field: value})
                    path.write_text(json.dumps({"schema_version": 1, "records": [invalid]}))
                    with self.assertRaisesRegex(ValueError, "incomplete canonical evidence"):
                        load_reviewed_rows(path)

    def test_loader_rejects_duplicate_canonical_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review.json"
            record = dict(self.record, canonical_promotion_allowed=True)
            path.write_text(json.dumps({"schema_version": 1, "records": [record, record]}))
            with self.assertRaisesRegex(ValueError, "duplicate canonical key"):
                load_reviewed_rows(path)

    def test_ingest(self):
        original = dict(DATA)
        imports = list(IMPORTS)
        try:
            DATA.clear()
            header = "symbol,date,open,high,low,close,volume\n"
            for data in ["TEST,2025-01-01,nan,12,9,11,100", "TEST,2025-01-01,10,12,9,11,1.5"]:
                with self.assertRaises(ValueError):
                    store_rows(header + data, "fixture")
            store_rows(header + "TEST,2025-01-01,10,12,9,11,100", "fixture")
            with self.assertRaises(ValueError):
                store_rows(header + "TEST,2025-01-01,10,12,9,10,100", "fixture")
            self.assertEqual(DATA["TEST"][0]["close"], 11)
        finally:
            DATA.clear()
            DATA.update(original)
            IMPORTS[:] = imports


if __name__ == "__main__":
    unittest.main()
