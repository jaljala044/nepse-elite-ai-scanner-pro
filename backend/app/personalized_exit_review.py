"""Caller-attested personalized holding review; no executable orders."""
from .corporate_action_trade_plan import _time, _number
from .unified_portfolio_event_engine import _available

def review_personalized_exit(*,holding,quote,assessment_time,distribution=None):
    now=_time(assessment_time)
    for name,item in (("holding",holding),("quote",quote)):
        _available(item,now,name)
    symbol=holding["symbol"]
    if quote["symbol"]!=symbol or not holding.get("basis_id") or quote.get("basis_id")!=holding["basis_id"]:
        raise ValueError("symbol_or_price_basis_mismatch")
    horizon=holding["horizon"]
    if horizon not in ("t_plus_2","swing","positional","investment"):
        raise ValueError("invalid_horizon")
    qty,cost,mark=map(_number,(holding["quantity"],holding["average_cost"],quote["close"]))
    if min(qty,cost,mark)<=0 or qty!=int(qty):
        raise ValueError("invalid_holding")
    if _time(quote["observed_at"])>_time(quote["available_at"]):
        raise ValueError("quote_lookahead")
    fresh=_time(quote["observed_at"]).date()==now.date()
    stop=_number(holding["stop"]) if holding.get("stop") is not None else None
    trail=_number(holding["trailing_stop"]) if holding.get("trailing_stop") is not None else None
    target=_number(holding["profit_target"]) if holding.get("profit_target") is not None else None
    if any(v is not None and v<=0 for v in (stop,trail,target)):
        raise ValueError("invalid_plan_level")
    effective=max([v for v in (stop,trail) if v is not None],default=None)
    risk="UNKNOWN"
    if distribution is not None:
        _available(distribution,now,"distribution")
        if distribution["symbol"]!=symbol: raise ValueError("distribution_symbol_mismatch")
        if distribution.get("as_of_session")==_time(quote["observed_at"]).date().isoformat():
            risk=distribution["action"]
    action="UNKNOWN"
    reasons=[]
    if not fresh: reasons.append("quote_not_same_day")
    elif effective is not None and mark<=effective:
        action="EXIT_REVIEW"; reasons.append("stop_breached_on_close")
    elif risk=="DISTRIBUTION_RISK_REVIEW":
        action="REDUCE_REVIEW"; reasons.append("distribution_confluence")
    elif target is not None and mark>=target and mark>cost:
        action="PROFIT_BOOKING_REVIEW"; reasons.append("user_target_reached")
    elif risk in ("STRUCTURAL_WARNING","BROKER_SELLING_INTO_STRENGTH_REVIEW"):
        action="HOLD_WITH_CAUTION"; reasons.append(risk)
    elif effective is not None and risk=="NO_CONFLUENCE_OBSERVED":
        action="HOLD_REVIEW"
    else: reasons.append("insufficient_exit_evidence")
    return dict(symbol=symbol,horizon=horizon,action=action,reasons=reasons,
                quantity=int(qty),gross_unrealized_pnl=str(qty*(mark-cost)),
                gross_return_pct=float(100*(mark/cost-1)),effective_stop=str(effective) if effective is not None else None,
                distribution_status=risk,execution_eligible=False,production_eligible=False,
                limitations=["Same-day caller-attested closing quote required; no live fill.",
                             "Gross P&L excludes fees and taxes.",
                             "Stops and targets supplied by caller; no automatic trailing or sale quantity.",
                             "No independent market, sector or custody verification."])
