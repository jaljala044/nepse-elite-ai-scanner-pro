"""Chronological, leakage-aware NEPSE research backtesting.

Consumes frozen research signals and reviewed OHLCV only. Daily-bar touches are
price references, not fills. Long-only; no short-sale or order-routing model.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from statistics import mean

from .signal_outcome_validation import HORIZON_SESSIONS, evaluate_signal_path

METHODOLOGY_VERSION = "p4.43_walk_forward_v1"


def _canonical_day(value, name):
    if type(value) is date:
        return value
    if not isinstance(value, str):
        raise ValueError(name + "_must_be_canonical_iso_date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(name + "_must_be_canonical_iso_date") from None
    if parsed.isoformat() != value:
        raise ValueError(name + "_must_be_canonical_iso_date")
    return parsed


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _metrics(observations):
    returns = [Decimal(str(x["reference_return_pct"])) / Decimal("100")
               for x in observations if x.get("reference_return_pct") is not None]
    wins = [x for x in returns if x > 0]
    losses = [x for x in returns if x < 0]
    gross_profit, gross_loss = sum(wins, Decimal(0)), -sum(losses, Decimal(0))
    equity, peak, max_dd = Decimal(1), Decimal(1), Decimal(0)
    for ret in returns:
        equity *= Decimal(1) + ret
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak)
    avg_win = mean([float(x) for x in wins]) * 100 if wins else None
    avg_loss = mean([float(-x) for x in losses]) * 100 if losses else None
    return {
        "sample_size": len(returns),
        "win_rate_pct": float(Decimal(len(wins)) / Decimal(len(returns)) * 100) if returns else None,
        "average_gain_pct": avg_win,
        "average_loss_pct": avg_loss,
        "profit_factor": (float(gross_profit / gross_loss) if gross_loss else (None if not gross_profit else "undefined_no_losses")),
        "expectancy_pct": float(mean([float(x) for x in returns]) * 100) if returns else None,
        "max_drawdown_pct": float(max_dd * 100) if returns else None,
        "t1_hit_rate_pct": _hit_rate(observations, "T1"),
        "t2_hit_rate_pct": _hit_rate(observations, "T2"),
        "t3_hit_rate_pct": _hit_rate(observations, "T3"),
        "stop_rate_pct": _stop_rate(observations),
        "gross_only": True,
    }


def _hit_rate(observations, target):
    eligible = [x for x in observations if x.get("entry_touched")]
    return (sum(target in x.get("targets_touched", []) for x in eligible) / len(eligible) * 100) if eligible else None


def _stop_rate(observations):
    eligible = [x for x in observations if x.get("entry_touched")]
    return (sum(bool(x.get("stop_touched")) for x in eligible) / len(eligible) * 100) if eligible else None


def run_walk_forward_backtest(*, signals, rows_by_symbol, verified_sessions_by_symbol,
                               evaluation_date, reviewed=None, train_ratio=0.60,
                               validation_ratio=0.20, min_partition=3):
    """Evaluate frozen BUY research signals using chronological purged partitions.

    Partitioning is by decision timestamp. A signal is purged from an earlier
    partition if its full horizon label window reaches the next partition start.
    """
    if not isinstance(signals, list) or not signals:
        raise ValueError("signals_required")
    if not isinstance(rows_by_symbol, dict) or not isinstance(verified_sessions_by_symbol, dict):
        raise ValueError("symbol_market_data_required")
    if not 0 < train_ratio < 1 or not 0 < validation_ratio < 1 or train_ratio + validation_ratio >= 1:
        raise ValueError("invalid_partition_ratios")
    cutoff = _canonical_day(evaluation_date, "evaluation_date")
    unique = {}
    normalized = []
    for signal in signals:
        if not isinstance(signal, dict) or signal.get("classification") != "research_only_not_execution":
            raise ValueError("frozen_research_signals_required")
        if signal.get("action") != "BUY":
            continue
        horizon = signal.get("horizon")
        if horizon not in HORIZON_SESSIONS:
            raise ValueError("unsupported_horizon")
        sid = _digest(signal)
        if sid in unique:
            continue
        unique[sid] = True
        decision = _canonical_day(signal.get("details", {}).get("decision_date"),
                                   "signal_decision_date")
        if decision > cutoff:
            raise ValueError("signal_decision_date_after_evaluation_date")
        normalized.append((decision, sid, signal))
    normalized.sort(key=lambda x: (x[0], x[1]))
    if len(normalized) < min_partition * 3:
        return {"status": "insufficient_sample", "classification": "research_backtest_not_execution",
                "methodology_version": METHODOLOGY_VERSION, "signals_seen": len(normalized),
                "minimum_required": min_partition * 3, "partitions": {},
                "limitations": ["At least three chronological partitions are required.",
                                "No strategy performance or probability claim is supported."]}
    n = len(normalized)
    train_end = max(1, int(n * train_ratio))
    validation_end = max(train_end + 1, int(n * (train_ratio + validation_ratio)))
    if n - validation_end < 1:
        raise ValueError("test_partition_empty")
    boundaries = [normalized[train_end][0], normalized[validation_end][0]]
    raw_parts = {"train": normalized[:train_end],
                 "validation": normalized[train_end:validation_end],
                 "test": normalized[validation_end:]}
    results = {}
    for name, part in raw_parts.items():
        next_start = boundaries[0] if name == "train" else boundaries[1] if name == "validation" else None
        kept, purged = [], 0
        for decision, sid, signal in part:
            symbol = signal["symbol"]
            sessions = verified_sessions_by_symbol.get(symbol)
            if not isinstance(sessions, list) or not sessions:
                continue
            try:
                parsed = [_canonical_day(x, "verified_session") for x in sessions]
            except ValueError:
                continue
            if parsed != sorted(parsed) or len(parsed) != len(set(parsed)):
                continue
            horizon_len = HORIZON_SESSIONS[signal["horizon"]]
            future = [d for d in parsed if d > decision]
            label_end = future[min(len(future), horizon_len) - 1] if future else decision
            if next_start and label_end >= next_start:
                purged += 1
                continue
            kept.append((decision, sid, signal))
        evaluated, withheld = [], 0
        for decision, sid, signal in kept:
            symbol = signal["symbol"]
            rows = rows_by_symbol.get(symbol)
            sessions = verified_sessions_by_symbol.get(symbol)
            if not isinstance(rows, list) or not isinstance(sessions, list):
                withheld += 1
                continue
            try:
                outcome = evaluate_signal_path(signal, rows, sessions,
                    evaluation_date=cutoff.isoformat(), reviewed=reviewed)
            except (ValueError, TypeError, KeyError):
                withheld += 1
                continue
            if outcome.get("status") not in {"observed"} or not outcome.get("entry_touched"):
                withheld += 1
                continue
            outcome["signal_id"] = sid
            outcome["partition"] = name
            evaluated.append(outcome)
        results[name] = {
            "candidate_signals": len(part), "purged_for_horizon_overlap": purged,
            "evaluated_trades": len(evaluated), "withheld_or_unfilled": withheld,
            "metrics": _metrics(evaluated),
            "observations": evaluated,
            "quality": "LOW_CONFIDENCE" if len(evaluated) < min_partition else "RESEARCH_ONLY",
        }
    config = {"methodology_version": METHODOLOGY_VERSION, "train_ratio": train_ratio,
              "validation_ratio": validation_ratio, "min_partition": min_partition,
              "evaluation_date": cutoff.isoformat(), "long_only": True,
              "fill_model": "daily_ohlcv_price_reference_only"}
    return {
        "status": "completed_with_limitations",
        "classification": "research_backtest_not_execution",
        "methodology_version": METHODOLOGY_VERSION,
        "config_hash": _digest(config), "config": config,
        "signals_seen": len(normalized), "partitions": results,
        "out_of_sample": results["test"]["metrics"],
        "confidence": "LOW_CONFIDENCE" if results["test"]["evaluated_trades"] < min_partition else "RESEARCH_ONLY",
        "unavailable_metrics": ["net_return", "fees_and_tax_adjusted_return", "slippage_adjusted_return",
            "benchmark_excess_return", "Sharpe", "Sortino", "actual_fill_rate", "market_impact"],
        "limitations": [
            "Long-only BUY research signals; SELL/HOLD/NO TRADE are not simulated as short trades.",
            "Daily OHLCV price-reference touches are not exchange fills or realized trades.",
            "No fees, taxes, slippage, market impact, queue priority, partial fills or circuit-limit fill model.",
            "No benchmark series is supplied; benchmark-relative performance is unavailable.",
            "Only complete, reviewed signal paths are included; incomplete paths are withheld, not scored as losses.",
            "Partition metrics are descriptive; this does not establish a profitable strategy or calibrated probabilities."
        ]
    }
