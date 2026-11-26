import unittest
from datetime import date, timedelta
from app.scanner import analyze

class ScannerQualityGateTests(unittest.TestCase):
    def rows(self):
        return [{"date": date(2025, 1, 1)+timedelta(days=i), "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000} for i in range(21)]

    def test_valid(self):
        self.assertEqual(analyze("TEST", self.rows())["status"], "screened")

    def test_invalid_and_nonfinite(self):
        for key, value in [("high", 98), ("close", float("nan")), ("volume", 1.5), ("volume", -1)]:
            rows = self.rows()
            rows[-1][key] = value
            result = analyze("TEST", rows)
            self.assertEqual(result["status"], "data_quality_failed")
            self.assertEqual(result["signals"], [])

    def test_duplicate(self):
        rows = self.rows()
        rows.append(dict(rows[-1]))
        self.assertEqual(analyze("TEST", rows)["status"], "data_quality_failed")

    def test_missing_field(self):
        rows = self.rows()
        del rows[0]["open"]
        self.assertEqual(analyze("TEST", rows)["status"], "data_quality_failed")
