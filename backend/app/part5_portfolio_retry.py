"""Research-only portfolio replay with bounded settlement-aware retries."""
from .execution_costs import round_trip
from .part5_exit_retry import retry_exit
from .scanner import quality_errors
from math import floor,isfinite

def replay_portfolio(series, sessions, signals, *, costs, initial_capital=1000000,
                     allocation=.05, max_positions=10, participation=.001,
                     stop=.05, target=.10, holding=5, retry=10):
    if sessions!=sorted(set(sessions)) or not sessions or not all(isfinite(x) and x>0 for x in (initial_capital,allocation,participation,stop,target)) or max(allocation,participation,stop)>=1:
        raise ValueError("invalid configuration")
    if any(type(x) is not int or x<1 for x in (max_positions,holding,retry)) or holding<4:
        raise ValueError("invalid session settings")
    for rows in series.values():
        if quality_errors(rows):raise ValueError("invalid historical bars")
    data={s:{str(r["date"]):r for r in rows} for s,rows in series.items()}
    cash=float(initial_capital); positions={}; closed=[]; excluded=0
    fields=("open","high","low","close","volume")
    def usable(s,i,qty):
        if i<1:return None,None
        bar=data[s].get(sessions[i]);prior=data[s].get(sessions[i-1])
        if bar is None or prior is None:return None,None
        if all(float(bar[k])==float(prior[k]) for k in fields):return None,None
        ref=float(prior["close"]);band={"lower":ref*.9,"upper":ref*1.1}
        if float(bar["low"])<band["lower"]-.11 or float(bar["high"])>band["upper"]+.11 or qty>float(bar["volume"])*participation:return None,None
        return {**bar,**{k:float(bar[k]) for k in fields}},band
    for i,day in enumerate(sessions):
        # Opening entries cannot use cash released by later same-day exits.
        for s in sorted(set(signals.get(sessions[i-1],[]))) if i else []:
            if s not in data or s in positions or len(positions)>=max_positions or i+holding+retry>=len(sessions):
                excluded+=1;continue
            bar,band=usable(s,i,1)
            if bar is None or bar["open"]>=band["upper"]:excluded+=1;continue
            q=min(floor(min(cash,initial_capital*allocation)/bar["open"]),floor(bar["volume"]*participation))
            if q<1:excluded+=1;continue
            budget=min(cash,initial_capital*allocation)
            lo,hi=1,q
            affordable=None
            while lo<=hi:
                mid=(lo+hi)//2
                trial=round_trip(bar["open"],bar["open"],mid,assumptions=costs)
                if trial["status"]!="scenario_only":break
                if trial["buy_cash"]<=budget:
                    affordable=(mid,trial)
                    lo=mid+1
                else:hi=mid-1
            if affordable is None:
                excluded+=1;continue
            q,result=affordable
            cash-=result["buy_cash"]
            positions[s]=dict(entry=i,price=bar["open"],qty=q,invested=result["buy_cash"],pending=bar["low"]<=bar["open"]*(1-stop))
        for s,p in list(positions.items()):
            if i<=p["entry"]:continue
            bar,band=usable(s,i,p["qty"])
            settled=p["entry"]+2; deadline=p["entry"]+holding
            if i<=settled:
                if bar and bar["low"]<=p["price"]*(1-stop):p["pending"]=True
                continue
            if i>deadline+retry:continue
            if bar is None:continue
            result=retry_exit([day],{day:bar},{day:band},settled_on=sessions[settled],
                deadline=sessions[deadline],stop=p["price"]*(1-stop),target=p["price"]*(1+target),pending_stop=p["pending"])
            if result["price"] is None:
                p["pending"]=result.get("pending_stop",p["pending"]);continue
            cost=round_trip(p["price"],result["price"],p["qty"],assumptions=costs)
            if cost["status"]!="scenario_only":continue
            cash+=cost["sell_cash"]
            closed.append(dict(symbol=s,entry_date=sessions[p["entry"]],exit_date=day,net_pnl=cost["net_pnl"]))
            del positions[s]
    return {"classification":"hypothetical_research_only","production_eligible":False,
            "closed":closed,"unresolved":positions,"excluded":excluded,"cash":cash,
            "realized_pnl":sum(t["net_pnl"] for t in closed),
            "total_return_pct":None if positions else (cash/initial_capital-1)*100,
            "limitations":["Observed trading dates proxy for settlement; assumed 10% price band; daily volume ex-post proxy.",
            "No certified fills or historical fees; unresolved positions retain invested capital."]}
