import unittest
from app.unified_portfolio_event_engine import run_unified_portfolio_event_ledger

class RecordDateSettlementTests(unittest.TestCase):
    def replay(self,record):
        days=["2024-05-01","2024-05-02","2024-05-05","2024-05-06","2024-05-07"]
        evidence=dict(status="verified",source_id="synthetic",available_at="2024-05-07T17:00:00+05:45")
        return run_unified_portfolio_event_ledger(initial_cash=1000,
            initial_holdings={"AAA":{"quantity":100,"average_cost":10}},
            trades=[dict(evidence,trade_id="S",symbol="AAA",side="SELL",trade_date=days[0],
                settlement_date=days[2],quantity=40,price=10,fees=0)],
            corporate_actions=[dict(evidence,action_id="D",symbol="AAA",action_type="dividend",
                record_date=record,payment_date=days[-1],cash_per_share=1)],
            price_rows_by_symbol={"AAA":[dict(date=d,close=10) for d in days]},
            portfolio_sessions=days,as_of_date=days[-1],evidence_cutoff=evidence["available_at"])
    def test_pending_sale_record_date(self):
        with self.assertRaisesRegex(ValueError,"record_date_unsettled_sale_requires_custody_evidence"):
            self.replay("2024-05-02")
    def test_same_day_settlement_conservative(self):
        with self.assertRaisesRegex(ValueError,"record_date_unsettled_sale_requires_custody_evidence"):
            self.replay("2024-05-05")
    def test_after_settlement(self):
        result=self.replay("2024-05-06")
        self.assertEqual(result["corporate_action_entitlements"][0]["entitlement_quantity"],60)
        self.assertEqual(result["ending_equity"],2060)
