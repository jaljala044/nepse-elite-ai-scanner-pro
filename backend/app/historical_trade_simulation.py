"""Long-only, non-overlapping hypothetical replay. No executable fill claims."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from math import isfinite
from .scanner_eligibility import assess
from .execution_constraints import settlement_date, price_band, exit_scenario
from .execution_costs import round_trip, _number
from .dated_execution_costs import dated_round_trip
from .historical_fee_reference import brokerage_cap
from .strategy_research import HORIZONS
from .performance_statistics import summarize

def simulate(symbol, rows, observations, *, reviewed, sessions, settlement_days,
             session_controls, costs, horizon, holding_sessions, quantity,
             initial_capital, max_participation, stop_fraction, target_fraction,
             cost_mode="flat_scenario", retry_sessions=0):
    base={"classification":"hypothetical_research_only","production_approved":False,
          "action":"NO TRADE","trades":[],"excluded":[],"statistics":None}
    if cost_mode not in ("flat_scenario","dated_reference"):
        raise ValueError("invalid cost mode")
    base["cost_mode"]=cost_mode
    if type(retry_sessions) is not int or not 0<=retry_sessions<=20:
        raise ValueError("invalid retry window")
    if horizon not in HORIZONS or type(holding_sessions) is not int or not HORIZONS[horizon][0]<=holding_sessions<=HORIZONS[horizon][1]:
        raise ValueError("invalid horizon")
    if type(quantity) is not int or quantity<=0:
        raise ValueError("invalid quantity")
    for value in (initial_capital,max_participation,stop_fraction,target_fraction):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<=0:
            raise ValueError("invalid scenario parameters")
    if max_participation>1 or stop_fraction>=1:
        raise ValueError("invalid participation or stop")
    if costs is None or sessions is None or settlement_days is None or session_controls is None:
        return dict(base,status="missing_execution_evidence")
    days=[date.fromisoformat(str(d)) for d in sessions]
    if days!=sorted(set(days)):
        raise ValueError("invalid session order")
    indexed={}
    for r in rows:
        day=date.fromisoformat(str(r["date"]))
        if day in indexed or day not in days:
            raise ValueError("duplicate or non-calendar bar")
        indexed[day]=r
    capital=initial_capital
    busy_until=date.min
    unresolved=False
    def reject(day,reason):
        base["excluded"].append({"decision_date":str(day),"reason":reason})
    def usable(d):
        r=indexed.get(d)
        if r is None:
            return None,None
        cutoff=datetime.combine(d,time.max,ZoneInfo("Asia/Kathmandu")).isoformat()
        if assess(symbol,[r],cutoff,reviewed):
            return None,None
        control=session_controls.get(str(d),{})
        if control.get("verified") is not True or not control.get("evidence_id"):
            return None,None
        band=price_band(d,previous_close=control.get("previous_close"),
                        preopen_reference=control.get("preopen_reference"),ordinary_session=control.get("ordinary_session") is True)
        if band is None or float(r["low"])<band["lower"]-1e-8 or float(r["high"])>band["upper"]+1e-8:
            return None,None
        if quantity>float(r["volume"])*max_participation:
            return None,None
        return r,band
    seen=set()
    for obs in sorted(observations,key=lambda x:x["decision_date"]):
        d=date.fromisoformat(obs["decision_date"])
        if d in seen:
            raise ValueError("duplicate observation")
        seen.add(d)
        if unresolved or d<=busy_until or d not in days:
            reject(d,"position_unresolved_or_session_unavailable");continue
        research=obs.get("strategy_research",{})
        if research.get("as_of")!=str(d) or research.get("status")!="research_only" or research.get("alignment")!="aligned" or set(research.get("biases",{}).values())!={"bullish"}:
            reject(d,"no_aligned_long_setup");continue
        if not any(e.get("confirmed_breakout") is True and e.get("direction")=="bullish" and e.get("retest_date")==str(d) for e in research.get("breakouts",[])):
            reject(d,"no_new_confirmed_retest");continue
        i=days.index(d)+1
        if i>=len(days):
            reject(d,"next_session_missing");continue
        entry_day=days[i]
        entry,band=usable(entry_day)
        if entry is None or float(entry["open"])>=band["upper"]-1e-8:
            reject(d,"entry_liquidity_or_band_unverified");continue
        buy=float(entry["open"])
        if cost_mode=="dated_reference":
            required=("regulatory_rate","sell_dp_charge","slippage_bps","min_broker_fee")
            if any(k not in costs for k in required):
                reject(d,"historical_entry_cost_missing");continue
            notional=_number(buy)*(1+_number(costs["slippage_bps"])/10000)*quantity
            ref=brokerage_cap(entry_day,notional)
            if ref.get("rate") is None:
                reject(d,"historical_entry_cost_missing");continue
            # Entry sizing does not depend on future sale tax or commission.
            sizing=round_trip(buy,buy,quantity,assumptions={**costs,
                "buy_broker_rate":ref["rate"],"sell_broker_rate":ref["rate"],
                "capital_gain_tax_rate":0})
        else:
            sizing=round_trip(buy,buy,quantity,assumptions=costs)
        if sizing["status"]!="scenario_only" or sizing["buy_cash"]>capital:
            reject(d,"costs_or_capital_unavailable");continue
        settled=settlement_date(entry_day,settlement_days)
        if settled is None:
            reject(d,"settlement_unverified");continue
        deadline=i+holding_sessions
        trade={"decision_date":str(d),"entry_date":str(entry_day),"entry_price":buy,
               "quantity":quantity,"horizon":horizon,"status":"open_unresolved"}
        pending_stop=False
        for j in range(i+1,min(deadline+1+retry_sessions,len(days))):
            day=days[j]
            bar,band=usable(day)
            if day<=settled:
                if retry_sessions and bar is not None and float(bar["low"])<=buy*(1-stop_fraction):
                    pending_stop=True
                continue
            if bar is None:
                if retry_sessions:
                    continue
                break
            if retry_sessions and (pending_stop or j>deadline):
                from .part5_exit_retry import retry_exit
                retried=retry_exit([str(day)],{str(day):bar},{str(day):band},
                    settled_on=settled,deadline=day,stop=buy*(1-stop_fraction),
                    target=buy*(1+target_fraction),pending_stop=pending_stop)
                if retried["price"] is None:
                    continue
                exit={"status":"retry_open_scenario","price":retried["price"]}
            else:
                exit=exit_scenario(bar,stop=buy*(1-stop_fraction),target=buy*(1+target_fraction),
                               settled_before_session=True,band=band,eligible=True)
            if exit["status"] not in ("no_exit","stop_gap_scenario","target_open_scenario","ambiguous_stop_first","stop_scenario","target_scenario","retry_open_scenario"):
                if retry_sessions:
                    pending_stop=pending_stop or float(bar["low"])<=buy*(1-stop_fraction)
                    continue
                break
            price=exit["price"]
            if price is None and j==deadline and float(bar["close"])>band["lower"]+1e-8:
                price=float(bar["close"])
                exit["status"]="time_exit_scenario"
            if price is not None:
                result=(dated_round_trip(buy,price,quantity,buy_date=entry_day,sell_date=day,assumptions=costs)
                        if cost_mode=="dated_reference" else round_trip(buy,price,quantity,assumptions=costs))
                if result["status"]!="scenario_only":
                    trade.update(unresolved_reason="historical_exit_cost_missing", attempted_exit_date=str(day))
                    break
                trade.update(status="closed_scenario",exit_date=str(day),exit_price=price,exit_reason=exit["status"],net_pnl=result["net_pnl"],costs=result)
                capital+=result["net_pnl"];busy_until=day;break
        base["trades"].append(trade)
        if trade["status"]!="closed_scenario":
            unresolved=True
    base["statistics"]=summarize(base["trades"],initial_capital=initial_capital)
    return dict(base,status="research_only",limitations=["Caller-supplied controls and observations require independent certification.",
        "Daily volume is an ex-post feasibility proxy, not available opening depth.",
        "Settlement must precede exit session; two-session horizon may remain unresolved.",
        "No short selling, overlapping positions, or guaranteed fills."])
