"""Conservative fixed-horizon execution scenarios on qualified archive prefixes."""
from .execution_costs import round_trip
from .execution_constraints import settlement_date, price_band
from .part5_strategy_candidates import candidates
from .scanner import quality_errors
from datetime import date

def compare_engines(symbol, rows, sessions, *, start, end, holding_sessions, costs,
                    settlement_days=None, session_controls=None, quantity=10,
                    max_participation=.01, broker_db=None):
    if type(holding_sessions) is not int or holding_sessions<3 or type(quantity) is not int or quantity<1 or not 0<max_participation<=1:
        raise ValueError("invalid execution assumptions")
    if quality_errors(rows) or sessions!=sorted(set(sessions)):
        raise ValueError("invalid archive or calendar")
    modes=("minervini","wyckoff","smc","provisional","broker","authentic_idpat","master")
    results={m:{"eligible_decisions":0,"signals":0,"trades":[],"execution_exclusions":0} for m in modes}
    indexed={str(r["date"]):r for r in rows}
    fields=("open","high","low","close","volume")
    repeated={b for a,b in zip(sessions,sessions[1:]) if a in indexed and b in indexed and
              tuple(float(indexed[a][k]) for k in fields)==tuple(float(indexed[b][k]) for k in fields)}
    prefix=[]
    busy={m:-1 for m in modes}
    for i,d in enumerate(sessions):
        if d not in indexed or d in repeated:
            prefix=[]
            continue
        prefix.append(indexed[d])
        if not start<=d<=end or i+holding_sessions>=len(sessions) or sessions[i+holding_sessions]>end:
            continue
        flags=candidates(prefix[-252:],symbol=symbol,broker_db=broker_db,
                         broker_sessions=sessions[max(0,i-4):i+1] if i>=4 else None)["candidates"]
        for mode,flag in flags.items():
            if flag is None:continue
            stats=results[mode]
            stats["eligible_decisions"]+=1
            if not flag:continue
            stats["signals"]+=1
            if i<=busy[mode]:continue
            entry_day,exit_day=sessions[i+1],sessions[i+holding_sessions]
            # Explicit controls required; do not invent settlement or daily price bands.
            if settlement_days is None or session_controls is None:
                stats["execution_exclusions"]+=1
                continue
            settled=settlement_date(entry_day,settlement_days)
            span=sessions[i+1:i+holding_sessions+1]
            if settled is None or date.fromisoformat(exit_day)<=settled or any(x not in indexed or x in repeated for x in span):
                stats["execution_exclusions"]+=1
                continue
            bars=[]
            for day in (entry_day,exit_day):
                row=indexed[day]
                control=session_controls.get(day,{})
                band=price_band(day,previous_close=control.get("previous_close"),preopen_reference=control.get("preopen_reference"),ordinary_session=control.get("ordinary_session") is True)
                if control.get("verified") is not True or not control.get("evidence_id") or band is None or float(row["low"])<band["lower"]-1e-8 or float(row["high"])>band["upper"]+1e-8 or quantity>float(row["volume"])*max_participation:
                    break
                bars.append((row,band))
            if len(bars)!=2 or float(bars[0][0]["open"])>=bars[0][1]["upper"]-1e-8 or float(bars[1][0]["close"])<=bars[1][1]["lower"]+1e-8:
                stats["execution_exclusions"]+=1
                continue
            result=round_trip(bars[0][0]["open"],bars[1][0]["close"],quantity,assumptions=costs)
            if result["status"]!="scenario_only":
                stats["execution_exclusions"]+=1
                continue
            stats["trades"].append({"decision_date":d,"entry_date":entry_day,"exit_date":exit_day,"net_return_pct":result["net_return_pct"]})
            busy[mode]=i+holding_sessions
    for stats in results.values():
        values=[t["net_return_pct"] for t in stats["trades"]]
        stats.update(n=len(values),mean_net_pct=sum(values)/len(values) if values else None,
                     positive_pct=100*sum(v>0 for v in values)/len(values) if values else None)
    return {"classification":"hypothetical_research_only","symbol":symbol,"results":results,
            "production_eligible":False,"independent_holdout":False,
            "limitations":["Caller execution controls and archive availability unverified.",
            "Fixed horizon only; no stops or portfolio capital accounting. Daily volume is ex-post proxy."]}
