import tempfile
import unittest
from pathlib import Path

from app.ohlcv_reconciliation import read_ohlcv, reconcile_roots


class OHLCVReconciliationTests(unittest.TestCase):
    def _write(self, root, relative, content):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_identical_rows_and_numeric_formatting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left, right = root / "left", root / "right"
            self._write(left, "ABC.csv", "date,open,high,low,close,volume\n2024-01-02,10,12,9,11,100\n")
            self._write(right, "ABC.csv", "date,open,high,low,close,volume\n2024-01-02,10.0,12.00,9.0,11.00,100.0\n")
            report = reconcile_roots(left, right, left_source="a", right_source="b",
                                     left_revision="sha-a", right_revision="sha-b")
            self.assertEqual(report["symbols"]["ABC.csv"]["status"], "identical_ohlcv_rows")
            self.assertTrue(report["symbols"]["ABC.csv"]["left_sha256"])

    def test_duplicates_and_conflicting_values_are_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left, right = root / "left", root / "right"
            self._write(left, "ABC.csv", "date,open,high,low,close,volume\n2024-01-02,10,12,9,11,100\n2024-01-02,10,12,9,11,100\n")
            self._write(right, "ABC.csv", "date,open,high,low,close,volume\n2024-01-02,10,12,9,12,100\n")
            result = reconcile_roots(left, right, left_source="a", right_source="b",
                                     left_revision="a1", right_revision="b1")
            item = result["symbols"]["ABC.csv"]
            self.assertEqual(item["status"], "conflict")
            self.assertEqual(item["duplicate_dates"]["left"]["2024-01-02"], 2)
            self.assertEqual(len(item["field_value_mismatches"]), 1)

    def test_missing_dates_are_reported_without_session_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left, right = root / "left", root / "right"
            self._write(left, "ABC.csv", "date,open,high,low,close,volume\n2024-01-02,10,12,9,11,100\n")
            self._write(right, "ABC.csv", "date,open,high,low,close,volume\n2024-01-03,10,12,9,11,100\n")
            item = reconcile_roots(left, right, left_source="a", right_source="b",
                                   left_revision="a1", right_revision="b1")["symbols"]["ABC.csv"]
            self.assertEqual(item["left_only_dates"], ["2024-01-02"])
            self.assertEqual(item["right_only_dates"], ["2024-01-03"])
            self.assertEqual(item["status"], "date_coverage_differs")

    def test_non_iso_date_is_quarantined_as_invalid_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("date,open,high,low,close,volume\n02/01/2024,10,12,9,11,100\n")
            rows, errors = read_ohlcv(path)
            self.assertEqual(rows, {})
            self.assertEqual(errors[0]["error"], "invalid_or_non_iso_date")

    def test_adjacent_identical_candles_are_flagged_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            left, right = root / "left", root / "right"
            content = ("date,open,high,low,close,volume\\n"
                       "2024-01-02,10,12,9,11,100\\n"
                       "2024-01-03,10,12,9,11,100\\n")
            self._write(left, "ABC.csv", content)
            self._write(right, "ABC.csv", content)
            item = reconcile_roots(left, right, left_source="a", right_source="b",
                                   left_revision="a1", right_revision="b1")["symbols"]["ABC.csv"]
            self.assertEqual(len(item["adjacent_identical_candles"]["left"]), 1)
            self.assertEqual(item["status"], "identical_ohlcv_rows")

    def test_invalid_candle_bounds_are_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("date,open,high,low,close,volume\\n2024-01-02,13,12,9,11,100\\n")
            rows, errors = read_ohlcv(path)
            self.assertEqual(rows, {})
            self.assertIn("OHLC values violate", errors[0]["error"])


if __name__ == "__main__":
    unittest.main()
