import csv
import tempfile
import unittest
from pathlib import Path

from reconcile_ohlcv_source_daily import reconcile_ohlcv_sources


class OhlcvSourceDailyReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.a = self.root / "source-a.csv"
        self.b = self.root / "source-b.csv"
        self.controls = self.root / "controls.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, path, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "source_id","symbol","date","open","high","low","close","volume"])
            writer.writeheader()
            writer.writerows(rows)

    def row(self, source, symbol="AAA", close="10", volume="100"):
        return {"source_id":source,"symbol":symbol,"date":"2026-11-24",
                "open":"9","high":"11","low":"8","close":close,"volume":volume}

    def test_daily_source_totals_and_cross_source_match(self):
        self.write_rows(self.a, [self.row("A")])
        self.write_rows(self.b, [self.row("B")])
        result = reconcile_ohlcv_sources([self.a, self.b])
        self.assertEqual(result["source_date_count"], 2)
        self.assertEqual(result["daily_source_totals"][0]["total_volume"], "100")
        self.assertEqual(result["cross_source_comparisons"][0]["classification"], "exact_cross_source_match")
        self.assertFalse(result["promotion_allowed"])

    def test_cross_source_conflict_preserves_both_values(self):
        self.write_rows(self.a, [self.row("A", close="10")])
        self.write_rows(self.b, [self.row("B", close="10.01")])
        result = reconcile_ohlcv_sources([self.a, self.b])
        item = result["cross_source_comparisons"][0]
        self.assertEqual(item["classification"], "cross_source_conflict")
        self.assertEqual(item["source_values"]["A"][0]["close"], "10")
        self.assertEqual(item["source_values"]["B"][0]["close"], "10.01")

    def test_duplicate_source_symbol_date_is_preserved_and_flagged(self):
        self.write_rows(self.a, [self.row("A"), self.row("A")])
        result = reconcile_ohlcv_sources([self.a])
        self.assertEqual(result["duplicate_source_symbol_dates"][0]["row_count"], 2)

    def test_daily_control_totals_are_compared_exactly(self):
        self.write_rows(self.a, [self.row("A")])
        with self.controls.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["source_id","date","row_count","total_volume"])
            writer.writeheader()
            writer.writerow({"source_id":"A","date":"2026-11-24","row_count":1,"total_volume":"100"})
        result = reconcile_ohlcv_sources([self.a], self.controls)
        self.assertEqual(result["control_total_results"][0]["status"], "passed")

    def test_control_total_mismatch_fails(self):
        self.write_rows(self.a, [self.row("A")])
        with self.controls.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["source_id","date","row_count","total_volume"])
            writer.writeheader()
            writer.writerow({"source_id":"A","date":"2026-11-24","row_count":2,"total_volume":"99"})
        result = reconcile_ohlcv_sources([self.a], self.controls)
        self.assertEqual(result["control_total_results"][0]["status"], "failed")

    def test_control_date_without_source_rows_is_failed(self):
        self.write_rows(self.a, [])
        with self.controls.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["source_id","date","row_count","total_volume"])
            writer.writeheader()
            writer.writerow({"source_id":"A","date":"2026-11-24","row_count":1,"total_volume":"100"})
        result = reconcile_ohlcv_sources([self.a], self.controls)
        self.assertEqual(result["control_total_results"][0]["differences"], ["missing_source_rows"])

    def test_invalid_ohlc_bounds_rejected(self):
        self.write_rows(self.a, [self.row("A")])
        content = self.a.read_text(encoding="utf-8")
        self.a.write_text(content.replace(",9,11,8,10,", ",9,7,8,10,"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid_ohlc_bounds"):
            reconcile_ohlcv_sources([self.a])

    def test_duplicate_csv_headers_rejected(self):
        self.a.write_text(
            "source_id,symbol,date,open,high,low,close,volume,volume\n",
            encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate CSV headers"):
            reconcile_ohlcv_sources([self.a])

    def test_extra_unmapped_csv_column_rejected(self):
        self.a.write_text(
            "source_id,symbol,date,open,high,low,close,volume,extra\n"
            "A,AAA,2026-11-24,9,11,8,10,100,unmapped\n",
            encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "extra_unmapped_columns"):
            reconcile_ohlcv_sources([self.a])

    def test_invalid_ohlcv_numeric_rejected(self):
        self.write_rows(self.a, [self.row("A", volume="NaN")])
        with self.assertRaisesRegex(ValueError, "must be finite"):
            reconcile_ohlcv_sources([self.a])


if __name__ == "__main__":
    unittest.main()
