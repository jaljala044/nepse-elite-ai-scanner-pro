"""Concentration and exposure diagnostics for independent portfolio replays.

This is an exposure diagnostic, not mark-to-market portfolio risk or a complete
backtest. Independent strategy/horizon books are never pooled.
"""
from datetime import date
from decimal import Decimal, InvalidOperation


def _d(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() else None


def _day(value, field):
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}_must_be_iso_date") from exc
    if parsed.isoformat() != str(value):
        raise ValueError(f"{field}_must_be_canonical_iso_date")
    return parsed


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
        portfolio = item["portfolio"]
        initial = _d(portfolio.get("initial_equity"))
        accepted = portfolio.get("accepted_positions", [])
        closed = portfolio.get("closed_positions", [])
        if initial is None or initial <= 0 or not isinstance(accepted, list) or not isinstance(closed, list):
            raise ValueError("portfolio_equity_or_position_records_invalid")

        accepted_by_id = {}
        intervals = {}
        for position in accepted:
            if not isinstance(position, dict):
                raise ValueError("accepted_position_record_invalid")
            signal_id = position.get("source_signal_id")
            if not isinstance(signal_id, str) or not signal_id.strip() or signal_id in accepted_by_id:
                raise ValueError("accepted_position_id_missing_or_duplicate")
            entry_day = _day(position.get("entry_date"), "entry_date")
            scheduled_value = position.get("scheduled_exit_date")
            scheduled_day = _day(scheduled_value, "scheduled_exit_date") if scheduled_value is not None else None
            notional = _d(position.get("allocated_notional"))
            if notional is None or notional < 0:
                raise ValueError("accepted_position_notional_invalid")
            if scheduled_day is not None and scheduled_day < entry_day:
                raise ValueError("scheduled_exit_precedes_entry")
            accepted_by_id[signal_id] = position
            intervals[signal_id] = {"entry": entry_day, "scheduled_exit": scheduled_day}

        closed_by_id = {}
        for close in closed:
            if not isinstance(close, dict):
                raise ValueError("closed_position_record_invalid")
            signal_id = close.get("source_signal_id")
            if not isinstance(signal_id, str) or not signal_id.strip() or signal_id in closed_by_id:
                raise ValueError("closed_position_id_missing_or_duplicate")
            if signal_id not in accepted_by_id:
                raise ValueError("closed_position_without_accepted_entry")
            exit_day = _day(close.get("exit_date"), "exit_date")
            if exit_day < intervals[signal_id]["entry"]:
                raise ValueError("closed_position_exit_precedes_entry")
            closed_by_id[signal_id] = close
            intervals[signal_id]["exit"] = exit_day

        for signal_id, interval in intervals.items():
            if signal_id not in closed_by_id:
                scheduled = interval["scheduled_exit"]
                if scheduled is None:
                    raise ValueError("open_position_scheduled_exit_missing")
                interval["exit"] = scheduled
        reported_open = portfolio.get("open_position_count")
        actual_open = len(accepted_by_id) - len(closed_by_id)
        if reported_open is not None and (isinstance(reported_open, bool) or reported_open != actual_open):
            raise ValueError("open_position_count_reconciliation_failed")

        dates = sorted({interval["entry"] for interval in intervals.values()}
                       | {interval["exit"] for interval in intervals.values()})
        daily = []
        peak_gross = Decimal("0")
        peak_symbol = Decimal("0")
        peak_sector = Decimal("0")
        peak_risk = Decimal("0")
        peak_symbol_name = peak_sector_name = None
        missing_sector_positions = sum(
            not str(position.get("sector") or "").strip() for position in accepted
        )

        for day in dates:
            active = [
                accepted_by_id[signal_id]
                for signal_id, interval in intervals.items()
                if interval["entry"] <= day < interval["exit"]
            ]
            symbol_values, sector_values = {}, {}
            gross = risk = Decimal("0")
            for position in active:
                notional = _d(position.get("allocated_notional"))
                budget = _d(position.get("risk_budget", "0"))
                if notional is None or notional < 0 or budget is None:
                    raise ValueError("active_position_exposure_invalid")
                gross += notional
                risk += max(Decimal("0"), budget)
                symbol = str(position.get("symbol") or "UNKNOWN")
                sector = str(position.get("sector") or "UNKNOWN")
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
            daily.append({
                "date": day.isoformat(), "open_positions": len(active),
                "gross_exposure": str(gross),
                "gross_exposure_pct_equity": str(gross / initial * 100),
                "open_stop_risk_budget": str(risk), "top_symbol": top_symbol,
                "top_symbol_exposure": str(top_symbol_value), "top_sector": top_sector,
                "top_sector_exposure": str(top_sector_value),
            })

        symbol_pct = peak_symbol / initial * 100
        sector_pct = peak_sector / initial * 100
        status = "CONCENTRATION_WARNING" if symbol_pct > symbol_limit or sector_pct > sector_limit else "WITHIN_CONFIGURED_LIMITS"
        reports.append({
            "strategy_id": item.get("strategy_id"), "horizon": item.get("horizon"),
            "partition": item.get("partition"), "status": status,
            "initial_equity": str(initial), "peak_gross_exposure": str(peak_gross),
            "peak_gross_exposure_pct_equity": str(peak_gross / initial * 100),
            "peak_open_stop_risk_budget": str(peak_risk),
            "peak_symbol": peak_symbol_name, "peak_symbol_exposure": str(peak_symbol),
            "peak_symbol_exposure_pct_equity": str(symbol_pct),
            "peak_sector": peak_sector_name, "peak_sector_exposure": str(peak_sector),
            "peak_sector_exposure_pct_equity": str(sector_pct),
            "accepted_position_count": len(accepted), "closed_position_count": len(closed),
            "ending_open_position_count": actual_open,
            "missing_sector_position_count": missing_sector_positions,
            "sector_coverage": "INCOMPLETE" if missing_sector_positions else "COMPLETE",
            "daily_exposure": daily,
        })

    return {
        "schema_version": "nepse-portfolio-risk-dashboard-1.0.0",
        "partition": comparison.get("partition"), "portfolio_count": len(reports),
        "reports": reports, "symbol_concentration_limit_pct": str(symbol_limit),
        "sector_concentration_limit_pct": str(sector_limit),
        "aggregation_policy": "strategy_horizon portfolios are independent; never sum their exposures as one live book",
        "limitations": [
            "Exposure diagnostics use accepted entry notional and actual/scheduled exit dates.",
            "Stop risk is the allocated risk budget proxy, not a guaranteed loss or executable stop fill.",
            "No mark-to-market valuation is inferred for open positions; this is not a complete portfolio-risk backtest.",
            "Unknown sector is retained as UNKNOWN and lowers coverage.",
        ],
        "performance_claimed": False, "production_enabled": False,
    }
