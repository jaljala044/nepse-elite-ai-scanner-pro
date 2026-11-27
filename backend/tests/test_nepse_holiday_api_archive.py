from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_nepse_holiday_api_archive import audit_archive


class NepseHolidayApiArchiveAuditTests(unittest.TestCase):
    def _capture(self, root: Path, year: int, records: list[dict]) -> Path:
        folder = root / f"{year}-11-25"
        folder.mkdir(parents=True)
        raw = json.dumps(records, separators=(",", ":")).encode()
        (folder / "response-body.bin").write_bytes(raw)
        (folder / "parsed-response.json").write_text(json.dumps(records), encoding="utf-8")
        (folder / "capture-report.json").write_text(json.dumps({
            "requested_year": year,
            "http_status": 200,
            "response_preserved": True,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "response_bytes": len(raw),
            "parsed_record_count": len(records),
        }), encoding="utf-8")
        return folder

    def test_valid_capture_and_duplicate_date_are_reported_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, 2020, [
                {"holidayDate": "2020-04-13", "holidayDescription": "Lockdown"},
                {"holidayDate": "2020-04-13", "holidayDescription": "New Year"},
            ])
            result = audit_archive(root)
            self.assertEqual(result["failure_count"], 0)
            self.assertEqual(result["total_record_count"], 2)
            self.assertEqual(result["total_unique_dates_within_years"], 1)
            self.assertEqual(result["years"][0]["duplicate_dates"][0]["record_count"], 2)
            self.assertFalse(result["canonical_calendar_promotion_allowed"])

    def test_non_official_source_host_is_rejected_even_with_valid_payload_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = self._capture(root, 2025, [
                {"holidayDate": "2025-01-01", "holidayDescription": "Holiday"},
            ])
            report_path = folder / "capture-report.json"
            report = json.loads(report_path.read_text())
            report["source_url"] = "https://nepalstock.com.np.attacker.example/api/nots/holiday/list?year=2025"
            report_path.write_text(json.dumps(report))
            result = audit_archive(root)
            self.assertEqual(result["failure_count"], 1)
            self.assertIn("official NEPSE holiday endpoint", result["failures"][0]["error"])

    def test_source_url_must_match_requested_year(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = self._capture(root, 2025, [
                {"holidayDate": "2025-01-01", "holidayDescription": "Holiday"},
            ])
            report_path = folder / "capture-report.json"
            report = json.loads(report_path.read_text())
            report["source_url"] = "https://nepalstock.com.np/api/nots/holiday/list?year=2024"
            report_path.write_text(json.dumps(report))
            result = audit_archive(root)
            self.assertEqual(result["failure_count"], 1)
            self.assertIn("official NEPSE holiday endpoint", result["failures"][0]["error"])

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = self._capture(root, 2025, [
                {"holidayDate": "2025-01-01", "holidayDescription": "Holiday"},
            ])
            report_path = folder / "capture-report.json"
            report = json.loads(report_path.read_text())
            report["response_sha256"] = "0" * 64
            report_path.write_text(json.dumps(report))
            result = audit_archive(root)
            self.assertEqual(result["failure_count"], 1)
            self.assertIn("SHA-256", result["failures"][0]["error"])

    def test_out_of_year_record_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, 2024, [
                {"holidayDate": "2025-01-01", "holidayDescription": "Wrong year"},
            ])
            result = audit_archive(root)
            self.assertEqual(result["failure_count"], 1)
            self.assertIn("outside requested year", result["failures"][0]["error"])

    def test_parsed_copy_must_match_raw_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = self._capture(root, 2025, [
                {"holidayDate": "2025-01-01", "holidayDescription": "Holiday"},
            ])
            (folder / "parsed-response.json").write_text("[]", encoding="utf-8")
            result = audit_archive(root)
            self.assertEqual(result["failure_count"], 1)
            self.assertIn("parsed response differs", result["failures"][0]["error"])


if __name__ == "__main__":
    unittest.main()
