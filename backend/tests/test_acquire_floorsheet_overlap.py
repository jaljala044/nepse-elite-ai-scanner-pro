import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from acquire_floorsheet_overlap import (
    SAMIR_REPO, SAMIR_COMMIT, SOCRATE_REPO, SOCRATE_COMMIT,
    git_blob_sha1, main,
)


class FloorsheetOverlapAcquisitionTests(unittest.TestCase):
    def test_git_blob_hash_matches_git_object_format(self):
        payload = b"sample floorsheet bytes\n"
        self.assertEqual(
            git_blob_sha1(payload),
            hashlib.sha1(f"blob {len(payload)}\\0".encode() + payload).hexdigest(),
        )

    @patch("acquire_floorsheet_overlap.fetch")
    def test_bounded_overlap_acquisition_pins_and_hashes_both_sources(self, mocked_fetch):
        samir_payload = b"date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n2026-11-24,1,C1,NABIL,11,22,2,100,200\n"
        socrate_payload = b"transaction,symbol,buyer,seller,quantity,rate,amount,date\nC1,NABIL,11,22,2,100,200,2026-11-24\n"
        samir_entry = {
            "path": "data/floorsheet/floorsheet_2026-11-24.csv",
            "type": "blob", "sha": git_blob_sha1(samir_payload),
        }
        socrate_entry = {
            "path": "floorsheet/floorsheet_2026-11-24.csv",
            "type": "blob", "sha": git_blob_sha1(socrate_payload),
        }
        tree_samir = json.dumps({"truncated": False, "tree": [samir_entry]}).encode()
        tree_socrate = json.dumps({"truncated": False, "tree": [socrate_entry]}).encode()
        mocked_fetch.side_effect = [tree_samir, tree_socrate, samir_payload, socrate_payload]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output_dir = root / "raw"
            manifest = root / "manifest.json"
            argv = [
                "acquire_floorsheet_overlap.py",
                "--limit", "1",
                "--end-date", "2026-11-25",
                "--days", "10",
                "--output-dir", str(output_dir),
                "--manifest", str(manifest),
            ]
            with patch("sys.argv", argv):
                main()
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["selected_dates"], ["2026-11-24"])
            self.assertEqual(data["source_revisions"]["samir"]["commit"], SAMIR_COMMIT)
            self.assertEqual(data["source_revisions"]["socrateai"]["commit"], SOCRATE_COMMIT)
            self.assertEqual(len(data["pairs"][0]["left_sha256"]), 64)
            self.assertTrue((output_dir / "samir-2026-11-24.csv").exists())
            self.assertEqual(mocked_fetch.call_count, 4)


if __name__ == "__main__":
    unittest.main()
