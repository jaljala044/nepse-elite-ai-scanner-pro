import unittest
from datetime import date, timedelta

from app.signal_outcome_validation import evaluate_signal_path


def fixture():
    days = [date(2025, 1, 2) + timedelta(days=i) for i in range(6)]
    bars = [
        (100, 101, 99, 100),
        (100, 104, 99, 103),
        (103, 106, 101, 105),
        (105, 111, 104, 110),
        (110, 112, 94, 96),
        (96, 99, 95, 98),
    ]
    rows = [dict(date=d, open=o, high=h, low=l, close=c, volume=100)
            for d, (o, h, l, c) in zip(days, bars)]
    reviewed = {}
    for row in rows:
        d = str(row["date"])
        reviewed[("TEST", d)] = {
            **row, "symbol":"TEST", "date":d, "security_id":"fixture-security",
            "instrument_type":"equity", "security_status":"active",
            "lifecycle_evidence_id":"fixture-lifecycle", "session_status":"verified_open",
            "session_evidence_id":"fixture-session", "source_id":"sharehub",
            "evidence_id":"fixture-" + d, "source_payload_sha256":"a"*64,
            "price_basis_reviewed":True, "price_basis_status":"verified_unadjusted_no_actions",
            "corporate_action_status":"clear", "corporate_action_evidence_id":"fixture-action",
            "available_at":d + "T11:00:00+05:45",
        }
    signal = {
        "schema_version":1, "symbol":"TEST", "decision_time":days[0].isoformat()+"T15:00:00+05:45",
        "horizon":"t_plus_2", "action":"BUY", "methodology":"test_v1",
        "evidence":[], "details":{"decision_date":days[0].isoformat(),
            "plan":{"entry":"100","stop":"95","targets":["105","110","115"]}},
        "classification":"research_only_not_execution",
    }
    return days, rows, reviewed, signal


class SignalOutcomeValidationTests(unittest.TestCase):
    def test_entry_targets_and_ambiguous_stop_are_conservative(self):
        days, rows, reviewed, signal = fixture()
        result = evaluate_signal_path(signal, rows, [d.isoformat() for d in days],
            evaluation_date=days[-1].isoformat(), reviewed=reviewed)
        self.assertEqual(result["status"], "observed")
        self.assertTrue(result["entry_touched"])
        self.assertEqual(result["targets_touched"], ["T1", "T2", "T3"])
        self.assertTrue(result["stop_touched"])
        self.assertEqual(result["exit_reason"], "stop_target_same_session_conservative_stop_first")
        self.assertEqual(result["reference_return_pct"], "-5.00")

    def test_missing_calendar_fails_closed(self):
        days, rows, reviewed, signal = fixture()
        result = evaluate_signal_path(signal, rows, [],
            evaluation_date=days[-1].isoformat(), reviewed=reviewed)
        self.assertEqual(result["status"], "data_unavailable")

    def test_missing_verified_session_bar_is_not_skipped(self):
        days, rows, reviewed, signal = fixture()
        result = evaluate_signal_path(signal, rows[:3] + rows[4:],
            [d.isoformat() for d in days], evaluation_date=days[-1].isoformat(), reviewed=reviewed)
        self.assertEqual(result["status"], "data_incomplete")

    def test_late_or_unreviewed_ohlcv_is_withheld(self):
        days, rows, reviewed, signal = fixture()
        reviewed[("TEST", str(days[2]))]["available_at"] = "2025-02-01T11:00:00+05:45"
        result = evaluate_signal_path(signal, rows, [d.isoformat() for d in days],
            evaluation_date=days[-1].isoformat(), reviewed=reviewed)
        self.assertEqual(result["status"], "evidence_unverified")

    def test_non_buy_research_signal_has_no_long_path(self):
        days, rows, reviewed, signal = fixture()
        signal["action"] = "SELL"
        result = evaluate_signal_path(signal, rows, [d.isoformat() for d in days],
            evaluation_date=days[-1].isoformat(), reviewed=reviewed)
        self.assertEqual(result["status"], "not_applicable")

    def test_evaluation_cannot_precede_decision(self):
        days, rows, reviewed, signal = fixture()
        with self.assertRaises(ValueError):
            evaluate_signal_path(signal, rows, [d.isoformat() for d in days],
                evaluation_date="2025-01-01", reviewed=reviewed)


if __name__ == "__main__":
    unittest.main()
