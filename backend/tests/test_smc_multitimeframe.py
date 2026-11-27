import unittest
from datetime import date, timedelta
from app.smc_multitimeframe import evaluate_multitimeframe, week_key, aggregate_complete

class MultiTimeframeTests(unittest.TestCase):
    def fixture(self):
        start=date(2026,3,1)
        days=[start+timedelta(days=i) for i in range(100)]
        days=[d for d in days if (d.weekday() in (6,0,1,2,3) if d<date(2026,4,6) else d.weekday()<5)]
        rows=[dict(date=str(d),open=100+i,high=102+i,low=99+i,close=101+i,volume=100) for i,d in enumerate(days)]
        return rows,[str(d) for d in days]
    def test_transition(self):
        self.assertEqual(week_key(date(2026,4,2)),date(2026,3,29))
        self.assertEqual(week_key(date(2026,4,10)),date(2026,4,6))
    def test_gate(self):
        rows,days=self.fixture()
        self.assertEqual(evaluate_multitimeframe(rows)["status"],"unavailable")
    def test_frames(self):
        rows,days=self.fixture()
        result=evaluate_multitimeframe(rows,eligible=True,verified_sessions=days,as_of=days[-1])
        self.assertEqual(result["status"],"research_only")
        self.assertGreater(result["timeframes"]["weekly"]["bars"],5)
        self.assertEqual(result["timeframes"]["monthly"]["bars"],3)
        self.assertIsNone(result["production_score"])
    def test_missing_session(self):
        rows,days=self.fixture()
        result=evaluate_multitimeframe(rows[:-3]+rows[-2:],eligible=True,verified_sessions=days,as_of=days[-1])
        self.assertEqual(result["timeframes"]["daily"]["bars"],2)
        self.assertEqual(result["missing_daily_sessions"],1)
    def test_cutoff(self):
        rows,days=self.fixture()
        a=evaluate_multitimeframe(rows,eligible=True,verified_sessions=days,as_of=days[-5])
        b=evaluate_multitimeframe(rows[:-4],eligible=True,verified_sessions=days,as_of=days[-5])
        self.assertEqual(a,b)


class NumericalFrameTests(unittest.TestCase):
    # Synthetic sessions isolate the calculation, not actual NEPSE calendars.
    def fixture(self, period, values):
        days = [date(2025,1,5)+timedelta(weeks=i) if period=="weekly"
                else date(2025+i//12,i%12+1,5) for i in range(len(values))]
        rows = [dict(date=str(d),open=o,high=h,low=l,close=c,volume=100)
                for d,(o,h,l,c) in zip(days,values)]
        return rows,days
    def frame(self, period, values):
        rows,days=self.fixture(period,values+[(10,11,9,10)])
        return evaluate_multitimeframe(rows,eligible=True,verified_sessions=days,as_of=days[-1])["timeframes"][period]
    def pattern(self):
        return [(9,10,8,9),(10,11,9,10),(12,13,10,12),
                (11.5,12,9,10),(10,11,7,9),(12,14,10,12),
                (13,15,11,14),(10,12,6,6.5)]
    def test_weekly_bos_value(self):
        events=self.frame("weekly",self.pattern())["structure"]["events"]
        bos=next(e for e in events if e["type"]=="bos")
        self.assertEqual((bos["direction"],bos["level"],bos["observed_close"]),("bullish",13,14))
    def test_monthly_bos_value(self):
        events=self.frame("monthly",self.pattern())["structure"]["events"]
        bos=next(e for e in events if e["type"]=="bos")
        self.assertEqual((bos["direction"],bos["level"],bos["observed_close"]),("bullish",13,14))
    def test_weekly_sweep_value(self):
        events=self.frame("weekly",self.pattern())["structure"]["events"]
        sweep=next(e for e in events if e["type"]=="liquidity_sweep")
        self.assertEqual((sweep["side"],sweep["level"],sweep["observed_close"]),("high",13,12))
    def test_monthly_choch_value(self):
        events=self.frame("monthly",self.pattern())["structure"]["events"]
        event=next(e for e in events if e["type"]=="choch")
        self.assertEqual((event["direction"],event["level"],event["observed_close"]),("bearish",7,6.5))
    def test_order_block_bounds(self):
        events=self.frame("weekly",self.pattern())["structure"]["events"]
        block=next(e for e in events if e["type"]=="order_block")
        self.assertEqual((block["lower"],block["upper"],block["trigger"]),(7,11,"bos"))
    def test_monthly_fvg_bounds(self):
        frame=self.frame("monthly",[(9,10,8,9),(10,13,9,12),(14,15,12,14)])
        gap=next(z for z in frame["zones"]["zones"] if z["zone_type"]=="fvg")
        self.assertEqual((gap["lower"],gap["upper"],gap["state"]),(10,12,"untested"))
    def test_weekly_mitigation_fraction(self):
        frame=self.frame("weekly",[(9,10,8,9),(10,13,9,12),(14,15,12,14),(12,13,11,12)])
        gap=next(z for z in frame["zones"]["zones"] if z["zone_type"]=="fvg")
        self.assertEqual((gap["state"],gap["max_penetration"]),("partially_mitigated",0.5))
    def test_monthly_invalidation_precedes_touch(self):
        frame=self.frame("monthly",[(9,10,8,9),(10,13,9,12),(14,15,12,14),(12,13,9,9)])
        gap=next(z for z in frame["zones"]["zones"] if z["zone_type"]=="fvg")
        self.assertEqual((gap["state"],gap["touch_count"]),("invalidated",0))
    def test_ipda_exact_lookback(self):
        frame=self.frame("weekly",[(100+i,102+i,99+i,101+i) for i in range(60)])
        for n in (20,40,60):
            window=frame["ipda"]["windows"][str(n)]
            self.assertEqual((window["observations"],window["low"],window["high"]),(n,159-n,161))
    def test_aggregation_exact_values(self):
        days=[date(2025,1,5),date(2025,1,6),date(2025,1,12)]
        rows=[dict(date=str(d),open=o,high=h,low=l,close=c,volume=v)
              for d,(o,h,l,c,v) in zip(days,[(10,13,9,12,100),(12,15,11,14,200),(14,16,13,15,300)])]
        bars,_=aggregate_complete(rows,days,days[-1],"weekly")
        self.assertEqual(bars,[dict(date="2025-01-06",open=10,high=15,low=9,close=14,volume=300)])
