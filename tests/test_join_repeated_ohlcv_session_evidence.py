import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.join_repeated_ohlcv_session_evidence import join_candidates


class RepeatedOHLCVSessionJoinTests(unittest.TestCase):
    def test_join_preserves_candidates_and_never_promotes_missing_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            calendar = root / "calendar.csv"
            output = root / "joined.csv"
            summary = root / "summary.json"
            with candidates.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "repository", "commit_sha", "path", "file_sha256", "symbol",
                    "previous_date", "current_date", "previous_csv_line", "current_csv_line",
                ])
                writer.writeheader()
                writer.writerow({
                    "repository": "source/a", "commit_sha": "a" * 40,
                    "path": "ABC.csv", "file_sha256": "b" * 64, "symbol": "ABC",
                    "previous_date": "2026-11-05", "current_date": "2026-11-06",
                    "previous_csv_line": 2, "current_csv_line": 3,
                })
                writer.writerow({
                    "repository": "source/a", "commit_sha": "a" * 40,
                    "path": "XYZ.csv", "file_sha256": "c" * 64, "symbol": "XYZ",
                    "previous_date": "2026-11-06", "current_date": "2026-11-07",
                    "previous_csv_line": 8, "current_csv_line": 9,
                })
            calendar.write_text(
                "date,status,source_id,evidence_uri,raw_evidence_sha256,published_at,retrieved_at_utc,verified_at_utc,scope,notes\n"
                "2026-11-05,verified_open,NEPSE,https://nepalstock.com/evidence," + "d" * 64 +
                ",2026-11-05T10:00:00+05:45,2026-11-05T11:00:00Z,2026-11-05T12:00:00Z,all_market,official open\n"
                "2026-11-06,verified_open,NEPSE,https://nepalstock.com/evidence," + "d" * 64 +
                ",2026-11-06T10:00:00+05:45,2026-11-06T11:00:00Z,2026-11-06T12:00:00Z,all_market,official open\n",
                encoding="utf-8",
            )
            result = join_candidates(candidates, calendar, output, summary)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["session_pair_classification"], "both_dates_verified_open")
            self.assertEqual(rows[1]["session_pair_classification"], "session_evidence_incomplete")
            self.assertEqual(rows[1]["current_session_classification"],
                             "unverified_non_session_candidate")
            self.assertEqual(result["candidate_rows"], 2)
            saved = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(saved["output_csv_sha256"], result["output_csv_sha256"])
            self.assertIn("review-only", saved["policy"])

    def test_verified_closure_is_explicitly_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            calendar = root / "calendar.csv"
            output = root / "joined.csv"
            summary = root / "summary.json"
            candidates.write_text(
                "repository,commit_sha,path,file_sha256,symbol,previous_date,current_date,previous_csv_line,current_csv_line\n"
                "source/a," + "a" * 40 + ",ABC.csv," + "b" * 64 +
                ",ABC,2026-11-05,2026-11-06,2,3\n", encoding="utf-8"
            )
            calendar.write_text(
                "date,status,source_id,evidence_uri,raw_evidence_sha256,published_at,retrieved_at_utc,verified_at_utc,scope,notes\n"
                "2026-11-05,verified_open,NEPSE,https://nepalstock.com/evidence," + "d" * 64 +
                ",2026-11-05T10:00:00+05:45,2026-11-05T11:00:00Z,2026-11-05T12:00:00Z,all_market,open\n"
                "2026-11-06,verified_closed,NEPSE,https://nepalstock.com/evidence," + "d" * 64 +
                ",2026-11-06T10:00:00+05:45,2026-11-06T11:00:00Z,2026-11-06T12:00:00Z,all_market,closure\n",
                encoding="utf-8",
            )
            join_candidates(candidates, calendar, output, summary)
            with output.open(newline="", encoding="utf-8") as handle:
                row = next(csv.DictReader(handle))
            self.assertEqual(row["session_pair_classification"], "contains_verified_closure")


    def test_rejects_noncanonical_dates_and_timestamp_suffixes(self):
        invalid_dates = ("20261105", "2026-11-05T00:00:00", "2026-1-05")
        for invalid in invalid_dates:
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                candidates = root / "candidates.csv"
                calendar = root / "calendar.csv"
                output = root / "joined.csv"
                summary = root / "summary.json"
                candidates.write_text(
                    "repository,commit_sha,path,file_sha256,symbol,previous_date,current_date,previous_csv_line,current_csv_line\\n"
                    "source/a," + "a" * 40 + ",ABC.csv," + "b" * 64 +
                    ",ABC," + invalid + ",2026-11-06,2,3\\n",
                    encoding="utf-8",
                )
                calendar.write_text(
                    "date,status,source_id,evidence_uri,raw_evidence_sha256,published_at,retrieved_at_utc,verified_at_utc,scope,notes\\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "previous_date must be canonical YYYY-MM-DD"):
                    join_candidates(candidates, calendar, output, summary)


if __name__ == "__main__":
    unittest.main()
