"""Shared-capital OOS portfolio gate across strategy/horizon execution replays."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from app.scanner_portfolio_mark_to_market import build_mark_to_market_curve

STRATEGIES={"trend_momentum","idpat_smart_money","broker_footprint","smc_ict_liquidity","hybrid_consensus","fundamental_investment"}
HORIZONS={"t_plus_2","swing","positional","investment"}

def _d(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def _time(v):
    if not isinstance(v,str): return None
    try: x=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError: return None
    if x.tzinfo is None or x.utcoffset() is None: return None
    return x.astimezone(timezone.utc)

def _verified(row,cutoff):
    if not isinstance(row,dict) or row.get("evidence_status")!="verified": return False
    if not all(isinstance(row.get(k),str) and row[k].strip() for k in ("source_id","evidence_id")): return False
    available=_time(row.get("available_at"))
    return available is not None and available<=cutoff

def run_unified_portfolio_risk(*, execution_runs, daily_marks, market_controls,
    initial_cash="100000", transaction_cost_bps="0",
    max_gross_exposure_pct="80", max_symbol_exposure_pct="25",
    max_sector_exposure_pct="40", max_open_symbols=10,
    initial_positions=None, require_out_of_sample=True):
    """Pool verified fills under one cash ledger and point-in-time market-risk limits.

    market_controls: one verified per-symbol/session record with lower/upper circuit
    prices. Sell fills must carry the source order's verified sellable_inventory.
    """
    if not isinstance(execution_runs,list) or not isinstance(daily_marks,list) or not isinstance(market_controls,list):
        raise ValueError("execution_runs_daily_marks_and_market_controls_required")
    if initial_positions is None: initial_positions=[]
    if not isinstance(initial_positions,list): raise ValueError("initial_positions_must_be_list")
    cash=_d(initial_cash); cost=_d(transaction_cost_bps)
    gross_cap=_d(max_gross_exposure_pct); symbol_cap=_d(max_symbol_exposure_pct); sector_cap=_d(max_sector_exposure_pct)
    if cash is None or cash<=0 or cost is None or cost<0 or cost>=10000:
        raise ValueError("cash_or_cost_invalid")
    if any(x is None or x<=0 or x>100 for x in (gross_cap,symbol_cap,sector_cap)):
        raise ValueError("exposure_limit_invalid")
    if isinstance(max_open_symbols,bool) or not isinstance(max_open_symbols,int) or max_open_symbols<1:
        raise ValueError("max_open_symbols_invalid")
    marks={}; mark_days=set()
    for mark in daily_marks:
        if not isinstance(mark,dict): raise ValueError("daily_mark_invalid")
        day=mark.get("session_date"); symbol=mark.get("symbol"); price=_d(mark.get("close")); cutoff=_time(mark.get("decision_cutoff"))
        if not isinstance(day,str) or not isinstance(symbol,str) or not symbol.strip() or price is None or price<=0 or cutoff is None or not _verified(mark,cutoff):
            raise ValueError("daily_mark_provenance_or_values_invalid")
        key=(day,symbol)
        if key in marks: raise ValueError("duplicate_daily_mark")
        marks[key]=price; mark_days.add(day)
    controls={}
    for control in market_controls:
        if not isinstance(control,dict): raise ValueError("market_control_invalid")
        day=control.get("session_date"); symbol=control.get("symbol")
        low=_d(control.get("lower_circuit_price")); high=_d(control.get("upper_circuit_price"))
        cutoff=_time(control.get("available_at"))
        if (not isinstance(day,str) or not isinstance(symbol,str) or not symbol.strip()
            or low is None or high is None or low<=0 or high<low or cutoff is None
            or not _verified(control,cutoff)):
            raise ValueError("market_control_provenance_or_band_invalid")
        key=(day,symbol)
        if key in controls: raise ValueError("duplicate_market_control")
        controls[key]=(low,high,cutoff)
    positions={}; opening=[]; seen_open=set()
    for p in initial_positions:
        if not isinstance(p,dict): raise ValueError("initial_position_invalid")
        symbol=p.get("symbol"); qty=p.get("quantity"); basis=_d(p.get("cost_basis"))
        if not isinstance(symbol,str) or not symbol.strip() or isinstance(qty,bool) or not isinstance(qty,int) or qty<1 or basis is None or basis<=0 or symbol in seen_open:
            raise ValueError("initial_position_fields_invalid")
        positions[symbol]={"quantity":qty,"sector":p.get("sector"),"cost_basis":basis}
        seen_open.add(symbol); opening.append(p)
    candidates=[]; rejected=[]; seen_execution=set(); partitions=set()
    for run_index,run in enumerate(execution_runs):
        if not isinstance(run,dict): rejected.append({"run_index":run_index,"reason":"run_not_object"}); continue
        strategy=run.get("strategy_id"); horizon=run.get("horizon"); partition=run.get("partition")
        if strategy not in STRATEGIES or horizon not in HORIZONS or partition not in {"train","validation","out_of_sample"}:
            rejected.append({"run_index":run_index,"reason":"strategy_horizon_partition_invalid"}); continue
        if require_out_of_sample and partition!="out_of_sample":
            rejected.append({"run_index":run_index,"reason":"non_oos_run_excluded"}); continue
        if run.get("status")!="valued":
            rejected.append({"run_index":run_index,"reason":"execution_run_not_valued"}); continue
        partitions.add(partition)
        for execution in run.get("executions",[]):
            if not isinstance(execution,dict): rejected.append({"run_index":run_index,"reason":"execution_invalid"}); continue
            item={**execution,"strategy_id":strategy,"horizon":horizon,"partition":partition}
            item["sector"]=execution.get("sector") or run.get("sector")
            item["source_signal_id"]=execution.get("source_signal_id") or run.get("source_signal_id")
            item["sellable_inventory"]=execution.get("sellable_inventory")
            eid=item.get("execution_id")
            if not isinstance(eid,str) or not eid.strip() or eid in seen_execution:
                rejected.append({"execution_id":eid,"reason":"missing_or_duplicate_execution_id"}); continue
            seen_execution.add(eid)
            candidates.append(item)
    candidates.sort(key=lambda x:(_time(x.get("execution_at")) or datetime.max.replace(tzinfo=timezone.utc),
                                  x.get("sequence",0),x["execution_id"]))
    accepted=[]; total_cost=Decimal("0"); realized_notional=Decimal("0")
    for item in candidates:
        symbol=item.get("symbol"); sector=item.get("sector")
        ts=_time(item.get("execution_at")); day=item.get("execution_date")
        side=item.get("side"); qty=item.get("quantity"); price=_d(item.get("price"))
        if (not isinstance(symbol,str) or not symbol.strip() or not isinstance(sector,str) or not sector.strip()
            or ts is None or not isinstance(day,str) or ts.date().isoformat()!=day
            or side not in {"buy","sell"} or isinstance(qty,bool) or not isinstance(qty,int) or qty<1
            or price is None or price<=0 or not _verified(item,ts)):
            rejected.append({"execution_id":item.get("execution_id"),"reason":"execution_fields_or_provenance_invalid"}); continue
        control=controls.get((day,symbol))
        if control is None or control[2]>ts:
            rejected.append({"execution_id":item["execution_id"],"reason":"point_in_time_circuit_control_missing"}); continue
        low,high,_=control
        if price<low or price>high:
            rejected.append({"execution_id":item["execution_id"],"reason":"execution_outside_circuit_band"}); continue
        notional=price*qty; fee=notional*cost/Decimal("10000")
        current=positions.get(symbol,{"quantity":0,"sector":sector,"cost_basis":Decimal("0")})
        if current["sector"] not in (None,sector):
            rejected.append({"execution_id":item["execution_id"],"reason":"symbol_sector_identity_conflict"}); continue
        if side=="sell":
            inventory=item.get("sellable_inventory")
            if not _verified(inventory,ts) or inventory.get("symbol")!=symbol:
                rejected.append({"execution_id":item["execution_id"],"reason":"verified_symbol_sellable_inventory_required"}); continue
            sellable=inventory.get("quantity"); sellable_at=_time(inventory.get("sellable_at"))
            if isinstance(sellable,bool) or not isinstance(sellable,int) or sellable<qty or sellable_at is None or sellable_at>ts:
                rejected.append({"execution_id":item["execution_id"],"reason":"settlement_or_sellable_quantity_failed"}); continue
            if current["quantity"]<qty:
                rejected.append({"execution_id":item["execution_id"],"reason":"sell_exceeds_shared_portfolio_inventory"}); continue
            cash+=notional-fee; current["quantity"]-=qty
            if current["quantity"]==0: positions.pop(symbol,None)
            else: positions[symbol]=current
        else:
            if cash<notional+fee:
                rejected.append({"execution_id":item["execution_id"],"reason":"shared_cash_insufficient"}); continue
            known_values={}
            for held,position in positions.items():
                if held==symbol: mark_price=price
                else:
                    eligible=[(d,p) for (d,s),p in marks.items() if s==held and _time(next(m["decision_cutoff"] for m in daily_marks if m["symbol"]==s and m["session_date"]==d))<=ts]
                    mark_price=max(eligible,key=lambda z:z[0])[1] if eligible else None
                if mark_price is None:
                    known_values=None; break
                known_values[held]=Decimal(position["quantity"])*mark_price
            if known_values is None:
                rejected.append({"execution_id":item["execution_id"],"reason":"held_position_mark_unavailable_at_execution"}); continue
            equity=cash+sum(known_values.values(),Decimal("0"))
            new_value=known_values.get(symbol,Decimal("0"))+notional
            gross=sum(known_values.values(),Decimal("0"))+notional
            if symbol not in positions and len(positions)>=max_open_symbols:
                rejected.append({"execution_id":item["execution_id"],"reason":"max_open_symbols_exceeded"}); continue
            if equity<=0 or gross/equity*100>gross_cap:
                rejected.append({"execution_id":item["execution_id"],"reason":"gross_exposure_limit_exceeded"}); continue
            if new_value/equity*100>symbol_cap:
                rejected.append({"execution_id":item["execution_id"],"reason":"symbol_exposure_limit_exceeded"}); continue
            sector_value=sum((value for held,value in known_values.items() if positions[held]["sector"]==sector),Decimal("0"))+notional
            if sector_value/equity*100>sector_cap:
                rejected.append({"execution_id":item["execution_id"],"reason":"sector_exposure_limit_exceeded"}); continue
            cash-=notional+fee
            current["quantity"]+=qty; current["sector"]=sector
            positions[symbol]=current
        total_cost+=fee; realized_notional+=notional; accepted.append(item)
    try:
        mtm=build_mark_to_market_curve(initial_cash=str(_d(initial_cash)),
            executions=accepted,daily_marks=daily_marks,
            transaction_cost_bps=transaction_cost_bps,initial_positions=opening)
    except (ValueError,TypeError) as exc:
        mtm={"status":"BLOCKED","reason":str(exc)}
    return {"schema_version":"nepse-unified-portfolio-risk-1.0.0",
        "status":"VALUED" if "daily_curve" in mtm else "BLOCKED",
        "partition_policy":"only out_of_sample strategy/horizon runs are pooled by default",
        "strategy_horizon_partitions":sorted(partitions),"accepted_execution_count":len(accepted),
        "rejected_execution_count":len(rejected),"accepted_executions":accepted,
        "rejected_executions":rejected,"shared_cash_after_screen":str(cash),
        "shared_open_positions_after_screen":{s:{"quantity":p["quantity"],"sector":p["sector"]} for s,p in positions.items()},
        "transaction_costs_screened":str(total_cost),"screened_notional":str(realized_notional),
        "mark_to_market":mtm,"production_enabled":False,"performance_claimed":False,
        "limitations":["Circuit-band controls must be supplied per symbol/session and available before each execution; missing controls reject fills.",
            "Sellable inventory must be externally reconciled to prior fills and settlement; this module does not infer T+2 dates.",
            "Shared-capital allocation is a conservative research screen, not an exchange matching engine or live router.",
            "No price impact, hidden liquidity, taxes, corporate-action processing or dynamic portfolio re-optimization is modeled.",
            "All strategy/horizon candidates compete for the same capital; run selection order is chronological, then exchange sequence and execution ID."]}
