import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from build_calendar_coverage_matrix import build_matrix


class CalendarCoverageMatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calendar = self.root / "calendar.csv"
        self.manifest = self.root / "source.jsonl"
        with self.calendar.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "date", "status", "source_id", "evidence_uri", "raw_evidence_sha256", "published_at", "retrieved_at_utc", "verified_at_utc", "scope", "notes"
            ])
            writer.writeheader()
            writer.writerow({
                "date": "2026-11-23", "status": "verified_open",
                "source_id": "nepse_notice_1", "evidence_uri": "https://example.invalid/1",
                "raw_evidence_sha256": "a" * 64, "published_at": "2026-11-23T09:00:00+05:45",
                "retrieved_at_utc": "2026-11-24T00:00:00Z",
                "verified_at_utc": "2026-11-24T00:00:00Z", "scope": "all securities", "notes": "test"
            })
            writer.writerow({
                "date": "2026-11-24", "status": "verified_closed",
                "source_id": "nepse_notice_2", "evidence_uri": "https://example.invalid/2",
                "raw_evidence_sha256": "b" * 64, "published_at": "2026-11-24T09:00:00+05:45",
                "retrieved_at_utc": "2026-11-24T10:00:00Z",
                "verified_at_utc": "2026-11-24T10:00:00Z", "scope": "all securities", "notes": "test closure"
            })
        rows = [
            {"date": "2026-11-23", "repo_id": "source/A", "path": "floorsheet/2026-11-23.csv", "size_bytes": 100},
            {"date": "2026-11-24", "repo_id": "source/A", "path": "floorsheet/2026-11-24.csv", "size_bytes": 200},
            {"date": "2026-11-23", "repo_id": "source/B", "path": "daily/2026-11-23.csv", "size_bytes": 300},
        ]
        self.manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_matrix_distinguishes_calendar_evidence_and_file_presence(self):
        report = build_matrix(
            [self.manifest], self.calendar,
            date(2026, 11, 23), date(2026, 11, 28)
        )
        self.assertEqual(report["days_in_matrix"], 6)
        self.assertEqual(report["manifest_files_observed"], 3)
        self.assertEqual(report["days_with_source_files"], 2)
        self.assertEqual(report["days_with_explicit_calendar_evidence"], 2)
        self.assertEqual(report["rows"][0]["calendar_classification"], "verified_open")
        self.assertEqual(report["rows"][0]["source_count"], 2)
        self.assertEqual(report["rows"][0]["calendar_evidence"]["raw_evidence_sha256"], "a" * 64)
        self.assertEqual(report["rows"][0]["calendar_evidence"]["scope"], "all securities")
        self.assertIn("source_file_on_verified_closed_date", report["rows"][1]["flags"])
        self.assertEqual(report["rows"][5]["date"], "2026-11-28")
        self.assertEqual(report["rows"][5]["calendar_classification"], "unverified_non_session_candidate")
        self.assertIn("calendar_evidence_missing", report["rows"][5]["flags"])

    def test_exceptional_closure_flags_source_files(self):
        with self.calendar.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "date", "status", "source_id", "evidence_uri", "raw_evidence_sha256",
                "published_at", "retrieved_at_utc", "verified_at_utc", "scope", "notes"
            ])
            writer.writerow({
                "date": "2026-11-25", "status": "verified_exceptional_closed",
                "source_id": "nepse_notice_3", "evidence_uri": "https://example.invalid/3",
                "raw_evidence_sha256": "c" * 64, "published_at": "",
                "retrieved_at_utc": "2026-11-25T00:00:00Z",
                "verified_at_utc": "2026-11-25T00:00:00Z",
                "scope": "all securities", "notes": "exceptional closure"
            })
        with self.manifest.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"date":"2026-11-25","repo_id":"source/A",
                                     "path":"floorsheet/2026-11-25.csv","size_bytes":10}) + "\\n")
        report = build_matrix([self.manifest], self.calendar,
                              date(2026,11,25), date(2026,11,25))
        self.assertIn("source_file_on_verified_closed_date", report["rows"][0]["flags"])

    def test_reversed_date_range_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix([self.manifest], self.calendar, date(2026, 11, 28), date(2026, 11, 23))


if __name__ == "__main__":
    unittest.main()
