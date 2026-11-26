import unittest
from app.early_entry_exit_signals import SignalEngineError, generate_early_entry_exit_signals


def snapshot():
    stamp = "2026-11-26T10:00:00+05:45"
    def ev(source, **values):
        return {"status":"verified","source_id":source,"coverage":"1","available_at":stamp,**values}
    plan = {"setup":"momentum_breakout","entry_type":"breakout_retest","confirmation":"confirmed",
            "entry":"100","stop":"94","targets":["112","118","125"],
            "invalidation_condition":"close_below_stop","level_status":"inferred_chart_level",
            "evidence_dates":["2026-11-25","2026-11-26"]}
    return {"symbol":"CFCL","as_of_date":"2026-11-26","available_at":stamp,
      "market":ev("MARKET",regime="bull"),
      "sector":ev("SECTOR",alignment="leading_or_improving",excess_return_1m="2.5"),
      "liquidity":ev("LIQ",median_turnover="5000000",median_spread_pct="0.8",
                     median_trade_count="80",median_displayed_depth="500000"),
      "broker":ev("BROKER",net_amount="100000",positive_net_session_ratio="0.7"),
      "price_volume":ev("OHLCV",structure="bullish_bos"),
      "candidate":ev("CANDIDATE",classification="early_accumulation_candidate"),
      "plans":{"t_plus_2":plan,"swing":plan,"positional":plan}}


class SignalEngineTests(unittest.TestCase):
    def runit(self, data=None, **kwargs):
        return generate_early_entry_exit_signals(data or snapshot(),as_of_date="2026-11-26",
            as_of_timestamp="2026-11-26T12:00:00+05:45",**kwargs)

    def test_all_horizons_separate_and_confirmed(self):
        result=self.runit()
        self.assertEqual(result["action"],"BUY")
        self.assertEqual(set(result["horizons"]),{"t_plus_2","swing","positional"})
        self.assertEqual(result["horizons"]["t_plus_2"]["action"],"BUY")
        self.assertEqual(result["horizons"]["t_plus_2"]["targets"][0]["label"],"T1")
        self.assertEqual(result["horizons"]["swing"]["reward_risk"],"2")

    def test_late_snapshot_withheld(self):
        data=snapshot(); data["available_at"]="2026-11-27T09:00:00+05:45"
        self.assertEqual(self.runit(data)["action"],"NO_TRADE")

    def test_unverified_market_fails_closed(self):
        data=snapshot(); data["market"]["status"]="unverified"
        self.assertIn("market_not_verified",self.runit(data)["common_reasons"])

    def test_late_broker_evidence_fails_closed(self):
        data=snapshot(); data["broker"]["available_at"]="2026-11-27T09:00:00+05:45"
        self.assertIn("broker_not_available_as_of_cutoff",self.runit(data)["common_reasons"])

    def test_low_coverage_fails_closed(self):
        data=snapshot(); data["sector"]["coverage"]="0.80"
        self.assertIn("sector_coverage_below_threshold",self.runit(data)["common_reasons"])

    def test_weak_market_regime_fails_closed(self):
        data=snapshot(); data["market"]["regime"]="distribution"
        self.assertIn("market_regime_not_supportive_or_unknown",self.runit(data)["common_reasons"])

    def test_weak_sector_fails_closed(self):
        data=snapshot(); data["sector"]["excess_return_1m"]="-1"
        self.assertIn("sector_alignment_not_confirmed",self.runit(data)["common_reasons"])

    def test_illiquidity_fails_closed(self):
        data=snapshot(); data["liquidity"]["median_turnover"]="100"
        self.assertIn("liquidity_execution_threshold_failed",self.runit(data)["common_reasons"])

    def test_broker_flow_not_a_signal(self):
        data=snapshot(); data["broker"]["net_amount"]="-100"
        self.assertIn("broker_flow_not_supportive",self.runit(data)["common_reasons"])

    def test_distribution_candidate_fails_closed(self):
        data=snapshot(); data["candidate"]["classification"]="distribution_risk_candidate"
        self.assertIn("distribution_risk_candidate",self.runit(data)["common_reasons"])

    def test_missing_horizon_plan_no_trade_only_that_horizon(self):
        data=snapshot(); del data["plans"]["t_plus_2"]
        result=self.runit(data)
        self.assertEqual(result["horizons"]["t_plus_2"]["action"],"NO_TRADE")
        self.assertEqual(result["horizons"]["swing"]["action"],"BUY")

    def test_rr_below_two_rejected(self):
        data=snapshot(); data["plans"]["swing"]["targets"]=["110"]
        result=self.runit(data)
        self.assertEqual(result["horizons"]["swing"]["action"],"NO_TRADE")
        self.assertIn("nearest_target_reward_risk_below_minimum",result["horizons"]["swing"]["reasons"])

    def test_unconfirmed_breakout_rejected(self):
        data=snapshot(); data["plans"]["swing"]["confirmation"]="watch"
        self.assertEqual(self.runit(data)["horizons"]["swing"]["action"],"NO_TRADE")

    def test_unproven_levels_rejected(self):
        data=snapshot(); data["plans"]["swing"]["level_status"]="verified_order_book"
        self.assertEqual(self.runit(data)["horizons"]["swing"]["action"],"NO_TRADE")

    def test_minimum_rr_cannot_be_weakened(self):
        with self.assertRaises(SignalEngineError):
            self.runit(minimum_reward_risk="1.5")



    def test_exit_review_missing_is_unknown_not_hold(self):
        result = self.runit()
        self.assertEqual(result["exit_reviews"]["swing"]["action"], "NO_TRADE")
        self.assertEqual(result["exit_reviews"]["swing"]["status"], "unknown")

    def test_verified_breakdown_requires_sell_or_reduce(self):
        data = snapshot()
        stamp = data["available_at"]
        data["exit_evidence"] = {"status":"verified","source_id":"EXIT_A","coverage":"1",
            "available_at":stamp,"horizons":{"swing":{"status":"confirmed",
            "triggers":["structural_breakdown"]}}}
        result = self.runit(data)
        self.assertEqual(result["exit_reviews"]["swing"]["action"], "SELL_OR_REDUCE")
        self.assertEqual(result["action"], "SELL_OR_REDUCE")

    def test_verified_no_exit_trigger_is_cautious_hold(self):
        data = snapshot()
        stamp = data["available_at"]
        data["exit_evidence"] = {"status":"verified","source_id":"EXIT_A","coverage":"1",
            "available_at":stamp,"horizons":{"swing":{"status":"confirmed","triggers":["none"]}}}
        result = self.runit(data)
        self.assertEqual(result["exit_reviews"]["swing"]["action"], "HOLD_WITH_CAUTION")

    def test_late_exit_evidence_is_unknown(self):
        data = snapshot()
        data["exit_evidence"] = {"status":"verified","source_id":"EXIT_A","coverage":"1",
            "available_at":"2026-11-27T09:00:00+05:45",
            "horizons":{"swing":{"status":"confirmed","triggers":["stop_triggered"]}}}
        result = self.runit(data)
        self.assertEqual(result["exit_reviews"]["swing"]["action"], "NO_TRADE")
        self.assertIn("exit_not_available_as_of_cutoff", result["exit_reviews"]["swing"]["reasons"])

    def test_unknown_exit_trigger_rejected(self):
        data = snapshot()
        stamp = data["available_at"]
        data["exit_evidence"] = {"status":"verified","source_id":"EXIT_A","coverage":"1",
            "available_at":stamp,"horizons":{"swing":{"status":"confirmed","triggers":["operator_activity"]}}}
        result = self.runit(data)
        self.assertEqual(result["exit_reviews"]["swing"]["action"], "NO_TRADE")
        self.assertIn("invalid_exit_trigger_evidence", result["exit_reviews"]["swing"]["reasons"])

if __name__=="__main__": unittest.main()
