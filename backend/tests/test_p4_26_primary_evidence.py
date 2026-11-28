import hashlib
import tempfile
import unittest
from pathlib import Path

from app.p4_26_primary_evidence import (
    validate_corporate_action_ledger,
    validate_predecessor_identity_evidence,
    validate_primary_notice_archive,
)


class P426PrimaryEvidenceTests(unittest.TestCase):
    cutoff = "2026-11-28T12:00:00+05:45"

    def write_pdf(self, root):
        path = root / "notices" / "notice.pdf"
        path.parent.mkdir(parents=True)
        raw = b"%PDF-1.4\n" + b"x" * 200
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def doc_row(self, digest):
        return {"event_id": "EVT1", "source_url": "https://nepalstock.com.np/api/nots/security/file.pdf",
                "http_status": 200, "content_type": "application/pdf",
                "retrieved_at": "2026-11-20T10:00:00+05:45",
                "available_at": "2026-11-19T10:00:00+05:45", "archive_path": "notices/notice.pdf",
                "sha256": digest, "publisher_id": "nepse", "document_title": "Listing notice"}

    def test_primary_notice_archive_verifies_raw_pdf_hash_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, digest = self.write_pdf(root)
            report = validate_primary_notice_archive(entries=[self.doc_row(digest)], archive_root=root,
                decision_cutoff=self.cutoff, required_event_ids=["EVT1"])
        self.assertEqual(report["status"], "PRIMARY_NOTICE_ARCHIVE_VERIFIED")
        self.assertEqual(report["verified_document_count"], 1)

    def test_missing_or_tampered_notice_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path, digest = self.write_pdf(root)
            path.write_bytes(b"%PDF-1.4 tampered")
            report = validate_primary_notice_archive(entries=[self.doc_row(digest)], archive_root=root,
                decision_cutoff=self.cutoff, required_event_ids=["EVT1"])
        self.assertEqual(report["status"], "PRIMARY_NOTICE_ARCHIVE_BLOCKED")
        self.assertFalse(report["historical_identity_promotion_allowed"])

    def test_archive_path_traversal_and_non_primary_host_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, digest = self.write_pdf(root)
            row = self.doc_row(digest)
            row["archive_path"] = "../notice.pdf"
            report = validate_primary_notice_archive(entries=[row], archive_root=root,
                decision_cutoff=self.cutoff, required_event_ids=["EVT1"])
        self.assertEqual(report["status"], "PRIMARY_NOTICE_ARCHIVE_BLOCKED")
        self.assertIn("unsafe_archive_relative_path", [x["reason"] for x in report["errors"]])

    def test_predecessor_identity_requires_archived_primary_document_and_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, digest = self.write_pdf(root)
            archive = validate_primary_notice_archive(entries=[self.doc_row(digest)], archive_root=root,
                decision_cutoff=self.cutoff, required_event_ids=["EVT1"])
        row = {"predecessor_symbol": "OLD", "predecessor_security_id": "10",
               "successor_symbol": "NEW", "successor_security_id": "20",
               "effective_from": "2024-01-01", "available_at": "2024-01-01T10:00:00+05:45",
               "event_id": "EVT1", "evidence_tier": "primary_nepse_or_cdsc",
               "publisher_id": "nepse", "independent_review_status": "approved", "reviewer_id": "reviewer-1"}
        report = validate_predecessor_identity_evidence(records=[row], required_symbols=["OLD"],
            archive_report=archive, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "PREDECESSOR_IDENTITY_REVIEWED")

    def test_unresolved_predecessor_symbols_remain_blocked(self):
        report = validate_predecessor_identity_evidence(records=[], required_symbols=["BPW", "JALPA"],
            archive_report={"verified_documents": []}, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "PREDECESSOR_IDENTITY_BLOCKED")
        self.assertEqual(report["missing_symbols"], ["BPW", "JALPA"])

    def action_row(self, publisher, tier, digest, **extra):
        row = {"action_id": "ACT1", "symbol": "ABC", "security_id": "10",
               "action_type": "bonus", "announced_at": "2024-01-01T10:00:00+05:45",
               "available_at": "2024-01-01T10:00:00+05:45", "ex_date": "2024-02-01",
               "publisher_id": publisher, "source_id": publisher, "source_tier": tier,
               "evidence_sha256": digest, "status": "confirmed", "adjustment_factor": "0.9",
               "factor_methodology_id": "approved-bonus-factor-v1",
               "independent_review_status": "approved", "reviewer_id": "reviewer-1"}
        row.update(extra)
        return row

    def test_corporate_action_needs_primary_and_independent_second_publisher(self):
        rows = [self.action_row("nepse", "primary_nepse_or_cdsc", "a" * 64)]
        report = validate_corporate_action_ledger(records=rows, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "CORPORATE_ACTION_LEDGER_BLOCKED")

    def test_corporate_action_disagreement_blocks_event(self):
        rows = [self.action_row("nepse", "primary_nepse_or_cdsc", "a" * 64),
                self.action_row("secondary", "independent_secondary", "b" * 64, adjustment_factor="0.8")]
        report = validate_corporate_action_ledger(records=rows, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "CORPORATE_ACTION_LEDGER_BLOCKED")
        self.assertTrue(any(x["reason"] == "publisher_action_assertions_conflict" for x in report["errors"]))

    def test_future_available_action_is_rejected(self):
        rows = [self.action_row("nepse", "primary_nepse_or_cdsc", "a" * 64,
                                available_at="2026-12-01T00:00:00+05:45"),
                self.action_row("secondary", "independent_secondary", "b" * 64)]
        report = validate_corporate_action_ledger(records=rows, decision_cutoff=self.cutoff)
        self.assertEqual(report["status"], "CORPORATE_ACTION_LEDGER_BLOCKED")


if __name__ == "__main__":
    unittest.main()
