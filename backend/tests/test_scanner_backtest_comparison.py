import unittest
from app.scanner_backtest import replay_strategy_horizon
from app.scanner_strategy_comparison import compare_strategy_results

def bar(day,o,h,l,c):
    return {"date":day,"open":o,"high":h,"low":l,"close":c,"volume":10000,
        "evidence_status":"verified","source_id":"OHLCV","evidence_id":"BAR-"+day,
        "available_at":day+"T16:00:00+05:45"}

def signal():
    return {"strategy_id":"trend_momentum","horizon":"swing","symbol":"TEST",
        "decision_date":"2026-01-01","decision_time":"2026-01-01T15:00:00+05:45",
        "sample_partition":"out_of_sample","signal_id":"SIG-1",
        "stop":{"price":"90","evidence_status":"verified","source_id":"LEVEL","evidence_id":"STOP","available_at":"2026-01-01T14:00:00+05:45"},
        "target":{"price":"120","evidence_status":"verified","source_id":"LEVEL","evidence_id":"TARGET","available_at":"2026-01-01T14:00:00+05:45"}}

class ReplayTests(unittest.TestCase):
    def replay(self,bars,delay=0):
        return replay_strategy_horizon(strategy_id="trend_momentum",horizon="swing",
            signals=[signal()],bars_by_symbol={"TEST":bars},partition="out_of_sample",
            round_trip_cost_pct="0.4",round_trip_slippage_pct="0.2",sellable_after_sessions=delay)
    def test_next_session_entry_and_target_exit_net_of_costs(self):
        r=self.replay([bar("2026-01-01",100,101,99,100),bar("2026-01-02",100,121,99,115)])
        self.assertEqual(r["metrics"]["sample_size"],1); self.assertEqual(r["trades"][0]["exit_reason"],"target")
        self.assertLess(float(r["trades"][0]["net_return_pct"]),20)
    def test_stop_wins_when_stop_and_target_both_hit(self):
        r=self.replay([bar("2026-01-01",100,101,99,100),bar("2026-01-02",100,121,89,100)])
        self.assertEqual(r["trades"][0]["exit_reason"],"stop")
    def test_settlement_lock_delays_stop_exit_until_sellable(self):
        r=self.replay([bar("2026-01-01",100,101,99,100),bar("2026-01-02",100,110,89,95),bar("2026-01-03",92,100,91,96),bar("2026-01-04",93,100,92,98)],delay=2)
        self.assertEqual(r["trades"][0]["exit_reason"],"stop_exit_after_settlement_lock")
        self.assertEqual(r["trades"][0]["exit_date"],"2026-01-04")
    def test_future_signal_evidence_is_rejected(self):
        s=signal(); s["stop"]["available_at"]="2026-01-02T15:00:00+05:45"
        r=replay_strategy_horizon(strategy_id="trend_momentum",horizon="swing",signals=[s],
            bars_by_symbol={"TEST":[bar("2026-01-01",100,101,99,100),bar("2026-01-02",100,110,99,105)]},
            partition="out_of_sample",round_trip_cost_pct=0,round_trip_slippage_pct=0,sellable_after_sessions=0)
        self.assertEqual(r["metrics"]["rejected_signals"],1)
    def test_duplicate_bars_rejected(self):
        r=self.replay([bar("2026-01-01",100,101,99,100),bar("2026-01-02",100,110,99,105),bar("2026-01-02",100,110,99,105)])
        self.assertEqual(r["metrics"]["rejected_signals"],1)

class ComparisonTests(unittest.TestCase):
    def result(self,s,h,n=40,e="2",pf="1.5",dd="10"):
        return {"strategy_id":s,"horizon":h,"partition":"out_of_sample",
            "metrics":{"sample_size":n,"expectancy_net_pct_per_trade":e,"profit_factor":pf,"max_drawdown_pct":dd,"win_rate_pct":"55"}}
    def test_winner_selected_per_horizon_only_with_oos_gate(self):
        rs=[self.result("trend_momentum","swing"),self.result("idpat_smart_money","swing",e="3"),
            self.result("broker_footprint","t_plus_2",n=10),self.result("smc_ict_liquidity","positional",pf="0.8"),
            self.result("hybrid_consensus","investment",dd="30"),self.result("fundamental_investment","investment",e="4",pf="2")]
        out=compare_strategy_results(replay_results=rs,minimum_sample=30)
        self.assertEqual(out["best_strategy_by_horizon"]["swing"]["strategy_id"],"idpat_smart_money")
        self.assertIsNone(out["best_strategy_by_horizon"]["t_plus_2"])
        self.assertEqual(out["best_strategy_by_horizon"]["investment"]["strategy_id"],"fundamental_investment")
    def test_in_sample_results_not_used(self):
        r=self.result("trend_momentum","swing"); r["partition"]="train"
        self.assertIsNone(compare_strategy_results(replay_results=[r])["best_strategy_by_horizon"]["swing"])
    def test_duplicate_strategy_horizon_rejected(self):
        r=self.result("trend_momentum","swing")
        with self.assertRaisesRegex(ValueError,"duplicate_strategy_horizon"): compare_strategy_results(replay_results=[r,r])

if __name__=="__main__": unittest.main()
