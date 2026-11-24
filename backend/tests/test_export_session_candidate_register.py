import csv
import tempfile
import unittest
from pathlib import Path

from export_session_candidate_register import build_candidate_rows, write_candidate_csv


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

    def test_exports_all_source_coverage_columns(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidate.csv"
            rows = write_candidate_csv(self.market, self.yonepse, path)
            with path.open(encoding="utf-8", newline="") as handle:
                exported = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual(len(exported), 3)
            row = next(x for x in exported if x["date"] == "2026-11-20")
            self.assertEqual(row["ohlcv_source_count"], "2")
            self.assertEqual(row["floorsheet_source_count"], "2")
            self.assertEqual(row["calendar_verified_status"], "not_verified_primary_exchange_evidence_missing")


if __name__ == "__main__":
    unittest.main()
