import hashlib, tempfile, unittest
from pathlib import Path
from app.p4_28_evidence_package import run_historical_evidence_package, verify_raw_evidence_archive

class EvidencePackageTests(unittest.TestCase):
 cutoff="2026-11-28T12:00:00+05:45"
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
  self.raw=b"official notice or source record bytes"; (self.root/"notice.bin").write_bytes(self.raw)
  self.digest=hashlib.sha256(self.raw).hexdigest()
 def tearDown(self): self.temp.cleanup()
 def artifact(self,**extra):
  row={"artifact_id":"NEPSE-LIST-1","source_url":"https://www.nepalstock.com/listing/notice","publisher_id":"nepse","source_tier":"primary_nepse_or_cdsc","archive_path":"notice.bin","sha256":self.digest,"media_type":"application/pdf","event_ids":["LIST1"],"retrieved_at":"2024-01-01T10:00:00+05:45","available_at":"2024-01-01T09:00:00+05:45"}
  row.update(extra); return row
 def test_archive_hash_and_provenance_verified(self):
  r=verify_raw_evidence_archive(artifacts=[self.artifact()],archive_root=self.root,decision_cutoff=self.cutoff,required_artifact_ids=["NEPSE-LIST-1"])
  self.assertEqual(r["status"],"RAW_EVIDENCE_ARCHIVE_VERIFIED"); self.assertEqual(r["artifact_count"],1)
 def test_hash_mismatch_blocks(self):
  r=verify_raw_evidence_archive(artifacts=[self.artifact(sha256="0"*64)],archive_root=self.root,decision_cutoff=self.cutoff,required_artifact_ids=["NEPSE-LIST-1"])
  self.assertEqual(r["status"],"RAW_EVIDENCE_ARCHIVE_BLOCKED")
 def test_unapproved_host_and_path_traversal_block(self):
  rows=[self.artifact(source_url="https://example.com/x"),self.artifact(artifact_id="BADPATH",archive_path="../notice.bin")]
  r=verify_raw_evidence_archive(artifacts=rows,archive_root=self.root,decision_cutoff=self.cutoff,required_artifact_ids=["NEPSE-LIST-1"])
  self.assertEqual(r["status"],"RAW_EVIDENCE_ARCHIVE_BLOCKED"); self.assertEqual(len(r["errors"]),3); self.assertIn("required_raw_artifacts_missing",{e.get("reason") for e in r["errors"]})
 def test_future_evidence_blocks(self):
  r=verify_raw_evidence_archive(artifacts=[self.artifact(available_at="2026-12-01T00:00:00+05:45")],archive_root=self.root,decision_cutoff=self.cutoff,required_artifact_ids=["NEPSE-LIST-1"])
  self.assertEqual(r["status"],"RAW_EVIDENCE_ARCHIVE_BLOCKED")
 def test_missing_artifact_blocks(self):
  r=verify_raw_evidence_archive(artifacts=[],archive_root=self.root,decision_cutoff=self.cutoff,required_artifact_ids=["MISSING"])
  self.assertEqual(r["missing_artifact_ids"],["MISSING"])
 def test_package_schema_and_cutoff_are_enforced(self):
  r=run_historical_evidence_package(package={"package_id":"P1","schema_version":"2.0","created_at":"2026-01-01T00:00:00+05:45"},archive_root=self.root,decision_cutoff=self.cutoff)
  self.assertEqual(r["status"],"EVIDENCE_PACKAGE_BLOCKED"); self.assertFalse(r["historical_admission_allowed"])
 def test_package_does_not_claim_readiness_without_required_evidence(self):
  package={"package_id":"PILOT-001","schema_version":"1.0","created_at":"2026-01-01T00:00:00+05:45","artifacts":[self.artifact()],"required_artifact_ids":["NEPSE-LIST-1"],"primary_notice_entries":[],"required_primary_event_ids":["LIST1"],"identity_records":[],"required_identity_symbols":["BENH"],"corporate_action_records":[],"required_action_ids":["CA-001"]}
  r=run_historical_evidence_package(package=package,archive_root=self.root,decision_cutoff=self.cutoff)
  self.assertEqual(r["status"],"EVIDENCE_PACKAGE_BLOCKED"); self.assertEqual(r["missing_required_action_ids"],["CA-001"]); self.assertFalse(r["price_adjustment_admission_allowed"])

if __name__=="__main__": unittest.main()
