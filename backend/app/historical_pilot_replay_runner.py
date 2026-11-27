"""Execute six-scanner/four-horizon research runs only after explicit admission."""
from __future__ import annotations
from copy import deepcopy
from typing import Callable, Iterable, Mapping
from app.historical_pilot_replay_admission import STRATEGIES, HORIZONS


def run_admitted_six_scanner_replay(*, admission_report: Mapping[str, object], dataset_manifest_sha256: str, panel_rows: Iterable[Mapping[str, object]], run_one: Callable[..., Mapping[str, object]]) -> dict:
    """Invoke the injected existing runner for all 24 strategy/horizon combinations."""
    if admission_report.get("status") != "ADMITTED_FOR_RESEARCH_REPLAY" or admission_report.get("admitted") is not True:
        return {"status":"BLOCKED","runs":[],"errors":[{"reason":"research_replay_admission_not_granted"}],"historical_replay_executed":False}
    if dataset_manifest_sha256 != admission_report.get("dataset_manifest_sha256"):
        return {"status":"BLOCKED","runs":[],"errors":[{"reason":"dataset_manifest_fingerprint_mismatch"}],"historical_replay_executed":False}
    rows = [deepcopy(dict(row)) for row in panel_rows]
    if not rows: return {"status":"BLOCKED","runs":[],"errors":[{"reason":"admitted_panel_rows_missing"}],"historical_replay_executed":False}
    partition = admission_report.get("partition")
    if partition != "untouched_out_of_sample":
        return {"status":"BLOCKED","runs":[],"errors":[{"reason":"partition_not_untouched_oos"}],"historical_replay_executed":False}
    runs, errors = [], []
    for strategy_id in STRATEGIES:
        for horizon in HORIZONS:
            try:
                result = run_one(strategy_id=strategy_id,horizon=horizon,panel_rows=deepcopy(rows),dataset_manifest_sha256=dataset_manifest_sha256,partition=partition)
                if not isinstance(result,Mapping): raise TypeError("runner_result_must_be_mapping")
                expected = {"strategy_id":strategy_id,"horizon":horizon,"dataset_manifest_sha256":dataset_manifest_sha256,"partition":partition}
                mismatches = [key for key,value in expected.items() if result.get(key) != value]
                if mismatches:
                    errors.append({"strategy_id":strategy_id,"horizon":horizon,"reason":"runner_output_provenance_mismatch","fields":mismatches}); continue
                runs.append({"strategy_id":strategy_id,"horizon":horizon,"result":dict(result)})
            except Exception as exc:
                errors.append({"strategy_id":strategy_id,"horizon":horizon,"reason":"runner_execution_error","detail":type(exc).__name__})
    complete = len(runs)==len(STRATEGIES)*len(HORIZONS) and not errors
    return {"status":"RESEARCH_REPLAY_COMPLETED" if complete else "RESEARCH_REPLAY_INCOMPLETE","runs":runs,"errors":errors,"run_count":len(runs),"expected_run_count":len(STRATEGIES)*len(HORIZONS),"dataset_manifest_sha256":dataset_manifest_sha256,"partition":partition,"common_dataset_verified":all(x["result"].get("dataset_manifest_sha256")==dataset_manifest_sha256 for x in runs),"historical_replay_executed":bool(runs),"performance_metrics_interpreted":False,"probabilities_calibrated":False,"canonical_promotion_allowed":False,"production_enabled":False,"limitations":["Injected runner must implement chronological walk-forward, dated costs, liquidity, settlement, stop-first, price limits, circuits/no-bid and realistic fills.","Adapter verifies provenance metadata, not the correctness of trading calculations.","Partial runs remain incomplete and must not be compared as if all 24 evaluations completed.","No performance conclusion or probability calibration is performed."]}
