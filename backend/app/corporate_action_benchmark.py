"""Point-in-time corporate-action OHLCV adjustment and benchmark comparison.

This module only transforms caller-supplied, evidence-attested records. It does not
fetch NEPSE/CDSC data or infer missing corporate-action terms.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime

_PRICE_FIELDS = ("open", "high", "low", "close")

def _day(value, field):
    try:
        parsed = value if isinstance(value, date) and not isinstance(value, datetime) else date.fromisoformat(value)
        if parsed.isoformat() != str(value):
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        raise ValueError("invalid_" + field) from None

def _positive(value, field, allow_zero=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("invalid_" + field) from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError("invalid_" + field)
    if number < 0 or (number == 0 and not allow_zero):
        raise ValueError("invalid_" + field)
    return number

def _evidence(action, cutoff):
    if action.get("status") != "verified":
        raise ValueError("corporate_action_not_verified")
    source = action.get("source_id")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("corporate_action_source_id_required")
    try:
        available = datetime.fromisoformat(str(action.get("available_at", "")).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("corporate_action_available_at_invalid") from None
    if available.tzinfo is None or available.utcoffset() is None:
        raise ValueError("corporate_action_timezone_required")
    if available > cutoff:
        raise ValueError("corporate_action_lookahead")
    return source

def adjust_ohlcv_for_corporate_actions(*, rows, actions, as_of_date, evidence_cutoff):
    """Backward-adjust pre-ex-date OHLCV for verified bonus/split/dividend/rights.

    Ratio means additional shares per existing share. Dividend is cash per share.
    Rights use theoretical ex-rights adjustment and require subscription_price.
    Terms must be point-in-time available by evidence_cutoff.
    """
    as_of = _day(as_of_date, "as_of_date")
    try:
        cutoff = datetime.fromisoformat(str(evidence_cutoff).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("evidence_cutoff_invalid") from None
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("evidence_cutoff_timezone_required")
    if not isinstance(rows, list) or not rows:
        raise ValueError("ohlcv_rows_required")
    ordered = [deepcopy(row) for row in rows]
    dates = [_day(row.get("date"), "ohlcv_date") for row in ordered]
    if len(set(dates)) != len(dates) or dates != sorted(dates):
        raise ValueError("ohlcv_dates_must_be_unique_and_ordered")
    for row in ordered:
        for field in _PRICE_FIELDS:
            _positive(row.get(field), "ohlcv_" + field)
        _positive(row.get("volume"), "ohlcv_volume", allow_zero=True)
    normalized = []
    for action in actions or []:
        if not isinstance(action, dict):
            raise ValueError("corporate_action_record_invalid")
        ex_date = _day(action.get("ex_date"), "corporate_action_ex_date")
        if ex_date > as_of:
            continue
        source_id = _evidence(action, cutoff)
        kind = action.get("action_type")
        if kind in ("bonus", "split"):
            ratio = _positive(action.get("ratio"), "corporate_action_ratio", allow_zero=True)
            if ratio <= 0:
                raise ValueError("corporate_action_ratio_must_be_positive")
            factor = 1.0 / (1.0 + ratio)
        elif kind == "dividend":
            dividend = _positive(action.get("cash_per_share"), "cash_per_share", allow_zero=True)
            prior = [row for row, day in zip(ordered, dates) if day < ex_date]
            if not prior:
                raise ValueError("dividend_prior_close_unavailable")
            prior_close = float(prior[-1]["close"])
            if dividend >= prior_close:
                raise ValueError("dividend_not_less_than_prior_close")
            factor = (prior_close - dividend) / prior_close
        elif kind == "rights":
            ratio = _positive(action.get("ratio"), "rights_ratio", allow_zero=True)
            subscription = _positive(action.get("subscription_price"), "subscription_price", allow_zero=True)
            prior = [row for row, day in zip(ordered, dates) if day < ex_date]
            if not prior:
                raise ValueError("rights_prior_close_unavailable")
            prior_close = float(prior[-1]["close"])
            factor = ((prior_close + ratio * subscription) / (1.0 + ratio)) / prior_close
        else:
            raise ValueError("unsupported_corporate_action_type")
        volume_factor = factor if kind in ("bonus", "split") else 1.0
        normalized.append((ex_date, factor, volume_factor, kind, source_id))
    adjusted, audit = [], []
    for row, day in zip(ordered, dates):
        out = dict(row)
        combined = 1.0
        for ex_date, factor, _, _, _ in normalized:
            if day < ex_date:
                combined *= factor
        for field in _PRICE_FIELDS:
            out[field] = round(float(out[field]) * combined, 10)
        volume_adjustment = 1.0
        for ex_date, _, volume_factor, _, _ in normalized:
            if day < ex_date:
                volume_adjustment *= volume_factor
        if volume_adjustment:
            out["volume"] = round(float(out["volume"]) / volume_adjustment, 6)
        out["corporate_action_adjustment_factor"] = round(combined, 12)
        adjusted.append(out)
    for ex_date, factor, _, kind, source_id in normalized:
        audit.append({"ex_date": ex_date.isoformat(), "action_type": kind,
                      "backward_price_factor": factor, "source_id": source_id,
                      "classification": "caller_attested_verified_corporate_action"})
    return {"status": "adjusted_with_limitations", "as_of_date": as_of.isoformat(),
            "evidence_cutoff": cutoff.isoformat(), "rows": adjusted,
            "action_audit": audit,
            "classification": "point_in_time_corporate_action_adjustment_not_official_certification"}

def compare_portfolio_to_benchmark(*, portfolio_curve, benchmark_rows, as_of_date):
    """Compare aligned portfolio equity and benchmark close; never forward-fill."""
    end = _day(as_of_date, "as_of_date")
    if not isinstance(portfolio_curve, list) or not portfolio_curve:
        raise ValueError("portfolio_equity_curve_required")
    if not isinstance(benchmark_rows, list) or not benchmark_rows:
        raise ValueError("benchmark_rows_required")
    pmap, bmap = {}, {}
    for row in portfolio_curve:
        day = _day(row.get("date"), "portfolio_date")
        if day > end or day.isoformat() in pmap:
            raise ValueError("portfolio_dates_invalid_or_duplicate")
        pmap[day.isoformat()] = _positive(row.get("equity"), "portfolio_equity")
    for row in benchmark_rows:
        day = _day(row.get("date"), "benchmark_date")
        if day > end or day.isoformat() in bmap:
            raise ValueError("benchmark_dates_invalid_or_duplicate")
        bmap[day.isoformat()] = _positive(row.get("close"), "benchmark_close")
    common = sorted(set(pmap).intersection(bmap))
    if len(common) < 2:
        raise ValueError("two_aligned_benchmark_observations_required")
    start, finish = common[0], common[-1]
    portfolio_return = (pmap[finish] / pmap[start] - 1.0) * 100
    benchmark_return = (bmap[finish] / bmap[start] - 1.0) * 100
    return {"status": "benchmark_comparison_available", "start_date": start,
            "end_date": finish, "aligned_observations": len(common),
            "portfolio_return_pct": round(portfolio_return, 8),
            "benchmark_return_pct": round(benchmark_return, 8),
            "excess_return_pct": round(portfolio_return - benchmark_return, 8),
            "benchmark_symbol": "caller_supplied",
            "classification": "descriptive_historical_comparison_not_alpha_or_strategy_validation",
            "limitations": ["Benchmark identity and source provenance are caller supplied.",
                            "Only exact common dates are compared; no forward filling or interpolation.",
                            "Portfolio curve must already include supported corporate-action cash/share effects."]}
