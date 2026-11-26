import os
import tempfile
import unittest
from pathlib import Path

from app.signal_tracking import freeze_signal
from app.signal_store import store_signal, store_outcome, get_signal, list_signal_outcomes


class ImmutableSignalStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "signals.duckdb")
        self.envelope = freeze_signal(
            symbol="TEST", decision_time="2025-01-02T12:00:00Z",
            horizon="swing", action="NO TRADE", methodology="research_v1",
            evidence=[{"evidence_id": "fixture", "available_at": "2025-01-02T11:00:00Z"}],
            details={"score": None},
        )

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_signal_insert_is_idempotent_and_retrievable(self):
        first = store_signal(self.envelope)
        second = store_signal(self.envelope)
        self.assertEqual(first["status"], "stored")
        self.assertEqual(second["status"], "already_stored")
        self.assertEqual(get_signal(self.envelope["signal_id"]), self.envelope["record"])

    def test_tampered_or_actionable_signal_rejected(self):
        tampered = {"signal_id": self.envelope["signal_id"],
                    "record": {**self.envelope["record"], "action": "BUY"}}
        with self.assertRaises(ValueError):
            store_signal(tampered)

    def test_outcome_requires_signal_and_matching_horizon(self):
        with self.assertRaises(ValueError):
            store_outcome(signal_id=self.envelope["signal_id"], horizon="swing",
                          observed_at="2025-01-03T12:00:00Z", outcome={"status": "observed"})
        store_signal(self.envelope)
        with self.assertRaises(ValueError):
            store_outcome(signal_id=self.envelope["signal_id"], horizon="t_plus_2",
                          observed_at="2025-01-03T12:00:00Z", outcome={"status": "observed"})

    def test_outcome_append_only_idempotent_and_time_ordered(self):
        store_signal(self.envelope)
        args = dict(signal_id=self.envelope["signal_id"], horizon="swing",
                    observed_at="2025-01-03T12:00:00Z",
                    outcome={"status": "research_only", "return_pct": 1.25})
        self.assertEqual(store_outcome(**args)["status"], "stored")
        self.assertEqual(store_outcome(**args)["status"], "already_stored")
        self.assertEqual(len(list_signal_outcomes(self.envelope["signal_id"])), 1)
        with self.assertRaises(ValueError):
            store_outcome(**{**args, "observed_at": "2025-01-01T12:00:00Z"})

    def test_non_finite_json_rejected(self):
        store_signal(self.envelope)
        with self.assertRaises(ValueError):
            store_outcome(signal_id=self.envelope["signal_id"], horizon="swing",
                          observed_at="2025-01-03T12:00:00Z",
                          outcome={"return_pct": float("nan")})



    def test_buy_research_signal_can_be_stored_without_execution(self):
        buy = freeze_signal(
            symbol="TEST", decision_time="2025-01-02T12:00:00Z",
            horizon="swing", action="BUY", methodology="research_v1",
            evidence=[{"evidence_id":"fixture","available_at":"2025-01-02T11:00:00Z"}],
            details={"plan":{"entry":"100","stop":"95","targets":["110"]}},
        )
        self.assertEqual(store_signal(buy)["status"], "stored")
        self.assertEqual(get_signal(buy["signal_id"])["action"], "BUY")

if __name__ == "__main__":
    unittest.main()
