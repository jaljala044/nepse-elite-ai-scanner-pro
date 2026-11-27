import unittest
from copy import deepcopy
from decimal import Decimal
from app.portfolio_lot_accounting import reconcile_lots

class LotAccountingTests(unittest.TestCase):
    def setUp(self):
        now="2024-05-07T17:00:00+05:45"
        e=dict(status="verified",source_id="synthetic",available_at=now)
        self.args=dict(assessment_time=now,lots=[
            dict(e,lot_id="A",symbol="AAA",quantity=500,total_cost=90000,acquisition_date="2024-05-01",settlement_date="2024-05-05"),
            dict(e,lot_id="B",symbol="AAA",quantity=500,total_cost=100000,acquisition_date="2024-05-02",settlement_date="2024-05-06")],
            sales=[dict(e,sale_id="S",symbol="AAA",trade_date="2024-05-07",quantity=600,price=250,fees=100,
                allocations=[dict(lot_id="A",quantity=500),dict(lot_id="B",quantity=100)])],
            marks={"AAA":dict(e,symbol="AAA",date="2024-05-07",close=250)})
    def test_cost_conservation(self):
        r=reconcile_lots(**self.args)
        self.assertEqual(Decimal(r["realized"][0]["realized_pnl"]),39900)
        self.assertEqual(Decimal(r["remaining_lots"][0]["remaining_cost"]),80000)
        self.assertEqual(Decimal(r["remaining_lots"][0]["unrealized_pnl"]),20000)
        self.assertFalse(r["production_eligible"])
    def test_duplicate_sale(self):
        self.args["sales"]*=2
        with self.assertRaisesRegex(ValueError,"invalid_sale_sequence"): reconcile_lots(**self.args)
    def test_oversold(self):
        s=deepcopy(self.args["sales"][0])
        s.update(sale_id="S2",quantity=1,allocations=[dict(lot_id="A",quantity=1)])
        self.args["sales"].append(s)
        with self.assertRaisesRegex(ValueError,"lot_unavailable_or_oversold"): reconcile_lots(**self.args)
    def test_unsettled(self):
        self.args["sales"][0]["trade_date"]="2024-05-05"
        with self.assertRaisesRegex(ValueError,"lot_unavailable_or_oversold"): reconcile_lots(**self.args)
    def test_missing_mark(self):
        self.args["marks"]={}
        self.assertIsNone(reconcile_lots(**self.args)["remaining_lots"][0]["unrealized_pnl"])
