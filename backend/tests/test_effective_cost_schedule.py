import unittest
from app.effective_cost_schedule import resolve_cost_assumptions
from app.execution_costs import round_trip

H = "a" * 64

def record(schedule_id, side="both", lower="0", upper="10000", rate="0.0036",
           start="2026-01-01", end="2026-12-31"):
    return {"schedule_id":schedule_id,"source_id":"fixture-source","source_sha256":H,
            "status":"verified","side":side,"amount_min":lower,
            "amount_max_exclusive":upper,"rate":rate,
            "effective_from":start,"effective_to":end}

def fixture():
    return {
        "brokerage_slabs":[
            record("small-buy","buy","0","10000"),
            record("large-buy","buy","10000",None,"0.0033"),
            record("small-sell","sell","0","10000"),
            record("large-sell","sell","10000",None,"0.0033"),
        ],
        "tax_schedules":[{"schedule_id":"tax-2026","source_id":"tax-fixture",
            "source_sha256":"b"*64,"status":"verified","effective_from":"2026-01-01",
            "effective_to":"2026-12-31","rate":"0.05"}],
        "regulatory_rate":"0","sell_dp_charge":"25","min_broker_fee":"10",
        "slippage_bps":"10",
    }

class EffectiveCostScheduleTests(unittest.TestCase):
    def test_buy_slab_lower_boundary_inclusive(self):
        x=resolve_cost_assumptions("2026-06-01",10000,9999,fixture())
        self.assertEqual(x["buy_broker_rate"],"0.0033")

    def test_buy_slab_upper_boundary_exclusive(self):
        x=resolve_cost_assumptions("2026-06-01",9999.99,10000,fixture())
        self.assertEqual(x["buy_broker_rate"],"0.0036")
        self.assertEqual(x["sell_broker_rate"],"0.0033")

    def test_sell_slab_boundary_is_independent(self):
        x=resolve_cost_assumptions("2026-06-01",5000,15000,fixture())
        self.assertEqual(x["buy_broker_rate"],"0.0036")
        self.assertEqual(x["sell_broker_rate"],"0.0033")

    def test_effective_start_and_end_are_inclusive(self):
        for day in ("2026-01-01","2026-12-31"):
            with self.subTest(day=day):
                self.assertEqual(resolve_cost_assumptions(day,100,100,fixture())["capital_gain_tax_rate"],"0.05")

    def test_missing_tax_period_fails_closed(self):
        s=fixture()
        s["tax_schedules"]=[]
        with self.assertRaisesRegex(ValueError,"tax_schedule_missing"):
            resolve_cost_assumptions("2026-06-01",100,100,s)

    def test_tax_schedule_gap_fails_closed(self):
        s=fixture()
        s["tax_schedules"][0]["effective_to"]="2026-05-31"
        with self.assertRaisesRegex(ValueError,"tax_schedule_missing"):
            resolve_cost_assumptions("2026-06-01",100,100,s)

    def test_overlapping_tax_periods_are_ambiguous(self):
        s=fixture()
        s["tax_schedules"].append(dict(s["tax_schedules"][0],schedule_id="tax-overlap"))
        with self.assertRaisesRegex(ValueError,"tax_schedule_ambiguous"):
            resolve_cost_assumptions("2026-06-01",100,100,s)

    def test_brokerage_slab_gap_and_overlap_fail_closed(self):
        s=fixture()
        s["brokerage_slabs"]=[r for r in s["brokerage_slabs"] if r["schedule_id"]!="large-buy"]
        with self.assertRaisesRegex(ValueError,"brokerage_slab_missing"):
            resolve_cost_assumptions("2026-06-01",10000,100,s)
        s=fixture()
        s["brokerage_slabs"].append(record("overlap-buy","buy","5000","15000"))
        with self.assertRaisesRegex(ValueError,"brokerage_slab_ambiguous"):
            resolve_cost_assumptions("2026-06-01",7000,100,s)

    def test_missing_source_hash_fails_closed(self):
        s=fixture()
        del s["brokerage_slabs"][0]["source_sha256"]
        with self.assertRaisesRegex(ValueError,"cost_schedule_provenance_incomplete"):
            resolve_cost_assumptions("2026-06-01",100,100,s)

    def test_dp_minimum_brokerage_and_cost_engine_integration(self):
        assumptions=resolve_cost_assumptions("2026-06-01",5000,5500,fixture())
        result=round_trip(100,110,50,assumptions=assumptions)
        self.assertEqual(assumptions["sell_dp_charge"],"25")
        self.assertEqual(assumptions["min_broker_fee"],"10")
        self.assertGreater(result["buy_fees"],0)
        self.assertGreater(result["sell_fees"],25)
        self.assertFalse(result["production_eligible"])

    def test_cross_period_sell_and_tax_selection(self):
        s = fixture()
        for row in s["brokerage_slabs"]:
            row["effective_to"] = "2026-06-30"
        later = [dict(row, effective_from="2026-07-01", effective_to="2026-12-31", rate="0.002", schedule_id=row["schedule_id"]+"-later") for row in s["brokerage_slabs"]]
        s["brokerage_slabs"].extend(later)
        s["tax_schedules"][0]["effective_to"] = "2026-06-30"
        s["tax_schedules"].append(dict(s["tax_schedules"][0], effective_from="2026-07-01", effective_to="2026-12-31", rate="0.07", schedule_id="tax-later"))
        result = resolve_cost_assumptions("2026-06-30", 5000, 5500, s, sell_date="2026-07-01")
        self.assertEqual(result["buy_broker_rate"], "0.0036")
        self.assertEqual(result["sell_broker_rate"], "0.002")
        self.assertEqual(result["capital_gain_tax_rate"], "0.07")
        self.assertEqual(result["sell_date"], "2026-07-01")

    def test_exit_before_entry_rejected(self):
        with self.assertRaisesRegex(ValueError, "sell_date_before_buy_date"):
            resolve_cost_assumptions("2026-06-02", 100, 100, fixture(), sell_date="2026-06-01")

    def test_exit_schedule_gap_rejected(self):
        with self.assertRaisesRegex(ValueError, "brokerage_slab_missing"):
            resolve_cost_assumptions("2026-12-31", 100, 100, fixture(), sell_date="2027-01-01")

    def test_holding_period_boundary(self):
        s = fixture()
        short = dict(s["tax_schedules"][0], holding_days_min=0, holding_days_max_exclusive=30, rate="0.08")
        long = dict(s["tax_schedules"][0], holding_days_min=30, rate="0.04")
        s["tax_schedules"] = [short, long]
        for day, rate, days in (("2026-06-30","0.08",29),("2026-07-01","0.04",30)):
            result = resolve_cost_assumptions("2026-06-01",100,110,s,sell_date=day)
            self.assertEqual(result["capital_gain_tax_rate"],rate)
            self.assertEqual(result["holding_calendar_days"],days)

    def test_holding_band_gap(self):
        s=fixture()
        s["tax_schedules"][0]["holding_days_min"]=30
        with self.assertRaisesRegex(ValueError,"tax_schedule_missing"):
            resolve_cost_assumptions("2026-06-01",100,110,s,sell_date="2026-06-02")

    def test_holding_band_overlap(self):
        s=fixture()
        s["tax_schedules"].append(dict(s["tax_schedules"][0],holding_days_min=1))
        with self.assertRaisesRegex(ValueError,"tax_schedule_ambiguous"):
            resolve_cost_assumptions("2026-06-01",100,110,s,sell_date="2026-06-02")

    def test_fractional_holding_band_rejected(self):
        s=fixture()
        s["tax_schedules"][0]["holding_days_min"]="0.5"
        with self.assertRaisesRegex(ValueError,"invalid_holding_period_band"):
            resolve_cost_assumptions("2026-06-01",100,110,s)

if __name__ == "__main__":
    unittest.main()
