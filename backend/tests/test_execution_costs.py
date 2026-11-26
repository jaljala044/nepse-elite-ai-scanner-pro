import unittest
from app.execution_costs import round_trip

ZERO = dict(buy_broker_rate=0,sell_broker_rate=0,regulatory_rate=0,
            sell_dp_charge=0,capital_gain_tax_rate=0,slippage_bps=0,min_broker_fee=0)

class ExecutionCostTests(unittest.TestCase):
    def test_missing_assumptions(self):
        self.assertIsNone(round_trip(100,110,10)["net_pnl"])
    def test_zero_cost_reference(self):
        result=round_trip(100,110,10,assumptions=ZERO)
        self.assertAlmostEqual(result["net_pnl"],100)
        self.assertAlmostEqual(result["net_return_pct"],10)
        self.assertFalse(result["production_eligible"])
    def test_costs_and_tax(self):
        a=dict(ZERO,buy_broker_rate=.01,sell_broker_rate=.01,
               sell_dp_charge=5,capital_gain_tax_rate=.05)
        result=round_trip(100,110,10,assumptions=a)
        self.assertAlmostEqual(result["tax"],3.7)
        self.assertAlmostEqual(result["net_pnl"],70.3)
    def test_loss_not_taxed(self):
        result=round_trip(100,90,10,assumptions=dict(ZERO,capital_gain_tax_rate=.05))
        self.assertEqual(result["tax"],0)
        self.assertAlmostEqual(result["net_pnl"],-100)
    def test_slippage_reduces_return(self):
        self.assertLess(round_trip(100,110,10,assumptions=dict(ZERO,slippage_bps=50))["net_return_pct"],10)
    def test_invalid_input(self):
        for qty in (0,-1,1.5,float("nan"),True):
            with self.assertRaises(ValueError):
                round_trip(100,110,qty,assumptions=ZERO)
