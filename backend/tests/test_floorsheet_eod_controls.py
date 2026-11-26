import unittest

from audit_floorsheet_eod_controls import (
    _read_eod,
    _read_floor,
    git_blob_sha1,
    verify_pinned_eod,
)


class FloorsheetEodControlTests(unittest.TestCase):
    def test_git_blob_hash_matches_git_object_format(self):
        self.assertEqual(
            git_blob_sha1(b"abc"),
            "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f",
        )

    def test_floor_aggregates_volume_turnover_and_contract_count(self):
        payload = (
            b"transaction,symbol,quantity,rate,amount,date\n"
            b"1,ABC,10,100,1000,2026-11-20\n"
            b"2,ABC,5,110,550,2026-11-20\n"
            b"3,XYZ,2,50,100,2026-11-20\n"
        )
        result = _read_floor(payload, "2026-11-20")
        self.assertEqual(result["ABC"]["contract_count"], 2)
        self.assertEqual(str(result["ABC"]["volume"]), "15")
        self.assertEqual(str(result["ABC"]["turnover"]), "1550")
        self.assertEqual(str(result["XYZ"]["volume"]), "2")

    def test_floor_duplicate_contract_and_wrong_date_fail_closed(self):
        duplicate = (
            b"transaction,symbol,quantity,rate,amount,date\n"
            b"1,ABC,10,100,1000,2026-11-20\n"
            b"1,ABC,5,100,500,2026-11-20\n"
        )
        with self.assertRaisesRegex(ValueError, "duplicate floorsheet contract"):
            _read_floor(duplicate, "2026-11-20")
        wrong_date = (
            b"transaction,symbol,quantity,rate,amount,date\n"
            b"1,ABC,10,100,1000,2026-11-19\n"
        )
        with self.assertRaisesRegex(ValueError, "has date"):
            _read_floor(wrong_date, "2026-11-20")

    def test_eod_duplicate_symbols_and_zero_mismatch_fail_closed(self):
        duplicate = (
            b"date,symbol,volume,turnover\n"
            b"2026-11-20,ABC,10,1000\n"
            b"2026-11-20,ABC,5,500\n"
        )
        with self.assertRaisesRegex(ValueError, "duplicate EOD symbol"):
            _read_eod(duplicate, "2026-11-20")
        inconsistent = (
            b"date,symbol,volume,turnover\n"
            b"2026-11-20,ABC,0,1000\n"
        )
        with self.assertRaisesRegex(ValueError, "zero volume/turnover inconsistency"):
            _read_eod(inconsistent, "2026-11-20")

    def test_pinned_eod_size_and_blob_mismatch_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "byte-size mismatch"):
            verify_pinned_eod(b"fixture", "2026-11-20")
        with self.assertRaises(KeyError):
            verify_pinned_eod(b"fixture", "2026-11-21")


if __name__ == "__main__":
    unittest.main()
