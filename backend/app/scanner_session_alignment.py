"""Coverage diagnostics only: dates do not establish provenance."""
from .derived_scanner_ingestion import LOOKBACK

def coverage_report(*,sessions,stock_dates,benchmark_dates,sector_dates,broker_dates):
    days=list(sessions)
    if days!=sorted(set(days)): raise ValueError("invalid_sessions")
    sources=dict(stock=set(stock_dates),benchmark=set(benchmark_dates),sector=set(sector_dates),broker=set(broker_dates))
    result={}
    for horizon,n in LOOKBACK.items():
        window=days[-n:]
        missing={k:sorted(set(window if k!="broker" else window[-5:])-v) for k,v in sources.items()}
        result[horizon]=dict(window_size=len(window),required=n,missing=missing,
            date_coverage_complete=len(window)==n and not any(missing.values()),
            backtest_eligible=False,reason="date_overlap_not_point_in_time_verification")
    return result
