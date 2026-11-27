"""Portfolio-level replay with overlapping positions and conservative capacity limits.

Consumes trade outcomes from the verified single-trade replay. Liquidity capacity
must be supplied per trade from a trusted ADV/depth policy; it is never assumed.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_FLOOR

def _d(v):
    try: x=Decimal(str(v))
    except (InvalidOperation,TypeError,ValueError): return None
    return x if x.is_finite() else None

def _day(v):
    try: return date.fromisoformat(v)
    except (TypeError,ValueError): return None

def replay_portfolio(*, trades, initial_equity=Decimal("100000"),
    risk_pct=Decimal("1"), max_position_pct=Decimal("20"),
    max_portfolio_exposure_pct=Decimal("80"), max_open_positions=5,
    max_risk_pct=Decimal("2"), round_trip_cost_pct=Decimal("0.4"),
    round_trip_slippage_pct=Decimal("0.2"), settlement_gap_stress_pct=Decimal("5")):
    """Replay candidate trades in date order; exits occur before same-day entries.

    Each trade must carry verified-replay stop/target fields and a positive
    liquidity_quantity_cap from an external, point-in-time capacity check.
    Net return already includes round-trip costs/slippage from single-trade replay.
    """
    numeric={"initial_equity":initial_equity,"risk_pct":risk_pct,
        "max_position_pct":max_position_pct,"max_portfolio_exposure_pct":max_portfolio_exposure_pct,
        "max_risk_pct":max_risk_pct,"round_trip_cost_pct":round_trip_cost_pct,
        "round_trip_slippage_pct":round_trip_slippage_pct,
        "settlement_gap_stress_pct":settlement_gap_stress_pct}
    v={k:_d(x) for k,x in numeric.items()}
    if any(x is None for x in v.values()): raise ValueError("portfolio_numeric_input_invalid")
    if v["initial_equity"]<=0 or not (0<v["risk_pct"]<=v["max_risk_pct"]<=2):
        raise ValueError("portfolio_equity_or_risk_cap_invalid")
    if not (0<v["max_position_pct"]<=100 and 0<v["max_portfolio_exposure_pct"]<=100):
        raise ValueError("portfolio_allocation_cap_invalid")
    if min(v["round_trip_cost_pct"],v["round_trip_slippage_pct"],v["settlement_gap_stress_pct"])<0 or v["settlement_gap_stress_pct"]>=100 or v["round_trip_cost_pct"]+v["round_trip_slippage_pct"]>=100:
        raise ValueError("portfolio_cost_or_stress_invalid")
    if isinstance(max_open_positions,bool) or not isinstance(max_open_positions,int) or max_open_positions<1:
        raise ValueError("max_open_positions_must_be_positive_integer")
    if not isinstance(trades,list): raise ValueError("trades_must_be_list")
    candidates=[]; rejected=[]; seen=set()
    for t in trades:
        if not isinstance(t,dict): rejected.append({"reason":"trade_record_invalid"}); continue
        sid=t.get("source_signal_id")
        if not isinstance(sid,str) or not sid.strip() or sid in seen:
            rejected.append({"source_signal_id":sid,"reason":"missing_or_duplicate_signal_id"}); continue
        seen.add(sid)
        entry_day=_day(t.get("entry_date")); exit_day=_day(t.get("exit_date"))
        entry=_d(t.get("entry_price")); stop=_d(t.get("stop_price")); exit_price=_d(t.get("exit_price"))
        net=_d(t.get("net_return_pct")); cap=t.get("liquidity_quantity_cap")
        if entry_day is None or exit_day is None or exit_day<entry_day or any(x is None or x<=0 for x in (entry,stop,exit_price)) or stop>=entry or net is None:
            rejected.append({"source_signal_id":sid,"reason":"trade_prices_dates_or_return_invalid"}); continue
        if isinstance(cap,bool) or not isinstance(cap,int) or cap<1:
            rejected.append({"source_signal_id":sid,"reason":"verified_liquidity_quantity_cap_missing"}); continue
        candidates.append({**t,"_entry_day":entry_day,"_exit_day":exit_day,
            "_entry":entry,"_stop":stop,"_exit":exit_price,"_net":net,"_cap":cap})
    candidates.sort(key=lambda t:(t["_entry_day"],-(float(_d(t.get("strategy_score")) or Decimal("-1"))),str(t.get("strategy_id","")),str(t.get("horizon","")),str(t.get("symbol","")),t["source_signal_id"]))
    cash=v["initial_equity"]; invested=Decimal("0"); peak=v["initial_equity"]; max_dd=Decimal("0")
    open_positions={}; accepted=[]; daily=[]; realized=[]
    dates=sorted({t["_entry_day"] for t in candidates}|{t["_exit_day"] for t in candidates})
    by_entry={}
    for t in candidates: by_entry.setdefault(t["_entry_day"],[]).append(t)
    for day in dates:
        # Settle positions before allocating new entries on the same session.
        for sid,pos in list(open_positions.items()):
            if pos["trade"]["_exit_day"]!=day: continue
            proceeds=pos["notional"]*(Decimal("1")+pos["trade"]["_net"]/100)
            cash+=proceeds; invested-=pos["notional"]
            pnl=proceeds-pos["notional"]
            realized.append({"source_signal_id":sid,"symbol":pos["trade"].get("symbol"),"sector":pos["trade"].get("sector"),
                "exit_date":day.isoformat(),"quantity":pos["quantity"],
                "allocated_notional":str(pos["notional"]),"net_pnl":str(pnl),
                "net_return_pct":str(pos["trade"]["_net"])})
            del open_positions[sid]
        for t in by_entry.get(day,[]):
            sid=t["source_signal_id"]
            if len(open_positions)>=max_open_positions:
                rejected.append({"source_signal_id":sid,"reason":"max_open_positions_reached"}); continue
            equity=cash+invested
            exposure_cap=equity*v["max_portfolio_exposure_pct"]/100
            remaining_exposure=max(Decimal("0"),exposure_cap-invested)
            allocation_cap=equity*v["max_position_pct"]/100
            half=(v["round_trip_cost_pct"]+v["round_trip_slippage_pct"])/200
            stressed_stop=t["_stop"]*(1-v["settlement_gap_stress_pct"]/100)
            risk_per_share=t["_entry"]*(1+half)-stressed_stop*(1-half)
            if risk_per_share<=0:
                rejected.append({"source_signal_id":sid,"reason":"non_positive_stressed_risk_per_share"}); continue
            risk_qty=(equity*v["risk_pct"]/100/risk_per_share).to_integral_value(rounding=ROUND_FLOOR)
            cash_qty=(cash/t["_entry"]).to_integral_value(rounding=ROUND_FLOOR)
            allocation_qty=(allocation_cap/t["_entry"]).to_integral_value(rounding=ROUND_FLOOR)
            portfolio_qty=(remaining_exposure/t["_entry"]).to_integral_value(rounding=ROUND_FLOOR)
            qty=max(Decimal("0"),min(risk_qty,cash_qty,allocation_qty,portfolio_qty,Decimal(t["_cap"])))
            if qty<1:
                rejected.append({"source_signal_id":sid,"reason":"portfolio_capacity_or_risk_limit_zero",
                    "quantity_caps":{"risk":int(risk_qty),"cash":int(cash_qty),"allocation":int(allocation_qty),
                    "portfolio_exposure":int(portfolio_qty),"liquidity":t["_cap"]}}); continue
            notional=qty*t["_entry"]
            cash-=notional; invested+=notional
            open_positions[sid]={"trade":t,"quantity":int(qty),"notional":notional}
            accepted.append({"source_signal_id":sid,"symbol":t.get("symbol"),
                "strategy_id":t.get("strategy_id"),"horizon":t.get("horizon"),"sector":t.get("sector"),
                "entry_date":day.isoformat(),"scheduled_exit_date":t["exit_date"],"quantity":int(qty),"allocated_notional":str(notional),
                "risk_budget":str(equity*v["risk_pct"]/100),
                "limiting_cap":"risk" if qty==risk_qty else "cash/allocation/exposure/liquidity",
                "liquidity_quantity_cap":t["_cap"]})
        equity=cash+invested; peak=max(peak,equity)
        max_dd=max(max_dd,(peak-equity)/peak if peak else Decimal("0"))
        daily.append({"date":day.isoformat(),"cash":str(cash),"invested_at_cost":str(invested),
            "equity_at_cost_for_open_positions":str(equity),"open_positions":len(open_positions)})
    total_pnl=sum((_d(x["net_pnl"]) for x in realized),Decimal("0"))
    wins=[_d(x["net_pnl"]) for x in realized if _d(x["net_pnl"])>0]
    losses=[_d(x["net_pnl"]) for x in realized if _d(x["net_pnl"])<0]
    return {"schema_version":"nepse-portfolio-replay-1.0.0",
        "status":"completed_with_open_positions" if open_positions else "completed",
        "initial_equity":str(v["initial_equity"]),"ending_cash":str(cash),
        "ending_invested_at_cost":str(invested),"ending_equity_at_cost":str(cash+invested),
        "net_pnl":str(total_pnl),"net_return_pct":str(total_pnl/v["initial_equity"]*100),
        "max_realized_equity_drawdown_pct":str(max_dd*100),
        "closed_trade_count":len(realized),"accepted_position_count":len(accepted),
        "rejected_trade_count":len(rejected),"open_position_count":len(open_positions),
        "win_rate_pct":str(Decimal(len(wins))/len(realized)*100) if realized else None,
        "profit_factor":str(sum(wins,Decimal("0"))/abs(sum(losses,Decimal("0")))) if losses else ("infinity" if wins else None),
        "accepted_positions":accepted,"closed_positions":realized,"rejected_trades":rejected,
        "open_positions":[{"source_signal_id":sid,"symbol":p["trade"].get("symbol"),"quantity":p["quantity"],
            "entry_date":p["trade"]["entry_date"],"scheduled_exit_date":p["trade"]["exit_date"]}
            for sid,p in open_positions.items()],"daily_equity":daily,
        "assumptions":{"exit_before_entry_on_same_session":True,"cash_only_no_leverage":True,
            "risk_pct":str(v["risk_pct"]),"max_position_pct":str(v["max_position_pct"]),
            "max_portfolio_exposure_pct":str(v["max_portfolio_exposure_pct"]),
            "max_open_positions":max_open_positions,"gap_stress_pct":str(v["settlement_gap_stress_pct"]),
            "round_trip_cost_pct":str(v["round_trip_cost_pct"]),"round_trip_slippage_pct":str(v["round_trip_slippage_pct"]),
            "liquidity_capacity":"mandatory per-trade integer cap supplied from trusted external ADV/depth evidence",
            "open_position_valuation":"held at entry cost; drawdown excludes unrealized mark-to-market losses"},
        "limitations":["Portfolio replay is a deterministic research simulator, not exchange execution.",
            "It assumes trade exit prices/returns from the single-trade replay and does not model partial fills, circuits, queue priority or market impact.",
            "Liquidity quantity caps must be independently validated and point-in-time; this module does not calculate ADV.",
            "Open positions are valued at cost, so reported drawdown is realized-only and understates possible intraperiod risk.",
            "No corporate-action adjustment is performed here; upstream panel must already be reconciled."],
        "performance_claimed":False,"production_enabled":False}
