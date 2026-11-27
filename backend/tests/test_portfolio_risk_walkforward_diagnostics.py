import unittest
from app.scanner_portfolio_risk_dashboard import build_portfolio_risk_dashboard
from app.scanner_walk_forward_diagnostics import diagnose_walk_forward_folds

class PortfolioRiskDashboardTests(unittest.TestCase):
    def test_exposure_concentration_and_unknown_sector_coverage(self):
        comparison={"partition":"out_of_sample","portfolios":[{"strategy_id":"trend_momentum","horizon":"swing",
            "partition":"out_of_sample","portfolio":{"initial_equity":"100000","accepted_positions":[
                {"source_signal_id":"A","symbol":"AAA","sector":"Hydro","entry_date":"2026-01-01",
                 "scheduled_exit_date":"2026-01-04","allocated_notional":"30000","risk_budget":"1000"},
                {"source_signal_id":"B","symbol":"BBB","sector":"Hydro","entry_date":"2026-01-02",
                 "scheduled_exit_date":"2026-01-05","allocated_notional":"20000","risk_budget":"1000"}],
                "closed_positions":[],"open_position_count":2}}]}
        out=build_portfolio_risk_dashboard(comparison=comparison)
        row=out["reports"][0]
        self.assertEqual(row["status"],"CONCENTRATION_WARNING")
        self.assertEqual(row["peak_sector"],"Hydro")
        self.assertEqual(row["peak_sector_exposure_pct_equity"],"50")
        self.assertEqual(row["sector_coverage"],"COMPLETE")
    def test_strategy_portfolios_are_not_pooled(self):
        out=build_portfolio_risk_dashboard(comparison={"portfolios":[
            {"portfolio":{"initial_equity":"100","accepted_positions":[],"closed_positions":[]}},
            {"portfolio":{"initial_equity":"100","accepted_positions":[],"closed_positions":[]}}]})
        self.assertEqual(out["portfolio_count"],2)
        self.assertIn("never sum",out["aggregation_policy"])

class WalkForwardDiagnosticsTests(unittest.TestCase):
    def test_stable_candidate_requires_multiple_profitable_oos_folds(self):
        folds=[]
        for i in range(3):
            folds.append({"strategy_id":"trend_momentum","horizon":"swing","fold_id":f"F{i}",
                "partition":"out_of_sample","metrics":{"closed_trade_count":12,
                "expectancy_net_pct_per_trade":"1.2","profit_factor":"1.4","max_drawdown_pct":"10"}})
        out=diagnose_walk_forward_folds(fold_results=folds)
        row=out["results"][0]
        self.assertTrue(row["eligible_for_selection"])
        self.assertEqual(row["total_closed_trade_count"],36)
        self.assertEqual(out["best_strategy_by_horizon"]["swing"]["strategy_id"],"trend_momentum")
    def test_one_bad_fold_blocks_selection(self):
        folds=[]
        for i in range(3):
            folds.append({"strategy_id":"idpat_smart_money","horizon":"t_plus_2","fold_id":f"F{i}",
                "partition":"out_of_sample","metrics":{"closed_trade_count":12,
                "expectancy_net_pct_per_trade":"-0.1" if i==2 else "1.2",
                "profit_factor":"0.8" if i==2 else "1.4","max_drawdown_pct":"10"}})
        out=diagnose_walk_forward_folds(fold_results=folds)
        self.assertFalse(out["results"][0]["eligible_for_selection"])
        self.assertIsNone(out["best_strategy_by_horizon"]["t_plus_2"])
    def test_duplicate_fold_and_validation_partition(self):
        row={"strategy_id":"trend_momentum","horizon":"swing","fold_id":"F1","partition":"out_of_sample",
            "metrics":{"closed_trade_count":30,"expectancy_net_pct_per_trade":"1","profit_factor":"1.2","max_drawdown_pct":"10"}}
        with self.assertRaisesRegex(ValueError,"duplicate_strategy_horizon_fold"):
            diagnose_walk_forward_folds(fold_results=[row,row])
        out=diagnose_walk_forward_folds(fold_results=[{**row,"partition":"validation"}])
        self.assertEqual(out["results"],[])

if __name__=="__main__": unittest.main()
