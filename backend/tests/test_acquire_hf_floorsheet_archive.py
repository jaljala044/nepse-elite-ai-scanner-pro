import hashlib
import tempfile
import unittest
from pathlib import Path

from acquire_hf_floorsheet_archive import dated_file, lfs_sha256, verify_file


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
