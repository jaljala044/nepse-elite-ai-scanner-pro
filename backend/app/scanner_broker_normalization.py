"""Explicit broker cohort aggregation, never infer ownership."""
from decimal import Decimal
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def normalize_broker_day(*,symbol,session,rows,cohort,manifest,decision_time):
    cutoff=_time(decision_time)
    _available(manifest,cutoff,"broker_manifest")
    if manifest.get("symbol")!=symbol or manifest.get("session")!=session: raise ValueError("manifest_identity")
    ids=set(cohort)
    if not ids or len(ids)!=len(cohort): raise ValueError("invalid_cohort")
    seen=set(); buy=Decimal(0); sell=Decimal(0); sources=set()
    for r in rows:
        _available(r,cutoff,"broker_row")
        if r["symbol"]!=symbol or r["session"]!=session or _time(r["observed_at"])>_time(r["available_at"]): raise ValueError("broker_identity")
        k=r["broker_id"]
        if k in seen: raise ValueError("duplicate_broker")
        seen.add(k)
        b,s=(Decimal(str(r[x])) for x in ("buy_turnover","sell_turnover"))
        if any(not x.is_finite() or x<0 for x in (b,s)): raise ValueError("invalid_turnover")
        if k in ids: buy+=b; sell+=s; sources.add(r["source_id"])
    complete=ids<=seen and manifest.get("coverage_complete") is True
    return dict(symbol=symbol,session=session,date=session,broker_ids=sorted(ids),buy_turnover=str(buy),sell_turnover=str(sell),
        coverage_complete=complete,status="verified" if complete else "unknown",source_id=manifest["source_id"],
        observed_at=manifest["available_at"],available_at=max([manifest["available_at"]]+[r["available_at"] for r in rows],key=_time),
        component_source_ids=sorted(sources),production_eligible=False)
