import unittest
from app.scanner_delayed_exit_costs import delayed_stop_costs
class DelayedCostTests(unittest.TestCase):
    def test_capacity(self):
        days=["2026-11-16","2026-11-17","2026-11-18","2026-11-19"]
        rows=[dict(date=d,open=p,high=p,low=p,close=p,volume=100,status="verified",source_id="synthetic",available_at=d+"T16:00:00+05:45") for d,p in zip(days,[490,470,450,460])]
        bands={d:dict(lower=400,upper=550) for d in days}
        bands[days[2]]["lower"]=450
        r=delayed_stop_costs(risk_inputs=dict(entry_date=days[0],entry_price=490,stop=480,rows=rows,sessions=days,assessment_time=days[-1]+"T17:00:00+05:45",price_bands=bands),quantity=20,cost_assumptions={"slippage_bps":0},tick_size=1,max_participation=.1)
        self.assertEqual(r["exit_reference_date"],days[3])
        self.assertEqual(r["cost_status"],"FULL_QUANTITY_CAPACITY_UNPROVEN")
        self.assertIsNone(r["net_pnl"])
