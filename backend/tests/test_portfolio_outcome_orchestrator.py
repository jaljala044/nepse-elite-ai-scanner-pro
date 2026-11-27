import unittest
from app.scanner_portfolio_outcome_orchestrator import run_portfolio_outcome_comparison

class PortfolioOutcomeOrchestratorTests(unittest.TestCase):
    def test_runs_independent_strategy_horizon_portfolios_and_oos_ledger(self):
        trade={"source_signal_id":"SIG1","symbol":"AAA","strategy_id":"trend_momentum","horizon":"swing",
            "entry_date":"2026-01-02","exit_date":"2026-01-05","decision_time":"2026-01-02T00:00:00+00:00",\n            "feature_snapshot_sha256":"a"*64,"replay_policy_sha256":"d"*64,"entry_price":"100","stop_price":"90",
            "target_price":"120","exit_price":"110","exit_reason":"target","net_return_pct":"9.2","liquidity_quantity_cap":100}
        bundle={"runs":[{"strategy_id":"trend_momentum","horizon":"swing","partition":"out_of_sample",
            "trades":[trade],"pending_exits":[],"metrics":{}},
            {"strategy_id":"idpat_smart_money","horizon":"swing","partition":"out_of_sample",
            "trades":[],"pending_exits":[],"metrics":{}},
            {"strategy_id":"trend_momentum","horizon":"swing","partition":"train",
            "trades":[],"pending_exits":[],"metrics":{}}]}
        signals=[{"signal_id":"SIG1","symbol":"AAA","strategy_id":"trend_momentum","horizon":"swing",
            "decision_time":"2026-01-02T00:00:00+00:00","feature_snapshot_sha256":"a"*64,\n            "action":"RESEARCH_BUY_FOR_HUMAN_REVIEW","sample_partition":"out_of_sample"}]
        out=run_portfolio_outcome_comparison(replay_bundle=bundle,signals=signals,
            portfolio_config={"initial_equity":"100000"})
        self.assertEqual(out["portfolio_run_count"],2)
        self.assertEqual(out["signal_outcome_ledger"]["outcomes"][0]["outcome"],"target_hit")
        self.assertEqual(out["partition"],"out_of_sample")
    def test_cross_partition_signal_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"signal_partition_mismatch"):
            run_portfolio_outcome_comparison(replay_bundle={"runs":[]},
                signals=[{"signal_id":"X","sample_partition":"train"}],partition="out_of_sample")

if __name__=="__main__":unittest.main()
