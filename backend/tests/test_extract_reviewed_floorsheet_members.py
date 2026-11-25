import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from pathlib import Path

from extract_reviewed_floorsheet_members import extract_reviewed_csv_members, main


class ReviewedFloorsheetExtractionTests(unittest.TestCase):
    def _archive(self, root, members):
        path = Path(root) / "floorsheet.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in members:
                archive.writestr(name, data)
        return path

    def test_extracts_only_allowlisted_csv_and_hashes_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = b"date,contract\n2026-11-24,1\n"
            archive = self._archive(root, [("day.csv", payload), ("readme.txt", b"not selected")])
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            output = root / "out"
            result = extract_reviewed_csv_members(
                archive, output, member_names=["day.csv"], expected_archive_sha256=archive_hash
            )
            extracted = output / "day.csv"
            self.assertEqual(extracted.read_bytes(), payload)
            self.assertEqual(result["members"][0]["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertTrue(result["members"][0]["zip_crc_verified"])
            self.assertFalse((output / "readme.txt").exists())
            self.assertFalse(result["promotion_allowed"])

    def test_cli_writes_extraction_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, [("day.csv", b"sample")])
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            manifest = root / "report.json"
            argv = [
                "extract_reviewed_floorsheet_members.py", str(archive), str(root / "out"),
                "--expected-archive-sha256", digest, "--member", "day.csv",
                "--manifest-output", str(manifest),
            ]
            with patch("sys.argv", argv):
                self.assertEqual(main(), 0)
            self.assertEqual(json.loads(manifest.read_text())["extracted_member_count"], 1)

    def test_archive_hash_mismatch_blocks_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, [("day.csv", b"x")])
            with self.assertRaisesRegex(ValueError, "does not match"):
                extract_reviewed_csv_members(
                    archive, root / "out", member_names=["day.csv"], expected_archive_sha256="0" * 64
                )
            self.assertFalse((root / "out" / "day.csv").exists())

    def test_non_csv_member_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, [("readme.txt", b"x")])
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "not a CSV"):
                extract_reviewed_csv_members(
                    archive, root / "out", member_names=["readme.txt"], expected_archive_sha256=digest
                )

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, [("day.csv", b"new")])
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            output = root / "out"
            output.mkdir()
            target = output / "day.csv"
            target.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                extract_reviewed_csv_members(
                    archive, output, member_names=["day.csv"], expected_archive_sha256=digest
                )
            self.assertEqual(target.read_bytes(), b"keep")

    def test_member_and_total_size_limits_block_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, [("day.csv", b"x" * 100)])
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "max_member_bytes"):
                extract_reviewed_csv_members(
                    archive, root / "out1", member_names=["day.csv"],
                    expected_archive_sha256=digest, max_member_bytes=10
                )
            with self.assertRaisesRegex(ValueError, "max_total_extracted_bytes"):
                extract_reviewed_csv_members(
                    archive, root / "out2", member_names=["day.csv"],
                    expected_archive_sha256=digest, max_total_extracted_bytes=10
                )

    def test_unknown_member_and_duplicate_allowlist_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._archive(root, [("day.csv", b"x")])
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "absent from inventory"):
                extract_reviewed_csv_members(
                    archive, root / "out", member_names=["missing.csv"], expected_archive_sha256=digest
                )
            with self.assertRaisesRegex(ValueError, "must be unique"):
                extract_reviewed_csv_members(
                    archive, root / "out", member_names=["day.csv", "day.csv"], expected_archive_sha256=digest
                )


if __name__ == "__main__":
    unittest.main()
