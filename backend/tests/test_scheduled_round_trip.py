import unittest
from decimal import Decimal
from app.dated_execution_costs import scheduled_round_trip
from test_dated_transaction_charges import charges


class ScheduledRoundTripTests(unittest.TestCase):
    def scenario(self, entry="99.5", exit="100.5", quantity=100, schedule=None, **dates):
        s = charges() if schedule is None else schedule
        s = {**s, "slippage_bps": s.get("slippage_bps", "100")}
        return scheduled_round_trip(entry, exit, quantity,
            buy_date=dates.get("buy_date", "2026-06-30"),
            sell_date=dates.get("sell_date", "2026-07-01"), schedule=s)

    def test_buy_slab_crosses_threshold_after_slippage(self):
        s = {**charges(), "slippage_bps": "100"}
        r = self.scenario(schedule=s)
        self.assertEqual(Decimal(r["buy_scenario_notional"]), Decimal("10049.5"))
        self.assertEqual(r["assumptions"]["buy_broker_rate"], "0.0033")

    def test_sell_slab_crosses_threshold_after_slippage(self):
        r = self.scenario(schedule={**charges(), "slippage_bps": "100"})
        self.assertEqual(Decimal(r["sell_scenario_notional"]), Decimal("9949.5"))
        self.assertEqual(r["assumptions"]["sell_broker_rate"], "0.0036")

    def test_slippage_applied_only_once_and_cash_reconciles(self):
        r = self.scenario(entry=100, exit=110, quantity=10,
                          schedule={**charges(), "slippage_bps": "100"})
        self.assertEqual(Decimal(r["buy_scenario_notional"]), Decimal("1010"))
        self.assertEqual(Decimal(r["sell_scenario_notional"]), Decimal("1089"))
        self.assertAlmostEqual(r["buy_cash"], 1021.01)
        self.assertAlmostEqual(r["sell_cash"], 1045.5314)
        self.assertAlmostEqual(r["net_pnl"], r["sell_cash"]-r["buy_cash"])
        self.assertEqual(r["assumptions"]["slippage_bps"], "0")
        self.assertEqual(r["applied_slippage_bps"], "100")

    def test_dated_evidence_and_no_production_promotion(self):
        r = self.scenario()
        self.assertEqual(len(r["schedule_evidence"]), 8)
        self.assertTrue(r["dated_charges_resolved"])
        self.assertFalse(r["production_eligible"])

    def test_incomplete_schedule_rejected(self):
        s=charges()
        del s["dp_schedules"]
        with self.assertRaises(ValueError):
            self.scenario(schedule=s)

    def test_missing_explicit_slippage_rejected(self):
        s=charges()
        del s["slippage_bps"]
        with self.assertRaisesRegex(ValueError, "explicit_slippage"):
            scheduled_round_trip(100,110,10,buy_date="2026-06-30",
                sell_date="2026-07-01",schedule=s)

    def test_invalid_slippage_and_quantity_rejected(self):
        for bps in ("10000","-1","NaN"):
            with self.subTest(bps=bps), self.assertRaises(ValueError):
                self.scenario(schedule={**charges(),"slippage_bps":bps})
        with self.assertRaises(ValueError):
            self.scenario(quantity="1.5")

    def test_same_day_or_reversed_sale_rejected(self):
        for day in ("2026-06-30","2026-06-29"):
            with self.subTest(day=day), self.assertRaises(ValueError):
                self.scenario(sell_date=day)
