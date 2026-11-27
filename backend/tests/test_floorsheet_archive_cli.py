import hashlib
import tempfile
import unittest
from pathlib import Path

from audit_floorsheet_archive_pair import load_profile_payload, source_manifest


class FloorsheetArchiveCliTests(unittest.TestCase):
    def test_urek_profile_loads_explicit_headers_and_builds_provenance_manifest(self):
        payload = (
            b"contract_no,calculation_date,time,stock_symbol,sector,buyer,seller,quantity,rate,amount,id\n"
            b"C1,2026-11-24,11:00:00,AAA,Finance,11,22,10,10,100,1\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "urek.csv"
            path.write_bytes(payload)
            loaded, mapping, review = load_profile_payload(path, "urek")
            manifest = source_manifest(
                "urek", "urek@pinned", path, hashlib.sha256(payload).hexdigest(),
                loaded, review,
            )
        self.assertEqual(loaded, payload)
        self.assertEqual(mapping.columns["contract_id"], "contract_no")
        self.assertTrue(review.valid)
        self.assertEqual(manifest["local_size_bytes"], len(payload))
        self.assertEqual(manifest["local_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(manifest["pinned_revision"], "11ef83a9c3cdbe78112f0245451cdc52bdb1a8f0")
        self.assertNotEqual(manifest["profile_evidence_status"], "verified")

    def test_date_specific_blob_pin_allows_different_daily_size_and_binds_manifest(self):
        payload = (
            b"date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
            b"2026-11-25,1,C1,AAA,11,22,10,10,100\n"
        )
        blob_sha1 = hashlib.sha1(
            b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        ).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samir-2026-11-25.csv"
            path.write_bytes(payload)
            loaded, mapping, review = load_profile_payload(
                path, "samir", expected_git_blob_sha1=blob_sha1
            )
            manifest = source_manifest(
                "samir", "SamirWagle/Nepse-All-Scraper@blob:" + blob_sha1,
                path, hashlib.sha256(payload).hexdigest(), loaded, review,
                expected_git_blob_sha1=blob_sha1,
            )
        self.assertEqual(loaded, payload)
        self.assertTrue(review.valid)
        self.assertEqual(mapping.columns["symbol"], "stock_symbol")
        self.assertEqual(manifest["expected_git_blob_sha1"], blob_sha1)
        self.assertEqual(manifest["payload_pin_mode"], "explicit_date_specific_git_blob_sha1")
        self.assertIsNone(manifest["profile_expected_size_bytes"])
        self.assertIsNone(manifest["profile_expected_raw_sha256"])
        self.assertFalse(manifest["canonical_promotion_allowed"] if "canonical_promotion_allowed" in manifest else True)

    def test_date_specific_blob_pin_rejects_wrong_blob_sha1(self):
        payload = b"date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samir.csv"
            path.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, "does not match supplied date-specific pin"):
                load_profile_payload(path, "samir", expected_git_blob_sha1="0" * 40)

    def test_profile_header_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("contract_no,calculation_date,quantity\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "header mismatch"):
                load_profile_payload(path, "urek")

    def test_pinned_samir_profile_rejects_wrong_file_size_before_parse(self):
        payload = b"date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "samir.csv"
            path.write_bytes(payload)
            with self.assertRaisesRegex(ValueError, "byte-size mismatch"):
                load_profile_payload(path, "samir")


if __name__ == "__main__":
    unittest.main()
