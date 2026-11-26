import csv
import tempfile
import unittest
from pathlib import Path

from app.session_candidate_audit import audit_session_candidates

FIELDS = ["date", "status", "source_repository", "source_revision", "source_path", "git_blob_sha1", "source_bytes", "lineage"]
CAL_FIELDS = ["date", "status", "source_id", "evidence_uri", "raw_evidence_sha256", "published_at", "retrieved_at_utc", "verified_at_utc", "scope", "notes"]


class SessionCandidateAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.candidates = self.root / "candidates.csv"
        self.calendar = self.root / "calendar.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def write_inputs(self, candidates, calendar=()):
        with self.candidates.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(candidates)
        with self.calendar.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAL_FIELDS)
            w.writeheader()
            w.writerows(calendar)

    def candidate(self, day="2026-11-23", **overrides):
        row = {"date": day, "status": "candidate_unverified", "source_repository": "example/data",
               "source_revision": "a" * 40, "source_path": f"daily/{day}.csv",
               "git_blob_sha1": "b" * 40, "source_bytes": "100",
               "lineage": "secondary EOD; not primary exchange evidence"}
        row.update(overrides)
        return row

    def test_candidate_is_never_promoted_by_weekday_or_file_presence(self):
        self.write_inputs([self.candidate()])
        report = audit_session_candidates(self.candidates, self.calendar)
        self.assertTrue(report["gate_pass"])
        self.assertFalse(report["promotion_allowed"])
        self.assertEqual(report["canonical_open_dates_promoted"], 0)

    def test_explicit_verified_closure_conflicts_with_candidate(self):
        closure = {"date": "2026-11-23", "status": "verified_closed", "source_id": "NEPSE",
                   "evidence_uri": "https://example.invalid", "raw_evidence_sha256": "c" * 64,
                   "published_at": "", "retrieved_at_utc": "2026-11-24T00:00:00Z",
                   "verified_at_utc": "2026-11-24T00:00:00Z", "scope": "all_securities", "notes": "closure"}
        self.write_inputs([self.candidate()], [closure])
        report = audit_session_candidates(self.candidates, self.calendar)
        self.assertFalse(report["gate_pass"])
        self.assertEqual(report["verified_closure_conflicts"], ["2026-11-23"])

    def test_weekday_regime_violation_is_flagged(self):
        self.write_inputs([self.candidate("2026-11-21")])  # Saturday
        report = audit_session_candidates(self.candidates, self.calendar)
        self.assertFalse(report["gate_pass"])
        self.assertEqual(report["weekday_regime_violations"][0]["date"], "2026-11-21")

    def test_duplicate_date_is_not_silently_collapsed(self):
        self.write_inputs([self.candidate(), self.candidate()])
        report = audit_session_candidates(self.candidates, self.calendar)
        self.assertFalse(report["gate_pass"])
        self.assertEqual(report["duplicate_dates"], ["2026-11-23"])

    def test_invalid_source_blob_metadata_fails_gate(self):
        self.write_inputs([self.candidate(git_blob_sha1="bad", source_bytes="0")])
        report = audit_session_candidates(self.candidates, self.calendar)
        self.assertFalse(report["gate_pass"])
        self.assertEqual(len(report["malformed_rows"]), 2)
