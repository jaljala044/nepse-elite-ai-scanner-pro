"""Research statistics over completed hypothetical trades, not verified performance."""
from math import isfinite

def summarize(trades, *, initial_capital):
    if isinstance(initial_capital,bool) or not isinstance(initial_capital,(int,float)) or not isfinite(initial_capital) or initial_capital<=0:
        raise ValueError("positive finite initial capital required")
    values=[]
    excluded=0
    for trade in trades:
        if trade.get("status")!="closed_scenario":
            excluded+=1
            continue
        pnl=trade.get("net_pnl")
        if isinstance(pnl,bool) or not isinstance(pnl,(int,float)) or not isfinite(pnl):
            raise ValueError("invalid completed trade PnL")
        values.append(pnl)
    wins=[v for v in values if v>0]
    losses=[v for v in values if v<0]
    capital=peak=initial_capital
    drawdown=0
    for pnl in values:
        capital+=pnl
        peak=max(peak,capital)
        drawdown=max(drawdown,100*(peak-capital)/peak)
    n=len(values)
    return {"classification":"hypothetical_research_statistics","sample_size":n,
            "excluded_count":excluded,"wins":len(wins),"losses":len(losses),
            "breakeven":n-len(wins)-len(losses),
            "win_rate_pct":100*len(wins)/n if n else None,
            "average_win":sum(wins)/len(wins) if wins else None,
            "average_loss":sum(losses)/len(losses) if losses else None,
            "profit_factor":sum(wins)/-sum(losses) if losses else None,
            "expectancy":sum(values)/n if n else None,
            "max_closed_trade_drawdown_pct":drawdown if n else None,
            "net_pnl":sum(values) if n else None,
            "net_return_pct":100*sum(values)/initial_capital if n else None,
            "limitations":["Trades must be supplied in chronological realization order.",
                           "Closed-trade equity only; no intraday or mark-to-market drawdown.",
                           "No inference of predictive accuracy or verified execution."]}


def risk_adjusted(returns, benchmark, *, expected_sessions, periods_per_year, annual_risk_free=0.0):
    """Aligned hypothetical net daily returns; decimal units, no missing-session fill."""
    from datetime import date
    from math import sqrt, prod
    from statistics import mean, stdev
    if type(periods_per_year) is not int or periods_per_year<=0:
        raise ValueError("explicit positive annualization required")
    if isinstance(annual_risk_free,bool) or not isinstance(annual_risk_free,(int,float)) or not isfinite(annual_risk_free) or annual_risk_free<=-1:
        raise ValueError("invalid risk free rate")
    days=list(expected_sessions)
    if any(not isinstance(d,str) or date.fromisoformat(d).isoformat()!=d for d in days) or days!=sorted(set(days)):
        raise ValueError("invalid session calendar")
    def values(records):
        records=list(records)
        if [r["date"] for r in records]!=days:
            raise ValueError("return dates must exactly match verified session calendar")
        out=[r["net_return"] for r in records]
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not isfinite(x) or x<=-1 for x in out):
            raise ValueError("invalid daily return")
        return out
    a,b=values(returns),values(benchmark)
    base=dict(classification="hypothetical_research_statistics",sample_size=len(a),sharpe=None,sortino=None,information_ratio=None,
        net_return=None,benchmark_return=None,excess_return=None,max_drawdown=None,annualized_volatility=None,
        production_approved=False)
    if len(a)<2:
        return dict(base,status="insufficient_history")
    rf=(1+annual_risk_free)**(1/periods_per_year)-1
    excess=[x-rf for x in a]; active=[x-y for x,y in zip(a,b)]
    vol=stdev(a); tracking=stdev(active)
    downside=sqrt(mean(min(x,0)**2 for x in excess))
    equity=peak=1.0; dd=0.0
    for x in a:
        equity*=1+x; peak=max(peak,equity); dd=max(dd,1-equity/peak)
    bench=prod(1+x for x in b)-1
    return dict(base,status="research_only",net_return=equity-1,benchmark_return=bench,excess_return=equity-1-bench,
        max_drawdown=dd,annualized_volatility=vol*sqrt(periods_per_year),
        sharpe=mean(excess)/vol*sqrt(periods_per_year) if vol else None,
        sortino=mean(excess)/downside*sqrt(periods_per_year) if downside else None,
        information_ratio=mean(active)/tracking*sqrt(periods_per_year) if tracking else None,
        limitations=["Caller must certify session completeness, benchmark basis and net execution costs.","Statistics do not establish actual fills or predictive accuracy."])


def benchmark_report(returns, benchmark, *, expected_sessions, periods_per_year, annual_risk_free=0.0):
    """Extend aligned daily-return statistics with annualized growth and Calmar."""
    result = risk_adjusted(returns, benchmark, expected_sessions=expected_sessions,
                           periods_per_year=periods_per_year, annual_risk_free=annual_risk_free)
    result.update(cagr=None, benchmark_cagr=None, calmar=None)
    if result["status"] != "research_only":
        return result
    n = result["sample_size"]
    # Do not extrapolate short samples into annual growth claims.
    if n < periods_per_year:
        return result
    for source,target in (("net_return","cagr"),("benchmark_return","benchmark_cagr")):
        result[target] = (1+result[source])**(periods_per_year/n)-1
    if result["max_drawdown"] > 0:
        result["calmar"] = result["cagr"]/result["max_drawdown"]
    return result
