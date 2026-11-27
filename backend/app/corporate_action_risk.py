"""Research risk alerts from a caller-attested post-action portfolio snapshot."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from .corporate_action_trade_plan import _time
from .unified_portfolio_event_engine import _available

def _amount(value, name):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid_"+name) from None
    if not n.is_finite() or n < 0:
        raise ValueError("invalid_"+name)
    return n

def assess_post_action_risk(*, snapshot, limits, assessment_time):
    now = _time(assessment_time)
    _available(snapshot, now, "snapshot")
    cash = _amount(snapshot["available_cash"], "cash")
    receivables = _amount(snapshot.get("receivables",0), "receivables")
    pending = _amount(snapshot.get("pending_rights_payment",0), "rights_payment")
    peak = _amount(snapshot["peak_equity"], "peak_equity")
    caps = {k:_amount(limits[k],k) for k in
            ("max_position_pct","max_sector_pct","risk_per_trade_pct","max_drawdown_pct")}
    if any(not 0 < v <= 1 for v in caps.values()):
        raise ValueError("invalid_risk_limit")
    positions, sectors = {}, defaultdict(Decimal)
    for p in snapshot["positions"]:
        _available(p, now, "position")
        symbol, sector = p["symbol"], p["sector"]
        if not symbol or not sector or symbol in positions:
            raise ValueError("invalid_or_duplicate_position")
        qty, mark = _amount(p["quantity"],"quantity"), _amount(p["mark"],"mark")
        if qty <= 0 or mark <= 0 or qty != qty.to_integral_value():
            raise ValueError("invalid_position_geometry")
        value = qty*mark
        stop = None if p.get("stop") is None else _amount(p["stop"],"stop")
        if stop == 0:
            raise ValueError("invalid_stop")
        positions[symbol] = (sector,qty,mark,value,stop)
        sectors[sector] += value
    equity = cash+receivables+sum(sectors.values(),Decimal(0))
    if equity <= 0 or peak <= 0:
        raise ValueError("positive_equity_and_peak_required")
    drawdown = max(Decimal(0),1-equity/max(peak,equity))
    breaker = drawdown >= caps["max_drawdown_pct"]
    alerts = []
    for symbol,(sector,qty,mark,value,stop) in positions.items():
        reasons = []
        risk = None if stop is None else qty*max(Decimal(0),mark-stop)
        if stop is None: reasons.append("stop_evidence_missing")
        elif mark <= stop: reasons.append("stop_breached")
        if value/equity > caps["max_position_pct"]: reasons.append("stock_concentration")
        if sectors[sector]/equity > caps["max_sector_pct"]: reasons.append("sector_concentration")
        if risk is not None and risk/equity > caps["risk_per_trade_pct"]: reasons.append("stop_risk_limit")
        if breaker: reasons.append("drawdown_circuit_breaker")
        if pending > cash: reasons.append("rights_funding_shortfall")
        action = ("EXIT_REVIEW" if "stop_breached" in reasons else
                  "WAIT" if stop is None else
                  "REDUCE_REVIEW" if any(x in reasons for x in ("stock_concentration","sector_concentration","stop_risk_limit","drawdown_circuit_breaker")) else
                  "WAIT" if reasons else "HOLD_REVIEW")
        alerts.append(dict(symbol=symbol,sector=sector,action=action,reasons=reasons,
                           position_pct=float(value/equity*100),
                           sector_pct=float(sectors[sector]/equity*100),
                           stop_risk_cash=None if risk is None else float(risk)))
    return dict(classification="research_snapshot_risk_review",execution_eligible=False,
                equity=float(equity),available_cash=float(cash),receivables=float(receivables),
                rights_funding_shortfall=float(max(Decimal(0),pending-cash)),
                drawdown_pct=float(drawdown*100),circuit_breaker=breaker,
                new_entries_allowed_by_risk_gate=not breaker and pending<=cash and not any(a["reasons"] for a in alerts),
                alerts=alerts,limitations=["Caller-attested snapshot; no automatic rebalancing or orders.",
                "Receivables are not spendable; pending rights payments are funding commitments.",
                "Stop distance is not a guaranteed execution loss."])
