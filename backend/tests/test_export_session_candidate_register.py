import csv
import tempfile
import unittest
from pathlib import Path

from export_session_candidate_register import (
    build_candidate_rows, load_closure_leads, write_candidate_csv,
)


class SessionCandidateRegisterTests(unittest.TestCase):
    def setUp(self):
        self.market = {
            "index_commit_sha": "index-sha",
            "dates": [
                {
                    "date": "2026-11-20",
                    "index_row": {"nepse_index_row_valid": True, "index_row_status": "valid_single_row", "validation_errors": []},
                    "ohlcv_sources": {
                        "source-a": {"unique_symbols": 400},
                        "source-b": {"unique_symbols": 398},
                    },
                    "floorsheet_sources_file_count": {"floor-a": 1, "floor-b": 1},
                },
                {
                    "date": "2026-11-21",
                    "index_row": {"nepse_index_row_valid": False, "index_row_status": "exact_duplicate_rows", "validation_errors": ["exact_duplicate_rows"]},
                    "ohlcv_sources": {},
                    "floorsheet_sources_file_count": {"floor-a": 1},
                },
            ],
        }
        self.yonepse = {
            "yonepse_commit_sha": "yonepse-sha",
            "dates": [
                {"date": "2026-11-20", "comparison": {"status": "numeric_differences", "yonepse_finality": "unmarked", "yonepse_updated_at": "2026-11-24T12:00:00+05:45"}},
                {"date": "2026-11-21", "comparison": {"status": "socrateai_row_anomaly", "yonepse": {"finality_status": "unmarked"}}},
                {"date": "2026-11-24", "comparison": {"status": "yonepse_latest_provisional", "yonepse": {"finality_status": "provisional", "updated_at": "2026-11-24T12:04:02+05:45"}}},
            ],
        }

    def test_classifies_candidates_without_promoting_calendar(self):
        rows = build_candidate_rows(self.market, self.yonepse)
        by_date = {row["date"]: row for row in rows}
        self.assertEqual(by_date["2026-11-20"]["candidate_classification"], "observed_session_candidate_unverified")
        self.assertEqual(by_date["2026-11-21"]["candidate_classification"], "observed_candidate_with_socrateai_row_anomaly")
        self.assertEqual(by_date["2026-11-24"]["candidate_classification"], "provisional_latest_not_final")
        self.assertTrue(all(row["calendar_verified_status"] == "not_verified_primary_exchange_evidence_missing" for row in rows))

    def test_merges_closure_leads_and_flags_conflicts_with_index_rows(self):
        leads = [
            {"date": "2026-11-16", "event": "Chhath closure", "lead_status": "unverified_closure_candidate", "evidence_level": "secondary_report", "source_id": "news-a", "evidence_uri": "https://example.test/a", "notes": "reported closure"},
            {"date": "2026-11-20", "event": "test closure", "lead_status": "unverified_closure_candidate", "evidence_level": "secondary_report", "source_id": "news-b", "evidence_uri": "https://example.test/b", "notes": "conflict test"},
        ]
        rows = build_candidate_rows(self.market, self.yonepse, leads)
        by_date = {row["date"]: row for row in rows}
        self.assertEqual(by_date["2026-11-16"]["candidate_classification"], "reported_closure_candidate_unverified")
        self.assertEqual(by_date["2026-11-16"]["closure_lead_count"], 1)
        self.assertEqual(by_date["2026-11-20"]["candidate_classification"], "closure_lead_conflicts_with_index_record")
        self.assertEqual(by_date["2026-11-20"]["closure_sources"], "news-b")
        self.assertTrue(all(row["calendar_verified_status"] == "not_verified_primary_exchange_evidence_missing" for row in rows))

    def test_loads_multiple_evidence_rows_for_same_date(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "leads.csv"
            lines = [
                "date,event,lead_status,evidence_level,source_id,evidence_uri,notes",
                "2026-11-16,Chhath,unverified_closure_candidate,secondary,a,https://example.test/a,one",
                "2026-11-16,Chhath,unverified_closure_candidate,secondary,b,https://example.test/b,two",
            ]
            path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
            leads = load_closure_leads(path)
            self.assertEqual(len(leads), 2)
            self.assertEqual({x["source_id"] for x in leads}, {"a", "b"})

    def test_exports_all_source_coverage_and_closure_columns(self):
        leads = [
            {"date": "2026-11-16", "event": "Chhath closure", "lead_status": "unverified_closure_candidate", "evidence_level": "secondary_report", "source_id": "news-a", "evidence_uri": "https://example.test/a", "notes": "reported closure"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidate.csv"
            rows = write_candidate_csv(self.market, self.yonepse, path, leads)
            with path.open(encoding="utf-8", newline="") as handle:
                exported = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 4)
            self.assertEqual(len(exported), 4)
            row = next(x for x in exported if x["date"] == "2026-11-20")
            self.assertEqual(row["ohlcv_source_count"], "2")
            self.assertEqual(row["floorsheet_source_count"], "2")
            self.assertEqual(row["calendar_verified_status"], "not_verified_primary_exchange_evidence_missing")
            closure = next(x for x in exported if x["date"] == "2026-11-16")
            self.assertEqual(closure["candidate_classification"], "reported_closure_candidate_unverified")
            self.assertEqual(closure["closure_evidence_uris"], "https://example.test/a")


if __name__ == "__main__":
    unittest.main()
