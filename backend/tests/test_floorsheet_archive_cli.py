import hashlib
import tempfile
import unittest
from pathlib import Path

from audit_floorsheet_archive_pair import load_profile_payload, source_manifest


class FloorsheetArchiveCliTests(unittest.TestCase):
    def test_samir_profile_loads_explicit_headers_and_builds_provenance_manifest(self):
        payload = (
            b"date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
            b"2026-11-24,1,C1,AAA,11,22,10,10,100\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samir.csv"
            path.write_bytes(payload)
            loaded, mapping, review = load_profile_payload(path, "samir")
            manifest = source_manifest(
                "samir", "samir@pinned", path, hashlib.sha256(payload).hexdigest(),
                loaded, review,
            )
        self.assertEqual(loaded, payload)
        self.assertEqual(mapping.columns["contract_id"], "contract_no")
        self.assertTrue(review.valid)
        self.assertEqual(manifest["local_size_bytes"], len(payload))
        self.assertEqual(manifest["local_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(manifest["pinned_revision"], "e6160adc6bdf3d19562167388e3d9d4f645c455a")
        self.assertFalse(manifest["profile_evidence_status"] == "verified")

    def test_profile_header_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("date,contract_no,quantity\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "header mismatch"):
                load_profile_payload(path, "samir")


if __name__ == "__main__":
    unittest.main()
