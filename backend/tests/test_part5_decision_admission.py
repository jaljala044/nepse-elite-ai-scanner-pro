import unittest
from app.part5_decision_admission import admit_decision, mature_training_rows
from app.execution_costs import round_trip
from app.execution_constraints import settlement_date, exit_scenario
from datetime import date

class Part5Regression(unittest.TestCase):
    def setUp(self):
        d = "2025-01-02"
        self.inputs = dict(segment=dict(symbol="TEST",security_id="synthetic",identity_verified=True,
            effective_from=d,effective_to=None,boundary_reviewed=True,suspension_overlap=False,
            merger_or_successor_boundary=False,adjustment_basis="raw",minimum_warmup_sessions=0),
            expected_sessions=[d],session_statuses={d:"traded"},required_sessions=1,
            available_warmup_sessions=0,records=[dict(session_date=d,symbol="TEST",
            security_id="synthetic",open=100,high=105,low=95,close=102,volume=1000,
            adjustment_basis="raw",rights_status="approved",evidence_sha256="a"*64,
            available_at=d+"T15:00:00+05:45")])
        self.cutoff=d+"T16:00:00+05:45"
        self.feature=dict(record_id="f",event_at=d+"T15:00:00+05:45",
            available_at=self.cutoff,evidence_reviewed=True)

    def admit(self, features):
        return admit_decision(segment_inputs=self.inputs,decision_time=self.cutoff,features=features)

    def test_eligible_segment_is_research_only(self):
        result=self.admit([self.feature])
        self.assertTrue(result["exploratory_eligible"])
        self.assertFalse(result["approved_backtest_eligible"])

    def test_missing_bar(self):
        self.inputs["records"]=[]
        self.assertFalse(self.admit([self.feature])["exploratory_eligible"])

    def test_empty_and_future_features(self):
        self.assertFalse(self.admit([])["exploratory_eligible"])
        self.assertFalse(self.admit([dict(self.feature,available_at="2025-01-03T00:00:00+05:45")])["exploratory_eligible"])

    def test_duplicate_feature(self):
        self.assertFalse(self.admit([self.feature,self.feature])["exploratory_eligible"])

    def test_label_maturity(self):
        row=dict(record_id="a",decision_at="2025-01-02T12:00:00Z",
            feature_available_at="2025-01-02T11:00:00Z",label_end_at="2025-01-03T12:00:00Z",
            label_available_at="2025-01-03T13:00:00Z")
        args=dict(fit_cutoff="2025-01-04T00:00:00Z",first_test_decision="2025-01-05T00:00:00Z")
        result=mature_training_rows([row,dict(row,record_id="b",label_available_at="2025-01-06T00:00:00Z")],**args)
        self.assertEqual(result["included_ids"],["a"])
        self.assertEqual(result["excluded_ids"],["b"])

    def test_independent_synthetic_cost_arithmetic(self):
        # Buy 1000 + 10 brokerage + 1 regulatory = 1011.
        # Sell 1200 - 12 brokerage - 1.2 regulatory - 5 DP = 1181.8.
        # Pretax gain 170.8; 5% scenario tax 8.54; net 162.26.
        result=round_trip(100,120,10,assumptions=dict(buy_broker_rate=.01,
            sell_broker_rate=.01,regulatory_rate=.001,sell_dp_charge=5,
            capital_gain_tax_rate=.05,slippage_bps=0,min_broker_fee=0))
        self.assertAlmostEqual(result["net_pnl"],162.26)
        self.assertAlmostEqual(result["tax"],8.54)
        self.assertFalse(result["production_eligible"])

    def test_settlement_and_gap_stop(self):
        self.assertEqual(settlement_date("2025-01-02",["2025-01-05","2025-01-06"]),date(2025,1,6))
        bar=dict(open=94,high=98,low=93,close=96,volume=1000)
        args=dict(stop=95,target=110,band=dict(lower=90,upper=110),eligible=True)
        self.assertIsNone(exit_scenario(bar,settled_before_session=False,**args)["price"])
        self.assertEqual(exit_scenario(bar,settled_before_session=True,**args)["price"],94)

    def test_limit_down_no_fill(self):
        bar=dict(open=90,high=90,low=90,close=90,volume=1000)
        result=exit_scenario(bar,stop=95,target=110,band=dict(lower=90,upper=110),
            eligible=True,settled_before_session=True)
        self.assertEqual(result["status"],"limit_down_execution_unverified")
        self.assertIsNone(result["price"])
