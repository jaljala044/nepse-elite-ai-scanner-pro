import unittest
from app.chronological_ledger_reconciliation import reconcile_chronological_ledger

class CrossLedgerTests(unittest.TestCase):
    def scenario(self):
        days=["2025-01-05","2025-01-06","2025-01-07","2025-01-08","2025-01-09","2025-01-12","2025-01-13"]
        now=days[-1]+"T18:00:00+05:45"
        evidence=dict(status="verified",source_id="synthetic",available_at=now,symbol="ABC")
        buy=dict(evidence,trade_id="B",side="BUY",quantity=10,price=100,fees=0,trade_date=days[0],settlement_date=days[2])
        action=dict(evidence,action_id="A",action_type="bonus",ratio=.2,record_date=days[3],listing_date=days[4])
        inputs=dict(initial_cash=2000,initial_holdings={},trades=[buy],corporate_actions=[action],portfolio_sessions=days,as_of_date=days[-1],evidence_cutoff=now,price_rows_by_symbol={"ABC":[dict(date=d,close=100) for d in days]})
        events=[dict(evidence,event_id="B",type="buy",date=days[0],quantity=10,total_cost=1000,settlement_date=days[2]),
                dict(evidence,event_id="R",type="record",date=days[3],action_id="A",action_type="bonus",ratio=.2),
                dict(evidence,event_id="C",type="credit",date=days[4],action_id="A",quantities={"B":2})]
        return inputs,events
    def test_bonus_reconciliation(self):
        inputs,events=self.scenario()
        result=reconcile_chronological_ledger(ledger_inputs=inputs,events=events)
        self.assertTrue(result["balance_checks_passed"],result["differences"])
        self.assertEqual(result["chronological"]["record_entitlements"]["A"],10)
        self.assertFalse(result["production_eligible"])
    def test_cost_discrepancy(self):
        inputs,events=self.scenario()
        events[0]["total_cost"]=1001
        result=reconcile_chronological_ledger(ledger_inputs=inputs,events=events)
        self.assertFalse(result["balance_checks_passed"])
        self.assertIn("remaining_cost:ABC",result["differences"])
        self.assertIn("cash",result["differences"])
    def test_missing_credit(self):
        inputs,events=self.scenario()
        result=reconcile_chronological_ledger(ledger_inputs=inputs,events=events[:-1])
        self.assertFalse(result["balance_checks_passed"])
        self.assertIn("missing_chronological_event:A:bonus_shares",result["differences"])

    def opening_scenario(self):
        inputs,events=self.scenario()
        inputs["trades"]=[]
        inputs["initial_holdings"]={"ABC":{"quantity":10,"average_cost":100}}
        lots=[dict(lot_id="old",symbol="ABC",quantity=10,total_cost=1000,
                   acquisition_date="2024-12-20",settlement_date="2024-12-24",
                   status="verified",source_id="synthetic",available_at=inputs["evidence_cutoff"])]
        events=events[1:]
        events[1]["quantities"]={"old":2}
        return inputs,events,lots
    def test_opening_lot_reconciliation(self):
        inputs,events,lots=self.opening_scenario()
        result=reconcile_chronological_ledger(ledger_inputs=inputs,events=events,opening_lots=lots)
        self.assertTrue(result["balance_checks_passed"],result["differences"])
        self.assertEqual(result["chronological"]["available_cash"],"2000")
    def test_opening_cost_mismatch(self):
        inputs,events,lots=self.opening_scenario()
        lots[0]["total_cost"]=999
        with self.assertRaisesRegex(ValueError,"opening_lot_balance_mismatch"):
            reconcile_chronological_ledger(ledger_inputs=inputs,events=events,opening_lots=lots)
    def test_opening_unsettled_lot(self):
        inputs,events,lots=self.opening_scenario()
        lots[0]["settlement_date"]=inputs["portfolio_sessions"][0]
        with self.assertRaisesRegex(ValueError,"invalid_opening_lot"):
            reconcile_chronological_ledger(ledger_inputs=inputs,events=events,opening_lots=lots)
    def test_opening_duplicate_lot(self):
        inputs,events,lots=self.opening_scenario()
        lots[0]["quantity"]=5
        lots[0]["total_cost"]=500
        with self.assertRaisesRegex(ValueError,"invalid_opening_lot"):
            reconcile_chronological_ledger(ledger_inputs=inputs,events=events,opening_lots=lots*2)
