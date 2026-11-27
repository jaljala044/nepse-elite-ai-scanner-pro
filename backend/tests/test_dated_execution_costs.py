import unittest
from app.historical_fee_reference import brokerage_cap,resident_tax_reference
from app.dated_execution_costs import dated_round_trip

class DatedCostTests(unittest.TestCase):
    def setUp(self):
        self.a=dict(regulatory_rate="0.00015",sell_dp_charge=25,slippage_bps=0,min_broker_fee=10)
    def run_cost(self, entry=100,exit=120,qty=100, buy="2026-10-01",sell="2026-10-15"):
        return dated_round_trip(entry,exit,qty,buy_date=buy,sell_date=sell,assumptions=self.a)
    def test_old_slabs(self):
        for n,rate in [(50000,"0.0040"),(50001,"0.0037"),(500001,"0.0034"),(2000001,"0.0030"),(10000001,"0.0027")]:
            self.assertEqual(brokerage_cap("2024-05-13",n)["rate"],rate)
    def test_revised_boundaries(self):
        for n,rate in [(50000,"0.0036"),(50000.01,"0.0033"),(500000,"0.0033"),(500000.01,"0.0031"),(2000000,"0.0031"),(2000000.01,"0.0027"),(10000000,"0.0027"),(10000000.01,"0.0024")]:
            self.assertEqual(brokerage_cap("2024-05-14",n)["rate"],rate)
    def test_schedule_boundary(self):
        self.assertIsNone(brokerage_cap("2020-12-26",100)["rate"])
        self.assertEqual(brokerage_cap("2020-12-27",100)["rate"],"0.0040")
        self.assertIsNone(brokerage_cap("2026-11-27",100)["rate"])
    def test_tax_boundary(self):
        self.assertIsNone(resident_tax_reference("2026-09-21",20)["rate"])
        self.assertEqual(resident_tax_reference("2026-09-22",365)["rate"],"0.05")
        self.assertEqual(resident_tax_reference("2026-09-22",366)["rate"],"0.0375")
    def test_tax_missing_blocks_pnl(self):
        r=self.run_cost(buy="2024-06-01",sell="2024-06-10")
        self.assertEqual(r["status"],"historical_cost_evidence_missing")
        self.assertIsNone(r["net_pnl"])
    def test_exact_costs(self):
        r=self.run_cost()
        self.assertEqual(r["status"],"scenario_only")
        self.assertAlmostEqual(r["buy_fees"],37.5)
        self.assertAlmostEqual(r["sell_fees"],70)
        self.assertAlmostEqual(r["tax"],94.625)
        self.assertAlmostEqual(r["net_pnl"],1797.875)
        self.assertFalse(r["production_eligible"])
    def test_separate_slabs(self):
        r=self.run_cost(entry=490,exit=510)
        self.assertEqual(r["brokerage_buy"]["rate"],"0.0036")
        self.assertEqual(r["brokerage_sell"]["rate"],"0.0033")
    def test_slippage_crosses_slab(self):
        self.a["slippage_bps"]=100
        r=self.run_cost(entry=500,exit=510)
        self.assertEqual(r["brokerage_buy"]["rate"],"0.0033")
        self.assertEqual(r["brokerage_sell"]["rate"],"0.0033")
    def test_missing_charge(self):
        del self.a["sell_dp_charge"]
        self.assertEqual(self.run_cost()["status"],"historical_cost_evidence_missing")
    def test_invalid_trade(self):
        for args in [dict(qty=1.5),dict(entry=0),dict(sell="2026-10-01")]:
            with self.assertRaises(ValueError): self.run_cost(**args)
