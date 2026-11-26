import unittest
from datetime import date
from app.execution_constraints import settlement_date,price_band,exit_scenario

class ConstraintTests(unittest.TestCase):
    def test_settlement(self):
        self.assertEqual(settlement_date("2025-01-02",["2025-01-05","2025-01-06"]),date(2025,1,6))
        self.assertIsNone(settlement_date("2025-01-02",None))
    def test_regime(self):
        self.assertAlmostEqual(price_band("2026-04-19",previous_close=100,ordinary_session=True)["lower"],90)
        self.assertIsNone(price_band("2026-04-20",previous_close=100,ordinary_session=True))
        self.assertAlmostEqual(price_band("2026-04-20",preopen_reference=100,ordinary_session=True)["upper"],115)
    def scenario(self,o,h,l,c,settled=True):
        return exit_scenario(dict(open=o,high=h,low=l,close=c,volume=100),
            stop=95,target=105,settled_before_session=settled,eligible=True,
            band={"lower":90,"upper":110})
    def test_gap(self):
        self.assertEqual(self.scenario(93,100,92,98)["price"],93)
    def test_both(self):
        self.assertEqual(self.scenario(100,107,94,101)["status"],"ambiguous_stop_first")
    def test_limit(self):
        self.assertIsNone(self.scenario(100,107,90,101)["price"])
    def test_unsettled(self):
        self.assertIsNone(self.scenario(100,107,94,101,False)["price"])
