import unittest
from app.scanner_unified_portfolio_risk import run_unified_portfolio_risk

def ev(source,eid,at):
    return {"evidence_status":"verified","source_id":source,"evidence_id":eid,"available_at":at}

def execution(eid,side="buy",qty=5,price="100"):
    at="2025-01-02T10:00:00+05:45"
    return {"execution_id":eid,"symbol":"ABC","sector":"Hydropower",
        "execution_date":"2025-01-02","execution_at":at,"sequence":1,
        "side":side,"quantity":qty,"price":price,**ev("tape",eid,at),
        "sellable_inventory":({**ev("settle","s1","2025-01-02T09:00:00+05:45"),
            "symbol":"ABC","quantity":qty,"sellable_at":"2025-01-02T09:00:00+05:45"} if side=="sell" else None)}

def run(execs):
    return {"strategy_id":"idpat_smart_money","horizon":"swing","partition":"out_of_sample",
        "status":"valued","executions":execs}

def mark():
    return [{"symbol":"ABC","session_date":"2025-01-02","close":"100",
        "decision_cutoff":"2025-01-02T16:00:00+05:45",**ev("eod","m1","2025-01-02T16:00:00+05:45")}]

def control():
    return [{"symbol":"ABC","session_date":"2025-01-02","lower_circuit_price":"90",
        "upper_circuit_price":"110","available_at":"2025-01-02T09:30:00+05:45",
        **ev("exchange","c1","2025-01-02T09:30:00+05:45")}]

class UnifiedPortfolioRiskTests(unittest.TestCase):
    def test_shared_capital_limits_across_strategy_runs(self):
        a=run([execution("x1")]); b=run([execution("x2")])
        result=run_unified_portfolio_risk(execution_runs=[a,b],daily_marks=mark(),
            market_controls=control(),initial_cash="1000",max_symbol_exposure_pct="60",
            max_sector_exposure_pct="80",max_gross_exposure_pct="100")
        self.assertEqual(result["accepted_execution_count"],1)
        self.assertEqual(result["rejected_executions"][0]["reason"],"symbol_exposure_limit_exceeded")
        self.assertEqual(result["status"],"VALUED")

    def test_circuit_band_and_missing_control_fail_closed(self):
        bad=execution("x1",price="120")
        result=run_unified_portfolio_risk(execution_runs=[run([bad])],daily_marks=mark(),
            market_controls=control(),initial_cash="1000")
        self.assertEqual(result["rejected_executions"][0]["reason"],"execution_outside_circuit_band")
        result=run_unified_portfolio_risk(execution_runs=[run([execution("x2")])],
            daily_marks=mark(),market_controls=[],initial_cash="1000")
        self.assertEqual(result["rejected_executions"][0]["reason"],"point_in_time_circuit_control_missing")

    def test_settlement_evidence_and_oos_filter(self):
        sell=execution("x1",side="sell")
        result=run_unified_portfolio_risk(execution_runs=[run([sell])],daily_marks=mark(),
            market_controls=control(),initial_cash="1000")
        self.assertEqual(result["rejected_executions"][0]["reason"],"sell_exceeds_shared_portfolio_inventory")
        train=run([execution("x2")]); train["partition"]="train"
        result=run_unified_portfolio_risk(execution_runs=[train],daily_marks=mark(),
            market_controls=control(),initial_cash="1000")
        self.assertEqual(result["rejected_executions"][0]["reason"],"non_oos_run_excluded")

if __name__=="__main__": unittest.main()
