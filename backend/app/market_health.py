"""Point-in-time equity breadth and market-health research; no forward-filled prices."""
from decimal import Decimal, InvalidOperation
from datetime import date

def market_health(rows, *, session, expected_symbols, calendar_verified=False, membership_verified=False):
    base={"status":"unavailable","session":str(session),"production_score":None}
    if not calendar_verified or not membership_verified:
        return dict(base,reason="calendar_or_membership_unverified")
    day=date.fromisoformat(str(session)).isoformat()
    expected=set(expected_symbols)
    if not expected:
        return dict(base,reason="missing_equity_universe")
    seen=set(); up=down=flat=no_trade=0; turnover=Decimal(0)
    for r in rows:
        symbol=r.get("symbol")
        if symbol not in expected or symbol in seen or str(r.get("date"))!=day:
            return dict(base,reason="duplicate_or_out_of_scope")
        if r.get("reviewed") is not True or not r.get("evidence_id"):
            return dict(base,reason="unreviewed_row")
        seen.add(symbol)
        if r.get("verified_no_trade") is True:
            no_trade+=1
            continue
        try:
            close,prior,amount=(Decimal(str(r[k])) for k in ("close","previous_close","turnover"))
            if not all(x.is_finite() for x in (close,prior,amount)) or min(close,prior)<=0 or amount<=0:
                raise ValueError()
        except (InvalidOperation,ValueError,KeyError,TypeError):
            return dict(base,reason="invalid_market_row")
        turnover+=amount
        if close>prior: up+=1
        elif close<prior: down+=1
        else: flat+=1
    coverage=len(seen)/len(expected)
    if coverage!=1:
        return dict(base,reason="incomplete_market_coverage",coverage=coverage,missing_symbols=sorted(expected-seen))
    traded=up+down+flat
    return dict(base,status="research_only",coverage=coverage,advances=up,declines=down,unchanged=flat,
                verified_no_trade=no_trade,traded=traded,turnover=str(turnover),
                advance_decline_ratio=up/down if down else None,
                net_breadth=up-down,breadth_pct=100*(up-down)/traded if traded else None,
                limitation="Breadth is descriptive; previous closes must be corporate-action comparable.")
