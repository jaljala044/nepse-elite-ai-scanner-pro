import unittest
from app.broker_research_leaderboards import research_leaderboards

def row(s,b,n,status="descriptive_only"):
    return dict(security_id=s,broker_id=b,symbol=s,net_amount=str(n),
        gross_broker_side_amount="100",classification="mixed_flow",
        status=status,production_eligible=False,score_eligible=False,
        sessions=["2026-01-01","2026-01-02","2026-01-03","2026-01-04","2026-01-05"])
def context(rows):
    return dict(profiles=rows,production_eligible=False,signals_enabled=False)

class LeaderboardTests(unittest.TestCase):
    def test_stock_and_broker_directions(self):
        r=research_leaderboards(context([row("A","1",30),row("A","2",-25),row("B","1",-50),row("C","1",40),row("A","3",50),row("A","4",0)]))
        a=r["by_security"][0]
        self.assertEqual([x["broker_id"] for x in a["net_buyers"]],["3","1"])
        self.assertEqual([x["broker_id"] for x in a["net_sellers"]],["2"])
        b=r["by_broker"][0]
        self.assertEqual([x["security_id"] for x in b["net_buyers"]],["C","A"])
        self.assertEqual([x["security_id"] for x in b["net_sellers"]],["B"])
        self.assertFalse(r["production_eligible"])
        self.assertFalse(r["signals_enabled"])
    def test_exact_decimal_order_and_limit(self):
        r=research_leaderboards(context([row("A","1","10.000000001"),row("A","2","10.000000002")]),limit=1)
        self.assertEqual(r["by_security"][0]["net_buyers"][0]["broker_id"],"2")
    def test_excluded_unknown_and_empty(self):
        r=research_leaderboards(context([row("A","1",10,"insufficient_evidence")]))
        self.assertEqual(r["status"],"insufficient_evidence")
        self.assertEqual(r["excluded_profiles"],1)
    def test_reject_duplicates_and_unsafe(self):
        x=row("A","1",10)
        with self.assertRaises(ValueError): research_leaderboards(context([x,x]))
        with self.assertRaises(ValueError): research_leaderboards(context([dict(x,score_eligible=True)]))
        with self.assertRaises(ValueError): research_leaderboards(context([dict(x,net_amount="101")]))
    def test_reject_mismatched_windows(self):
        x=row("A","1",10);y=row("A","2",-10);y["sessions"]=["2026-01-06"]
        with self.assertRaises(ValueError): research_leaderboards(context([x,y]))
