import unittest
from app.scanner_portfolio_mark_to_market import build_mark_to_market_curve

def ev(source,eid):
    return {"evidence_status":"verified","source_id":source,"evidence_id":eid}

class MarkToMarketTests(unittest.TestCase):
    def test_unrealized_drawdown_is_included(self):
        executions=[{"execution_id":"x1","symbol":"ABC","execution_date":"2025-01-02",
            "side":"buy","quantity":10,"price":"100","execution_at":"2025-01-02T11:00:00+05:45",**ev("fills","f1","2025-01-02T11:00:00+05:45")}]
        marks=[{"symbol":"ABC","session_date":"2025-01-02","close":"100","decision_cutoff":"2025-01-02T16:00:00+05:45",**ev("eod","m1","2025-01-02T16:00:00+05:45")},
            {"symbol":"ABC","session_date":"2025-01-03","close":"80","decision_cutoff":"2025-01-03T16:00:00+05:45",**ev("eod","m2","2025-01-03T16:00:00+05:45")}]
        result=build_mark_to_market_curve(initial_cash="5000",executions=executions,daily_marks=marks)
        self.assertEqual(result["max_mark_to_market_drawdown_pct"],"4.0")
        self.assertEqual(result["ending_equity"],"4800")

    def test_missing_open_position_mark_fails_closed(self):
        executions=[{"execution_id":"x1","symbol":"ABC","execution_date":"2025-01-02",
            "side":"buy","quantity":1,"price":"100","execution_at":"2025-01-02T11:00:00+05:45",**ev("fills","f1","2025-01-02T11:00:00+05:45")}]
        with self.assertRaisesRegex(ValueError,"missing_point_in_time_marks"):
            build_mark_to_market_curve(initial_cash="500",executions=executions,
                daily_marks=[{"symbol":"XYZ","session_date":"2025-01-02","close":"10","decision_cutoff":"2025-01-02T16:00:00+05:45",**ev("eod","m1","2025-01-02T16:00:00+05:45")}])

    def test_sale_cannot_exceed_inventory(self):
        executions=[{"execution_id":"x1","symbol":"ABC","execution_date":"2025-01-02",
            "side":"sell","quantity":1,"price":"100","execution_at":"2025-01-02T11:00:00+05:45",**ev("fills","f1","2025-01-02T11:00:00+05:45")}]
        with self.assertRaisesRegex(ValueError,"sell_exceeds_portfolio_inventory"):
            build_mark_to_market_curve(initial_cash="500",executions=executions,
                daily_marks=[{"symbol":"ABC","session_date":"2025-01-02","close":"100",**ev("eod","m1")}])

if __name__=="__main__": unittest.main()
