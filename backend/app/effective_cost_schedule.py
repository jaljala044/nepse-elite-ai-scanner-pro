"""Resolve caller-supplied, dated NEPSE cost schedules without inventing rates.

This module validates schedule coverage and provenance. It does not certify a
publisher, rate, tax rule, or official fee schedule.
"""
from datetime import date
from decimal import Decimal, InvalidOperation


def _decimal(value, name):
    if isinstance(value, bool):
        raise ValueError("invalid_" + name)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("invalid_" + name) from None
    if not number.is_finite() or number < 0:
        raise ValueError("invalid_" + name)
    return number


def _day(value, name):
    if not isinstance(value, str):
        raise ValueError("invalid_" + name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("invalid_" + name) from None
    if parsed.isoformat() != value:
        raise ValueError("invalid_" + name)
    return parsed


def _record_provenance(record):
    if (record.get("status") != "verified" or
        not isinstance(record.get("schedule_id"), str) or not record["schedule_id"].strip() or
        not isinstance(record.get("source_id"), str) or not record["source_id"].strip() or
        not isinstance(record.get("source_sha256"), str) or
        len(record["source_sha256"]) != 64 or
        any(c not in "0123456789abcdef" for c in record["source_sha256"])):
        raise ValueError("cost_schedule_provenance_incomplete")


def _effective(records, trade_day, kind):
    matches = []
    for record in records:
        start = _day(record.get("effective_from"), "effective_from")
        end_text = record.get("effective_to")
        end = _day(end_text, "effective_to") if end_text is not None else None
        if end is not None and end < start:
            raise ValueError("invalid_effective_interval")
        if start <= trade_day and (end is None or trade_day <= end):
            matches.append(record)
    if len(matches) != 1:
        raise ValueError(kind + ("_schedule_missing" if not matches else "_schedule_ambiguous"))
    selected = matches[0]
    _record_provenance(selected)
    return selected


def _broker_rate(records, trade_day, amount, side):
    active = []
    for record in records:
        start = _day(record.get("effective_from"), "effective_from")
        end = _day(record["effective_to"], "effective_to") if record.get("effective_to") else None
        if end is not None and end < start:
            raise ValueError("invalid_effective_interval")
        if not (start <= trade_day and (end is None or trade_day <= end)):
            continue
        lower = _decimal(record.get("amount_min"), "amount_min")
        upper = _decimal(record.get("amount_max_exclusive"), "amount_max_exclusive") if record.get("amount_max_exclusive") is not None else None
        if upper is not None and upper <= lower:
            raise ValueError("invalid_brokerage_slab")
        if lower <= amount and (upper is None or amount < upper):
            if record.get("side") in (side, "both"):
                active.append(record)
    if len(active) != 1:
        raise ValueError("brokerage_slab_missing" if not active else "brokerage_slab_ambiguous")
    record = active[0]
    _record_provenance(record)
    rate = _decimal(record.get("rate"), "brokerage_rate")
    if rate > 1:
        raise ValueError("invalid_brokerage_rate")
    return rate, record


def resolve_cost_assumptions(trade_date, buy_amount, sell_amount, schedule, *, sell_date=None):
    """Return scenario rates only when every dated schedule component is covered."""
    day = _day(trade_date, "trade_date")
    exit_day = day if sell_date is None else _day(sell_date, "sell_date")
    if exit_day < day:
        raise ValueError("sell_date_before_buy_date")
    buy = _decimal(buy_amount, "buy_amount")
    sell = _decimal(sell_amount, "sell_amount")
    if buy <= 0 or sell <= 0 or not isinstance(schedule, dict):
        raise ValueError("invalid_cost_schedule_input")
    buy_rate, buy_record = _broker_rate(schedule.get("brokerage_slabs", []), day, buy, "buy")
    sell_rate, sell_record = _broker_rate(schedule.get("brokerage_slabs", []), exit_day, sell, "sell")
    tax_record = _effective(schedule.get("tax_schedules", []), exit_day, "tax")
    tax_rate = _decimal(tax_record.get("rate"), "capital_gain_tax_rate")
    regulatory = _decimal(schedule.get("regulatory_rate"), "regulatory_rate")
    dp = _decimal(schedule.get("sell_dp_charge"), "sell_dp_charge")
    minimum = _decimal(schedule.get("min_broker_fee"), "min_broker_fee")
    if tax_rate > 1 or regulatory > 1:
        raise ValueError("invalid_cost_rate")
    return {
        "buy_broker_rate": str(buy_rate), "sell_broker_rate": str(sell_rate),
        "regulatory_rate": str(regulatory), "sell_dp_charge": str(dp),
        "capital_gain_tax_rate": str(tax_rate), "slippage_bps": str(_decimal(schedule.get("slippage_bps", 0), "slippage_bps")),
        "min_broker_fee": str(minimum),
        "schedule_evidence": {
            "buy_brokerage": {k: buy_record[k] for k in ("schedule_id", "source_id", "source_sha256")},
            "sell_brokerage": {k: sell_record[k] for k in ("schedule_id", "source_id", "source_sha256")},
            "tax": {k: tax_record[k] for k in ("schedule_id", "source_id", "source_sha256")},
        },
        "buy_date": day.isoformat(), "sell_date": exit_day.isoformat(),
        "classification": "caller_supplied_dated_cost_scenario",
        "production_eligible": False,
    }
