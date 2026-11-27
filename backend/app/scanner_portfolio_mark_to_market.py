"""Daily mark-to-market portfolio curve from verified execution fills and closes."""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation

def _d(value):
    try: result=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): return None
    return result if result.is_finite() else None

def _day(value):
    try: return date.fromisoformat(value)
    except (TypeError,ValueError): return None

def _verified(item):
    if not isinstance(item,dict) or item.get("evidence_status")!="verified": return False
    return all(isinstance(item.get(k),str) and item[k].strip() for k in ("source_id","evidence_id"))

def build_mark_to_market_curve(*, initial_cash, executions, daily_marks, transaction_cost_bps="0"):
    cash=_d(initial_cash); cost=_d(transaction_cost_bps)
    if cash is None or cash<=0 or cost is None or cost<0 or cost>=10000:
        raise ValueError("initial_cash_or_transaction_cost_invalid")
    if not isinstance(executions,list) or not isinstance(daily_marks,list):
        raise ValueError("executions_and_marks_must_be_lists")
    fills=[]; rejected=[]; seen=set()
    for i,item in enumerate(executions):
        if not isinstance(item,dict) or not _verified(item):
            rejected.append({"index":i,"reason":"execution_provenance_invalid"}); continue
        day=_day(item.get("execution_date")); side=item.get("side"); qty=item.get("quantity"); price=_d(item.get("price"))
        key=item.get("execution_id")
        if day is None or side not in {"buy","sell"} or isinstance(qty,bool) or not isinstance(qty,int) or qty<1 or price is None or price<=0 or not isinstance(key,str) or not key.strip() or key in seen:
            rejected.append({"index":i,"reason":"execution_fields_invalid_or_duplicate"}); continue
        seen.add(key); fills.append({**item,"_day":day,"_price":price,"_notional":price*qty})
    marks={}; mark_days=set()
    for i,item in enumerate(daily_marks):
        if not isinstance(item,dict) or not _verified(item): raise ValueError("daily_mark_provenance_invalid")
        day=_day(item.get("session_date")); symbol=item.get("symbol"); price=_d(item.get("close"))
        if day is None or not isinstance(symbol,str) or not symbol.strip() or price is None or price<=0:
            raise ValueError("daily_mark_fields_invalid")
        key=(day,symbol)
        if key in marks: raise ValueError("duplicate_symbol_session_mark")
        marks[key]=price; mark_days.add(day)
    if not mark_days: raise ValueError("daily_marks_required")
    fills.sort(key=lambda x:(x["_day"],x.get("sequence",0),x["execution_id"]))
    dates=sorted(mark_days); positions={}; fill_index=0; peak=cash; max_dd=Decimal("0"); curve=[]
    total_cost=Decimal("0")
    for day in dates:
        while fill_index<len(fills) and fills[fill_index]["_day"]<=day:
            item=fills[fill_index]; fill_index+=1
            symbol=item.get("symbol")
            if not isinstance(symbol,str) or not symbol.strip(): raise ValueError("execution_symbol_required")
            qty=Decimal(item["quantity"]); notional=item["_notional"]; fee=notional*cost/Decimal("10000")
            total_cost+=fee
            current=positions.get(symbol,Decimal("0"))
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
        if missing: 
            # Missing marks are not carried forward or silently valued at cost.
            raise ValueError("missing_point_in_time_marks:"+",".join(sorted(missing)))
        equity=cash+market_value; peak=max(peak,equity)
        drawdown=(peak-equity)/peak*100 if peak else Decimal("0")
        max_dd=max(max_dd,drawdown)
        curve.append({"session_date":day.isoformat(),"cash":str(cash),
            "market_value":str(market_value),"equity":str(equity),
            "drawdown_pct":str(drawdown),"open_symbols":sorted(s for s,q in positions.items() if q>0)})
    ending=Decimal(curve[-1]["equity"])
    return {"schema_version":"nepse-portfolio-mtm-1.0.0","daily_curve":curve,
        "initial_cash":str(_d(initial_cash)),"ending_equity":str(ending),
        "net_pnl":str(ending-_d(initial_cash)),"net_return_pct":str((ending/_d(initial_cash)-1)*100),
        "max_mark_to_market_drawdown_pct":str(max_dd),"transaction_costs":str(total_cost),
        "open_positions":{s:str(q) for s,q in positions.items() if q>0},
        "rejected_executions":rejected,"performance_claimed":False,"production_enabled":False,
        "limitations":["Requires complete verified daily close marks for every open position; missing marks fail closed.",
            "No corporate-action processing, taxes, settlement eligibility, market impact or order queue model is applied here.",
            "Execution inputs must already reflect actual or separately simulated fills."]}
