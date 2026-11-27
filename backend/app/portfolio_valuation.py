"""Daily mark-to-market for completed single-security scenarios, not live P&L."""
from datetime import date
from math import isfinite,isclose
from .performance_statistics import risk_adjusted

def daily_portfolio(simulation, marks, benchmark, *, sessions, initial_capital, periods_per_year, annual_risk_free=0):
    base=dict(status="unavailable",production_approved=False,returns=[],equity=[],performance=None)
    def positive(x):
        return isinstance(x,(int,float)) and not isinstance(x,bool) and isfinite(x) and x>0
    if not positive(initial_capital):
        raise ValueError("invalid initial capital")
    days=list(sessions)
    if not days or days!=sorted(set(days)) or any(date.fromisoformat(d).isoformat()!=d for d in days):
        raise ValueError("invalid calendar")
    if simulation.get("status")!="research_only" or simulation.get("classification")!="hypothetical_research_only":
        return dict(base,reason="simulation_unavailable")
    trades=simulation.get("trades",[])
    if any(t.get("status")!="closed_scenario" for t in trades):
        return dict(base,reason="unresolved_position")
    def indexed(records):
        records=list(records)
        if [r.get("date") for r in records]!=days or any(r.get("verified") is not True or not r.get("evidence_id") or not positive(r.get("close")) for r in records):
            return None
        return {r["date"]:r["close"] for r in records}
    prices=indexed(marks)
    # Benchmark must include a separately supplied prior close for first return.
    benchmark=list(benchmark)
    if len(benchmark)!=len(days)+1:
        return dict(base,reason="benchmark_history_missing")
    prior=benchmark[0]
    if not isinstance(prior.get("date"),str) or date.fromisoformat(prior["date"])>=date.fromisoformat(days[0]) or prior.get("verified") is not True or not prior.get("evidence_id") or not positive(prior.get("close")):
        return dict(base,reason="benchmark_prior_close_missing")
    bench=indexed(benchmark[1:])
    if prices is None or bench is None:
        return dict(base,reason="marks_or_benchmark_unverified")
    entries={}; exits={}; previous_exit=None
    for t in sorted(trades,key=lambda t:t["entry_date"]):
        start,end=t["entry_date"],t["exit_date"]
        costs=t.get("costs",{})
        buy,sell=costs.get("buy_cash"),costs.get("sell_cash")
        qty=t.get("quantity")
        if start not in prices or end not in prices or start>=end or (previous_exit is not None and start<=previous_exit):
            raise ValueError("overlapping or invalid trade dates")
        if type(qty) is not int or qty<=0 or not positive(buy) or not positive(sell):
            raise ValueError("invalid trade cash flow")
        pnl=t.get("net_pnl")
        if not isinstance(pnl,(int,float)) or isinstance(pnl,bool) or not isfinite(pnl) or not isclose(sell-buy,pnl,rel_tol=1e-9,abs_tol=1e-7):
            raise ValueError("trade cash flow mismatch")
        entries[start]=t;exits[end]=t;previous_exit=end
    cash=previous_equity=initial_capital;position=0;prev_bench=prior["close"]
    equity=[];returns=[];benchmark_returns=[]
    for day in days:
        if day in entries:
            t=entries[day]
            cash-=t["costs"]["buy_cash"];position=t["quantity"]
            if cash<0:
                raise ValueError("insufficient capital")
        if day in exits:
            cash+=exits[day]["costs"]["sell_cash"];position=0
        value=cash+position*prices[day]
        if not positive(value):
            raise ValueError("invalid portfolio equity")
        equity.append(dict(date=day,cash=cash,shares=position,equity=value))
        returns.append(dict(date=day,net_return=value/previous_equity-1))
        benchmark_returns.append(dict(date=day,net_return=bench[day]/prev_bench-1))
        previous_equity=value;prev_bench=bench[day]
    metrics=risk_adjusted(returns,benchmark_returns,expected_sessions=days,periods_per_year=periods_per_year,annual_risk_free=annual_risk_free)
    return dict(base,status="research_only",equity=equity,returns=returns,benchmark_returns=benchmark_returns,performance=metrics,
        limitations=["Single security, non-overlapping closed scenarios only.","Marks exclude estimated exit costs until actual hypothetical exit.","Caller must certify calendar, price basis, corporate actions, prior benchmark session and evidence."])
