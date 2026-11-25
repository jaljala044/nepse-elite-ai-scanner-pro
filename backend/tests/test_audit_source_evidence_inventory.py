import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_source_evidence_inventory import audit_source_evidence_inventory


class SourceEvidenceInventoryTests(unittest.TestCase):
    def test_raw_object_hash_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            obj = raw / "source.csv"
            obj.write_bytes(b"symbol,date\nAAA,2026-01-01\n")
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps({
                "source_id":"source-a","path":"source.csv","local_path":str(obj),
                "sha256":hashlib.sha256(obj.read_bytes()).hexdigest()
            }) + "\n", encoding="utf-8")
            report = audit_source_evidence_inventory([manifest], raw)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["verified_raw_object_count"], 1)
            self.assertFalse(report["canonical_promotion_allowed"])

    def test_missing_raw_object_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps({
                "source_id":"source-a","path":"missing.csv","sha256":"a"*64
            }) + "\n", encoding="utf-8")
            report = audit_source_evidence_inventory([manifest], root)
            self.assertEqual(report["errors"][0]["status"], "missing_raw_object")

    def test_hash_mismatch_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            obj = root / "source.csv"
            obj.write_bytes(b"changed")
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps({
                "source_id":"source-a","path":"source.csv","sha256":"a"*64
            }) + "\n", encoding="utf-8")
            report = audit_source_evidence_inventory([manifest], root)
            self.assertEqual(report["errors"][0]["status"], "sha256_mismatch")

    def test_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "outside.csv"
            manifest = root / "manifest.jsonl"
            manifest.write_text(json.dumps({
                "source_id":"source-a","path":"../outside.csv",
                "local_path":str(outside),"sha256":"a"*64
            }) + "\n", encoding="utf-8")
            report = audit_source_evidence_inventory([manifest], root)
            self.assertEqual(report["errors"][0]["status"], "invalid_manifest_row")


if __name__ == "__main__":
    unittest.main()
