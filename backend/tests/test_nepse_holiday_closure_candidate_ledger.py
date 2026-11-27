from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_nepse_holiday_closure_candidate_ledger import build_closure_candidate_ledger, write_outputs


class HolidayClosureCandidateLedgerTests(unittest.TestCase):
    def _capture(self, root: Path, year: int, records: list[dict]) -> None:
        folder = root / f"{year}-11-25"
        folder.mkdir(parents=True)
        raw = json.dumps(records, separators=(",", ":")).encode()
        (folder / "response-body.bin").write_bytes(raw)
        (folder / "parsed-response.json").write_text(json.dumps(records), encoding="utf-8")
        (folder / "capture-report.json").write_text(json.dumps({
            "source_id": "NEPSE_OFFICIAL_HOLIDAY_API",
            "source_url": f"https://nepalstock.com.np/api/nots/holiday/list?year={year}",
            "requested_year": year,
            "retrieved_at_utc": "2026-11-25T00:00:00Z",
            "http_status": 200,
            "response_preserved": True,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "response_bytes": len(raw),
            "parsed_record_count": len(records),
        }), encoding="utf-8")

    def test_duplicate_date_reasons_are_preserved_as_distinct_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, 2020, [
                {"holidayDate": "2020-04-13", "holidayDescription": "Lockdown",
                 "instrumentTypeId": None, "activeStatus": None},
                {"holidayDate": "2020-04-13", "holidayDescription": "New Year",
                 "instrumentTypeId": None, "activeStatus": None},
            ])
            result = build_closure_candidate_ledger(root, {2020})
            self.assertEqual(result["closure_evidence_candidate_count"], 2)
            self.assertEqual(result["unique_year_date_count"], 1)
            self.assertEqual(result["duplicate_date_row_count"], 1)
            self.assertEqual([row["holiday_description"] for row in result["rows"]], ["Lockdown", "New Year"])
            self.assertEqual({row["same_date_record_count"] for row in result["rows"]}, {2})
            self.assertTrue(all(row["disposition"] == "review_only_closure_evidence_candidate" for row in result["rows"]))
            self.assertTrue(all(row["scope_assessment"] == "unknown_null_source_fields" for row in result["rows"]))
            self.assertFalse(result["canonical_calendar_promotion_allowed"])

    def test_incomplete_looking_years_are_explicitly_flagged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, 2018, [{"holidayDate": "2018-11-09", "holidayDescription": "Holiday"}])
            result = build_closure_candidate_ledger(root, {2018})
            self.assertEqual(result["rows"][0]["annual_completeness"], "incomplete_looking_range")

    def test_expected_capture_year_set_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, 2025, [{"holidayDate": "2025-01-01", "holidayDescription": "Holiday"}])
            with self.assertRaisesRegex(ValueError, "captured year set mismatch"):
                build_closure_candidate_ledger(root, {2024, 2025})

    def test_outputs_preserve_json_csv_row_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._capture(root, 2025, [{"holidayDate": "2025-01-01", "holidayDescription": "Holiday"}])
            result = build_closure_candidate_ledger(root, {2025})
            json_path, csv_path = root / "out.json", root / "out.csv"
            write_outputs(result, json_path, csv_path)
            loaded = json.loads(json_path.read_text())
            self.assertEqual(loaded["rows"][0]["candidate_id"], result["rows"][0]["candidate_id"])
            self.assertIn("candidate_id,source_year,holiday_date", csv_path.read_text().splitlines()[0])
            self.assertIn(result["rows"][0]["candidate_id"], csv_path.read_text())


if __name__ == "__main__":
    unittest.main()
