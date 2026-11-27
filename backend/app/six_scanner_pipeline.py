"""Research-only orchestration, not a production recommendation engine."""
from .scanner_native_research_bridge import review_native
from .native_independent_scanners import native_reviews
from .independent_scanner_review import resolve_reviews
from .scanner_common_cohort import METHODS

def run_six_scanners(*,symbol,rows,benchmark_rows,sessions,decision_time,calendar_evidence,broker_records,feature_inputs,horizon):
    if horizon not in ("T+2","swing","positional","investment"): raise ValueError("invalid_horizon")
    bridge=review_native(symbol=symbol,rows=rows,sessions=sessions,decision_time=decision_time,calendar_evidence=calendar_evidence,broker_records=broker_records,feature_inputs=feature_inputs)
    if bridge["status"]=="UNKNOWN":
        return dict(status="UNKNOWN",reviews={m:dict(direction="UNKNOWN",action="NO_TRADE") for m in METHODS},missing_sessions=bridge["missing_sessions"],production_eligible=False)
    reviews=native_reviews(symbol=symbol,horizon=horizon,rows=rows,benchmark_rows=benchmark_rows,sessions=sessions,assessment_time=decision_time,broker_records=broker_records)
    idpat=bridge["IDPAT"]
    reviews["IDPAT"]=dict(direction="UNKNOWN",evidence=idpat,evidence_id=idpat["review_id"])
    reviews["MASTER"]=dict(direction="UNKNOWN",evidence=bridge["MASTER"])
    for name,r in reviews.items():
        r.update(action="NO_TRADE",confidence="LOW",production_eligible=False)
        r["independent_score"]=r["evidence"].get("score") if name in ("WYCKOFF","MASTER") else r["evidence"]["trend"].get("score") if name=="MINERVINI_MOMENTUM" else None
        r["plan"]=idpat["result"]["plans"][horizon] if name=="IDPAT" else dict(entry=None,stop=None,T1=None,T2=None,T3=None,reward_risk=None)
    return dict(status="RESEARCH",symbol=symbol,horizon=horizon,reviews=reviews,
        confluence=resolve_reviews({k:v["direction"] for k,v in reviews.items() if k!="MASTER"}),production_eligible=False,
        limitations=["No calibrated confidence or independent executable plans; feature records not reconciled row-by-row."])
