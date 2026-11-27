"""Research-only coordination; never sends orders."""
from .scanner_trap_confluence import trap_confluence
from .dynamic_exit_plan import dynamic_exit_plan

def review_entry_exit(*,trap_inputs,exit_inputs=None):
    trap=trap_confluence(**trap_inputs)
    result=dict(trap=trap,entry_action="WAIT" if trap["status"]=="WAIT" else "NO_TRADE",
                exit_review=None,production_eligible=False,execution_eligible=False)
    if exit_inputs is None or trap["status"]=="UNKNOWN": return result
    shared=("symbol","rows","benchmark_rows","sessions")
    if any(exit_inputs[k]!=trap_inputs[k] for k in shared) or exit_inputs["assessment_time"]!=trap_inputs["decision_time"]:
        raise ValueError("entry_exit_evidence_mismatch")
    result["exit_review"]=dynamic_exit_plan(**exit_inputs)
    if trap["status"] in ("HIGH_RISK_REVIEW","DISTRIBUTION_RISK_REVIEW","BROKER_WARNING","STRUCTURAL_WARNING"):
        result["holding_warning"]="MANUAL_RISK_REVIEW"
    return result
