import json
import tempfile
import unittest
from pathlib import Path

from build_market_date_crosscheck import INDEX_RE, load_floorsheet_dates, validate_index_csv


class MarketDateCrosscheckTests(unittest.TestCase):
    def test_index_archive_filename_pattern(self):
        self.assertEqual(INDEX_RE.fullmatch("ohlc_index/adj_2026-11-24.csv").group(1), "2026-11-24")
        self.assertIsNone(INDEX_RE.fullmatch("ohlc_index/unadj_2026-11-24.csv"))
        self.assertIsNone(INDEX_RE.fullmatch("ohlc_index/adj_2026-13-40.csv"))
    def test_valid_nepse_index_row(self):
        raw = (
            "date,symbol,open,high,low,close,volume\n"
            "2026-11-24,NEPSE_index,100,110,95,105,12345\n"
            "2026-11-24,Banking_index,200,210,190,205,500\n"
        ).encode()
        result = validate_index_csv(raw, "2026-11-24")
        self.assertTrue(result["nepse_index_row_valid"])
        self.assertEqual(result["nepse_index"]["close"], "105")

    def test_rejects_wrong_date(self):
        raw = b"date,symbol,open,high,low,close,volume\n2026-11-23,NEPSE_index,100,110,95,105,1\n"
        with self.assertRaisesRegex(ValueError, "date_mismatch"):
            validate_index_csv(raw, "2026-11-24")

    def test_rejects_invalid_ohlc_bounds(self):
        raw = b"date,symbol,open,high,low,close,volume\n2026-11-24,NEPSE_index,100,99,95,105,1\n"
        with self.assertRaisesRegex(ValueError, "high_below_ohlc"):
            validate_index_csv(raw, "2026-11-24")

    def test_requires_exactly_one_nepse_index_row(self):
        raw = b"date,symbol,open,high,low,close,volume\n2026-11-24,Banking_index,100,110,95,105,1\n"
        with self.assertRaisesRegex(ValueError, "exactly_one"):
            validate_index_csv(raw, "2026-11-24")

    def test_floorsheet_manifest_dates_group_by_source(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "manifest.jsonl"
            path.write_text(
                json.dumps({"date": "2026-11-24", "repository": "source-a", "path": "a.csv"}) + "\n" +
                json.dumps({"date": "2026-11-24", "repository": "source-a", "path": "b.csv"}) + "\n" +
                json.dumps({"date": "2026-11-24", "repository": "source-b", "path": "c.csv"}) + "\n",
                encoding="utf-8",
            )
            result = load_floorsheet_dates([path])
            self.assertEqual(result["2026-11-24"]["source-a"], 2)
            self.assertEqual(result["2026-11-24"]["source-b"], 1)


if __name__ == "__main__":
    unittest.main()
