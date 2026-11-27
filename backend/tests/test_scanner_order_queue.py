import unittest
from app.scanner_order_queue import replay_passive_order_queue

def ev(source,eid,at,**extra):
    return {"source_id":source,"evidence_id":eid,"available_at":at,"evidence_status":"verified",**extra}

def order(side="buy",quantity=10):
    t="2025-01-01T10:00:00+05:45"
    return {"side":side,"quantity":quantity,"limit_price":"100","submitted_at":t,**ev("orders","o1",t)}

def event(seq,kind,qty,*,price="100",side="SELL",at=None,**extra):
    t=at or f"2025-01-01T10:{seq+1:02d}:00+05:45"
    return {"sequence":seq,"event_type":kind,"event_at":t,"quantity":qty,"price":price,
        "aggressor_side":side,**ev("tape",f"e{seq}",t),**extra}

class QueueReplayTests(unittest.TestCase):
    def test_trade_consumes_queue_ahead_before_our_fill(self):
        result=replay_passive_order_queue(order=order(),initial_queue_ahead={"quantity":"5",**ev("book","b1","2025-01-01T10:00:00+05:45")},
            events=[event(1,"TRADE","8")])
        self.assertEqual(result["filled_quantity"],3)
        self.assertEqual(result["queue_ahead_remaining"],"0")

    def test_unknown_cancel_does_not_improve_queue_position(self):
        result=replay_passive_order_queue(order=order(),initial_queue_ahead={"quantity":"7",**ev("book","b1","2025-01-01T10:00:00+05:45")},
            events=[event(1,"CANCEL","7",queue_attribution="UNKNOWN"),event(2,"TRADE","5")])
        self.assertEqual(result["filled_quantity"],0)
        self.assertEqual(result["queue_ahead_remaining"],"2")

    def test_book_reset_invalidates_queue_and_stops_assumed_fills(self):
        result=replay_passive_order_queue(order=order(),initial_queue_ahead={"quantity":"0",**ev("book","b1","2025-01-01T10:00:00+05:45")},
            events=[event(1,"BOOK_RESET",0),event(2,"TRADE","20")])
        self.assertEqual(result["filled_quantity"],0)
        self.assertFalse(result["queue_position_valid"])

    def test_better_price_orders_block_fill_until_better_level_trades(self):
        result=replay_passive_order_queue(order=order(),initial_queue_ahead={"quantity":"0",**ev("book","b1","2025-01-01T10:00:00+05:45")},
            events=[event(1,"ADD","5",price="101",order_side="buy"),
                event(2,"TRADE","10",price="100"),
                event(3,"TRADE","5",price="101"),
                event(4,"TRADE","10",price="100")])
        self.assertEqual(result["filled_quantity"],10)
        self.assertEqual(result["better_price_ahead_remaining"],"0")

    def test_new_orders_are_behind_and_aggressor_side_must_match(self):
        result=replay_passive_order_queue(order=order(),initial_queue_ahead={"quantity":"0",**ev("book","b1","2025-01-01T10:00:00+05:45")},
            events=[event(1,"ADD","100",order_side="buy"),event(2,"TRADE","5",side="BUY")])
        self.assertEqual(result["filled_quantity"],0)

if __name__=="__main__": unittest.main()
