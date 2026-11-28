import tempfile
import unittest
from pathlib import Path

from scripts.extract_repeated_adjacent_ohlcv import extract


class RepeatedAdjacentTests(unittest.TestCase):
    def _write(self, root: Path, rows: str) -> Path:
        file = root / "ABC_OHLCV.csv"
        file.write_text("Date,Open,High,Low,Close,Volume\n" + rows, encoding="utf-8")
        return file


    def test_project_calendar_join_identifies_adjacent_sessions(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calendar = root / "calendar.csv"
            calendar.write_text(
                "date,status\n2026-01-01,project_accepted_open\n"
                "2026-01-02,verified_closed\n2026-01-04,project_accepted_open\n"
                "2026-01-05,project_accepted_open\n", encoding="utf-8")
            rows = [
                {"repository": "example/repo", "previous_date": "2026-01-01", "current_date": "2026-01-04"},
                {"repository": "example/repo", "previous_date": "2026-01-04", "current_date": "2026-01-05"},
                {"repository": "example/repo", "previous_date": "2026-01-01", "current_date": "2026-01-02"},
            ]
            joined, summary = join_project_calendar(rows, calendar)
            self.assertEqual(joined[0]["project_session_gap"], 1)
            self.assertEqual(joined[0]["session_join_classification"], "adjacent_project_sessions_review")
            self.assertEqual(joined[1]["project_session_gap"], 1)
            self.assertEqual(joined[2]["session_join_classification"], "explicit_closure_date_conflict_review")
            self.assertEqual(summary["project_accepted_open_dates"], 3)
            self.assertEqual(summary["explicit_closure_dates"], 1)

    def test_project_calendar_join_marks_missing_dates_unresolved(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calendar = root / "calendar.csv"
            calendar.write_text(
                "date,status\n2026-01-01,project_accepted_open\n"
                "2026-01-04,project_accepted_open\n", encoding="utf-8")
            rows = [{"repository": "example/repo", "previous_date": "2026-01-01", "current_date": "2026-01-03"}]
            joined, _ = join_project_calendar(rows, calendar)
            self.assertEqual(joined[0]["session_join_classification"], "date_not_in_project_calendar_review")

    def test_identical_valid_next_calendar_date_is_baseline_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "2026-01-01,10,11,9,10,100\n"
                "2026-01-02,10,11,9,10,100\n"
                "2026-01-03,10,12,9,11,150\n",
            )
            rows = extract("example/repo", "a" * 40, root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["previous_date"], "2026-01-01")
            self.assertEqual(rows[0]["current_date"], "2026-01-02")
            self.assertTrue(rows[0]["baseline_metric_eligible"])
            self.assertEqual(rows[0]["calendar_day_gap"], 1)

    def test_incomplete_rows_break_adjacency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "2026-01-01,,,,,\n"
                "2026-01-02,,,,,\n"
                "2026-01-03,10,11,9,10,100\n"
                "2026-01-04,10,,9,10,100\n"
                "2026-01-05,10,11,9,10,100\n",
            )
            self.assertEqual(extract("example/repo", "b" * 40, root), [])

    def test_date_gap_is_retained_but_not_baseline_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "2026-01-01,10,11,9,10,100\n"
                "2026-01-03,10,11,9,10,100\n",
            )
            rows = extract("example/repo", "c" * 40, root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["calendar_day_gap"], 2)
            self.assertFalse(rows[0]["baseline_metric_eligible"])
            self.assertEqual(rows[0]["review_reason"],
                             "adjacent_rows_but_calendar_date_gap_or_unparseable")

    def test_invalid_ohlc_bounds_are_retained_but_not_baseline_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                "2026-01-01,12,11,9,10,100\n"
                "2026-01-02,12,11,9,10,100\n",
            )
            rows = extract("example/repo", "d" * 40, root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["calendar_day_gap"], 1)
            self.assertFalse(rows[0]["ohlc_bounds_valid"])
            self.assertFalse(rows[0]["baseline_metric_eligible"])
            self.assertEqual(rows[0]["review_reason"],
                             "repeated_signature_has_invalid_ohlc_bounds")



    def test_malformed_candidate_dates_are_not_misclassified_as_calendar_gaps(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar, unlisted_date_queue
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calendar = root / "calendar.csv"
            calendar.write_text(
                "date,status\\n2026-01-01,project_accepted_open\\n",
                encoding="utf-8",
            )
            rows = [{
                "repository": "example/repo",
                "symbol": "ABC",
                "previous_date": "2026-02-30",
                "current_date": "2026-01-01",
            }]
            joined, _ = join_project_calendar(rows, calendar)
            self.assertEqual(joined[0]["session_join_classification"], "malformed_candidate_date_review")
            queue = unlisted_date_queue(joined)
            self.assertEqual(queue[0]["disposition"], "malformed_date_review")
            self.assertFalse(queue[0]["canonical_promotion_allowed"])

    def test_reject_invalid_calendar_date(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "calendar.csv"
            for day in ("2026-02-30", "20260101", ""):
                with self.subTest(day=day):
                    p.write_text("date,status\n" + day + ",project_accepted_open\n", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        join_project_calendar([], p)

    def test_reject_unknown_calendar_status(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "calendar.csv"
            for status in ("", "open", "unverified_closed"):
                with self.subTest(status=status):
                    p.write_text("date,status\n2026-01-01," + status + "\n", encoding="utf-8")
                    with self.assertRaises(ValueError):
                        join_project_calendar([], p)

    def test_reject_duplicate_calendar_date(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "calendar.csv"
            p.write_text("date,status\n2026-01-01,verified_open\n2026-01-01,verified_closed\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                join_project_calendar([], p)

    def test_verified_open_distinct_from_project_open(self):
        from scripts.extract_repeated_adjacent_ohlcv import join_project_calendar
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "calendar.csv"
            p.write_text("date,status\n2026-01-01,project_accepted_open\n2026-01-02,verified_exceptional_open\n", encoding="utf-8")
            rows = [{"repository":"example/repo","previous_date":"2026-01-01","current_date":"2026-01-02"}]
            joined, summary = join_project_calendar(rows,p)
            self.assertEqual(summary["project_accepted_open_dates"],1)
            self.assertEqual(summary["verified_open_dates"],1)
            self.assertEqual(joined[0]["session_join_classification"],"adjacent_project_sessions_review")


if __name__ == "__main__":
    unittest.main()
