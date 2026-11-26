import tempfile
import unittest
from pathlib import Path

from app.evidence_storage_config import inspect_evidence_storage


class EvidenceStorageConfigTests(unittest.TestCase):
    def configured(self, root):
        root = Path(root)
        return {
            "NEPSE_EVIDENCE_STORAGE_ROOT": str(root),
            "NEPSE_EVIDENCE_DATABASE": str(root / "catalog" / "evidence.duckdb"),
            "NEPSE_EVIDENCE_RAW_ROOT": str(root / "raw"),
            "NEPSE_EVIDENCE_PERSISTENT_VOLUME": "true",
        }

    def test_missing_configuration_fails_closed(self):
        result = inspect_evidence_storage({})
        self.assertEqual(result["status"], "not_ready")
        self.assertFalse(result["production_eligible"])
        self.assertIn("persistent_volume_not_operator_attested", result["reasons"])

    def test_configured_attested_volume_passes_filesystem_probe_but_not_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect_evidence_storage(self.configured(Path(tmp) / "volume"))
            self.assertEqual(result["status"], "configured_operator_attested")
            self.assertEqual(result["atomic_write_probe"], "passed")
            self.assertTrue(result["same_filesystem"])
            self.assertFalse(result["deployment_persistence_verified"])
            self.assertFalse(result["production_eligible"])

    def test_unattested_volume_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self.configured(Path(tmp) / "volume")
            env["NEPSE_EVIDENCE_PERSISTENT_VOLUME"] = "false"
            result = inspect_evidence_storage(env)
            self.assertEqual(result["status"], "not_ready")
            self.assertIn("persistent_volume_not_operator_attested", result["reasons"])

    def test_database_outside_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self.configured(Path(tmp) / "volume")
            env["NEPSE_EVIDENCE_DATABASE"] = str(Path(tmp) / "outside.duckdb")
            result = inspect_evidence_storage(env)
            self.assertIn("database_and_raw_root_must_be_inside_storage_root", result["reasons"])
            self.assertEqual(result["atomic_write_probe"], "not_run")

    def test_raw_objects_outside_root_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self.configured(Path(tmp) / "volume")
            env["NEPSE_EVIDENCE_RAW_ROOT"] = str(Path(tmp) / "outside")
            result = inspect_evidence_storage(env)
            self.assertIn("database_and_raw_root_must_be_inside_storage_root", result["reasons"])

    def test_failed_volume_attestation_never_enables_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect_evidence_storage(self.configured(Path(tmp) / "volume"))
            self.assertFalse(result["production_eligible"])
            self.assertFalse(result["deployment_persistence_verified"])


if __name__ == "__main__":
    unittest.main()
