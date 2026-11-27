"""Fail closed before invoking native research engines."""
from .scanner_pilot_inputs import pilot_inputs
from .six_scanner_pipeline import run_six_scanners
from .scanner_common_cohort import METHODS

def run_pilot(*,inputs,calendar_evidence,feature_inputs,horizon):
    report=pilot_inputs(**inputs)
    coverage=report["coverage"][horizon]
    if not coverage["date_coverage_complete"] or not coverage["action_basis_verified"]:
        return dict(status="UNKNOWN",coverage=coverage,reviews={m:dict(direction="UNKNOWN",action="NO_TRADE") for m in METHODS},production_eligible=False)
    symbol=inputs["symbol"]
    sessions=inputs["sessions"]
    rows=sorted([r for r in inputs["stocks"] if r["symbol"]==symbol and r["date"] in sessions],key=lambda r:r["date"])
    benchmark=sorted([r for r in inputs["benchmark"] if r["symbol"]=="NEPSE" and r["date"] in sessions],key=lambda r:r["date"])
    brokers=[r for r in inputs["brokers"] if r["symbol"]==symbol and r["date"] in sessions[-5:]]
    result=run_six_scanners(symbol=symbol,rows=rows,benchmark_rows=benchmark,sessions=sessions,decision_time=inputs["decision_time"],calendar_evidence=calendar_evidence,broker_records=brokers,feature_inputs=feature_inputs,horizon=horizon)
    return dict(result,coverage=coverage,backtest_eligible=False)
