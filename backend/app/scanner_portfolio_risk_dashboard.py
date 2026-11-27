"""Concentration and exposure diagnostics for independent portfolio replays.

This is a research risk report. It does not pool independent strategy portfolios.
"""
from decimal import Decimal, InvalidOperation

def _d(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None

def build_portfolio_risk_dashboard(*, comparison, symbol_limit_pct="25",
                                   sector_limit_pct="40"):
    if not isinstance(comparison, dict) or not isinstance(comparison.get("portfolios"), list):
        raise ValueError("portfolio_comparison_required")
    symbol_limit, sector_limit = _d(symbol_limit_pct), _d(sector_limit_pct)
    if symbol_limit is None or sector_limit is None or not (0 < symbol_limit <= 100 and 0 < sector_limit <= 100):
        raise ValueError("concentration_limits_invalid")
    reports = []
    for item in comparison["portfolios"]:
        if not isinstance(item, dict) or not isinstance(item.get("portfolio"), dict):
            continue
        p = item["portfolio"]
        initial = _d(p.get("initial_equity"))
        accepted = p.get("accepted_positions", [])
        closed = p.get("closed_positions", [])
        if initial is None or initial <= 0 or not isinstance(accepted, list) or not isinstance(closed, list):
            raise ValueError("portfolio_equity_or_position_records_invalid")
        closed_by_id = {x.get("source_signal_id"): x for x in closed if isinstance(x, dict)}
        daily = []
        dates = sorted({x.get("entry_date") for x in accepted if isinstance(x, dict) and x.get("entry_date")}
                       | {x.get("exit_date") for x in closed if isinstance(x, dict) and x.get("exit_date")})
        peak_gross = Decimal("0")
        peak_symbol = Decimal("0")
        peak_sector = Decimal("0")
        peak_risk = Decimal("0")
        peak_symbol_name = peak_sector_name = None
        missing_sector_positions = 0
        for day in dates:
            active = []
            for position in accepted:
                if not isinstance(position, dict):
                    continue
                entry_day = position.get("entry_date")
                close = closed_by_id.get(position.get("source_signal_id"))
                exit_day = close.get("exit_date") if close else position.get("scheduled_exit_date")
                if entry_day and exit_day and entry_day <= day < exit_day:
                    active.append(position)
            symbol_values, sector_values = {}, {}
            gross = risk = Decimal("0")
            for pos in active:
                notional = _d(pos.get("allocated_notional"))
                budget = _d(pos.get("risk_budget"))
                if notional is None or notional < 0:
                    continue
                gross += notional
                risk += max(Decimal("0"), budget or Decimal("0"))
                symbol = str(pos.get("symbol") or "UNKNOWN")
                sector = str(pos.get("sector") or "UNKNOWN")
                symbol_values[symbol] = symbol_values.get(symbol, Decimal("0")) + notional
                sector_values[sector] = sector_values.get(sector, Decimal("0")) + notional
            top_symbol = max(symbol_values, key=symbol_values.get) if symbol_values else None
            top_sector = max(sector_values, key=sector_values.get) if sector_values else None
            top_symbol_value = symbol_values.get(top_symbol, Decimal("0"))
            top_sector_value = sector_values.get(top_sector, Decimal("0"))
            peak_gross = max(peak_gross, gross)
            peak_risk = max(peak_risk, risk)
            if top_symbol_value > peak_symbol:
                peak_symbol, peak_symbol_name = top_symbol_value, top_symbol
            if top_sector_value > peak_sector:
                peak_sector, peak_sector_name = top_sector_value, top_sector
            daily.append({"date": day, "open_positions": len(active),
                "gross_exposure": str(gross), "gross_exposure_pct_equity": str(gross / initial * 100),
                "open_stop_risk_budget": str(risk),
                "top_symbol": top_symbol, "top_symbol_exposure": str(top_symbol_value),
                "top_sector": top_sector, "top_sector_exposure": str(top_sector_value)})
        for pos in accepted:
            if isinstance(pos, dict) and not pos.get("sector"):
                missing_sector_positions += 1
        symbol_pct = peak_symbol / initial * 100
        sector_pct = peak_sector / initial * 100
        status = "CONCENTRATION_WARNING" if symbol_pct > symbol_limit or sector_pct > sector_limit else "WITHIN_CONFIGURED_LIMITS"
        reports.append({"strategy_id": item.get("strategy_id"), "horizon": item.get("horizon"),
            "partition": item.get("partition"), "status": status,
            "initial_equity": str(initial), "peak_gross_exposure": str(peak_gross),
            "peak_gross_exposure_pct_equity": str(peak_gross / initial * 100),
            "peak_open_stop_risk_budget": str(peak_risk),
            "peak_symbol": peak_symbol_name, "peak_symbol_exposure": str(peak_symbol),
            "peak_symbol_exposure_pct_equity": str(symbol_pct),
            "peak_sector": peak_sector_name, "peak_sector_exposure": str(peak_sector),
            "peak_sector_exposure_pct_equity": str(sector_pct),
            "accepted_position_count": len(accepted), "closed_position_count": len(closed),
            "ending_open_position_count": p.get("open_position_count"),
            "missing_sector_position_count": missing_sector_positions,
            "sector_coverage": "INCOMPLETE" if missing_sector_positions else "COMPLETE",
            "daily_exposure": daily})
    return {"schema_version": "nepse-portfolio-risk-dashboard-1.0.0",
        "partition": comparison.get("partition"), "portfolio_count": len(reports),
        "reports": reports, "symbol_concentration_limit_pct": str(symbol_limit),
        "sector_concentration_limit_pct": str(sector_limit),
        "aggregation_policy": "strategy_horizon portfolios are independent; never sum their exposures as one live book",
        "limitations": ["Exposure uses accepted entry notional and scheduled/recorded exit dates.",
            "Stop risk is the allocated risk budget proxy, not a guaranteed loss or executable stop fill.",
            "No mark-to-market valuation is inferred for open positions.",
            "Unknown sector is retained as UNKNOWN and lowers coverage."],
        "performance_claimed": False, "production_enabled": False}
