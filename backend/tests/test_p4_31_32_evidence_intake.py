import unittest
from app.p4_31_primary_document_intake import validate_primary_document
from app.p4_32_action_batch_intake import build_action_batch_report

class PrimaryDocumentIntakeTests(unittest.TestCase):
    def base(self, **kw):
        x=dict(raw_bytes=b"%PDF-1.7\nsynthetic",source_url="https://www.nepalstock.com/notices/test.pdf",
          publisher_id="nepse",retrieved_at="2026-01-02T10:00:00+05:45",
          available_at="2026-01-01T10:00:00+05:45",decision_cutoff="2026-11-28T12:00:00+05:45",
          archive_path="raw/nepse/notice.pdf",event_id="LIST-1")
        x.update(kw); return validate_primary_document(**x)
    def test_valid_pdf_bytes_hashes_but_does_not_admit(self):
        r=self.base()
        self.assertEqual(r["status"],"PRIMARY_DOCUMENT_BYTES_VERIFIED")
        self.assertFalse(r["event_admission_allowed"])
        self.assertFalse(r["publisher_authenticity_verified"])
    def test_bad_signature_blocks(self):
        self.assertEqual(self.base(raw_bytes=b"not a pdf")["status"],"BLOCKED")
    def test_unapproved_host_blocks(self):
        self.assertEqual(self.base(source_url="https://example.com/test.pdf")["status"],"BLOCKED")
    def test_path_traversal_blocks(self):
        self.assertEqual(self.base(archive_path="../notice.pdf")["status"],"BLOCKED")
    def test_future_document_blocks(self):
        self.assertEqual(self.base(available_at="2026-12-01T00:00:00+05:45")["status"],"BLOCKED")
    def test_expected_hash_mismatch_blocks(self):
        self.assertEqual(self.base(expected_sha256="0"*64)["status"],"BLOCKED")

class ActionBatchIntakeTests(unittest.TestCase):
    def row(self,publisher,tier,factor="1.1"):
        return {"action_id":"CA1","publisher_id":publisher,"source_tier":tier,"symbol":"ABC",
          "security_id":"SEC1","action_type":"bonus","announced_at":"2026-01-01T09:00:00+05:45",
          "available_at":"2026-01-01T10:00:00+05:45","ex_date":"2026-01-10",
          "status":"confirmed","adjustment_factor":factor,"factor_methodology_id":"policy1"}
    def test_two_publishers_and_primary_review_ready_not_admitted(self):
        rows=[self.row("nepse","primary_nepse_or_cdsc"),self.row("sharesansar","independent_secondary")]
        result=build_action_batch_report(source_files=[{"source_id":"N","intake_result":{"status":"CSV_INTAKE_VERIFIED","records":[rows[0]]}},{"source_id":"S","intake_result":{"status":"CSV_INTAKE_VERIFIED","records":[rows[1]]}}],required_action_ids=["CA1"])
        self.assertEqual(result["status"],"REVIEW_READY")
        self.assertFalse(result["ohlcv_mutation_allowed"])
    def test_missing_primary_blocks(self):
        row=self.row("sharesansar","independent_secondary")
        result=build_action_batch_report(source_files=[{"source_id":"S","intake_result":{"status":"CSV_INTAKE_VERIFIED","records":[row]}}],required_action_ids=["CA1"])
        self.assertEqual(result["status"],"BLOCKED")
    def test_fact_conflict_blocks(self):
        a=self.row("nepse","primary_nepse_or_cdsc")
        b=self.row("sharesansar","independent_secondary","1.2")
        result=build_action_batch_report(source_files=[{"intake_result":{"status":"CSV_INTAKE_VERIFIED","records":[a,b]}}],required_action_ids=["CA1"])
        self.assertEqual(result["events"][0]["status"],"BLOCKED")
    def test_unverified_csv_file_blocks(self):
        result=build_action_batch_report(source_files=[{"source_id":"bad","intake_result":{"status":"CSV_INTAKE_BLOCKED","records":[]}}],required_action_ids=["CA1"])
        self.assertEqual(result["status"],"BLOCKED")
if __name__=="__main__": unittest.main()
