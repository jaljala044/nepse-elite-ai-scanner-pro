"""Conservative event-driven passive order queue replay.

Requires point-in-time verified order-book events with explicit ahead/behind
attribution. Unknown cancellation attribution never improves queue position.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

def _d(value):
    try: result=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError): return None
    return result if result.is_finite() else None

def _time(value):
    if not isinstance(value,str): return None
    try: result=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError: return None
    if result.tzinfo is None or result.utcoffset() is None: return None
    return result.astimezone(timezone.utc)

def _verified(item, cutoff):
    if not isinstance(item,dict) or item.get("evidence_status")!="verified": return False
    if not all(isinstance(item.get(k),str) and item[k].strip() for k in ("source_id","evidence_id")): return False
    available=_time(item.get("available_at"))
    return available is not None and available<=cutoff

def replay_passive_order_queue(*, order, initial_queue_ahead, events):
    if not isinstance(order,dict) or not isinstance(events,list): raise ValueError("order_and_event_list_required")
    side=order.get("side")
    if side not in {"buy","sell"}: raise ValueError("side_invalid")
    qty=order.get("quantity")
    if isinstance(qty,bool) or not isinstance(qty,int) or qty<1: raise ValueError("positive_integer_quantity_required")
    submitted=_time(order.get("submitted_at")); limit=_d(order.get("limit_price"))
    ahead=_d(initial_queue_ahead.get("quantity") if isinstance(initial_queue_ahead,dict) else None)
    better_ahead=_d(initial_queue_ahead.get("better_price_quantity","0") if isinstance(initial_queue_ahead,dict) else None)
    if submitted is None or limit is None or limit<=0 or ahead is None or ahead<0 or better_ahead is None or better_ahead<0:
        raise ValueError("order_or_initial_queue_invalid")
    if not _verified(order,submitted) or not _verified(initial_queue_ahead,submitted):
        raise ValueError("verified_order_and_initial_queue_required")
    remaining=qty; fills=[]; audit=[]; seen=set(); previous=(submitted,-1); queue_valid=True
    aggressor="SELL" if side=="buy" else "BUY"
    for index,event in enumerate(events):
        if not isinstance(event,dict): raise ValueError("event_record_invalid")
        ts=_time(event.get("event_at")); seq=event.get("sequence")
        if ts is None or isinstance(seq,bool) or not isinstance(seq,int) or seq<0:
            raise ValueError("event_timestamp_and_sequence_required")
        if ts<submitted: continue
        if (ts,seq)<=previous or (ts,seq) in seen: raise ValueError("events_must_be_strictly_ordered")
        previous=(ts,seq); seen.add((ts,seq))
        if not _verified(event,ts):
            audit.append({"index":index,"status":"withheld","reason":"event_provenance_invalid"}); continue
        kind=event.get("event_type")
        if kind=="BOOK_RESET":
            queue_valid=False
            audit.append({"index":index,"status":"queue_invalidated","reason":"book_reset_requires_new_queue_snapshot"})
            continue
        if not queue_valid:
            audit.append({"index":index,"status":"withheld","reason":"queue_position_unknown_after_reset"}); continue
        if kind=="CANCEL":
            cancelled=_d(event.get("quantity")); attribution=event.get("queue_attribution")
            cancel_price=_d(event.get("price",limit))
            if cancelled is None or cancelled<0 or cancel_price is None: raise ValueError("cancel_quantity_invalid")
            if attribution=="AHEAD":
                if (side=="buy" and cancel_price>limit) or (side=="sell" and cancel_price<limit):
                    better_ahead=max(Decimal("0"),better_ahead-cancelled)
                elif cancel_price==limit:
                    ahead=max(Decimal("0"),ahead-cancelled)
                audit.append({"index":index,"status":"ahead_reduced",
                    "queue_ahead":str(ahead),"better_price_ahead":str(better_ahead)})
            elif attribution=="BEHIND":
                audit.append({"index":index,"status":"no_queue_change"})
            else:
                audit.append({"index":index,"status":"ignored","reason":"cancellation_priority_unknown"})
            continue
        if kind=="ADD":
            added=_d(event.get("quantity")); added_price=_d(event.get("price")); order_side=event.get("order_side")
            if added is None or added<=0 or added_price is None or added_price<=0 or order_side not in {"buy","sell"}:
                raise ValueError("add_order_fields_invalid")
            if order_side!=side:
                audit.append({"index":index,"status":"other_side_no_queue_change"})
            elif (side=="buy" and added_price>limit) or (side=="sell" and added_price<limit):
                better_ahead+=added
                audit.append({"index":index,"status":"better_price_ahead_added","better_price_ahead":str(better_ahead)})
            else:
                audit.append({"index":index,"status":"behind_or_worse_price"})
            continue
        if kind!="TRADE": raise ValueError("unsupported_event_type")
        price=_d(event.get("price")); traded=_d(event.get("quantity"))
        if price is None or traded is None or price<=0 or traded<=0:
            raise ValueError("trade_price_or_quantity_invalid")
        if event.get("aggressor_side")!=aggressor:
            audit.append({"index":index,"status":"aggressor_side_not_executable"}); continue
        is_better_trade=(side=="buy" and price>limit) or (side=="sell" and price<limit)
        if is_better_trade:
            consumed=min(better_ahead,traded); better_ahead-=consumed
            audit.append({"index":index,"status":"better_price_queue_consumed",
                "better_price_ahead":str(better_ahead),"consumed":str(consumed)})
            continue
        if price!=limit:
            audit.append({"index":index,"status":"not_executable_at_our_price"}); continue
        if better_ahead>0:
            audit.append({"index":index,"status":"blocked_by_better_price_queue",
                "better_price_ahead":str(better_ahead)}); continue
        consumed=min(ahead,traded); ahead-=consumed; residual=traded-consumed
        filled=min(Decimal(remaining),residual)
        if filled>0:
            whole=int(filled)
            fills.append({"event_index":index,"event_at":ts.isoformat(),
                "quantity":whole,"price":str(limit),"queue_ahead_consumed":str(consumed)})
            remaining-=whole
        audit.append({"index":index,"status":"trade_applied","queue_ahead":str(ahead),
            "our_fill_quantity":int(filled)})
        if remaining==0: break
    return {"schema_version":"nepse-order-queue-replay-1.0.0",
        "status":"filled" if remaining==0 else ("partially_filled" if remaining<qty else "unfilled"),
        "side":side,"requested_quantity":qty,"filled_quantity":qty-remaining,
        "remaining_quantity":remaining,"queue_ahead_remaining":str(ahead),"better_price_ahead_remaining":str(better_ahead),
        "queue_position_valid":queue_valid,"fills":fills,"audit":audit,
        "assumptions":{"price_time_priority":True,"unknown_cancellations_reduce_queue":False,
            "new_same_price_orders_are_behind":True,"better_price_orders_take_priority":True,"fills_require_verified_aggressor_trade_at_limit":True},
        "limitations":["Queue ahead is only as reliable as the supplied initial snapshot and event attribution.",
            "Hidden orders, iceberg refresh, auction matching, cross-price routing and exchange-specific priority rules are not modeled.",
            "A book reset invalidates queue position until a fresh snapshot is supplied; no optimistic reinitialization occurs.",
            "This is a research replay, not a live order router."],
        "production_enabled":False,"performance_claimed":False}
