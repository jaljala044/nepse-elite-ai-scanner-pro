import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data/reference"

def read(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))

class CalendarEvidenceReconciliationTests(unittest.TestCase):
    def test_exact_source_union_and_classification(self):
        names = ["nepse_session_calendar.csv",
                 "nepse_primary_observed_open_sessions_2025-2026.csv",
                 "nepse_observed_index_dates_2026-05-18_2026-11-24.csv",
                 "nepse-session-calendar-candidates-2026.csv"]
        sets = []
        for name in names:
            rows = read(name)
            dates = {r.get("date") or r["session_date"] for r in rows}
            self.assertEqual(len(dates), len(rows))
            sets.append(dates)
        rows = read("p443_calendar_evidence_reconciliation.csv")
        dates = [r["date"] for r in rows]
        self.assertEqual(dates, sorted(set.union(*sets)))
        self.assertEqual(len(dates), len(set(dates)))
        fields = ["verified_closure_record", "official_positive_trade_observation",
                  "index_candidate", "market_summary_candidate"]
        for row in rows:
            day = row["date"]
            flags = [day in s for s in sets]
            self.assertEqual([int(row[f]) for f in fields], [int(f) for f in flags])
            closed, positive, _, _ = flags
            expected = ("conflict_review" if closed and positive else
                        "verified_closure" if closed else
                        "primary_open_observation_review" if positive else "candidate_only")
            self.assertEqual(row["disposition"], expected)
        self.assertFalse(sets[0] & sets[1])
