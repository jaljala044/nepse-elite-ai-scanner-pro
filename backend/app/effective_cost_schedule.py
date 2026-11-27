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


def _tax_for_holding(records, exit_day, holding_days):
    candidates = []
    for record in records:
        lower = _decimal(record.get("holding_days_min", 0), "holding_days_min")
        upper = (_decimal(record["holding_days_max_exclusive"], "holding_days_max_exclusive")
                 if record.get("holding_days_max_exclusive") is not None else None)
        if lower != lower.to_integral_value() or (upper is not None and
                (upper != upper.to_integral_value() or upper <= lower)):
            raise ValueError("invalid_holding_period_band")
        if lower <= holding_days and (upper is None or holding_days < upper):
            candidates.append(record)
    return _effective(candidates, exit_day, "tax")


def resolve_cost_assumptions(trade_date, buy_amount, sell_amount, schedule, *, sell_date=None, require_dated_charges=False):
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
    holding_days = (exit_day - day).days
    tax_record = _tax_for_holding(schedule.get("tax_schedules", []), exit_day, holding_days)
    tax_rate = _decimal(tax_record.get("rate"), "capital_gain_tax_rate")
    dated_keys = ("regulatory_schedules", "dp_schedules", "minimum_brokerage_schedules")
    charge_evidence = {}
    if require_dated_charges or any(k in schedule for k in dated_keys):
        def charge(key, when, side, field):
            records = [r for r in schedule.get(key, []) if r.get("side", "both") in (side, "both")]
            selected = _effective(records, when, key + "_" + side)
            charge_evidence[key + "_" + side] = {k: selected[k] for k in ("schedule_id", "source_id", "source_sha256")}
            return _decimal(selected.get(field), field)
        buy_regulatory = charge("regulatory_schedules", day, "buy", "rate")
        sell_regulatory = charge("regulatory_schedules", exit_day, "sell", "rate")
        dp = charge("dp_schedules", exit_day, "sell", "amount")
        buy_minimum = charge("minimum_brokerage_schedules", day, "buy", "amount")
        sell_minimum = charge("minimum_brokerage_schedules", exit_day, "sell", "amount")
    else:
        buy_regulatory = sell_regulatory = _decimal(schedule.get("regulatory_rate"), "regulatory_rate")
        dp = _decimal(schedule.get("sell_dp_charge"), "sell_dp_charge")
        buy_minimum = sell_minimum = _decimal(schedule.get("min_broker_fee"), "min_broker_fee")
    if tax_rate > 1 or max(buy_regulatory, sell_regulatory) > 1:
        raise ValueError("invalid_cost_rate")
    return {
        "buy_broker_rate": str(buy_rate), "sell_broker_rate": str(sell_rate),
        "regulatory_rate": str(buy_regulatory), "sell_dp_charge": str(dp),
        "buy_regulatory_rate": str(buy_regulatory), "sell_regulatory_rate": str(sell_regulatory),
        "capital_gain_tax_rate": str(tax_rate), "slippage_bps": str(_decimal(schedule.get("slippage_bps", 0), "slippage_bps")),
        "min_broker_fee": str(buy_minimum),
        "buy_min_broker_fee": str(buy_minimum), "sell_min_broker_fee": str(sell_minimum),
        "dated_charges_resolved": bool(charge_evidence),
        "schedule_evidence": {
            **charge_evidence,
            "buy_brokerage": {k: buy_record[k] for k in ("schedule_id", "source_id", "source_sha256")},
            "sell_brokerage": {k: sell_record[k] for k in ("schedule_id", "source_id", "source_sha256")},
            "tax": {k: tax_record[k] for k in ("schedule_id", "source_id", "source_sha256")},
        },
        "buy_date": day.isoformat(), "sell_date": exit_day.isoformat(),
        "holding_calendar_days": holding_days,
        "classification": "caller_supplied_dated_cost_scenario",
        "production_eligible": False,
    }
