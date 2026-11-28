import unittest
from app.performance_statistics import benchmark_report
from app.part5_holdout_universe import holdout_partition, historical_membership
from app.walk_forward_report import build_causal_walk_forward_report

def row(key, day, end):
    return dict(record_id=key, observation_date=day, decision_at=day+"T12:00:00Z",
        feature_available_at=day+"T10:00:00Z",forecast_issued_at=day+"T12:00:00Z",
        label_end_at=end+"T12:00:00Z",label_available_at=end+"T13:00:00Z",actual=1,probability=.8)

class Part5ValidationTests(unittest.TestCase):
    def test_benchmark(self):
        days=["2025-01-01","2025-01-02"]
        a=[dict(date=d,net_return=v) for d,v in zip(days,[.1,-.1])]
        b=[dict(date=d,net_return=0) for d in days]
        result=benchmark_report(a,b,expected_sessions=days,periods_per_year=2)
        self.assertAlmostEqual(result["cagr"],-.01)
        self.assertAlmostEqual(result["calmar"],-.1)
        self.assertFalse(result["production_approved"])
        self.assertIsNone(benchmark_report(a,b,expected_sessions=days,periods_per_year=250)["cagr"])
        with self.assertRaises(ValueError):
            benchmark_report(a,b[:1],expected_sessions=days,periods_per_year=2)

    def test_holdout_maturity(self):
        rows=[row("a","2025-01-01","2025-01-02"),row("b","2025-01-03","2025-01-07"),
              row("c","2025-01-06","2025-01-07")]
        result=holdout_partition(rows,frozen_at="2025-01-04T00:00:00Z",
            holdout_start="2025-01-05T00:00:00Z",holdout_end="2025-01-08T00:00:00Z",
            evaluation_at="2025-01-09T00:00:00Z")
        self.assertEqual(result["train_ids"],["a"])
        self.assertEqual(result["holdout_ids"],["c"])
        self.assertEqual(result["excluded_ids"],["b"])
        self.assertFalse(result["independent_holdout_verified"])

    def test_historical_missing_predecessor(self):
        records=[dict(security_id="old",effective_from="2024-01-01T00:00:00Z",
            effective_to="2025-02-01T00:00:00Z",available_at="2024-01-01T00:00:00Z",
            evidence_reviewed=True,status="suspended")]
        args=dict(decision_at="2025-01-01T00:00:00Z")
        self.assertTrue(historical_membership(["old"],records,**args)["research_membership_aligned"])
        self.assertEqual(historical_membership(["old"],[],**args)["missing_ids"],["old"])
        self.assertFalse(historical_membership(["old"],records*2,**args)["research_membership_aligned"])

    def test_walk_forward_purges_unmatured_labels(self):
        rows=[row("a","2025-01-01","2025-01-02"),row("b","2025-01-02","2025-01-05"),
              row("c","2025-01-03","2025-01-04")]
        result=build_causal_walk_forward_report(rows,2,1,evaluation_at="2025-01-07T00:00:00Z")
        self.assertEqual(result["folds"][0]["purged_train_rows"],1)
        self.assertEqual(result["folds"][0]["status"],"insufficient_sample")
