import unittest
from app.effective_cost_schedule import resolve_cost_assumptions
from app.execution_costs import round_trip
from test_effective_cost_schedule import fixture, record

def charges():
    s=fixture()
    def item(name, side, start, end, field, value):
        return dict(record(name,side,start=start,end=end), **{field:value})
    for key, field, side, values in (
        ("regulatory_schedules","rate","both",("0.001","0.002")),
        ("dp_schedules","amount","sell",("20","25")),
        ("minimum_brokerage_schedules","amount","both",("10","15")),
    ):
        s[key]=[item(key+"-early",side,"2026-01-01","2026-06-30",field,values[0]),
                item(key+"-late",side,"2026-07-01","2026-12-31",field,values[1])]
    return s

class DatedTransactionChargesTests(unittest.TestCase):
    def resolve(self,s):
        return resolve_cost_assumptions("2026-06-30",1000,1100,s,sell_date="2026-07-01",require_dated_charges=True)

    def test_buy_regulatory_rate(self):
        self.assertEqual(self.resolve(charges())["buy_regulatory_rate"],"0.001")

    def test_sell_regulatory_rate(self):
        self.assertEqual(self.resolve(charges())["sell_regulatory_rate"],"0.002")

    def test_exit_dp_charge(self):
        self.assertEqual(self.resolve(charges())["sell_dp_charge"],"25")

    def test_separate_minimum_brokerage(self):
        a=self.resolve(charges())
        self.assertEqual((a["buy_min_broker_fee"],a["sell_min_broker_fee"]),("10","15"))

    def test_missing_dated_charges(self):
        with self.assertRaises(ValueError):
            self.resolve(fixture())

    def test_partial_dated_schedule_never_falls_back(self):
        s=charges()
        del s["dp_schedules"]
        with self.assertRaises(ValueError):
            resolve_cost_assumptions("2026-06-30",1000,1100,s,sell_date="2026-07-01")

    def test_overlap_rejected(self):
        s=charges()
        s["dp_schedules"].append(dict(s["dp_schedules"][1]))
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            self.resolve(s)

    def test_provenance_required(self):
        s=charges()
        del s["dp_schedules"][1]["source_sha256"]
        with self.assertRaisesRegex(ValueError,"provenance"):
            self.resolve(s)

    def test_invalid_regulatory_rate(self):
        s=charges()
        s["regulatory_schedules"][1]["rate"]="1.01"
        with self.assertRaises(ValueError):
            self.resolve(s)

    def test_round_trip_applies_distinct_charges(self):
        s=charges()
        s["slippage_bps"]="0"
        a=self.resolve(s)
        result=round_trip(100,110,10,assumptions=a)
        self.assertAlmostEqual(result["buy_fees"],11)
        self.assertAlmostEqual(result["sell_fees"],42.2)
        self.assertAlmostEqual(result["net_pnl"],44.46)
        self.assertEqual(len(a["schedule_evidence"]),8)
        self.assertTrue(a["dated_charges_resolved"])
        self.assertFalse(result["production_eligible"])
