import unittest
from app.calendar_evidence_manifest import validate_calendar_evidence_manifest


class CalendarEvidenceManifestTests(unittest.TestCase):
    def captures(self):
        return [
            {"source_id":"n1","url":"https://www.nepalstock.com.np/notice/1","raw_evidence_sha256":"a"*64,"raw_evidence_path":"n1.bin","retrieved_at_utc":"2026-11-25T00:00:00Z"},
            {"source_id":"n2","url":"https://www.nepalstock.com.np/notice/2","raw_evidence_sha256":"b"*64,"raw_evidence_path":"n2.bin","retrieved_at_utc":"2026-11-25T00:00:00Z"},
        ]

    def test_multiple_notice_sources_validate_for_same_claim(self):
        rows = [{"date":"2026-11-24","status":"verified_open","scope":"all_securities",
                 "source_ids":["n1","n2"]}]
        result = validate_calendar_evidence_manifest(rows, self.captures())
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["claims"][0]["source_ids"], ["n1","n2"])
        self.assertFalse(result["calendar_population_allowed"])

    def test_conflicting_overlapping_scopes_are_detected(self):
        rows = [
            {"date":"2026-11-24","status":"verified_open","scope":"all_securities","source_ids":["n1"]},
            {"date":"2026-11-24","status":"verified_closed","scope":"SEC-1,SEC-2","source_ids":["n2"]},
        ]
        result = validate_calendar_evidence_manifest(rows, self.captures())
        self.assertEqual(result["conflict_count"], 1)

    def test_disjoint_security_scopes_do_not_conflict(self):
        rows = [
            {"date":"2026-11-24","status":"verified_open","scope":"SEC-1","source_ids":["n1"]},
            {"date":"2026-11-24","status":"verified_closed","scope":"SEC-2","source_ids":["n2"]},
        ]
        result = validate_calendar_evidence_manifest(rows, self.captures())
        self.assertEqual(result["conflict_count"], 0)

    def test_missing_capture_fails_closed(self):
        rows = [{"date":"2026-11-24","status":"verified_open","scope":"all_securities","source_ids":["missing"]}]
        with self.assertRaisesRegex(ValueError, "missing captured evidence"):
            validate_calendar_evidence_manifest(rows, self.captures())

    def test_non_official_capture_url_rejected(self):
        captures = self.captures()
        captures[0]["url"] = "https://example.com/notice"
        rows = [{"date":"2026-11-24","status":"verified_open","scope":"all_securities","source_ids":["n1"]}]
        with self.assertRaisesRegex(ValueError, "approved official host"):
            validate_calendar_evidence_manifest(rows, captures)


if __name__ == "__main__":
    unittest.main()
