import unittest
from app.scanner_candidate_decisions import classify_candidate,method_setup

class CandidateTests(unittest.TestCase):
    def test_buy_review(self):
        r=dict(direction="BULLISH",plan=dict(entry=100,stop=90,T1=120))
        self.assertEqual(classify_candidate(r,market="FAVORABLE",liquidity="ADEQUATE")["action"],"BUY_REVIEW")
        self.assertEqual(classify_candidate(r)["action"],"NO_TRADE")
    def test_exit(self):
        self.assertEqual(classify_candidate(dict(direction="BEARISH"),holding=True)["action"],"SELL_REVIEW")
    def test_spring(self):
        self.assertEqual(method_setup(dict(evidence=dict(events=[dict(event="spring",session_date="2025-01-01")])),"WYCKOFF","2025-01-01"),"EARLY_REVERSAL_WATCH")
