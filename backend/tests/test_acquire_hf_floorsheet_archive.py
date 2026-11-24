import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from acquire_hf_floorsheet_archive import dated_file, enumerate_files, lfs_sha256, verify_file


class HuggingFaceFloorsheetArchiveTests(unittest.TestCase):
    def test_accepts_compressed_and_plain_csv_dates(self):
        self.assertEqual(dated_file("floorsheet/2024-03-18.csv.gz"), "2024-03-18")
        self.assertEqual(dated_file("floorsheet/2026-11-24.csv"), "2026-11-24")

    def test_rejects_invalid_or_undated_paths(self):
        self.assertIsNone(dated_file("floorsheet/2024-02-30.csv.gz"))
        self.assertIsNone(dated_file("floorsheet/latest.csv.gz"))

    def test_reads_lfs_sha256_from_metadata(self):
        self.assertEqual(lfs_sha256({"lfs": {"sha256": "AB" * 32}}), "ab" * 32)
        self.assertIsNone(lfs_sha256({"lfs": None}))

    def test_enumeration_requests_expanded_metadata_and_pins_revision(self):
        digest = "ab" * 32
        api = SimpleNamespace(
            dataset_info=lambda *args, **kwargs: SimpleNamespace(sha="pinned-commit"),
            list_repo_tree=lambda *args, **kwargs: [SimpleNamespace(
                path="floorsheet/2024-03-18.csv.gz", size=123, blob_id="blob-1",
                lfs=SimpleNamespace(sha256=digest), xet_hash="xet-1")],
        )
        with patch("acquire_hf_floorsheet_archive.HfApi", return_value=api):
            revision, rows = enumerate_files("owner/data", "floorsheet", "main")
        self.assertEqual(revision, "pinned-commit")
        self.assertEqual(rows[0]["lfs_sha256"], digest)
        self.assertEqual(rows[0]["size_bytes"], 123)
        self.assertEqual(rows[0]["xet_hash"], "xet-1")

    def test_enumeration_fails_closed_when_expanded_size_missing(self):
        api = SimpleNamespace(
            dataset_info=lambda *args, **kwargs: SimpleNamespace(sha="pinned-commit"),
            list_repo_tree=lambda *args, **kwargs: [SimpleNamespace(
                path="floorsheet/2024-03-18.csv.gz", size=None, blob_id="blob-1")],
        )
        with patch("acquire_hf_floorsheet_archive.HfApi", return_value=api):
            with self.assertRaisesRegex(ValueError, "expanded file size"):
                enumerate_files("owner/data", "floorsheet", "main")

    def test_verifies_local_bytes_against_lfs_sha256_and_size(self):
        payload = b"contract_no,quantity\n000123,100\n"
        row = {"path": "floorsheet/2024-03-18.csv.gz",
               "size_bytes": len(payload),
               "lfs_sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv.gz"
            path.write_bytes(payload)
            result = verify_file(path, row)
        self.assertEqual(result["verification"], "size_and_hub_lfs_sha256_pass")
        self.assertEqual(result["local_sha256"], hashlib.sha256(payload).hexdigest())

    def test_refuses_missing_lfs_sha256(self):
        row = {"path": "floorsheet/2024-03-18.csv.gz", "size_bytes": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv.gz"
            path.write_bytes(b"x")
            with self.assertRaises(ValueError):
                verify_file(path, row)


if __name__ == "__main__":
    unittest.main()
