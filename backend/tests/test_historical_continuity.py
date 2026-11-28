import unittest
from app.historical_continuity import review_segment

class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.days = ["2026-11-23", "2026-11-24"]
        self.calendar = {d: {"status":"verified_open","evidence_id":"calendar"} for d in self.days}
        self.lifecycle = {d: {"symbol":"TEST","instrument_type":"equity","security_id":"1","status":"active","boundary":False,"evidence_id":"life"} for d in self.days}
        self.rows = [dict(date=d,symbol="TEST",security_id="1",open=10,high=12,low=9,close=11,volume=100,evidence_id="row",price_basis="raw",canonical_promotion_allowed=True) for d in self.days]

    def review(self, minimum=2, warmup=0):
        return review_segment("TEST", *self.days, self.calendar, self.lifecycle, self.rows, minimum_bars=minimum, warmup=warmup)

    def test_pass_never_promotes(self):
        r = self.review()
        self.assertTrue(r["continuity_preflight_passed"])
        self.assertFalse(r["backtest_promotion_allowed"])
        self.assertFalse(r["canonical_promotion_allowed"])

    def test_missing(self):
        self.rows.pop()
        self.assertIn(self.days[1]+":missing_or_unverified_no_trade",self.review()["reasons"])

    def test_no_trade_not_a_bar(self):
        self.rows.pop()
        self.lifecycle[self.days[1]]["no_trade_evidence_id"]="trade-ledger"
        self.assertTrue(self.review(1)["continuity_preflight_passed"])
        self.assertFalse(self.review()["continuity_preflight_passed"])

    def test_unverified_calendar(self):
        self.calendar.pop(self.days[1])
        self.assertFalse(self.review()["continuity_preflight_passed"])

    def test_closed_candle(self):
        self.calendar[self.days[1]]["status"]="verified_closed"
        self.assertIn(self.days[1]+":closed_day_candle",self.review()["reasons"])

    def test_merger_boundary(self):
        self.lifecycle[self.days[1]]["boundary"]=True
        self.assertFalse(self.review()["continuity_preflight_passed"])

    def test_identity_change(self):
        self.lifecycle[self.days[1]]["security_id"]="2"
        self.rows[1]["security_id"]="2"
        self.assertIn("identity_or_price_basis_changed",self.review()["reasons"])

    def test_price_basis(self):
        self.rows[1]["price_basis"]="adjusted"
        self.assertIn("identity_or_price_basis_changed",self.review()["reasons"])

    def test_duplicate(self):
        self.rows.append(self.rows[0].copy())
        self.assertFalse(self.review()["continuity_preflight_passed"])

    def test_invalid(self):
        self.rows[0]["high"]=8
        self.assertFalse(self.review()["continuity_preflight_passed"])

    def test_unreviewed(self):
        self.rows[0]["canonical_promotion_allowed"]=False
        self.assertFalse(self.review()["continuity_preflight_passed"])

    def test_warmup(self):
        self.assertFalse(self.review(warmup=1)["continuity_preflight_passed"])
