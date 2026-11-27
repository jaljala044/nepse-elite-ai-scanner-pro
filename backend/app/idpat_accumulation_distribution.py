"""IDPAT-2 accumulation/distribution and climax research detector.

Heuristic chart observations only. This module does not infer actual institutional
orders, ownership, manipulation, or actionable trade instructions.
"""
from __future__ import annotations

from decimal import Decimal

from app.idpat_price_volume import (
    IDPATError,
    _decimal,
    analyze_idpat_price_volume,
)


def _mean(values):
    return sum(values, Decimal("0")) / Decimal(len(values)) if values else None


def _range(bar):
    return bar["high"] - bar["low"]


def _close_location(bar):
    spread = _range(bar)
    return (bar["close"] - bar["low"]) / spread if spread > 0 else Decimal("0.5")


def analyze_idpat_accumulation_distribution(
    snapshot: dict, *, as_of_date: str, as_of_timestamp: str,
    min_coverage: Decimal = Decimal("0.95"),
) -> dict:
    """Return transparent accumulation/distribution hypotheses from >=40 daily bars.

    The first 20 bars in the comparison window form the reference period and
    the latest 20 bars form the recent period. The last bar is also tested for
    shakeout/upthrust and climax characteristics.
    """
    base = analyze_idpat_price_volume(
        snapshot, as_of_date=as_of_date,
        as_of_timestamp=as_of_timestamp, min_coverage=min_coverage,
    )
    symbol = snapshot.get("symbol") if isinstance(snapshot, dict) else None
    if base.get("status") != "partial_research_only":
        return {
            "symbol": symbol, "schema_version": "idpat-2.0.0",
            "status": "withheld", "action": "NO_TRADE",
            "overall_score": None, "data_quality": "LOW_CONFIDENCE",
            "coverage": base.get("coverage"), "reason": base.get("reason", "upstream_evidence_withheld"),
            "probability": None,
        }

    raw_bars = snapshot["price_volume"]["bars"]
    if len(raw_bars) < 40:
        return {
            "symbol": symbol, "schema_version": "idpat-2.0.0",
            "status": "withheld", "action": "NO_TRADE",
            "overall_score": None, "data_quality": "LOW_CONFIDENCE",
            "coverage": base.get("coverage"), "reason": "at_least_40_valid_bars_required",
            "probability": None,
        }

    bars = []
    for row in raw_bars:
        bars.append({
            "date": row["date"],
            "open": _decimal(row["open"], "bar_open"),
            "high": _decimal(row["high"], "bar_high"),
            "low": _decimal(row["low"], "bar_low"),
            "close": _decimal(row["close"], "bar_close"),
            "volume": _decimal(row["volume"], "bar_volume"),
        })

    reference = bars[-40:-20]
    recent = bars[-20:]
    last = recent[-1]
    reference_volume = _mean([b["volume"] for b in reference])
    recent_volume = _mean([b["volume"] for b in recent])
    reference_range = max(b["high"] for b in reference) - min(b["low"] for b in reference)
    recent_range = max(b["high"] for b in recent) - min(b["low"] for b in recent)
    volume_ratio = recent_volume / reference_volume if reference_volume else None
    range_ratio = recent_range / reference_range if reference_range else None

    up_bars = [b for b in recent if b["close"] > b["open"]]
    down_bars = [b for b in recent if b["close"] < b["open"]]
    up_volume = _mean([b["volume"] for b in up_bars])
    down_volume = _mean([b["volume"] for b in down_bars])
    up_down_volume_ratio = (
        up_volume / down_volume if up_volume is not None and down_volume not in (None, Decimal("0")) else None
    )
    average_spread = _mean([_range(b) for b in reference])
    last_spread_ratio = _range(last) / average_spread if average_spread and average_spread > 0 else None
    last_volume_ratio = (
        last["volume"] / _mean([b["volume"] for b in reference])
        if _mean([b["volume"] for b in reference]) not in (None, Decimal("0")) else None
    )

    prior_high = max(b["high"] for b in bars[-21:-1])
    prior_low = min(b["low"] for b in bars[-21:-1])
    shakeout = (
        last["low"] < prior_low and last["close"] > prior_low
        and last_volume_ratio is not None and last_volume_ratio >= Decimal("1.5")
        and _close_location(last) >= Decimal("0.60")
    )
    upthrust = (
        last["high"] > prior_high and last["close"] < prior_high
        and last_volume_ratio is not None and last_volume_ratio >= Decimal("1.5")
        and _close_location(last) <= Decimal("0.40")
    )

    buying_climax = (
        last_volume_ratio is not None and last_volume_ratio >= Decimal("2")
        and last_spread_ratio is not None and last_spread_ratio >= Decimal("1.5")
        and _close_location(last) >= Decimal("0.70")
        and last["close"] > last["open"]
    )
    selling_climax = (
        last_volume_ratio is not None and last_volume_ratio >= Decimal("2")
        and last_spread_ratio is not None and last_spread_ratio >= Decimal("1.5")
        and _close_location(last) <= Decimal("0.30")
        and last["close"] < last["open"]
    )

    range_compression = range_ratio is not None and range_ratio <= Decimal("0.85")
    volume_dry_up = volume_ratio is not None and volume_ratio <= Decimal("0.80")
    demand_preponderance = up_down_volume_ratio is not None and up_down_volume_ratio >= Decimal("1.20")
    supply_preponderance = up_down_volume_ratio is not None and up_down_volume_ratio <= Decimal("0.80")

    accumulation_points = (
        (30 if range_compression else 0)
        + (25 if volume_dry_up else 0)
        + (25 if demand_preponderance else 0)
        + (20 if shakeout else 0)
    )
    distribution_points = (
        (30 if range_compression else 0)
        + (25 if volume_dry_up else 0)
        + (25 if supply_preponderance else 0)
        + (20 if upthrust else 0)
    )

    if accumulation_points >= 65 and accumulation_points > distribution_points:
        hypothesis = "accumulation_candidate"
    elif distribution_points >= 65 and distribution_points > accumulation_points:
        hypothesis = "distribution_candidate"
    elif shakeout:
        hypothesis = "possible_shakeout_reclaim"
    elif upthrust:
        hypothesis = "possible_upthrust_rejection"
    else:
        hypothesis = "no_clear_accumulation_distribution_evidence"

    return {
        "symbol": symbol, "schema_version": "idpat-2.0.0",
        "status": "partial_research_only", "action": "NO_TRADE",
        "overall_score": None, "data_quality": base["data_quality"],
        "coverage": base["coverage"], "as_of_date": base["as_of_date"],
        "source_ids": base["source_ids"],
        "hypothesis": hypothesis,
        "components": {
            "accumulation_evidence_score_partial": accumulation_points,
            "distribution_evidence_score_partial": distribution_points,
        },
        "signals": {
            "recent_20_vs_reference_20_volume_ratio": str(volume_ratio) if volume_ratio is not None else None,
            "recent_20_vs_reference_20_range_ratio": str(range_ratio) if range_ratio is not None else None,
            "up_day_vs_down_day_average_volume_ratio": str(up_down_volume_ratio) if up_down_volume_ratio is not None else None,
            "range_compression": range_compression,
            "volume_dry_up": volume_dry_up,
            "demand_preponderance": demand_preponderance,
            "supply_preponderance": supply_preponderance,
            "possible_shakeout": shakeout,
            "possible_upthrust": upthrust,
            "possible_buying_climax": buying_climax,
            "possible_selling_climax": selling_climax,
            "last_session_volume_vs_reference": str(last_volume_ratio) if last_volume_ratio is not None else None,
            "last_session_spread_vs_reference": str(last_spread_ratio) if last_spread_ratio is not None else None,
        },
        "methodology_notes": [
            "Accumulation/distribution labels are heuristic candidates requiring subsequent structure and context confirmation.",
            "A buying or selling climax is an event candidate, not proof of reversal; follow-through is required.",
            "A shakeout/upthrust is a single-bar reclaim/rejection heuristic, not proof of stop hunting or operator intent.",
            "The 20-session comparison is a configurable research baseline, not a universal Wyckoff rule.",
        ],
        "limitations": [
            "No verified order-book, broker ownership, intraday footprint or actual institutional-order data is consumed.",
            "No SOS/SOW/LPS/LPSY campaign classification is emitted in this phase.",
            "No overall IDPAT score, BUY/SELL recommendation, probability, entry, stop, target or backtest statistic is generated.",
            "Output remains NO_TRADE until subsequent phases add independent market, sector, liquidity, structure and reward/risk confirmation.",
        ],
    }
