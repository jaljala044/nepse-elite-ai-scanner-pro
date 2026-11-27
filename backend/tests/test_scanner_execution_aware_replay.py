import unittest
from app.scanner_execution_aware_replay import run_execution_aware_replay

def ev(source,eid,at):
    return {"evidence_status":"verified","source_id":source,"evidence_id":eid,"available_at":at}

def batch(side="buy",qty=5):
    t="2025-01-02T10:00:00+05:45"; event_at="2025-01-02T10:01:00+05:45"
    order={"side":side,"quantity":qty,"limit_price":"100","submitted_at":t,**ev("orders","o1",t)}
    events=[{"sequence":1,"event_type":"TRADE","event_at":event_at,"quantity":"10",
        "price":"100","aggressor_side":"SELL" if side=="buy" else "BUY",**ev("tape","t1",event_at)}]
    return {"strategy_id":"idpat_smart_money","horizon":"t_plus_2","partition":"out_of_sample",
        "order_id":"ord-1","symbol":"ABC","order":order,
        "initial_queue_ahead":{"quantity":"0",**ev("book","b1",t)},"events":events}

def marks():
    return [{"symbol":"ABC","session_date":"2025-01-02","close":"100",
        "decision_cutoff":"2025-01-02T16:00:00+05:45",**ev("eod","m1","2025-01-02T16:00:00+05:45")},
        {"symbol":"ABC","session_date":"2025-01-03","close":"90",
        "decision_cutoff":"2025-01-03T16:00:00+05:45",**ev("eod","m2","2025-01-03T16:00:00+05:45")}]

def opening_inventory():
    return [{"symbol":"ABC","quantity":5,"cost_basis":"100",
        "as_of":"2025-01-02T09:00:00+05:45",**ev("holdings","h1","2025-01-02T09:00:00+05:45")}]

class ExecutionAwareReplayTests(unittest.TestCase):
    def test_verified_queue_fills_flow_into_daily_mtm(self):
        b=batch()
        result=run_execution_aware_replay(order_batches=[b],
            daily_marks_by_run={"idpat_smart_money|t_plus_2|out_of_sample":marks()},initial_cash="1000")
        run=result["runs"][0]
        self.assertEqual(run["status"],"valued")
        self.assertEqual(run["queues"][0]["result"]["filled_quantity"],5)
        self.assertEqual(run["mark_to_market"]["ending_equity"],"950")
        self.assertEqual(run["mark_to_market"]["max_mark_to_market_drawdown_pct"],"5.00")

    def test_sell_requires_verified_and_already_sellable_inventory(self):
        b=batch(side="sell")
        result=run_execution_aware_replay(order_batches=[b],daily_marks_by_run={})
        self.assertEqual(result["rejected_orders"][0]["reason"],"verified_sellable_inventory_required")
        b["sellable_inventory"]={**ev("settlement","s1","2025-01-02T09:00:00+05:45"),
            "quantity":5,"sellable_at":"2025-01-02T09:00:00+05:45"}
        key="idpat_smart_money|t_plus_2|out_of_sample"
        result=run_execution_aware_replay(order_batches=[b],daily_marks_by_run={key:marks()},
            initial_cash="500",initial_positions_by_run={key:opening_inventory()})
        self.assertEqual(result["runs"][0]["status"],"valued")
        self.assertEqual(result["runs"][0]["mark_to_market"]["ending_equity"],"1000")

    def test_sell_before_settlement_or_over_sell_is_rejected(self):
        b=batch(side="sell")
        b["sellable_inventory"]={**ev("settlement","s1","2025-01-02T09:00:00+05:45"),
            "quantity":5,"sellable_at":"2025-01-03T09:00:00+05:45"}
        result=run_execution_aware_replay(order_batches=[b],daily_marks_by_run={})
        self.assertEqual(result["rejected_orders"][0]["reason"],"inventory_not_yet_sellable_at_order_time")
        b["sellable_inventory"]["sellable_at"]="2025-01-02T09:00:00+05:45"
        b["sellable_inventory"]["quantity"]=2
        result=run_execution_aware_replay(order_batches=[b],daily_marks_by_run={})
        self.assertEqual(result["rejected_orders"][0]["reason"],"sell_quantity_exceeds_verified_sellable_inventory")

    def test_missing_marks_block_valuation_and_oos_groups_stay_separate(self):
        b=batch()
        result=run_execution_aware_replay(order_batches=[b],daily_marks_by_run={})
        self.assertEqual(result["runs"][0]["status"],"blocked")
        b2=batch(); b2["partition"]="train"; b2["order_id"]="ord-2"
        result=run_execution_aware_replay(order_batches=[b,b2],
            daily_marks_by_run={"idpat_smart_money|t_plus_2|out_of_sample":marks()})
        self.assertEqual(result["run_count"],2)
        self.assertEqual({x["partition"] for x in result["runs"]},{"train","out_of_sample"})

if __name__=="__main__": unittest.main()
