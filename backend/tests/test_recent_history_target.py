import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from build_recent_history_target import build_target


class RecentHistoryTargetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calendar = self.root / "calendar.csv"
        self.manifest = self.root / "source.jsonl"
        with self.calendar.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "date", "status", "source_id", "evidence_uri"
            ])
            writer.writeheader()
            for day, status in [
                ("2026-11-20", "verified_open"),
                ("2026-11-23", "verified_open"),
                ("2026-11-24", "verified_open"),
                ("2026-11-25", "verified_closed"),
            ]:
                writer.writerow({
                    "date": day, "status": status, "source_id": "NEPSE_NOTICE",
                    "evidence_uri": "https://example.invalid/notice"
                })
        rows = [
            {"date": "2026-11-20", "repo_id": "source/A", "path": "floorsheet/2026-11-20.csv"},
            {"date": "2026-11-23", "repo_id": "source/A", "path": "floorsheet/2026-11-23.csv"},
            {"date": "2026-11-23", "repo_id": "source/B", "path": "daily/2026-11-23.csv"},
            {"date": "2026-11-24", "repo_id": "source/B", "path": "daily/2026-11-24.csv"},
            {"date": "2026-11-25", "repo_id": "source/A", "path": "floorsheet/2026-11-25.csv"},
        ]
        self.manifest.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_verified_open_sessions_count(self):
        report = build_target([self.manifest], self.calendar, 2, 3)
        self.assertEqual(report["verified_open_sessions_available"], 3)
        self.assertEqual(report["verified_sessions_selected"], 3)
        self.assertTrue(report["minimum_target_met"])
        self.assertTrue(report["preferred_target_met"])
        self.assertEqual(report["selected_start_date"], "2026-11-20")
        self.assertEqual(report["selected_end_date"], "2026-11-24")
        self.assertEqual(report["selected_sessions"][-1]["sources_present"], ["source/B"])

    def test_insufficient_verified_history_does_not_promote_file_dates(self):
        report = build_target([self.manifest], self.calendar, 90, 120)
        self.assertFalse(report["minimum_target_met"])
        self.assertFalse(report["preferred_target_met"])
        self.assertEqual(report["verified_sessions_selected"], 3)
        self.assertEqual(report["source_manifest_date_count"], 4)

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            build_target([self.manifest], self.calendar, 120, 90)


if __name__ == "__main__":
    unittest.main()
