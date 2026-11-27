"""Research holding protection independent of optional trap evidence."""
from .personalized_exit_review import review_personalized_exit
from .scanner_trap_confluence import trap_confluence
from .corporate_action_trade_plan import _time, _number

def personalized_guard(*,holding,quote,assessment_time,trap_inputs=None):
    baseline=review_personalized_exit(holding=holding,quote=quote,assessment_time=assessment_time)
    result=dict(baseline=baseline,action=baseline["action"],trap=None,trap_status="UNKNOWN",
                production_eligible=False,execution_eligible=False,new_entry_allowed=False)
    if trap_inputs is None: return result
    if trap_inputs["symbol"]!=holding["symbol"] or _time(trap_inputs["decision_time"])!=_time(assessment_time):
        raise ValueError("holding_trap_identity_mismatch")
    if not trap_inputs["rows"]: return result
    latest=max(trap_inputs["rows"],key=lambda r:r["date"])
    if latest.get("basis_id")!=holding["basis_id"] or _number(latest["close"])!=_number(quote["close"]) or latest["date"]!=_time(quote["observed_at"]).date().isoformat():
        raise ValueError("holding_trap_quote_mismatch")
    try:
        trap=trap_confluence(**trap_inputs)
    except (ValueError,TypeError,KeyError,ArithmeticError) as exc:
        return dict(result,trap_error=str(exc))
    result.update(trap=trap,trap_status=trap["status"])
    if baseline["action"]=="EXIT_REVIEW": return result
    if _time(quote["observed_at"]).date()!=_time(assessment_time).date(): return result
    if trap["status"] in ("HIGH_RISK_REVIEW","DISTRIBUTION_RISK_REVIEW"):
        result["action"]="REDUCE_REVIEW"
    elif trap["status"] in ("STRUCTURAL_WARNING","BROKER_WARNING") and baseline["action"]!="PROFIT_BOOKING_REVIEW":
        result["action"]="HOLD_WITH_CAUTION"
    return result
