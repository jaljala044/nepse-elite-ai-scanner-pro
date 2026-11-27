from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path

from app.calendar_evidence_manifest import validate_calendar_evidence_manifest
from app.session_calendar import load_calendar


ROOT = Path(__file__).resolve().parents[2]


class OfficialNepseHolidayCaptureTests(unittest.TestCase):
    def test_raw_api_capture_hash_and_manifest_validate(self):
        manifest_path = ROOT / "data/evidence/acquired/calendar-evidence-manifest-2026.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        capture = manifest["captures"][0]
        raw_path = ROOT / capture["raw_evidence_path"]
        payload = raw_path.read_bytes()

        self.assertEqual(hashlib.sha256(payload).hexdigest(), capture["raw_evidence_sha256"])
        self.assertEqual(len(json.loads(payload)), 41)

        result = validate_calendar_evidence_manifest(manifest["claims"], manifest["captures"])
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["calendar_claim_count"], 41)
        self.assertEqual(result["captured_source_count"], 1)
        self.assertEqual(result["conflict_count"], 0)
        self.assertFalse(result["calendar_population_allowed"])

    def test_canonical_calendar_preserves_exact_official_api_closures(self):
        calendar = load_calendar(ROOT / "data/reference/nepse_session_calendar.csv")
        manifest = json.loads((ROOT / "data/evidence/acquired/calendar-evidence-manifest-2026.json").read_text(encoding="utf-8"))
        capture = manifest["captures"][0]
        expected = {claim["date"]: claim["status"] for claim in manifest["claims"]}
        official = {day.isoformat(): row for day, row in calendar.items()
                    if row["source_id"] == capture["source_id"]}
        self.assertEqual(len(expected), 41)
        self.assertEqual({day: row["status"] for day, row in official.items()}, expected)
        for row in official.values():
            self.assertEqual(row["raw_evidence_sha256"], capture["raw_evidence_sha256"])
            self.assertEqual(row["scope"], "all_securities")
            self.assertEqual(row["retrieved_at_utc"], capture["retrieved_at_utc"])
        self.assertEqual(expected["2026-09-21"], "verified_exceptional_closed")
        self.assertEqual(sum(status == "verified_closed" for status in expected.values()), 40)
        for row in calendar.values():
            if row["source_id"] == "SS_ARCHIVE":
                self.assertEqual(row["status"], "project_accepted_open")
                self.assertEqual(row["scope"], "project_baseline")


    def test_no_source_session_record_or_market_summary_conflicts_with_holiday_dates(self):
        manifest = json.loads(
            (ROOT / "data/raw/acquired/rajeevpaudel-nepse-history/manifest.json").read_text(encoding="utf-8")
        )
        holiday_dates = set(calendar_dates())
        source_ok = {
            day for day in holiday_dates
            if manifest.get(day, {}).get("status") == "ok"
        }
        self.assertEqual(source_ok, set())

        candidate_path = ROOT / "data/reference/nepse-session-calendar-candidates-2026.csv"
        with candidate_path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            date_column = "session_date" if "session_date" in (reader.fieldnames or []) else "date"
            candidates = {row[date_column] for row in reader}
        self.assertEqual(holiday_dates & candidates, set())


def calendar_dates():
    manifest = json.loads(
        (ROOT / "data/evidence/acquired/calendar-evidence-manifest-2026.json").read_text(encoding="utf-8")
    )
    return [row["date"] for row in manifest["claims"]]


if __name__ == "__main__":
    unittest.main()
