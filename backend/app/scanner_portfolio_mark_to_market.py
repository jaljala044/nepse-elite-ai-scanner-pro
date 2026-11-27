"""Daily mark-to-market portfolio curve from verified fills, marks and opening inventory."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

NEPAL=ZoneInfo("Asia/Kathmandu")

def _d(value):
    try: result=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): return None
    return result if result.is_finite() else None

def _day(value):
    try: return date.fromisoformat(value)
    except (TypeError,ValueError): return None

def _time(value):
    if not isinstance(value,str): return None
    try: result=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if result.tzinfo is None or result.utcoffset() is None: return None
    return result

def _verified(item, cutoff):
    if not isinstance(item,dict) or item.get("evidence_status")!="verified": return False
    if not all(isinstance(item.get(k),str) and item[k].strip() for k in ("source_id","evidence_id")): return False
    available=_time(item.get("available_at"))
    return available is not None and cutoff is not None and available<=cutoff

def build_mark_to_market_curve(*, initial_cash, executions, daily_marks,
    transaction_cost_bps="0", initial_positions=None):
    cash=_d(initial_cash); cost=_d(transaction_cost_bps)
    if cash is None or cash<=0 or cost is None or cost<0 or cost>=10000:
        raise ValueError("initial_cash_or_transaction_cost_invalid")
    if not isinstance(executions,list) or not isinstance(daily_marks,list):
        raise ValueError("executions_and_marks_must_be_lists")
    if initial_positions is None: initial_positions=[]
    if not isinstance(initial_positions,list): raise ValueError("initial_positions_must_be_list")
    fills=[]; rejected=[]; seen=set()
    for i,item in enumerate(executions):
        if not isinstance(item,dict):
            rejected.append({"index":i,"reason":"execution_record_invalid"}); continue
        day=_day(item.get("execution_date")); side=item.get("side"); qty=item.get("quantity"); price=_d(item.get("price"))
        execution_at=_time(item.get("execution_at")); key=item.get("execution_id")
        if (day is None or side not in {"buy","sell"} or isinstance(qty,bool) or not isinstance(qty,int)
                or qty<1 or price is None or price<=0 or execution_at is None
                or execution_at.astimezone(NEPAL).date()!=day or not _verified(item,execution_at)
                or not isinstance(key,str) or not key.strip() or key in seen):
            rejected.append({"index":i,"reason":"execution_fields_or_point_in_time_evidence_invalid"}); continue
        seq=item.get("sequence",0)
        if isinstance(seq,bool) or not isinstance(seq,int) or seq<0:
            rejected.append({"index":i,"reason":"execution_sequence_invalid"}); continue
        seen.add(key); fills.append({**item,"_day":day,"_price":price,"_notional":price*qty})
    marks={}; mark_days=set(); mark_cutoffs={}
    for item in daily_marks:
        if not isinstance(item,dict): raise ValueError("daily_mark_record_invalid")
        day=_day(item.get("session_date")); symbol=item.get("symbol"); price=_d(item.get("close"))
        decision_cutoff=_time(item.get("decision_cutoff"))
        if (day is None or not isinstance(symbol,str) or not symbol.strip() or price is None or price<=0
                or decision_cutoff is None or decision_cutoff.astimezone(NEPAL).date()<day
                or not _verified(item,decision_cutoff)):
            raise ValueError("daily_mark_fields_or_point_in_time_evidence_invalid")
        key=(day,symbol)
        if key in marks: raise ValueError("duplicate_symbol_session_mark")
        marks[key]=price; mark_days.add(day); mark_cutoffs[key]=decision_cutoff
    if not mark_days: raise ValueError("daily_marks_required")
    dates=sorted(mark_days); first_day=dates[0]
    if any(item["_day"]>dates[-1] for item in fills):
        raise ValueError("execution_after_last_mark_date")
    first_cutoff_by_symbol={symbol:cutoff for (day,symbol),cutoff in mark_cutoffs.items() if day==first_day}
    positions={}; opening_cost=Decimal("0"); seen_open=set()
    for item in initial_positions:
        if not isinstance(item,dict): raise ValueError("initial_position_record_invalid")
        symbol=item.get("symbol"); qty=item.get("quantity"); basis=_d(item.get("cost_basis"))
        as_of=_time(item.get("as_of")); cutoff=first_cutoff_by_symbol.get(symbol)
        if (not isinstance(symbol,str) or not symbol.strip() or isinstance(qty,bool)
                or not isinstance(qty,int) or qty<1 or basis is None or basis<=0
                or as_of is None or cutoff is None or as_of>cutoff or not _verified(item,cutoff)
                or symbol in seen_open):
            raise ValueError("initial_position_fields_or_point_in_time_evidence_invalid")
        seen_open.add(symbol); positions[symbol]=Decimal(qty); opening_cost+=Decimal(qty)*basis
    initial_equity=cash+opening_cost
    fills.sort(key=lambda x:(x["_day"],x.get("sequence",0),x["execution_id"]))
    fill_index=0; peak=initial_equity; max_dd=Decimal("0"); curve=[]; total_cost=Decimal("0")
    for day in dates:
        while fill_index<len(fills) and fills[fill_index]["_day"]<=day:
            item=fills[fill_index]; fill_index+=1
            symbol=item.get("symbol")
            if not isinstance(symbol,str) or not symbol.strip(): raise ValueError("execution_symbol_required")
            qty=Decimal(item["quantity"]); notional=item["_notional"]; fee=notional*cost/Decimal("10000")
            total_cost+=fee; current=positions.get(symbol,Decimal("0"))
            if item["side"]=="buy":
                if cash<notional+fee: raise ValueError("insufficient_cash_for_execution:"+symbol)
                cash-=notional+fee; positions[symbol]=current+qty
            else:
                if current<qty: raise ValueError("sell_exceeds_portfolio_inventory:"+symbol)
                cash+=notional-fee; positions[symbol]=current-qty
        market_value=Decimal("0"); missing=[]
        for symbol,qty in positions.items():
            if qty==0: continue
            mark=marks.get((day,symbol))
            if mark is None: missing.append(symbol)
            else: market_value+=qty*mark
        if missing: raise ValueError("missing_point_in_time_marks:"+",".join(sorted(missing)))
        equity=cash+market_value; peak=max(peak,equity)
        drawdown=(peak-equity)/peak*100 if peak else Decimal("0")
        max_dd=max(max_dd,drawdown)
        curve.append({"session_date":day.isoformat(),"cash":str(cash),
            "market_value":str(market_value),"equity":str(equity),
            "drawdown_pct":str(drawdown),"open_symbols":sorted(s for s,q in positions.items() if q>0)})
    ending=Decimal(curve[-1]["equity"])
    return {"schema_version":"nepse-portfolio-mtm-1.1.0","daily_curve":curve,
        "initial_cash":str(_d(initial_cash)),"initial_equity":str(initial_equity),
        "opening_inventory_cost_basis":str(opening_cost),"ending_equity":str(ending),
        "net_pnl":str(ending-initial_equity),"net_return_pct":str((ending/initial_equity-1)*100),
        "max_mark_to_market_drawdown_pct":str(max_dd),"transaction_costs":str(total_cost),
        "open_positions":{s:str(q) for s,q in positions.items() if q>0},
        "rejected_executions":rejected,"performance_claimed":False,"production_enabled":False,
        "limitations":["Requires complete verified daily close marks for every open position; missing marks fail closed.",
            "Opening inventory requires point-in-time verified quantity and cost basis; sellability is checked separately by the caller.",
            "No corporate-action processing, taxes, settlement calendar, market impact or order queue model is applied here.",
            "Execution inputs must already reflect actual or separately simulated fills."]}
