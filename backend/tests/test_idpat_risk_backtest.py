import unittest
from datetime import date, timedelta

from app.idpat_risk_management import build_idpat_risk_plan, RiskPlanError
from app.idpat_backtest import replay_idpat_signals, walk_forward_split


class RiskTests(unittest.TestCase):
    def plan(self, **changes):
        args = dict(symbol="TEST", entry="100", stop="95",
                    targets={"T1": "110", "T2": "115", "T3": "120"},
                    capital="100000", risk_pct="1", round_trip_cost_pct="0.2",
                    slippage_pct="0.1")
        args.update(changes)
        return build_idpat_risk_plan(**args)

    def test_whole_share_sizing_respects_risk_budget(self):
        result = self.plan()
        self.assertEqual(result["status"], "risk_plan_candidate")
        self.assertEqual(result["action"], "REVIEW_ONLY")
        self.assertGreater(result["quantity_whole_shares"], 0)
        self.assertLessEqual(float(result["estimated_risk_budget_used"]), 1000)

    def test_below_two_to_one_t1_is_rejected(self):
        result = self.plan(targets={"T1": "106"})
        self.assertEqual(result["status"], "rejected")
        self.assertIn("T1_net_reward_risk_below_minimum", result["rejection_reasons"])

    def test_risk_above_cap_raises(self):
        with self.assertRaises(RiskPlanError):
            self.plan(risk_pct="3")

    def test_turnover_participation_caps_quantity(self):
        result = self.plan(average_daily_turnover="10000",
                           max_turnover_participation_pct="1")
        self.assertLessEqual(result["quantity_whole_shares"] * 100, 100)

    def test_t1_is_mandatory(self):
        with self.assertRaises(RiskPlanError):
            self.plan(targets={"T2": "115"})


class ReplayTests(unittest.TestCase):
    def fixture(self):
        start = date(2026, 1, 1)
        bars = []
        for i in range(8):
            bars.append({
                "date": (start + timedelta(days=i)).isoformat(),
                "open": "100", "high": "112" if i == 3 else "105",
                "low": "94" if i == 3 else "99", "close": "105",
            })
        return bars

    def replay(self, bars=None, signals=None):
        return replay_idpat_signals(
            signals=signals or [{"symbol": "TEST", "signal_date": "2026-01-02",
                "entry_reference": "100", "stop": "95", "target": "110", "horizon": "T+2"}],
            bars_by_symbol={"TEST": {"status": "verified", "source_id": "SRC",
                "available_at": "2026-01-10T15:00:00+05:45", "bars": bars or self.fixture()}},
            as_of_date="2026-01-10", as_of_timestamp="2026-01-10T16:00:00+05:45",
            round_trip_cost_pct="0.2", slippage_pct="0.1", min_sample_size=1)

    def test_next_session_entry_and_stop_first_tie(self):
        result = self.replay()
        self.assertEqual(result["trades"][0]["entry_date"], "2026-01-03")
        self.assertEqual(result["trades"][0]["exit_reason"], "stop")

    def test_future_bar_is_rejected(self):
        bars = self.fixture()
        bars[-1]["date"] = "2026-01-11"
        result = self.replay(bars=bars)
        self.assertEqual(result["rejected_signals"][0]["reason"], "invalid_or_future_ohlc_history")

    def test_full_horizon_history_required(self):
        result = self.replay(bars=self.fixture()[:4])
        self.assertEqual(result["rejected_signals"][0]["reason"], "full_horizon_history_unavailable")

    def test_insufficient_sample_not_promoted(self):
        result = replay_idpat_signals(signals=[], bars_by_symbol={},
            as_of_date="2026-01-10", as_of_timestamp="2026-01-10T16:00:00+05:45",
            round_trip_cost_pct="0", slippage_pct="0")
        self.assertEqual(result["status"], "insufficient_sample")
        self.assertIsNone(result["metrics"]["win_rate_pct"])

    def test_walk_forward_split_is_chronological(self):
        rows = [{"signal_date": f"2026-01-{i:02d}", "symbol": "T"} for i in range(1, 11)]
        split = walk_forward_split(rows)
        self.assertEqual(split["train_cutoff"], "2026-01-07")
        self.assertEqual(split["test_start"], "2026-01-08")
        self.assertTrue(split["no_random_shuffle"])


if __name__ == "__main__":
    unittest.main()
