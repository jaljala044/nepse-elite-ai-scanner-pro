import unittest
from datetime import date,timedelta
from app.historical_quarantine import QUARANTINE,window_errors
from app.scanner_eligibility import assess
from app.structure_timeframes import evaluate_timeframes
from app.historical_replay import replay

def bar(day):
    return dict(date=str(day),open=100,high=102,low=99,close=101,volume=100)

class QuarantineTests(unittest.TestCase):
    def test_all_keys(self):
        self.assertEqual(len(QUARANTINE),1329)
        for symbol,day in sorted(QUARANTINE):
            with self.subTest(symbol=symbol,day=day):
                self.assertIn("historical_quarantine:"+day,window_errors(symbol,[bar(day)],[day]))
                self.assertIn("historical_quarantine:"+day,assess(symbol,[bar(day)],day+"T23:59:59+05:45",{}))
                self.assertEqual(evaluate_timeframes([bar(day)],eligible=True,verified_sessions=[day],symbol=symbol)["status"],"unavailable")
    def test_omitted_key(self):
        symbol,day=next(iter(sorted(QUARANTINE)))
        d=date.fromisoformat(day)
        before=str(d-timedelta(days=1)); after=str(d+timedelta(days=1))
        self.assertIn("historical_quarantine:"+day,window_errors(symbol.lower(),[bar(before),bar(after)],[before,after]))
    def test_continuity(self):
        days=["2025-01-01","2025-01-02","2025-01-03"]
        rows=[bar(days[0]),bar(days[2])]
        self.assertIn("session_continuity_failed",window_errors("TEST",rows,days))
        self.assertIn("verified_session_calendar_required",window_errors("TEST",rows))
        self.assertIn("invalid_session_calendar",window_errors("TEST",rows,days[::-1]))
        self.assertTrue(window_errors("TEST",[rows[0],rows[0]],days))
        self.assertEqual(window_errors("TEST",[bar(d) for d in days],days),[])
    def test_replay(self):
        symbol,day=next(iter(sorted(QUARANTINE)))
        r=replay(symbol,[bar(day)],reviewed={},verified_sessions=[day])
        self.assertEqual(r["observations"],[])
        self.assertIn("historical_quarantine:"+day,r["excluded"][0]["reasons"])
    def test_broker_detector_blocks_every_quarantine_key(self):
        from app.broker_pattern_detector import detect_broker_patterns
        for symbol, day in sorted(QUARANTINE):
            d = date.fromisoformat(day)
            sessions = [str(d + timedelta(days=i)) for i in (-2,-1,1,2,3)]
            with self.subTest(symbol=symbol,day=day):
                result = detect_broker_patterns(symbol, [], [], [],
                    expected_sessions=sessions, complete_broker_sessions=sessions,
                    decision_at=sessions[-1]+"T23:59:59+05:45")
                self.assertEqual(result["status"],"INSUFFICIENT_EVIDENCE")
                self.assertIn("historical_quarantine:"+day,result["missing_features"])
                self.assertFalse(result["production_eligible"])

    def test_broker_api_rejects_client_calendar_mismatch(self):
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.main import BrokerPatternRequest, broker_patterns
        days=["2025-01-01","2025-01-02","2025-01-03","2025-01-04","2025-01-05"]
        request=BrokerPatternRequest(symbol="TEST",broker_rows=[],price_rows=[],
            market_context=[],expected_sessions=days,complete_broker_sessions=days,
            decision_at="2025-01-06T23:59:59+05:45")
        with patch("app.main.trusted_sessions",return_value=days+["2025-01-06"]), \
             patch("app.main.detect_broker_patterns") as detector:
            with self.assertRaises(HTTPException) as exc:
                broker_patterns(request)
            self.assertEqual(exc.exception.status_code,422)
            detector.assert_not_called()
        with patch("app.main.trusted_sessions",return_value=None):
            with self.assertRaises(HTTPException):
                broker_patterns(request)
        with patch("app.main.trusted_sessions",return_value=days), \
             patch("app.main.detect_broker_patterns",return_value={"status":"test"}) as detector:
            self.assertEqual(broker_patterns(request),{"status":"test"})
            self.assertEqual(detector.call_args.kwargs["expected_sessions"],days)

if __name__=="__main__":unittest.main()
