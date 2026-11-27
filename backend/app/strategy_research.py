"""Causal breakout/retest research and horizon descriptors; no trade authorization."""
from .scanner import quality_errors
from .market_structure import detect_structure

HORIZONS={"t_plus_2":(2,2),"swing":(3,15),"positional":(10,40)}

def observe(rows, frames, *, eligible=False):
    base=dict(status="unavailable",action="NO TRADE",production_score=None,breakouts=[],horizons={})
    if not eligible or frames.get("status")!="research_only" or not rows or quality_errors(rows):
        return base
    bars=sorted(rows,key=lambda r:str(r["date"]))
    if frames.get("missing_daily_sessions")!=0 or frames.get("as_of")!=str(bars[-1]["date"]):
        return dict(base,reason="incomplete_or_mismatched_history")
    structure=detect_structure(bars)
    index={str(r["date"]):i for i,r in enumerate(bars)}
    events=[]
    for e in structure["events"]:
        if e["type"] not in ("bos","choch","liquidity_sweep"):
            continue
        i=index[e["date"]]; level=e["level"]; bar=bars[i]
        if e["type"]=="liquidity_sweep":
            events.append(dict(date=e["date"],level=level,classification="bull_trap_proxy" if e["side"]=="high" else "bear_trap_proxy",confirmed_breakout=False))
            continue
        bullish=e["direction"]=="bullish"
        prior=bars[max(0,i-20):i]
        avg=sum(float(r["volume"]) for r in prior)/20 if len(prior)==20 else None
        rv=float(bar["volume"])/avg if avg else None
        retest=None; failed=None
        for later in bars[i+1:]:
            close=float(later["close"])
            if (close<level if bullish else close>level):
                failed=str(later["date"]); break
            if retest is None and (float(later["low"])<=level<=float(later["high"])) and (close>level if bullish else close<level):
                retest=str(later["date"])
        swept=any(x["type"]=="liquidity_sweep" and x.get("side")==("low" if bullish else "high") and 0<i-index[x["date"]]<=20 for x in structure["events"])
        events.append(dict(date=e["date"],direction=e["direction"],level=level,
            classification=("false_breakout_proxy" if failed else "close_break_observation"),
            volume_ratio=rv,volume_confirmed=rv>=1.5 if rv is not None else None,
            retest_date=retest,failure_date=failed,prior_sweep=swept,
            confirmed_breakout=bool(not failed and retest and swept and rv is not None and rv>=1.5)))
    biases={k:frames.get("timeframes",{}).get(k,{}).get("structure",{}).get("bias") for k in ("daily","weekly","monthly")}
    alignment="unavailable"
    if all(v in ("bullish","bearish") for v in biases.values()):
        alignment="aligned" if len(set(biases.values()))==1 else "conflicting"
    for name,(lo,hi) in HORIZONS.items():
        base["horizons"][name]=dict(min_sessions=lo,max_sessions=hi,alignment=alignment,
            action="NO TRADE",status="research_only",execution_validated=False)
    return dict(base,status="research_only",as_of=str(bars[-1]["date"]),breakouts=events,biases=biases,alignment=alignment,
                limitations=["Trap labels are price proxies, not proof of manipulation.","T+2 denotes a two-session research horizon here, not permission to resell unsettled shares.","No fills, returns or risk-adjusted performance inferred."])
