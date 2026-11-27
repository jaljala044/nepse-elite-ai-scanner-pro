import unittest
from app.historical_pilot_replay_runner import run_admitted_six_scanner_replay
from app.historical_pilot_replay_admission import STRATEGIES, HORIZONS


class ReplayRunnerAdapterTests(unittest.TestCase):
    def admission(self):
        return {"status":"ADMITTED_FOR_RESEARCH_REPLAY","admitted":True,"dataset_manifest_sha256":"a"*64,"partition":"untouched_out_of_sample"}
    def test_runs_all_24_with_one_fingerprint(self):
        seen=[]
        def runner(**kwargs):
            seen.append((kwargs["strategy_id"],kwargs["horizon"],kwargs["dataset_manifest_sha256"]))
            return {k:kwargs[k] for k in ("strategy_id","horizon","dataset_manifest_sha256","partition")}
        out=run_admitted_six_scanner_replay(admission_report=self.admission(),dataset_manifest_sha256="a"*64,panel_rows=[{"symbol":"AAA"}],run_one=runner)
        self.assertEqual(out["status"],"RESEARCH_REPLAY_COMPLETED"); self.assertEqual(len(seen),24); self.assertEqual(out["run_count"],len(STRATEGIES)*len(HORIZONS))
    def test_unadmitted_dataset_never_calls_runner(self):
        called=[]
        out=run_admitted_six_scanner_replay(admission_report={"status":"BLOCKED"},dataset_manifest_sha256="a"*64,panel_rows=[{"symbol":"AAA"}],run_one=lambda **kw:called.append(kw))
        self.assertEqual(out["status"],"BLOCKED"); self.assertEqual(called,[])
    def test_fingerprint_mismatch_blocks(self):
        out=run_admitted_six_scanner_replay(admission_report=self.admission(),dataset_manifest_sha256="b"*64,panel_rows=[{"symbol":"AAA"}],run_one=lambda **kw:{})
        self.assertEqual(out["status"],"BLOCKED")
    def test_mismatched_runner_output_is_not_counted(self):
        def runner(**kwargs):
            return {"strategy_id":kwargs["strategy_id"],"horizon":kwargs["horizon"],"dataset_manifest_sha256":"wrong","partition":kwargs["partition"]}
        out=run_admitted_six_scanner_replay(admission_report=self.admission(),dataset_manifest_sha256="a"*64,panel_rows=[{"symbol":"AAA"}],run_one=runner)
        self.assertEqual(out["status"],"RESEARCH_REPLAY_INCOMPLETE"); self.assertEqual(out["run_count"],0)


if __name__=="__main__": unittest.main()
