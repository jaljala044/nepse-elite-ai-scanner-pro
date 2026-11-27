import unittest
from app.scanner_portfolio_replay import replay_portfolio
from app.scanner_signal_outcome_ledger import build_signal_outcome_ledger

def trade(sid,entry_day,exit_day,net="5",cap=1000):
    return {"source_signal_id":sid,"symbol":sid,"strategy_id":"trend_momentum","horizon":"swing",
        "entry_date":entry_day,"exit_date":exit_day,"entry_price":"100","stop_price":"90",
        "target_price":"120","exit_price":"105","net_return_pct":net,"liquidity_quantity_cap":cap}

class PortfolioReplayTests(unittest.TestCase):
    def test_overlapping_positions_respect_cash_risk_and_exposure(self):
        out=replay_portfolio(trades=[trade("A","2026-01-02","2026-01-05"),
            trade("B","2026-01-03","2026-01-06"),trade("C","2026-01-05","2026-01-07")],
            initial_equity="100000",max_position_pct="20",max_portfolio_exposure_pct="40",
            max_open_positions=2)
        self.assertGreaterEqual(out["accepted_position_count"],2)
        self.assertEqual(out["status"],"completed")
        self.assertEqual(out["open_position_count"],0)
        self.assertGreater(float(out["ending_equity_at_cost"]),100000)
    def test_missing_liquidity_cap_fails_closed(self):
        out=replay_portfolio(trades=[trade("A","2026-01-02","2026-01-05",cap=None)])
        self.assertEqual(out["accepted_position_count"],0)
        self.assertEqual(out["rejected_trades"][0]["reason"],"verified_liquidity_quantity_cap_missing")
    def test_duplicate_signal_ids_rejected(self):
        out=replay_portfolio(trades=[trade("A","2026-01-02","2026-01-05"),trade("A","2026-01-03","2026-01-06")])
        self.assertEqual(out["rejected_trades"][0]["reason"],"missing_or_duplicate_signal_id")
    def test_bad_stop_and_exit_dates_rejected(self):
        t=trade("A","2026-01-05","2026-01-02"); t["stop_price"]="100"
        out=replay_portfolio(trades=[t])
        self.assertEqual(out["accepted_position_count"],0)

class SignalLedgerTests(unittest.TestCase):
    def test_append_only_signal_outcome_events_and_horizon_metrics(self):
        signals=[{"signal_id":"A","symbol":"AAA","strategy_id":"trend_momentum","horizon":"swing","action":"RESEARCH_BUY_FOR_HUMAN_REVIEW"},
            {"signal_id":"B","symbol":"BBB","strategy_id":"trend_momentum","horizon":"swing","action":"NO_TRADE"},
            {"signal_id":"C","symbol":"CCC","strategy_id":"idpat_smart_money","horizon":"t_plus_2","action":"RESEARCH_BUY_FOR_HUMAN_REVIEW"}]
        replay=[{"trades":[{"source_signal_id":"A","exit_reason":"target","entry_date":"2026-01-02","exit_date":"2026-01-04",
            "net_return_pct":"4.5","max_favorable_excursion_pct":"7","max_adverse_excursion_pct":"-1.2","holding_sessions":3}],
            "pending_exits":[{"source_signal_id":"C"}]}]
        out=build_signal_outcome_ledger(signals=signals,replay_results=replay)
        self.assertEqual(out["signal_event_count"],3)
        self.assertEqual(out["outcome_event_count"],3)
        self.assertEqual(out["outcomes"][0]["outcome"],"target_hit")
        self.assertEqual(out["outcomes"][1]["outcome"],"not_executed")
        self.assertEqual(out["outcomes"][2]["outcome"],"settlement_or_horizon_pending")
        self.assertEqual(out["strategy_horizon_summaries"][0]["target_hit_count"],1)
        self.assertEqual(len(out["events"]),6)
    def test_duplicate_replay_outcome_is_rejected(self):
        trade={"source_signal_id":"A","exit_reason":"target"}
        with self.assertRaisesRegex(ValueError,"duplicate_replay_outcome_for_signal"):
            build_signal_outcome_ledger(signals=[{"signal_id":"A","action":"BUY"}],
                replay_results=[{"trades":[trade]},{"trades":[trade]}])
    def test_missing_signal_id_is_not_silently_logged(self):
        out=build_signal_outcome_ledger(signals=[{"action":"NO_TRADE"}],replay_results=[])
        self.assertEqual(out["rejected_signal_records"][0]["reason"],"missing_or_duplicate_signal_id")

if __name__=="__main__":unittest.main()
