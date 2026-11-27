import unittest
from app.scanner_feature_ablation_orchestrator import run_feature_ablation_matrix
from app.scanner_experiment_registry import append_experiment_events

class ExperimentRegistryTests(unittest.TestCase):
    def test_append_and_verify_hash_chain(self):
        one=append_experiment_events(existing_events=[],new_events=[{
            "event_id":"E1","event_type":"EXPERIMENT_REGISTERED","run_id":"R1",
            "occurred_at":"2026-01-01T00:00:00+00:00","payload":{"x":1}}])
        two=append_experiment_events(existing_events=one["events"],new_events=[{
            "event_id":"E2","event_type":"EXPERIMENT_COMPLETED","run_id":"R1",
            "occurred_at":"2026-01-01T00:01:00+00:00","payload":{"status":"completed"}}])
        self.assertEqual(two["event_count"],2)
        tampered=[dict(two["events"][0],payload={"x":2}),two["events"][1]]
        with self.assertRaisesRegex(ValueError,"registry_event_hash_mismatch"):
            append_experiment_events(existing_events=tampered,new_events=[])

class AblationMatrixTests(unittest.TestCase):
    def _folds(self):
        return [{"fold_id":f"F{i}","partition":"out_of_sample",
            "universe_fingerprint":"U","panel_fingerprint":f"P{i}",
            "cost_model_id":"C","execution_model_id":"X","methodology_version":"M"} for i in range(3)]
    def test_runs_all_strategies_horizons_and_matched_variants(self):
        calls=[]
        def runner(**kwargs):
            calls.append((kwargs["strategy_id"],kwargs["horizon"],kwargs["fold"]["fold_id"],kwargs["excluded_feature_groups"]))
            return {"universe_fingerprint":"U","panel_fingerprint":kwargs["fold"]["panel_fingerprint"],
                "cost_model_id":"C","execution_model_id":"X","methodology_version":"M",
                "closed_trades":[{"net_return_pct":"1" if not kwargs["excluded_feature_groups"] else "0.5",
                    "exit_date":"2026-01-02"} for _ in range(12)]}
        out=run_feature_ablation_matrix(run_variant=runner,folds=self._folds(),
            run_timestamp="2026-02-01T00:00:00+00:00",minimum_total_trades=30,minimum_folds=3)
        self.assertEqual(out["strategy_count"],6)
        self.assertEqual(out["horizon_count"],4)
        self.assertEqual(out["fold_count"],3)
        self.assertGreater(out["comparison_count"],0)
        self.assertEqual(out["status"],"completed")
        self.assertGreater(out["experiment_registry"]["event_count"],0)
        self.assertTrue(all(c[3] == () or len(c[3]) == 1 for c in calls))
    def test_rejects_non_oos_fold(self):
        fold=self._folds()[0];fold["partition"]="train"
        with self.assertRaisesRegex(ValueError,"every_fold_must_be_out_of_sample"):
            run_feature_ablation_matrix(run_variant=lambda **k:{},folds=[fold]*3,
                run_timestamp="2026-02-01T00:00:00+00:00")
    def test_assumption_mismatch_fails_closed(self):
        folds=self._folds()
        def runner(**kwargs):
            return {"universe_fingerprint":"U","panel_fingerprint":"WRONG",
                "cost_model_id":"C","execution_model_id":"X","methodology_version":"M",
                "closed_trades":[]}
        with self.assertRaisesRegex(ValueError,"baseline_fold_assumption_mismatch"):
            run_feature_ablation_matrix(run_variant=runner,folds=folds,
                run_timestamp="2026-02-01T00:00:00+00:00")

if __name__=="__main__": unittest.main()
