"""Research-only adaptive reduction scenario; never an executable order."""
from decimal import Decimal, ROUND_CEILING
from .corporate_action_risk import assess_post_action_risk
from .corporate_action_trade_plan import _time, _number
from .unified_portfolio_event_engine import _available
from .execution_costs import round_trip

def adaptive_exit_review(*,snapshot,limits,holding,distribution,market,sector,
                         assessment_time,reduction_fraction,cost_assumptions=None):
    now=_time(assessment_time)
    for name,item in (("holding",holding),("distribution",distribution),("market",market),("sector",sector)):
        _available(item,now,name)
    symbol=holding["symbol"]
    if distribution["symbol"]!=symbol: raise ValueError("symbol_mismatch")
    position=next((p for p in snapshot["positions"] if p["symbol"]==symbol),None)
    if position is None or sector.get("sector")!=position["sector"]: raise ValueError("position_or_sector_mismatch")
    qty,settled,cost,mark=map(_number,(position["quantity"],holding["settled_quantity"],holding["average_cost"],position["mark"]))
    fraction=_number(reduction_fraction)
    if not 0<=settled<=qty or settled!=int(settled) or cost<=0 or not 0<fraction<=1:
        raise ValueError("invalid_holding_or_fraction")
    if not holding.get("basis_id") or holding["basis_id"]!=position.get("basis_id"):
        raise ValueError("price_basis_mismatch")
    risk=assess_post_action_risk(snapshot=snapshot,limits=limits,assessment_time=assessment_time)
    alert=next(a for a in risk["alerts"] if a["symbol"]==symbol)
    fresh=all(item.get("as_of_session")==now.date().isoformat() for item in (position,holding,distribution,market,sector))
    action="UNKNOWN"
    desired=0
    reasons=list(alert["reasons"])
    if fresh:
        if alert["action"]=="EXIT_REVIEW":
            action="EXIT_REVIEW"; desired=int(qty)
        elif alert["action"]=="REDUCE_REVIEW" or distribution.get("action")=="DISTRIBUTION_RISK_REVIEW":
            action="REDUCE_REVIEW"; desired=int((qty*fraction).to_integral_value(rounding=ROUND_CEILING))
        elif market.get("regime") in ("markdown","distribution","correction") or sector.get("classification") in ("Weakening","Lagging"):
            action="HOLD_WITH_CAUTION"; reasons.append("market_or_sector_weakness")
        elif alert["action"]=="HOLD_REVIEW" and distribution.get("action")=="NO_CONFLUENCE_OBSERVED" and market.get("regime") in ("bull","markup","accumulation","sideways") and sector.get("classification") in ("Leading","Improving","Neutral"):
            action="HOLD_REVIEW"
    else: reasons.append("same_session_evidence_required")
    sale=min(desired,int(settled))
    costs=round_trip(cost,mark,sale,assumptions=cost_assumptions) if sale else None
    return dict(symbol=symbol,action=action,reasons=reasons,desired_reduction_quantity=desired,
                settled_share_capped_quantity=sale,unavailable_quantity=desired-sale,
                gross_pnl_scenario=str((mark-cost)*sale),cost_scenario=costs,portfolio_risk=risk,
                production_eligible=False,execution_eligible=False,
                limitations=["Caller-attested same-day evidence and settled quantity.",
                             "Reduction fraction is supplied, not optimized or guaranteed to cure concentration.",
                             "Round-trip costs approximate historical acquisition and hypothetical sale.",
                             "No verified tax lots, market depth, circuit limits or actual fills."])
