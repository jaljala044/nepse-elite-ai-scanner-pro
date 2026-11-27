"""Native research bridge. Uncalibrated component directions remain unknown."""
from .independent_scanner_review import generate_idpat_review
from .unified_scanner_review import review_scanner
from .scanner_historical_evidence import validate_history

def review_native(*,symbol,rows,sessions,decision_time,calendar_evidence,broker_records,feature_inputs):
    history=validate_history(rows,sessions,symbol,decision_time,calendar_evidence)
    if history["missing_sessions"]: return dict(status="UNKNOWN",missing_sessions=history["missing_sessions"],production_eligible=False)
    if feature_inputs["snapshot"]["symbol"]!=symbol or feature_inputs["decision_time"]!=decision_time or feature_inputs["session_dates"]!=sessions: raise ValueError("feature_alignment_mismatch")
    idpat=generate_idpat_review(symbol=symbol,rows=history["rows"],assessment_time=decision_time,broker_records=broker_records,sessions=sessions)
    master=review_scanner(**feature_inputs)
    return dict(status="RESEARCH",IDPAT=idpat,MASTER=master,
        independent_directions={k:"UNKNOWN" for k in ("IDPAT","WYCKOFF","SMC","BROKER","MINERVINI_MOMENTUM","MASTER")},
        production_eligible=False,limitations=["Feature inputs not reconciled row-by-row; native independent directional adapters pending."])
