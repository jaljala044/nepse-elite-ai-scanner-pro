import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import main


class EvidenceStorageReadinessApiTests(unittest.TestCase):
    def test_endpoint_fails_closed_when_storage_is_unconfigured(self):
        with patch.dict("os.environ", {}, clear=True):
            result = main.evidence_storage_readiness()
        self.assertEqual(result["status"], "not_ready")
        self.assertFalse(result["production_eligible"])
        self.assertFalse(result["deployment_persistence_verified"])

    def test_endpoint_reports_operator_attested_volume_without_claiming_verified_durability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "volume"
            env = {
                "NEPSE_EVIDENCE_STORAGE_ROOT": str(root),
                "NEPSE_EVIDENCE_DATABASE": str(root / "catalog" / "evidence.duckdb"),
                "NEPSE_EVIDENCE_RAW_ROOT": str(root / "raw"),
                "NEPSE_EVIDENCE_PERSISTENT_VOLUME": "true",
            }
            with patch.dict("os.environ", env, clear=True):
                result = main.evidence_storage_readiness()
            self.assertEqual(result["status"], "configured_operator_attested")
            self.assertEqual(result["atomic_write_probe"], "passed")
            self.assertFalse(result["deployment_persistence_verified"])
            self.assertFalse(result["production_eligible"])

    def test_endpoint_rejects_paths_outside_storage_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "volume"
            env = {
                "NEPSE_EVIDENCE_STORAGE_ROOT": str(root),
                "NEPSE_EVIDENCE_DATABASE": str(Path(tmp) / "outside.duckdb"),
                "NEPSE_EVIDENCE_RAW_ROOT": str(root / "raw"),
                "NEPSE_EVIDENCE_PERSISTENT_VOLUME": "true",
            }
            with patch.dict("os.environ", env, clear=True):
                result = main.evidence_storage_readiness()
            self.assertEqual(result["status"], "not_ready")
            self.assertIn("database_and_raw_root_must_be_inside_storage_root", result["reasons"])

    def test_unattested_mount_does_not_run_write_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "volume"
            env = {
                "NEPSE_EVIDENCE_STORAGE_ROOT": str(root),
                "NEPSE_EVIDENCE_DATABASE": str(root / "catalog" / "evidence.duckdb"),
                "NEPSE_EVIDENCE_RAW_ROOT": str(root / "raw"),
                "NEPSE_EVIDENCE_PERSISTENT_VOLUME": "false",
            }
            with patch.dict("os.environ", env, clear=True):
                result = main.evidence_storage_readiness()
            self.assertEqual(result["status"], "not_ready")
            self.assertEqual(result["atomic_write_probe"], "not_run")
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
