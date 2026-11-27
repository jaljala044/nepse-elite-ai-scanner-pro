"""Research statistics over completed hypothetical trades, not verified performance."""
from math import isfinite
from .historical_quarantine import QUARANTINE
from datetime import date

def summarize(trades, *, initial_capital, synthetic=False):
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
        if not synthetic:
            symbol = str(trade.get("symbol") or "").strip().upper()
            try:
                start = date.fromisoformat(trade["history_start"]).isoformat()
                end = date.fromisoformat(trade["history_end"]).isoformat()
            except (KeyError, TypeError, ValueError):
                excluded += 1
                continue
            if not symbol or start > end or any(t == symbol and start <= d <= end for t,d in QUARANTINE):
                excluded += 1
                continue
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
    return {"classification":"hypothetical_research_statistics","synthetic_only":synthetic,"production_eligible":False,"sample_size":n,
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
