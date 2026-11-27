import unittest
from datetime import date,timedelta
from unittest.mock import patch
from app.strategy_research import observe

class StrategyResearchTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(date=str(date(2025,1,1)+timedelta(days=i)),open=100,high=105,low=95,close=100,volume=100) for i in range(24)]
        self.rows[21].update(open=100,high=113,low=99,close=110,volume=150)
        self.rows[22].update(open=110,high=112,low=104,close=108)
        self.rows[23].update(open=108,high=112,low=106,close=109)
        self.frames=dict(status="research_only",missing_daily_sessions=0,as_of=self.rows[-1]["date"],
            timeframes={k:{"structure":{"bias":"bullish"}} for k in ("daily","weekly","monthly")})
        self.events=[dict(type="liquidity_sweep",side="low",level=95,date=self.rows[20]["date"]),
                     dict(type="bos",direction="bullish",level=105,date=self.rows[21]["date"])]
    def evaluate(self):
        with patch("app.strategy_research.detect_structure",return_value={"events":self.events}):
            return observe(self.rows,self.frames,eligible=True)
    def test_confirmation(self):
        e=self.evaluate()["breakouts"][-1]
        self.assertTrue(e["confirmed_breakout"])
        self.assertEqual(e["volume_ratio"],1.5)
        self.assertEqual(e["retest_date"],self.rows[22]["date"])
    def test_low_volume(self):
        self.rows[21]["volume"]=149
        self.assertFalse(self.evaluate()["breakouts"][-1]["confirmed_breakout"])
    def test_no_sweep(self):
        self.events=self.events[1:]
        self.assertFalse(self.evaluate()["breakouts"][-1]["confirmed_breakout"])
    def test_no_retest(self):
        self.rows[22]["low"]=106
        self.assertFalse(self.evaluate()["breakouts"][-1]["confirmed_breakout"])
    def test_false_breakout(self):
        self.rows[23].update(low=100,close=104)
        e=self.evaluate()["breakouts"][-1]
        self.assertEqual(e["classification"],"false_breakout_proxy")
        self.assertEqual(e["failure_date"],self.rows[23]["date"])
        self.assertFalse(e["confirmed_breakout"])
    def test_bear_trap(self):
        self.assertEqual(self.evaluate()["breakouts"][0]["classification"],"bear_trap_proxy")
    def test_bull_trap(self):
        self.events[0]["side"]="high"
        self.assertEqual(self.evaluate()["breakouts"][0]["classification"],"bull_trap_proxy")
    def test_calendar_gap(self):
        self.frames["missing_daily_sessions"]=1
        self.assertEqual(self.evaluate()["status"],"unavailable")
    def test_alignment(self):
        self.assertEqual(self.evaluate()["alignment"],"aligned")
        self.frames["timeframes"]["monthly"]["structure"]["bias"]="bearish"
        self.assertEqual(self.evaluate()["alignment"],"conflicting")
    def test_horizons_research_only(self):
        result=self.evaluate()
        self.assertEqual({k:(v["min_sessions"],v["max_sessions"]) for k,v in result["horizons"].items()},
                         {"t_plus_2":(2,2),"swing":(3,15),"positional":(10,40)})
        self.assertTrue(all(v["action"]=="NO TRADE" and not v["execution_validated"] for v in result["horizons"].values()))
