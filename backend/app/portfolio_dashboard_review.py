"""Stateless research dashboard; no saved holdings, execution or notifications."""
from .personalized_exit_review import review_personalized_exit
from .adaptive_exit_risk import adaptive_exit_review
from .dynamic_exit_plan import dynamic_exit_plan
from .corporate_action_trade_plan import _number

def portfolio_dashboard_review(*,holding,quote,snapshot,limits,distribution,market,sector,
                               assessment_time,reduction_fraction,cost_assumptions=None,
                               trailing_inputs=None):
    personal=review_personalized_exit(holding=holding,quote=quote,
        assessment_time=assessment_time,distribution=distribution)
    adaptive=adaptive_exit_review(snapshot=snapshot,limits=limits,holding=holding,
        distribution=distribution,market=market,sector=sector,assessment_time=assessment_time,
        reduction_fraction=reduction_fraction,cost_assumptions=cost_assumptions)
    position=next(p for p in snapshot["positions"] if p["symbol"]==holding["symbol"])
    if _number(position["mark"])!=_number(quote["close"]) or _number(position["quantity"])!=_number(holding["quantity"]):
        raise ValueError("holding_snapshot_mismatch")
    trail=None
    if trailing_inputs is not None:
        if trailing_inputs["remaining_quantity"]!=holding["quantity"]:
            raise ValueError("trailing_quantity_mismatch")
        if not trailing_inputs["rows"] or _number(max(trailing_inputs["rows"],key=lambda r:r["date"])["close"])!=_number(quote["close"]):
            raise ValueError("trailing_quote_mismatch")
        if personal["effective_stop"] is None or _number(trailing_inputs["previous_stop"])!=_number(personal["effective_stop"]):
            raise ValueError("trailing_stop_mismatch")
        trail=dynamic_exit_plan(symbol=holding["symbol"],horizon=holding["horizon"],
                               assessment_time=assessment_time,**trailing_inputs)
    actions=[personal["action"],adaptive["action"]]+([trail["action"]] if trail else [])
    action=next((a for a in ("EXIT_REVIEW","REDUCE_REVIEW","UNKNOWN","HOLD_WITH_CAUTION","PROFIT_BOOKING_REVIEW","TRAIL_REVIEW","HOLD_REVIEW") if a in actions),"UNKNOWN")
    # Never add independent reduction quantities: they refer to the same holding.
    return dict(schema_version="1",symbol=holding["symbol"],action=action,
                personal_review=personal,adaptive_review=adaptive,trailing_review=trail,
                broker_memory_status="NOT_ASSESSED",early_entry_status="NOT_ASSESSED",
                data_quality="CALLER_ATTESTED",production_eligible=False,execution_eligible=False,
                live_notifications_enabled=False,
                limitations=["Independent subreviews; no combined executable quantity.",
                             "No automatic broker memory retrieval or live portfolio persistence."])
