import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from acquire_hf_floorsheet_window import extract_window_metadata, load_dates


class HFFloorsheetWindowTests(unittest.TestCase):
    def test_extracts_available_files_and_reports_missing_dates(self):
        siblings = [
            SimpleNamespace(rfilename="floorsheet/2026-08-25.csv.gz", size=100, blob_id="a", lfs=SimpleNamespace(sha256="a" * 64), xet_hash="x"),
            SimpleNamespace(rfilename="floorsheet/2026-08-26.csv.gz", size=200, blob_id="b", lfs=SimpleNamespace(sha256="b" * 64), xet_hash="y"),
            SimpleNamespace(rfilename="indices/2026-08-26.csv.gz", size=10, blob_id="c", lfs=SimpleNamespace(sha256="c" * 64), xet_hash="z"),
        ]
        rows, missing, folder_count = extract_window_metadata(
            siblings, "owner/data", "pinned", "floorsheet",
            ["2026-08-25", "2026-08-26", "2026-08-27"],
        )
        self.assertEqual([x["date"] for x in rows], ["2026-08-25", "2026-08-26"])
        self.assertEqual(missing, ["2026-08-27"])
        self.assertEqual(folder_count, 2)

    def test_loads_unique_date_list(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dates.csv"
            path.write_text(chr(10).join(["date", "2026-08-25", "2026-08-26"]) + chr(10), encoding="utf-8")
            self.assertEqual(load_dates(path), ["2026-08-25", "2026-08-26"])
            path.write_text(chr(10).join(["date", "2026-08-25", "2026-08-25"]) + chr(10), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate dates"):
                load_dates(path)


if __name__ == "__main__":
    unittest.main()
