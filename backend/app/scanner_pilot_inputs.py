"""Research pilot evidence gate; no inferred historical membership."""
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available
from .scanner_session_alignment import coverage_report

def sector_key(value):
    key="".join(c for c in value.casefold() if c.isalnum())
    return {"tradings":"trading","commercialbank":"commercialbanks","developmentbank":"developmentbanks"}.get(key,key)

def pilot_inputs(*,symbol,decision_time,sessions,membership,stocks,benchmark,sectors,brokers,action_basis_verified=False):
    cutoff=_time(decision_time)
    if membership.get("symbol")!=symbol: raise ValueError("membership_symbol")
    _available(membership,cutoff,"membership")
    key=sector_key(membership["sector"])
    def dates(records,identity,expected):
        result=set()
        for r in records:
            if identity(r)!=expected: continue
            _available(r,cutoff,"pilot_record")
            if _time(r["observed_at"])>_time(r["available_at"]): raise ValueError("observation_after_availability")
            d=r["date"]
            if d>cutoff.date().isoformat(): raise ValueError("future_date")
            if d in result: raise ValueError("duplicate_date")
            result.add(d)
        return result
    report=coverage_report(sessions=sessions,stock_dates=dates(stocks,lambda r:r["symbol"],symbol),
        benchmark_dates=dates(benchmark,lambda r:r["symbol"],"NEPSE"),
        sector_dates=dates(sectors,lambda r:sector_key(r["sector"]),key),
        broker_dates=dates(brokers,lambda r:r["symbol"],symbol))
    for r in report.values():
        r["action_basis_verified"]=action_basis_verified is True
    return dict(symbol=symbol,coverage=report,production_eligible=False,backtest_eligible=False)
