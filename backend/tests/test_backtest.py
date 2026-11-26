import unittest
from datetime import date, timedelta
from app.backtest import run_walk_forward_backtest


class WalkForwardBacktestTests(unittest.TestCase):
    def _fixture(self):
        start = date(2025, 1, 1)
        sessions = [(start + timedelta(days=i)).isoformat() for i in range(80)]
        rows = []
        for i, day in enumerate(sessions):
            rows.append({"date": day, "open": 100, "high": 106, "low": 99, "close": 105, "volume": 1000})
        reviewed = {}
        for row in rows:
            d = row["date"]
            reviewed[("TEST", d)] = {**row, "symbol": "TEST", "security_id": "fixture-security",
                "instrument_type": "equity", "security_status": "active",
                "lifecycle_evidence_id": "fixture-lifecycle", "session_status": "verified_open",
                "session_evidence_id": "fixture-session", "source_id": "sharehub",
                "evidence_id": "fixture-" + d, "source_payload_sha256": "a"*64,
                "price_basis_reviewed": True, "price_basis_status": "verified_unadjusted_no_actions",
                "corporate_action_status": "clear", "corporate_action_evidence_id": "fixture-action",
                "available_at": d + "T11:00:00+05:45"}
        signals = []
        for i in range(18):
            day = sessions[i]
            signals.append({"schema_version": 1, "symbol": "TEST",
                "decision_time": day + "T15:00:00+05:45", "horizon": "t_plus_2",
                "action": "BUY", "methodology": "fixture_v1", "evidence": [],
                "details": {"decision_date": day, "plan": {"entry": "100", "stop": "95", "targets": ["105"]}},
                "classification": "research_only_not_execution"})
        return signals, {"TEST": rows}, {"TEST": sessions}, reviewed

    def test_chronological_purged_walk_forward_and_determinism(self):
        signals, rows, sessions, reviewed = self._fixture()
        kwargs = dict(signals=signals, rows_by_symbol=rows, verified_sessions_by_symbol=sessions,
            evaluation_date=sessions["TEST"][-1], reviewed=reviewed, min_partition=2)
        a = run_walk_forward_backtest(**kwargs)
        b = run_walk_forward_backtest(**kwargs)
        self.assertEqual(a["config_hash"], b["config_hash"])
        self.assertEqual(list(a["partitions"]), ["train", "validation", "test"])
        self.assertGreater(a["partitions"]["train"]["purged_for_horizon_overlap"], 0)
        self.assertEqual(a["classification"], "research_backtest_not_execution")

    def test_duplicate_signal_records_are_not_double_counted(self):
        signals, rows, sessions, reviewed = self._fixture()
        result = run_walk_forward_backtest(signals=signals + signals, rows_by_symbol=rows,
            verified_sessions_by_symbol=sessions, evaluation_date=sessions["TEST"][-1],
            reviewed=reviewed, min_partition=2)
        self.assertEqual(result["signals_seen"], len(signals))

    def test_future_or_non_research_signal_rejected(self):
        signals, rows, sessions, reviewed = self._fixture()
        signals[0]["classification"] = "execution"
        with self.assertRaises(ValueError):
            run_walk_forward_backtest(signals=signals, rows_by_symbol=rows,
                verified_sessions_by_symbol=sessions, evaluation_date=sessions["TEST"][-1], reviewed=reviewed)

    def test_insufficient_sample_does_not_emit_metrics(self):
        signals, rows, sessions, reviewed = self._fixture()
        result = run_walk_forward_backtest(signals=signals[:5], rows_by_symbol=rows,
            verified_sessions_by_symbol=sessions, evaluation_date=sessions["TEST"][-1], reviewed=reviewed)
        self.assertEqual(result["status"], "insufficient_sample")
        self.assertEqual(result["partitions"], {})


if __name__ == "__main__":
    unittest.main()
