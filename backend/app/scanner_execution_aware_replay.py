"""Execution-aware research replay joining queue fills to daily MTM valuation.

Runs are isolated by strategy/horizon/partition. Every simulated execution is
derived from verified queue events; sell orders require independently evidenced
sellable inventory. Missing marks, duplicate IDs and cash/inventory violations
fail closed. This is not a live router or proof of exchange execution.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from zoneinfo import ZoneInfo
from app.scanner_order_queue import replay_passive_order_queue
from app.scanner_portfolio_mark_to_market import build_mark_to_market_curve

NEPAL=ZoneInfo("Asia/Kathmandu")
STRATEGIES={"trend_momentum","idpat_smart_money","broker_footprint","smc_ict_liquidity","hybrid_consensus","fundamental_investment"}
HORIZONS={"t_plus_2","swing","positional","investment"}
PARTITIONS={"train","validation","out_of_sample"}

def _time(value):
    if not isinstance(value,str): return None
    try: parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _verified(item, cutoff):
    if not isinstance(item,dict) or item.get("evidence_status")!="verified": return False
    if not all(isinstance(item.get(k),str) and item[k].strip() for k in ("source_id","evidence_id")): return False
    available=_time(item.get("available_at"))
    return available is not None and available<=cutoff

def _stable_id(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def run_execution_aware_replay(*, order_batches, daily_marks_by_run,
    initial_cash="100000", transaction_cost_bps="0", initial_positions_by_run=None):
    """Replay orders then value fills; opening holdings must be explicitly evidenced."""
    if not isinstance(order_batches,list) or not isinstance(daily_marks_by_run,dict):
        raise ValueError("order_batches_and_daily_marks_required")
    if initial_positions_by_run is None: initial_positions_by_run={}
    if not isinstance(initial_positions_by_run,dict): raise ValueError("initial_positions_by_run_must_be_dict")
    grouped={}; rejected=[]
    for index,batch in enumerate(order_batches):
        if not isinstance(batch,dict):
            rejected.append({"index":index,"reason":"batch_not_object"}); continue
        strategy=batch.get("strategy_id"); horizon=batch.get("horizon"); partition=batch.get("partition")
        if strategy not in STRATEGIES or horizon not in HORIZONS or partition not in PARTITIONS:
            rejected.append({"index":index,"reason":"strategy_horizon_or_partition_invalid"}); continue
        order=batch.get("order"); submitted=_time(order.get("submitted_at")) if isinstance(order,dict) else None
        symbol=batch.get("symbol")
        if submitted is None or not isinstance(symbol,str) or not symbol.strip():
            rejected.append({"index":index,"reason":"order_timestamp_or_symbol_invalid"}); continue
        if order.get("side")=="sell":
            inventory=batch.get("sellable_inventory")
            requested=order.get("quantity")
            if not _verified(inventory,submitted):
                rejected.append({"index":index,"reason":"verified_sellable_inventory_required"}); continue
            available=inventory.get("quantity")
            if isinstance(requested,bool) or not isinstance(requested,int) or requested<1:
                rejected.append({"index":index,"reason":"sell_order_quantity_invalid"}); continue
            if isinstance(available,bool) or not isinstance(available,int) or available<requested:
                rejected.append({"index":index,"reason":"sell_quantity_exceeds_verified_sellable_inventory"}); continue
            sellable_at=_time(inventory.get("sellable_at"))
            if sellable_at is None or sellable_at>submitted:
                rejected.append({"index":index,"reason":"inventory_not_yet_sellable_at_order_time"}); continue
        try:
            queue=replay_passive_order_queue(order=order,
                initial_queue_ahead=batch.get("initial_queue_ahead"),events=batch.get("events",[]))
        except (ValueError,TypeError) as exc:
            rejected.append({"index":index,"reason":"queue_replay_rejected:"+str(exc)}); continue
        key="|".join((strategy,horizon,partition))
        group=grouped.setdefault(key,{"strategy_id":strategy,"horizon":horizon,
            "partition":partition,"queues":[],"executions":[]})
        queue_id=batch.get("order_id") or _stable_id({"key":key,"order":order,"index":index})
        group["queues"].append({"order_id":queue_id,"symbol":symbol,"result":queue})
        for fill in queue["fills"]:
            event=batch["events"][fill["event_index"]]
            event_at=_time(fill["event_at"])
            if event_at is None or not _verified(event,event_at):
                rejected.append({"index":index,"reason":"fill_event_evidence_invalid"}); continue
            group["executions"].append({
                "execution_id":_stable_id({"order_id":queue_id,"event":event.get("evidence_id"),
                    "event_index":fill["event_index"],"quantity":fill["quantity"]}),
                "symbol":symbol,"execution_date":event_at.astimezone(NEPAL).date().isoformat(),
                "execution_at":event_at.isoformat(),"sequence":event["sequence"],
                "side":queue["side"],"quantity":fill["quantity"],"price":fill["price"],
                "evidence_status":"verified","source_id":event["source_id"],
                "evidence_id":event["evidence_id"],"available_at":event["available_at"]})
    reports=[]
    for key,group in sorted(grouped.items()):
        marks=daily_marks_by_run.get(key)
        if not isinstance(marks,list) or not marks:
            reports.append({**group,"status":"blocked","reason":"daily_point_in_time_marks_missing"})
            continue
        try:
            mtm=build_mark_to_market_curve(initial_cash=initial_cash,
                executions=group["executions"],daily_marks=marks,
                transaction_cost_bps=transaction_cost_bps,
                initial_positions=initial_positions_by_run.get(key,[]))
            reports.append({**group,"status":"valued","mark_to_market":mtm})
        except (ValueError,TypeError) as exc:
            reports.append({**group,"status":"blocked","reason":"mark_to_market_rejected:"+str(exc)})
    return {"schema_version":"nepse-execution-aware-replay-1.1.0",
        "run_count":len(reports),"runs":reports,"rejected_orders":rejected,
        "strategy_count":len(STRATEGIES),"horizon_count":len(HORIZONS),
        "partition_policy":"strategy/horizon/partition portfolios are isolated; compare untouched out_of_sample only",
        "settlement_policy":"sell orders require verified, already-sellable inventory; opening inventory must also be supplied with verified cost basis",
        "production_enabled":False,"performance_claimed":False,
        "limitations":["Order queue fills are simulations from supplied verified event data, not exchange-confirmed fills.",
            "Sellable inventory must be externally reconciled to settlement and prior fills; the wrapper does not infer T+2 eligibility.",
            "Portfolio cash and opening inventory are isolated per strategy/horizon/partition; this is not a shared-capital combined portfolio.",
            "Partial fills are valued as individual executions; no circuit-lock, hidden liquidity, market impact, taxes or corporate-action processing is modeled.",
            "Every open position needs a verified daily mark for every session; missing marks block valuation."]}
