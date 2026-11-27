import unittest
from app.scanner_strategy_selection import select_six_strategies
from app.scanner_feature_ablation import compare_feature_ablations

def _folds(strategy="trend_momentum",horizon="swing"):
    return [{"strategy_id":strategy,"horizon":horizon,"fold_id":f"F{i}","partition":"out_of_sample",
        "metrics":{"closed_trade_count":12,"expectancy_net_pct_per_trade":"1.1","profit_factor":"1.3","max_drawdown_pct":"8"}} for i in range(3)]

def _portfolio(strategy="trend_momentum",horizon="swing"):
    closed=[{"net_return_pct":"2","net_pnl":"200","exit_date":"2026-01-02"},
            {"net_return_pct":"1","net_pnl":"100","exit_date":"2026-01-03"}]*16
    return {"strategy_id":strategy,"horizon":horizon,"partition":"out_of_sample",
        "portfolio":{"closed_positions":closed,"max_realized_equity_drawdown_pct":"8"}}

class StrategySelectionTests(unittest.TestCase):
    def test_requires_both_portfolio_and_fold_gates(self):
        out=select_six_strategies(portfolio_comparison={"partition":"out_of_sample","portfolios":[_portfolio()]},
            fold_results=_folds(),minimum_total_trades=30)
        self.assertEqual(out["best_strategy_by_horizon"]["swing"]["strategy_id"],"trend_momentum")
    def test_missing_fold_or_portfolio_withholds_winner(self):
        out=select_six_strategies(portfolio_comparison={"partition":"out_of_sample","portfolios":[_portfolio()]},
            fold_results=[],minimum_total_trades=30)
        self.assertIsNone(out["best_strategy_by_horizon"]["swing"])
    def test_rejects_non_oos_portfolio_comparison(self):
        with self.assertRaisesRegex(ValueError,"selection_requires_out_of_sample"):
            select_six_strategies(portfolio_comparison={"partition":"validation","portfolios":[]},fold_results=[])

class FeatureAblationTests(unittest.TestCase):
    def _row(self,delta="1"):
        base={"universe_fingerprint":"u1","panel_fingerprint":"p1","cost_model_id":"c1","execution_model_id":"e1",
            "closed_trades":[{"net_return_pct":"1","exit_date":"2026-01-02"} for _ in range(12)]}
        ablated={**base,"closed_trades":[{"net_return_pct":delta,"exit_date":"2026-01-02"} for _ in range(12)]}
        return {"strategy_id":"trend_momentum","horizon":"swing","feature_group":"volume_cluster",
            "partition":"out_of_sample","baseline":base,"ablated":ablated}
    def test_removal_improves_when_ablation_oos_returns_higher(self):
        rows=[]
        for i in range(3):
            row=self._row("2");row["fold_id"]=f"F{i}";rows.append(row)
        out=compare_feature_ablations(ablation_runs=rows)
        result=out["results"][0]
        self.assertEqual(result["direction"],"removal_improves")
        self.assertTrue(result["eligible_for_interpretation"])
    def test_mismatched_cost_model_is_rejected(self):
        row=self._row("2");row["fold_id"]="F1";row["ablated"]={**row["ablated"],"cost_model_id":"different"}
        out=compare_feature_ablations(ablation_runs=[row])
        self.assertEqual(out["results"],[])
        self.assertEqual(out["rejected_records"][0]["reason"],"comparison_assumptions_or_panel_mismatch")
    def test_duplicate_fold_rejected(self):
        row=self._row("2");row["fold_id"]="F1"
        with self.assertRaisesRegex(ValueError,"duplicate_feature_ablation_fold"):
            compare_feature_ablations(ablation_runs=[row,row])

if __name__=="__main__": unittest.main()
