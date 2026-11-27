"""Research-only long holding exit plan; no order execution."""
from decimal import Decimal
from .automatic_evidence_adapter import derive_chart_evidence
from .corporate_action_trade_plan import _number

def dynamic_exit_plan(*,symbol,rows,benchmark_rows,sessions,assessment_time,
                      original_quantity,remaining_quantity,previous_stop,targets,
                      cumulative_fractions,horizon):
    chart=derive_chart_evidence(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,
                                sessions=sessions,assessment_time=assessment_time)
    config={"t_plus_2":(14,2,5),"swing":(14,3,10),"positional":(20,4,20)}
    if horizon not in config: raise ValueError("unsupported_horizon")
    period,multiple,lookback=config[horizon]
    if any(type(q) is not int for q in (original_quantity,remaining_quantity)) or not 0<remaining_quantity<=original_quantity:
        raise ValueError("invalid_quantity")
    stop=_number(previous_stop)
    levels=list(map(_number,targets))
    fractions=list(map(_number,cumulative_fractions))
    if stop<=0 or len(levels)!=3 or levels!=sorted(set(levels)) or min(levels)<=0:
        raise ValueError("invalid_levels")
    if len(fractions)!=3 or fractions!=sorted(set(fractions)) or not 0<fractions[0]<fractions[-1]<=1:
        raise ValueError("invalid_fractions")
    bars=sorted(rows,key=lambda r:r["date"])
    close=_number(bars[-1]["close"])
    result=dict(symbol=symbol,horizon=horizon,production_eligible=False,execution_eligible=False,
                previous_stop=str(stop),next_stop=str(stop),suggested_sale_quantity=0)
    if close<=stop:
        return dict(result,action="EXIT_REVIEW",suggested_sale_quantity=remaining_quantity)
    if len(bars)<max(period+1,lookback+1):
        return dict(result,action="UNKNOWN",reason="insufficient_history")
    ranges=[]
    for prev,bar in zip(bars[-period-1:-1],bars[-period:]):
        high,low,prior=map(_number,(bar["high"],bar["low"],prev["close"]))
        ranges.append(max(high-low,abs(high-prior),abs(low-prior)))
    atr=sum(ranges)/Decimal(period)
    atr_stop=close-multiple*atr
    swing=min(_number(r["low"]) for r in bars[-lookback-1:-1])
    candidates=[v for v in (atr_stop,swing) if stop<v<close]
    next_stop=max([stop]+candidates)
    reached=[f for t,f in zip(levels,fractions) if close>=t]
    desired=int(original_quantity*max(reached)) if reached else 0
    sale=max(0,min(remaining_quantity,desired-(original_quantity-remaining_quantity)))
    return dict(result,action="PROFIT_BOOKING_REVIEW" if sale else "TRAIL_REVIEW",
                next_stop=str(next_stop),atr=str(atr),suggested_sale_quantity=sale,
                source_ids=chart["source_ids"],
                limitations=["Simple mean true range, not Wilder ATR.",
                             "Prior-window low proxy, not confirmed swing pivot.",
                             "New stop applies prospectively; no same-bar fill.",
                             "Cumulative fractions caller supplied; all prior reductions count.",
                             "No fees, taxes, liquidity or settlement verification."])
