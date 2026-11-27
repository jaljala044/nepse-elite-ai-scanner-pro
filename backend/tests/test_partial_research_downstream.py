import json
import unittest
from pathlib import Path
from app.partial_field_recovery import build_partial_view
from app.performance_statistics import summarize
from app.walk_forward_report import build_walk_forward_report
from app.broker_pattern_detector import detect_broker_patterns

class PartialResearchDownstreamTests(unittest.TestCase):
    def test_all_generated_keys_excluded(self):
        root=Path(__file__).resolve().parents[2]
        paths=["data/reference/p443_equity_quarantine.json",
               "data/reports/p443_reconstructed_candle_comparison_v1.json",
               "data/reports/p443_timestamp_chronology_comparison_v1.json"]
        rows=build_partial_view(*(json.loads((root/p).read_text())["records"] for p in paths))["records"]
        self.assertEqual(len(rows),1329)
        trades=[]
        forecasts=[]
        from datetime import date,timedelta
        for r in rows:
            s,d=r["symbol"],r["date"]
            lineage={"symbol":s,"history_start":d,"history_end":d}
            trades.append(dict(lineage,status="closed_scenario",net_pnl=100))
            forecasts.append(dict(lineage,observation_date=d,actual=1,probability=.9))
            day=date.fromisoformat(d)
            sessions=[str(day+timedelta(days=i)) for i in (-2,-1,1,2,3)]
            result=detect_broker_patterns(s,[],[],[],expected_sessions=sessions,
                complete_broker_sessions=sessions,decision_at=sessions[-1]+"T23:59:59+05:45")
            self.assertIn("historical_quarantine:"+d,result["missing_features"])
            self.assertFalse(result["production_eligible"])
        stats=summarize(trades,initial_capital=1000)
        self.assertEqual(stats["excluded_count"],1329)
        self.assertEqual(stats["sample_size"],0)
        wf=build_walk_forward_report(forecasts,1,1)
        self.assertEqual(wf["excluded_count"],1329)
        self.assertEqual(wf["fold_count"],0)
        self.assertFalse(wf["production_eligible"])
