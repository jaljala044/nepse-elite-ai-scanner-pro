import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.rank_unlisted_date_batches import rank_batches


FIELDS = [
    "repository", "commit_sha", "path", "file_sha256", "symbol",
    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
    "current_session_classification",
]


class RankUnlistedDateBatchTests(unittest.TestCase):
    def _write(self, root, rows):
        path = root / "candidates.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _row(self, symbol, current_date, line, repo="jaljala044/nepse-history-starter",
             current_status="not_listed_in_project_calendar"):
        return {
            "repository": repo, "commit_sha": "a" * 40, "path": f"{symbol}_OHLCV.csv",
            "file_sha256": "b" * 64, "symbol": symbol,
            "previous_date": "2026-02-19", "current_date": current_date,
            "previous_csv_line": str(line), "current_csv_line": str(line + 1),
            "current_session_classification": current_status,
        }

    def test_ranks_current_endpoint_once_and_preserves_unknown_disposition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                self._row("AAA", "2026-02-20", 2),
                self._row("BBB", "2026-02-20", 2),
                self._row("CCC", "2026-05-30", 2),
                self._row("DDD", "2026-12-01", 2),
            ]
            path = self._write(root, rows)
            with patch("scripts.rank_unlisted_date_batches.EXPECTED_CANDIDATE_ROWS", 4):
                report = rank_batches(path, top_n=2, excluded_dates=set(), expected_sha256=None)
        self.assertEqual([x["date"] for x in report["top_date_batches"]],
                         ["2026-02-20", "2026-05-30"])
        self.assertEqual(report["top_date_batches"][0]["candidate_pair_count"], 2)
        self.assertEqual(report["top_date_batches"][0]["schedule_context"],
                         "scheduled_non_session_candidate")
        self.assertEqual(report["top_date_batches"][0]["exchange_session_disposition"],
                         "UNKNOWN_NO_T1_NOTICE")
        self.assertFalse(report["canonical_promotion_allowed"])

    def test_excludes_already_reviewed_dates_and_ignores_previous_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                self._row("AAA", "2026-06-27", 2),
                self._row("BBB", "2026-02-20", 2),
                self._row("CCC", "2026-12-01", 2, current_status="project_accepted_open"),
            ]
            path = self._write(root, rows)
            with patch("scripts.rank_unlisted_date_batches.EXPECTED_CANDIDATE_ROWS", 3):
                report = rank_batches(path, excluded_dates={"2026-06-27"}, expected_sha256=None)
        self.assertEqual([x["date"] for x in report["top_date_batches"]], ["2026-02-20"])

    def test_duplicate_source_occurrence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = self._row("AAA", "2026-02-20", 2)
            path = self._write(root, [row, row])
            with patch("scripts.rank_unlisted_date_batches.EXPECTED_CANDIDATE_ROWS", 2):
                with self.assertRaisesRegex(ValueError, "duplicate source occurrence"):
                    rank_batches(path, expected_sha256=None)

    def test_expected_artifact_hash_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self._write(root, [self._row("AAA", "2026-02-20", 2)])
            with patch("scripts.rank_unlisted_date_batches.EXPECTED_CANDIDATE_ROWS", 1):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    rank_batches(path, expected_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
