import hashlib
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from inspect_floorsheet_archive import inspect_zip


class FloorsheetArchiveInventoryTests(unittest.TestCase):
    def _zip(self, directory, entries):
        path = Path(directory) / "source.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in entries:
                archive.writestr(name, payload)
        return path

    def test_inventory_is_hash_pinned_and_does_not_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("2026-01-01.csv", b"a,b\n1,2\n"), ("nested/day.csv", b"x\n")])
            result = inspect_zip(path)
            self.assertTrue(result["safe_to_extract"])
            self.assertEqual(result["inventory_mode"], "central_directory_only_no_extraction")
            self.assertEqual(result["member_count"], 2)
            self.assertEqual(result["file_count"], 2)
            self.assertEqual(result["archive_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse((Path(tmp) / "2026-01-01.csv").exists())

    def test_path_traversal_and_absolute_paths_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("../escape.csv", b"x"), ("/absolute.csv", b"x")])
            result = inspect_zip(path)
            codes = {issue["code"] for issue in result["issues"]}
            self.assertIn("path_traversal_or_empty_component", codes)
            self.assertIn("absolute_member_path", codes)
            self.assertFalse(result["safe_to_extract"])

    def test_duplicate_member_names_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("same.csv", b"a")
                archive.writestr("same.csv", b"b")
            result = inspect_zip(path)
            self.assertIn("duplicate_member_name", {x["code"] for x in result["issues"]})

    def test_case_insensitive_name_collision_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("Day.csv", b"a"), ("day.csv", b"b")])
            result = inspect_zip(path)
            self.assertIn("casefold_name_collision", {x["code"] for x in result["issues"]})

    def test_backslash_member_path_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("..\\\\escape.csv", b"x")])
            result = inspect_zip(path)
            self.assertIn("backslash_in_member_name", {x["code"] for x in result["issues"]})

    def test_symlink_member_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "link.zip"
            info = zipfile.ZipInfo("link.csv")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(info, "target.csv")
            result = inspect_zip(path)
            self.assertIn("symbolic_link_member", {x["code"] for x in result["issues"]})

    def test_declared_size_limits_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("large.csv", b"x" * 1000)])
            result = inspect_zip(path, max_member_uncompressed=100, max_total_uncompressed=200)
            codes = {x["code"] for x in result["issues"]}
            self.assertIn("member_size_limit_exceeded", codes)
            self.assertIn("total_uncompressed_size_limit_exceeded", codes)

    def test_entry_count_limit_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("a.csv", b"a"), ("b.csv", b"b")])
            result = inspect_zip(path, max_entries=1)
            self.assertIn("entry_count_limit_exceeded", {x["code"] for x in result["issues"]})

    def test_invalid_limits_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._zip(tmp, [("a.csv", b"a")])
            with self.assertRaisesRegex(ValueError, "max_entries"):
                inspect_zip(path, max_entries=0)
            with self.assertRaisesRegex(ValueError, "max_compression_ratio"):
                inspect_zip(path, max_compression_ratio=0)
            with self.assertRaisesRegex(ValueError, "finite and positive"):
                inspect_zip(path, max_compression_ratio=float("nan"))


if __name__ == "__main__":
    unittest.main()
