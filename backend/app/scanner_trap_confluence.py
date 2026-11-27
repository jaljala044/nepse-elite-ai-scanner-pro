"""Conservative research-only integration of existing trap evidence."""
from .scanner_breakout_guard import breakout_guard
from .liquidity_trap_review import review_liquidity_trap

def trap_confluence(*,symbol,rows,benchmark_rows,sessions,decision_time,calendar_evidence,broker_records,broker_numbers):
    guard=breakout_guard(symbol=symbol,rows=rows,sessions=sessions,decision_time=decision_time,calendar_evidence=calendar_evidence)
    base=dict(symbol=symbol,breakout=guard,production_eligible=False,execution_eligible=False,action="NO_TRADE")
    if guard["status"]=="UNKNOWN": return dict(base,status="UNKNOWN",trap=None)
    trap=review_liquidity_trap(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,sessions=sessions,assessment_time=decision_time,broker_records=broker_records,broker_numbers=broker_numbers)
    warning=guard["status"] in ("FAILED_BREAKOUT","REJECTION_WARNING")
    selling=trap["flags"]["persistent_broker_selling"]
    status="HIGH_RISK_REVIEW" if warning and selling is True else "STRUCTURAL_WARNING" if warning else "DISTRIBUTION_RISK_REVIEW" if trap["action"]=="DISTRIBUTION_RISK_REVIEW" else "STRUCTURAL_WARNING" if trap["action"]=="STRUCTURAL_WARNING" else "BROKER_WARNING" if trap["action"]=="BROKER_SELLING_INTO_STRENGTH_REVIEW" else "UNKNOWN" if not trap["complete_evidence"] else "WAIT"
    return dict(base,status=status,trap=trap,limitations=["No proof of operator manipulation; no automatic orders or calibrated probability."])
