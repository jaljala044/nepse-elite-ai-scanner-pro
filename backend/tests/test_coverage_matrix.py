import json
import tempfile
import unittest
from pathlib import Path

from app.coverage_matrix import build_coverage, load_calendar, path_date


class CoverageMatrixTests(unittest.TestCase):
    def test_path_date_is_strict_and_optional(self):
        self.assertEqual(path_date("floorsheet/2024-01-02.csv"), "2024-01-02")
        self.assertEqual(path_date("prices/2024_01_02.csv"), "2024-01-02")
        self.assertIsNone(path_date("tables/history.parquet"))
        self.assertIsNone(path_date("floorsheet/2024-13-40.csv"))

    def test_calendar_rejects_duplicate_and_unknown_status(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "calendar.csv"
            path.write_text(
                "session_date,calendar_status,evidence_source,evidence_ref,decision_reason\n"
                "2024-01-02,confirmed_session,exchange,notice-1,verified\n"
                "2024-01-02,confirmed_session,exchange,notice-2,duplicate\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate calendar date"):
                load_calendar(path)

    def test_unknown_dates_are_not_inferred_as_sessions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calendar = root / "calendar.csv"
            calendar.write_text(
                "session_date,calendar_status,evidence_source,evidence_ref,decision_reason\n"
                "2024-01-02,confirmed_session,exchange,notice-1,verified\n"
                "2024-01-03,candidate_unverified,,,not reviewed\n",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "datasets": {
                    "sample": {
                        "repo": "example/dataset",
                        "revision": "abc123",
                        "records": [
                            {"path": "floorsheet/2024-01-02.csv", "size": 10, "oid": "blob1"},
                            {"path": "floorsheet/2024-01-03.csv", "size": 11, "oid": "blob2"},
                            {"path": "history/no-date.parquet", "size": 12},
                        ],
                    }
                }
            }), encoding="utf-8")
            result = build_coverage(load_calendar(calendar), [manifest])
            rows = result["dated_file_matrix"]
            self.assertEqual(rows[0]["assessment"], "file_present_on_confirmed_session")
            self.assertEqual(rows[1]["assessment"], "date_unverified")
            self.assertEqual(len(result["undated_files"]), 1)
            self.assertEqual(result["confirmed_session_count"], 1)

    def test_non_session_file_is_flagged_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"repositories": [{
                "repository": "example/source",
                "commit_sha": "commit1",
                "truncated": False,
                "files": [{"path": "prices/2024-01-07.csv", "sha": "blob"}],
            }]}), encoding="utf-8")
            calendar = {"2024-01-07": {
                "calendar_status": "confirmed_non_session",
                "evidence_source": "exchange",
                "evidence_ref": "notice",
            }}
            result = build_coverage(calendar, [manifest])
            self.assertEqual(
                result["dated_file_matrix"][0]["assessment"],
                "file_on_confirmed_non_session_review",
            )


if __name__ == "__main__":
    unittest.main()
