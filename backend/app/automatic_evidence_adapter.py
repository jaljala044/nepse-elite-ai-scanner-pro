"""Partial automatic evidence adapter; never upgrades unverified inputs."""
from .scanner import analyze, quality_errors
from .market_structure import detect_structure
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available, _day

def derive_chart_evidence(*, symbol, rows, benchmark_rows, sessions, assessment_time):
    cutoff=_time(assessment_time)
    days=[_day(d,"session") for d in sessions]
    if not days or days!=sorted(set(days)) or days[-1]>cutoff.date():
        raise ValueError("invalid_sessions")
    def validate(items, expected_symbol):
        if quality_errors(items): raise ValueError("invalid_ohlcv")
        for row in items:
            _available(row,cutoff,"bar")
            if row.get("symbol")!=expected_symbol or row.get("price_basis")!="corporate_action_reviewed" or not row.get("basis_id"):
                raise ValueError("unreviewed_price_basis_or_symbol")
            if _day(row["date"],"bar")>_time(row["available_at"]).date():
                raise ValueError("bar_available_before_session")
        ordered=sorted(items,key=lambda r:r["date"])
        if [_day(r["date"],"bar") for r in ordered]!=days:
            raise ValueError("session_coverage_incomplete")
        if len({r["basis_id"] for r in ordered})!=1: raise ValueError("mixed_price_basis")
        return ordered
    stock=validate(rows,symbol)
    index=validate(benchmark_rows,"NEPSE")
    screen=analyze(symbol,stock)
    structure=detect_structure(stock)
    labels=dict(wyckoff="UNKNOWN",smc="UNKNOWN",volume="UNKNOWN",relative_strength="UNKNOWN",sector="UNKNOWN")
    if len(stock)>=21:
        recent={str(r["date"]) for r in stock[-5:]}
        breaks=[e for e in structure["events"] if e["type"] in ("bos","choch") and e["date"] in recent]
        if breaks:
            labels["smc"]=breaks[-1]["direction"].upper()
        ratio=screen["metrics"]["volume_vs_20sma"]
        if ratio is not None:
            labels["volume"]="BULLISH" if ratio>=1.5 and float(stock[-1]["close"])>float(stock[-2]["close"]) else "NEUTRAL"
        excess=float(stock[-1]["close"])/float(stock[-21]["close"])-float(index[-1]["close"])/float(index[-21]["close"])
        labels["relative_strength"]="BULLISH" if excess>0 else "BEARISH" if excess<0 else "NEUTRAL"
    return dict(symbol=symbol,labels=labels,screen=screen,structure=structure,
                source_ids=sorted({r["source_id"] for r in stock+index}),
                available_at=max(_time(r["available_at"]) for r in stock+index).isoformat(),
                classification="caller_attested_chart_research",production_eligible=False,
                limitations=["20-session relative return only, not weighted multi-window RS.",
                             "Volume expansion proxy, not full VSA.",
                             "Wyckoff and sector adapters not implemented."])
