import hashlib
import unittest
from app.p4_30_corporate_action_csv_intake import load_corporate_action_csv

HEADER="action_id,symbol,security_id,action_type,announced_at,available_at,ex_date,status,publisher_id,source_id,source_tier,evidence_sha256,reviewer_id,review_status,adjustment_factor,factor_methodology_id\n"
ROW="CA1,ABC,SEC1,bonus,2026-01-01T09:00:00+05:45,2026-01-01T10:00:00+05:45,2026-01-10,confirmed,nepse,N1,primary_nepse_or_cdsc,"+"a"*64+",reviewer1,approved,1.1,policy-v1\n"
class CorporateActionCsvIntakeTests(unittest.TestCase):
    def load(self, raw, **kwargs):
        base=dict(raw_bytes=raw,publisher_id="nepse",source_id="N1",source_tier="primary_nepse_or_cdsc",retrieved_at="2026-01-02T10:00:00+05:45",decision_cutoff="2026-11-28T12:00:00+05:45")
        base.update(kwargs)
        return load_corporate_action_csv(**base)
    def test_valid_csv_preserves_hash_and_provenance(self):
        raw=(HEADER+ROW).encode()
        result=self.load(raw)
        self.assertEqual(result["status"],"CSV_INTAKE_VERIFIED")
        self.assertEqual(result["raw_file_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertFalse(result["price_adjustment_allowed"])
    def test_missing_required_column_blocks(self):
        result=self.load(b"action_id,symbol\nCA1,ABC\n")
        self.assertEqual(result["status"],"CSV_INTAKE_BLOCKED")
        self.assertIn("required_columns_missing",result["errors"][0]["reason"])
    def test_manifest_publisher_mismatch_blocks_row(self):
        result=self.load((HEADER+ROW.replace(",nepse,N1,",",cdsc,C1,")).encode())
        self.assertEqual(result["status"],"CSV_INTAKE_BLOCKED")
    def test_future_retrieval_blocks(self):
        result=self.load((HEADER+ROW).encode(),retrieved_at="2026-12-01T00:00:00+05:45")
        self.assertEqual(result["status"],"CSV_INTAKE_BLOCKED")
    def test_duplicate_action_source_rows_block(self):
        result=self.load((HEADER+ROW+ROW).encode())
        self.assertEqual(result["status"],"CSV_INTAKE_BLOCKED")
    def test_bad_encoding_blocks(self):
        result=self.load(b"\xff\xfe")
        self.assertEqual(result["status"],"CSV_INTAKE_BLOCKED")
if __name__ == "__main__":
    unittest.main()
