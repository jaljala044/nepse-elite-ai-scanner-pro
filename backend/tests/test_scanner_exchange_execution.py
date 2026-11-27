import unittest
from app.scanner_exchange_execution import simulate_exchange_execution

def evidence(source, evidence_id, available_at):
    return {"evidence_status":"verified","source_id":source,"evidence_id":evidence_id,"available_at":available_at}

def session(day, *, bids=None, asks=None, halted=False, upper=False, lower=False):
    t=day+"T11:00:00+05:45"
    return {"session_date":day,"execution_at":t,"traded_volume":"1000",
        **evidence("session-feed","S-"+day,t),
        "price_band":{"lower_limit":"90","upper_limit":"110",**evidence("band-feed","B-"+day,t)},
        "order_book":{"halted":halted,"locked_at_upper":upper,"locked_at_lower":lower,
            "bids":bids or [],"asks":asks or [],**evidence("book-feed","OB-"+day,t)}}

def level(price, quantity, day):
    t=day+"T11:00:00+05:45"
    return {"price":price,"quantity":quantity,**evidence("book-feed","L-"+day+"-"+price,t)}

def order(side="buy", quantity=100, **extra):
    return {"side":side,"quantity":quantity,"submitted_at":"2025-01-01T10:00:00+05:45",
        "limit_price":"105","tick_size":"0.1",**evidence("order-feed","O-1","2025-01-01T10:00:00+05:45"),**extra}

class ExchangeExecutionTests(unittest.TestCase):
    def test_partial_fills_respect_depth_and_volume_participation(self):
        day="2025-01-02"
        result=simulate_exchange_execution(order=order(quantity=100),
            sessions=[session(day,asks=[level("100",30,day)])],impact_bps="0",max_participation_pct="5")
        self.assertEqual(result["status"],"partially_filled")
        self.assertEqual(result["filled_quantity"],30)
        self.assertEqual(result["remaining_quantity"],70)

    def test_upper_circuit_buy_and_lower_circuit_sell_are_not_filled(self):
        d1="2025-01-02"; d2="2025-01-03"
        buy=simulate_exchange_execution(order=order(),sessions=[session(d1,asks=[level("100",100,d1)],upper=True)])
        sell=simulate_exchange_execution(order=order("sell"),sessions=[session(d2,bids=[level("100",100,d2)],lower=True)])
        self.assertEqual(buy["filled_quantity"],0)
        self.assertEqual(sell["filled_quantity"],0)

    def test_sell_quantity_cannot_exceed_settled_inventory(self):
        result=simulate_exchange_execution(order=order("sell",quantity=50,sellable_quantity=20),sessions=[])
        self.assertEqual(result["status"],"blocked")
        self.assertEqual(result["reason"],"quantity_exceeds_settled_sellable_inventory")

    def test_limit_and_no_depth_prevent_invented_fill(self):
        day="2025-01-02"
        no_depth=simulate_exchange_execution(order=order(),sessions=[session(day)])
        over_limit=simulate_exchange_execution(order=order(),sessions=[
            session(day,asks=[level("106",100,day)])])
        self.assertEqual(no_depth["filled_quantity"],0)
        self.assertEqual(over_limit["filled_quantity"],0)

if __name__=="__main__": unittest.main()
