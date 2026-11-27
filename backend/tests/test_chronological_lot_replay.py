import unittest
from datetime import date,timedelta
from decimal import Decimal
from app.chronological_lot_replay import replay_lot_events

class ChronologicalLotTests(unittest.TestCase):
    def setUp(self):
        self.days=[(date(2024,1,1)+timedelta(days=i)).isoformat() for i in range(20)]
        self.now=self.days[-1]+"T18:00:00+05:45"
    def event(self,i,kind,**kw):
        return dict(event_id=str(i),date=self.days[i],type=kind,symbol="AAA",status="verified",source_id="synthetic",available_at=self.days[i]+"T17:00:00+05:45",**kw)
    def run_events(self,events,cash=30000):
        return replay_lot_events(events=events,sessions=self.days,assessment_time=self.now,initial_cash=cash)
    def history(self):
        return [
            self.event(0,"buy",quantity=100,total_cost=20000,settlement_date=self.days[2]),
            self.event(3,"sell",quantity=40,price=250,fees=100,allocations=[dict(lot_id="0",quantity=40)],settlement_date=self.days[5]),
            self.event(6,"record",action_id="B",action_type="bonus",ratio=".2"),
            self.event(7,"credit",action_id="B",quantities={"0":12}),
            self.event(8,"record",action_id="R",action_type="rights",ratio=".25",subscription_price=100),
            self.event(9,"rights_payment",action_id="R",subscriptions={"0":18},amount=1800),
            self.event(10,"credit",action_id="R",quantities={"0":18}),
            self.event(11,"record",action_id="S",action_type="split",ratio=2),
            self.event(12,"credit",action_id="S",quantities={"0":180}),
            self.event(13,"record",action_id="D",action_type="dividend",cash_per_share=5),
            self.event(14,"credit",action_id="D",net_amount=855)]
    def test_full_history(self):
        r=self.run_events(self.history())
        self.assertEqual(r["lots"]["0"]["quantity"],180)
        self.assertEqual(Decimal(r["lots"]["0"]["cost"]),13800)
        self.assertEqual(Decimal(r["realized"][0]["pnl"]),1900)
        self.assertEqual(Decimal(r["available_cash"]),18955)
        self.assertEqual(r["pending_action_ids"],[])
    def test_insufficient_purchase(self):
        with self.assertRaisesRegex(ValueError,"insufficient_purchase_cash"): self.run_events(self.history(),100)
    def test_unsettled_sale_cannot_fund_buy(self):
        events=self.history()[:2]+[self.event(4,"buy",quantity=1,total_cost=1,settlement_date=self.days[6])]
        with self.assertRaisesRegex(ValueError,"insufficient_purchase_cash"): self.run_events(events,20000)
    def test_wrong_credit(self):
        events=self.history()
        events[3]["quantities"]={"0":13}
        with self.assertRaisesRegex(ValueError,"credit_quantity_mismatch"): self.run_events(events)
    def test_record_during_settlement(self):
        events=self.history()[:2]+[self.event(4,"record",action_id="B",action_type="bonus",ratio=".2")]
        with self.assertRaisesRegex(ValueError,"ambiguous_record_date"): self.run_events(events)
    def test_insufficient_rights_funding(self):
        events=[self.event(0,"buy",quantity=100,total_cost=20000,settlement_date=self.days[2]),
                self.event(3,"record",action_id="R",action_type="rights",ratio=".25",subscription_price=100),
                self.event(4,"rights_payment",action_id="R",subscriptions={"0":25},amount=2500)]
        with self.assertRaisesRegex(ValueError,"insufficient_rights_cash"): self.run_events(events,20000)
