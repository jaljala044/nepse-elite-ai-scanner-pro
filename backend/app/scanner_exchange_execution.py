"""Conservative order-book/circuit-aware execution simulation for NEPSE replay.

All book, price-band and session inputs must be point-in-time verified evidence.
This is a scenario simulator, not a live order router or exchange-rule oracle.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR

def _d(value):
    try: number=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): return None
    return number if number.is_finite() else None

def _time(value):
    if not isinstance(value,str): return None
    try: result=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if result.tzinfo is None or result.utcoffset() is None: return None
    return result.astimezone(timezone.utc)

def _verified(record, cutoff):
    if not isinstance(record,dict) or record.get("evidence_status")!="verified": return False
    if not all(isinstance(record.get(k),str) and record[k].strip() for k in ("source_id","evidence_id")): return False
    available=_time(record.get("available_at"))
    return available is not None and available<=cutoff

def _round_tick(price, tick, side):
    units=price/tick
    rounding=ROUND_CEILING if side=="buy" else ROUND_FLOOR
    return units.to_integral_value(rounding=rounding)*tick

def simulate_exchange_execution(*, order, sessions, impact_bps="0", max_participation_pct="5"):
    if not isinstance(order,dict) or not isinstance(sessions,list):
        raise ValueError("order_and_sessions_required")
    side=order.get("side")
    if side not in {"buy","sell"}: raise ValueError("side_must_be_buy_or_sell")
    qty=order.get("quantity")
    if isinstance(qty,bool) or not isinstance(qty,int) or qty<1: raise ValueError("positive_whole_share_quantity_required")
    order_time=_time(order.get("submitted_at"))
    if order_time is None or not _verified(order,order_time): raise ValueError("verified_order_provenance_required")
    limit=_d(order.get("limit_price"))
    if limit is not None and limit<=0: raise ValueError("invalid_limit_price")
    tick=_d(order.get("tick_size"))
    impact_rate=_d(impact_bps); participation=_d(max_participation_pct)
    if tick is None or tick<=0 or impact_rate is None or impact_rate<0 or participation is None or not (0<participation<=100):
        raise ValueError("execution_parameters_invalid")
    sellable=order.get("sellable_quantity",qty)
    if isinstance(sellable,bool) or not isinstance(sellable,int) or sellable<0:
        raise ValueError("sellable_quantity_invalid")
    if side=="sell" and qty>sellable:
        return {"status":"blocked","filled_quantity":0,"remaining_quantity":qty,
            "fills":[],"reason":"quantity_exceeds_settled_sellable_inventory",
            "production_enabled":False}
    remaining=qty; fills=[]; events=[]
    seen_dates=set()
    for session in sessions:
        if remaining==0: break
        if not isinstance(session,dict): raise ValueError("session_record_invalid")
        day=session.get("session_date")
        if not isinstance(day,str) or day in seen_dates: raise ValueError("duplicate_or_invalid_session_date")
        seen_dates.add(day)
        execution_at=_time(session.get("execution_at"))
        if execution_at is None or execution_at<order_time: continue
        if not _verified(session,execution_at): 
            events.append({"session_date":day,"status":"withheld","reason":"session_provenance_invalid"}); continue
        bands=session.get("price_band")
        if not _verified(bands,execution_at): 
            events.append({"session_date":day,"status":"withheld","reason":"price_band_provenance_invalid"}); continue
        lower,upper=_d(bands.get("lower_limit")), _d(bands.get("upper_limit"))
        if lower is None or upper is None or lower<=0 or upper<lower: raise ValueError("price_band_invalid")
        book=session.get("order_book")
        if not _verified(book,execution_at):
            events.append({"session_date":day,"status":"withheld","reason":"order_book_provenance_invalid"}); continue
        if book.get("halted") is True:
            events.append({"session_date":day,"status":"blocked","reason":"trading_halt"}); continue
        if book.get("locked_at_upper") is True and side=="buy":
            events.append({"session_date":day,"status":"blocked","reason":"upper_circuit_no_buy_execution"}); continue
        if book.get("locked_at_lower") is True and side=="sell":
            events.append({"session_date":day,"status":"blocked","reason":"lower_circuit_no_sell_execution"}); continue
        levels=book.get("asks" if side=="buy" else "bids")
        if not isinstance(levels,list) or not levels:
            events.append({"session_date":day,"status":"unfilled","reason":"no_executable_depth"}); continue
        traded_volume=_d(session.get("traded_volume"))
        if traded_volume is None or traded_volume<0: raise ValueError("session_traded_volume_invalid")
        capacity=(traded_volume*participation/100).to_integral_value(rounding=ROUND_FLOOR)
        daily_filled=0
        for level in levels:
            if remaining<=0 or daily_filled>=capacity: break
            if not _verified(level,execution_at): continue
            price=_d(level.get("price")); depth=level.get("quantity")
            if price is None or price<=0 or isinstance(depth,bool) or not isinstance(depth,int) or depth<0:
                continue
            if price<lower or price>upper: continue
            # A limit order cannot pay above its limit or sell below it.
            if limit is not None and ((side=="buy" and price>limit) or (side=="sell" and price<limit)):
                continue
            available=min(depth,remaining,int(capacity)-daily_filled)
            if available<=0: continue
            impact_amount=price*impact_rate/Decimal("10000")
            execution_price=_round_tick(price+impact_amount if side=="buy" else price-impact_amount,tick,side)
            execution_price=max(lower,min(upper,execution_price))
            if limit is not None and ((side=="buy" and execution_price>limit) or (side=="sell" and execution_price<limit)):
                continue
            fills.append({"session_date":day,"execution_at":execution_at.isoformat(),
                "quantity":available,"price":str(execution_price),"source_level_price":str(price),
                "side":side,"impact_bps":str(_d(impact_bps))})
            remaining-=available; daily_filled+=available
        events.append({"session_date":day,"status":"filled" if daily_filled else "unfilled",
            "filled_quantity":daily_filled,"capacity_quantity":int(capacity)})
    filled=qty-remaining
    notional=sum((Decimal(f["quantity"])*Decimal(f["price"]) for f in fills),Decimal("0"))
    average=notional/filled if filled else None
    return {"schema_version":"nepse-execution-sim-1.0.0",
        "status":"filled" if remaining==0 else ("partially_filled" if filled else "unfilled"),
        "side":side,"requested_quantity":qty,"filled_quantity":filled,"remaining_quantity":remaining,
        "average_fill_price":str(average) if average is not None else None,
        "notional":str(notional),"fills":fills,"events":events,
        "assumptions":{"max_volume_participation_pct":str(participation),
            "market_impact_bps":str(impact_bps),"tick_size":str(tick),
            "price_limits_and_order_book_must_be_verified":True},
        "limitations":["Depth snapshots are treated as executable only at their supplied timestamps; queue priority and cancellations are not modeled.",
            "Circuit locks, halted sessions and missing depth prevent fills; no synthetic fill is invented.",
            "Partial fills are retained as partial; the simulator does not assume completion at the candle close.",
            "Price bands are supplied verified inputs, not derived from assumed NEPSE rules.",
            "This is historical scenario analysis only; it does not submit exchange orders."],
        "production_enabled":False,"performance_claimed":False}
