import json
import tempfile
import unittest
from pathlib import Path

from compare_floorsheet_windows import compare_windows


UREK_ROW = {
    "contract_no": "2026082601000001",
    "calculation_date": "2026-08-26",
    "time": "10:46:00",
    "stock_symbol": "NABIL",
    "sector": "Commercial Banks",
    "buyer": "58",
    "seller": "26",
    "quantity": "10",
    "rate": "540.60",
    "amount": "5406.00",
    "id": "20260826059442",
}
SOC_ROW = {
    "transaction": "2026082601000001",
    "date": "2026-08-26",
    "symbol": "NABIL",
    "buyer": "58",
    "seller": "26",
    "quantity": "10.0",
    "rate": "540.6",
    "amount": "5406.0",
}


class FloorsheetWindowComparisonTests(unittest.TestCase):
    def _write_csv(self, path, headers, row):
        path.write_text(",".join(headers) + "\\n" + ",".join(row[h] for h in headers) + "\\n", encoding="utf-8")

    def test_compares_all_shared_dates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            urek_path = root / "urek.csv"
            soc_path = root / "socrateai.csv"
            self._write_csv(urek_path, list(UREK_ROW), UREK_ROW)
            self._write_csv(soc_path, list(SOC_ROW), SOC_ROW)
            urek_manifest = root / "urek.json"
            soc_manifest = root / "soc.json"
            urek_manifest.write_text(json.dumps({"repo_id": "owner/data", "resolved_commit_sha": "u", "files": [{"date": "2026-08-26", "local_path": str(urek_path), "local_sha256": None}]}), encoding="utf-8")
            soc_manifest.write_text(json.dumps({"repository": "owner/repo", "resolved_commit_sha": "s", "files": [{"date": "2026-08-26", "local_path": str(soc_path), "local_sha256": None}]}), encoding="utf-8")
            result = compare_windows(urek_manifest, soc_manifest)
            self.assertEqual(result["status"], "all_shared_dates_exact_match")
            self.assertEqual(result["common_date_count"], 1)
            self.assertEqual(result["total_shared_contracts"], 1)

    def test_reports_date_coverage_gaps_without_filling_them(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            urek_path = root / "urek.csv"
            soc_path = root / "socrateai.csv"
            self._write_csv(urek_path, list(UREK_ROW), UREK_ROW)
            self._write_csv(soc_path, list(SOC_ROW), SOC_ROW)
            urek_manifest = root / "urek.json"
            soc_manifest = root / "soc.json"
            urek_manifest.write_text(json.dumps({"files": [{"date": "2026-08-26", "local_path": str(urek_path)}]}), encoding="utf-8")
            soc_manifest.write_text(json.dumps({"files": [{"date": "2026-08-26", "local_path": str(soc_path)}, {"date": "2026-08-27", "local_path": str(soc_path)}]}), encoding="utf-8")
            result = compare_windows(urek_manifest, soc_manifest)
            self.assertEqual(result["common_date_count"], 1)
            self.assertEqual(result["socrateai_only_dates"], ["2026-08-27"])


if __name__ == "__main__":
    unittest.main()
