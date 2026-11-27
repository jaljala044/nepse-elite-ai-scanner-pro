import unittest
from app.scanner_portfolio_risk_dashboard import build_portfolio_risk_dashboard
from app.scanner_walk_forward_diagnostics import diagnose_walk_forward_folds


class PortfolioRiskDashboardTests(unittest.TestCase):
    def base_portfolio(self):
        return {
            "initial_equity": "100000",
            "accepted_positions": [
                {"source_signal_id":"A","symbol":"AAA","sector":"Hydro","entry_date":"2026-01-01",
                 "scheduled_exit_date":"2026-01-04","allocated_notional":"30000","risk_budget":"1000"},
                {"source_signal_id":"B","symbol":"BBB","sector":"Hydro","entry_date":"2026-01-02",
                 "scheduled_exit_date":"2026-01-05","allocated_notional":"20000","risk_budget":"1000"},
                {"source_signal_id":"C","symbol":"CCC","entry_date":"2026-01-02",
                 "scheduled_exit_date":"2026-01-05","allocated_notional":"10000","risk_budget":"500"},
            ],
            "closed_positions": [], "open_position_count": 3,
        }

    def test_exposure_concentration_and_unknown_sector_coverage(self):
        comparison={"partition":"out_of_sample","portfolios":[{"strategy_id":"trend_momentum",
            "horizon":"swing","partition":"out_of_sample","portfolio":self.base_portfolio()}]}
        out=build_portfolio_risk_dashboard(comparison=comparison)
        row=out["reports"][0]
        self.assertEqual(row["status"],"CONCENTRATION_WARNING")
        self.assertEqual(row["peak_sector"],"Hydro")
        self.assertEqual(row["peak_sector_exposure_pct_equity"],"50.0")
        self.assertEqual(row["sector_coverage"],"INCOMPLETE")
        self.assertEqual(row["missing_sector_position_count"],1)

    def test_strategy_portfolios_are_not_pooled_even_for_same_symbol(self):
        one=self.base_portfolio()
        two=self.base_portfolio()
        one["accepted_positions"]=[{**one["accepted_positions"][0],"symbol":"SAME"}]
        one["open_position_count"]=1
        two["accepted_positions"]=[{**two["accepted_positions"][0],"symbol":"SAME"}]
        two["open_position_count"]=1
        out=build_portfolio_risk_dashboard(comparison={"portfolios":[
            {"strategy_id":"trend_momentum","horizon":"swing","portfolio":one},
            {"strategy_id":"idpat_smart_money","horizon":"swing","portfolio":two},
        ]})
        self.assertEqual(out["portfolio_count"],2)
        self.assertEqual([x["peak_symbol_exposure"] for x in out["reports"]],["30000","30000"])
        self.assertIn("never sum",out["aggregation_policy"])

    def test_duplicate_or_missing_position_ids_rejected(self):
        p=self.base_portfolio()
        p["accepted_positions"][1]["source_signal_id"]="A"
        with self.assertRaisesRegex(ValueError,"accepted_position_id_missing_or_duplicate"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})
        p=self.base_portfolio()
        p["accepted_positions"][0].pop("source_signal_id")
        with self.assertRaisesRegex(ValueError,"accepted_position_id_missing_or_duplicate"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})

    def test_duplicate_or_orphan_close_rejected(self):
        p=self.base_portfolio()
        p["closed_positions"]=[
            {"source_signal_id":"A","exit_date":"2026-01-03"},
            {"source_signal_id":"A","exit_date":"2026-01-03"},
        ]
        with self.assertRaisesRegex(ValueError,"closed_position_id_missing_or_duplicate"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})
        p=self.base_portfolio()
        p["closed_positions"]=[{"source_signal_id":"UNKNOWN","exit_date":"2026-01-03"}]
        with self.assertRaisesRegex(ValueError,"closed_position_without_accepted_entry"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})

    def test_dates_are_canonical_and_intervals_ordered(self):
        p=self.base_portfolio()
        p["accepted_positions"][0]["entry_date"]="2026/01/01"
        with self.assertRaisesRegex(ValueError,"entry_date_must_be_iso_date"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})
        p=self.base_portfolio()
        p["accepted_positions"][0]["scheduled_exit_date"]="2025-12-31"
        with self.assertRaisesRegex(ValueError,"scheduled_exit_precedes_entry"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})
        p=self.base_portfolio()
        p["closed_positions"]=[{"source_signal_id":"A","exit_date":"2025-12-31"}]
        with self.assertRaisesRegex(ValueError,"closed_position_exit_precedes_entry"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})

    def test_open_position_without_scheduled_exit_fails_closed(self):
        p=self.base_portfolio()
        p["accepted_positions"][0].pop("scheduled_exit_date")
        with self.assertRaisesRegex(ValueError,"open_position_scheduled_exit_missing"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})

    def test_closed_open_position_reconciliation(self):
        p=self.base_portfolio()
        p["closed_positions"]=[{"source_signal_id":"A","exit_date":"2026-01-03"}]
        p["open_position_count"]=2
        out=build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})
        self.assertEqual(out["reports"][0]["ending_open_position_count"],2)
        p["open_position_count"]=3
        with self.assertRaisesRegex(ValueError,"open_position_count_reconciliation_failed"):
            build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})

    def test_closed_position_interval_ends_on_actual_exit(self):
        p=self.base_portfolio()
        p["closed_positions"]=[{"source_signal_id":"A","exit_date":"2026-01-03"}]
        p["open_position_count"]=2
        out=build_portfolio_risk_dashboard(comparison={"portfolios":[{"portfolio":p}]})
        daily={x["date"]:x for x in out["reports"][0]["daily_exposure"]}
        self.assertEqual(daily["2026-01-03"]["open_positions"],2)


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


if __name__ == "__main__":
    unittest.main()
