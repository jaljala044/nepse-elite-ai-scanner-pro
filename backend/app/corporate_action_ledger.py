"""Point-in-time corporate-action-aware holdings and cash ledger.

All corporate-action records and price marks are caller supplied. This module
models explicit entitlement and payment/listing dates; it never guesses terms.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from math import floor


def _date(value, field):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValueError("invalid_" + field) from None


def _number(value, field, zero=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("invalid_" + field) from None
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError("invalid_" + field)
    if result < 0 or (result == 0 and not zero):
        raise ValueError("invalid_" + field)
    return result


def _verify(action, cutoff):
    if action.get("status") != "verified":
        raise ValueError("corporate_action_not_verified")
    if not isinstance(action.get("source_id"), str) or not action["source_id"].strip():
        raise ValueError("corporate_action_source_id_required")
    try:
        available = datetime.fromisoformat(str(action.get("available_at", "")).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("corporate_action_available_at_invalid") from None
    if available.tzinfo is None or available.utcoffset() is None:
        raise ValueError("corporate_action_timezone_required")
    if available > cutoff:
        raise ValueError("corporate_action_lookahead")


def run_corporate_action_portfolio_ledger(*, initial_cash, initial_holdings,
        corporate_actions, price_rows_by_symbol, as_of_date, evidence_cutoff):
    """Replay verified actions against holdings; use record/payment/listing dates.

    Bonus/rights fractional entitlements are reported but not valued or credited;
    only whole shares are added. Rights subscription is an explicit caller choice.
    """
    cash = _number(initial_cash, "initial_cash", zero=True)
    end = _date(as_of_date, "as_of_date")
    try:
        cutoff = datetime.fromisoformat(str(evidence_cutoff).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("evidence_cutoff_invalid") from None
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("evidence_cutoff_timezone_required")
    holdings = {}
    for item in initial_holdings:
        symbol = item.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip() or symbol in holdings:
            raise ValueError("initial_holding_symbol_invalid_or_duplicate")
        quantity = _number(item.get("quantity"), "holding_quantity", zero=True)
        if not quantity.is_integer():
            raise ValueError("initial_holding_quantity_must_be_whole")
        cost = _number(item.get("total_cost"), "holding_total_cost", zero=True)
        holdings[symbol] = {"quantity": int(quantity), "total_cost": cost}
    marks = {}
    all_days = set()
    for symbol, rows in price_rows_by_symbol.items():
        if not isinstance(rows, list) or not rows:
            raise ValueError("price_rows_missing:" + symbol)
        series = {}
        previous = None
        for row in rows:
            day = _date(row.get("date"), "price_date")
            if day > end or (previous is not None and day <= previous):
                raise ValueError("price_dates_not_chronological_or_after_asof:" + symbol)
            close = _number(row.get("close"), "price_close")
            series[day.isoformat()] = close
            all_days.add(day)
            previous = day
        marks[symbol] = series
    for symbol in holdings:
        if symbol not in marks:
            raise ValueError("holding_price_series_missing:" + symbol)
    actions = deepcopy(corporate_actions or [])
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("corporate_action_record_invalid")
        ex_date = _date(action.get("ex_date"), "action_ex_date")
        if ex_date <= end:
            _verify(action, cutoff)
    actions = [a for a in actions if _date(a.get("ex_date"), "action_ex_date") <= end]
    actions.sort(key=lambda a: (str(a.get("ex_date")), str(a.get("symbol")), str(a.get("source_id"))))
    for action in actions:
        symbol = action.get("symbol")
        if symbol not in marks:
            raise ValueError("corporate_action_price_series_missing:" + str(symbol))
        if symbol not in holdings:
            holdings[symbol] = {"quantity": 0, "total_cost": 0.0}
    events = []
    snapshots = {}
    action_state = []
    for action in actions:
        kind = action.get("action_type")
        symbol = action["symbol"]
        if kind == "split":
            effective = _date(action.get("effective_date", action.get("ex_date")), "split_effective_date")
            ratio = _number(action.get("ratio"), "split_ratio")
            action_state.append((effective, "split", action, ratio))
        elif kind == "bonus":
            record = _date(action.get("record_date"), "bonus_record_date")
            listing = _date(action.get("listing_date"), "bonus_listing_date")
            if listing < record:
                raise ValueError("bonus_listing_before_record_date")
            ratio = _number(action.get("ratio"), "bonus_ratio")
            action_state.append((record, "record_bonus", action, ratio))
            action_state.append((listing, "list_bonus", action, ratio))
        elif kind == "dividend":
            record = _date(action.get("record_date"), "dividend_record_date")
            pay = _date(action.get("payment_date"), "dividend_payment_date")
            if pay < record:
                raise ValueError("dividend_payment_before_record_date")
            amount = _number(action.get("cash_per_share"), "dividend_cash_per_share", zero=True)
            action_state.append((record, "record_dividend", action, amount))
            action_state.append((pay, "pay_dividend", action, amount))
        elif kind == "rights":
            record = _date(action.get("record_date"), "rights_record_date")
            subscribe_date = _date(action.get("subscription_date"), "rights_subscription_date")
            listing = _date(action.get("listing_date"), "rights_listing_date")
            if subscribe_date < record or listing < subscribe_date:
                raise ValueError("rights_dates_invalid")
            ratio = _number(action.get("ratio"), "rights_ratio")
            subscription_price = _number(action.get("subscription_price"), "rights_subscription_price", zero=True)
            action_state.append((record, "record_rights", action, ratio))
            action_state.append((subscribe_date, "subscribe_rights", action, subscription_price))
            action_state.append((listing, "list_rights", action, subscription_price))
        else:
            raise ValueError("unsupported_corporate_action_type")
    action_state.sort(key=lambda x: (x[0], x[1], str(x[2].get("source_id"))))
    # Replay every price date plus corporate-action event date; marks are only emitted
    # on supplied sessions and require exact-date closes for all held securities.
    timeline = sorted(set(all_days) | {x[0] for x in action_state if x[0] <= end})
    for day in timeline:
        for event_day, event_type, action, term in action_state:
            if event_day != day:
                continue
            symbol = action["symbol"]
            source = action["source_id"]
            state_key = source
            if event_type == "split":
                old = holdings[symbol]["quantity"]
                raw = old * (1.0 + term)
                new = floor(raw + 1e-12)
                holdings[symbol]["quantity"] = new
                events.append({"date": day.isoformat(), "type": "split_applied",
                               "symbol": symbol, "source_id": source,
                               "old_quantity": old, "new_quantity": new,
                               "fractional_remainder": round(raw - new, 8)})
            elif event_type in ("record_bonus", "record_dividend", "record_rights"):
                snapshots[(state_key, event_type)] = holdings[symbol]["quantity"]
                events.append({"date": day.isoformat(), "type": event_type,
                               "symbol": symbol, "source_id": source,
                               "eligible_quantity": holdings[symbol]["quantity"]})
            elif event_type == "list_bonus":
                eligible = snapshots.get((state_key, "record_bonus"))
                if eligible is None:
                    raise ValueError("bonus_record_snapshot_missing")
                raw = eligible * term
                credited = floor(raw + 1e-12)
                holdings[symbol]["quantity"] += credited
                events.append({"date": day.isoformat(), "type": "bonus_shares_listed",
                               "symbol": symbol, "source_id": source,
                               "eligible_quantity": eligible, "credited_quantity": credited,
                               "fractional_remainder": round(raw - credited, 8)})
            elif event_type == "pay_dividend":
                eligible = snapshots.get((state_key, "record_dividend"))
                if eligible is None:
                    raise ValueError("dividend_record_snapshot_missing")
                credit = eligible * term
                cash += credit
                events.append({"date": day.isoformat(), "type": "dividend_cash_credited",
                               "symbol": symbol, "source_id": source,
                               "eligible_quantity": eligible, "cash_credit": round(credit, 8)})
            elif event_type == "subscribe_rights":
                eligible = snapshots.get((state_key, "record_rights"))
                if eligible is None:
                    raise ValueError("rights_record_snapshot_missing")
                ratio = _number(action.get("ratio"), "rights_ratio")
                raw = eligible * ratio
                subscribed = floor(raw + 1e-12) if action.get("subscribe") is True else 0
                debit = subscribed * term
                if debit > cash + 1e-8:
                    raise ValueError("rights_subscription_cash_insufficient")
                cash -= debit
                snapshots[(state_key, "rights_subscribed_quantity")] = subscribed
                snapshots[(state_key, "rights_subscription_cost")] = debit
                events.append({"date": day.isoformat(), "type": "rights_subscription_processed",
                               "symbol": symbol, "source_id": source,
                               "eligible_quantity": eligible, "subscribed_quantity": subscribed,
                               "cash_debit": round(debit, 8),
                               "fractional_remainder": round(raw - floor(raw + 1e-12), 8) if action.get("subscribe") is True else 0})
            elif event_type == "list_rights":
                subscribed = snapshots.get((state_key, "rights_subscribed_quantity"), 0)
                debit = snapshots.get((state_key, "rights_subscription_cost"), 0.0)
                holdings[symbol]["quantity"] += subscribed
                holdings[symbol]["total_cost"] += debit
                events.append({"date": day.isoformat(), "type": "rights_shares_listed",
                               "symbol": symbol, "source_id": source,
                               "credited_quantity": subscribed, "capitalized_cost": round(debit, 8)})
        if day in all_days:
            equity = cash
            valuation = []
            for symbol, holding in holdings.items():
                mark = marks.get(symbol, {}).get(day.isoformat())
                if holding["quantity"] and mark is None:
                    raise ValueError("holding_mark_missing:" + symbol + ":" + day.isoformat())
                market_value = (mark or 0.0) * holding["quantity"]
                equity += market_value
                valuation.append({"symbol": symbol, "quantity": holding["quantity"],
                                  "close": mark, "market_value": round(market_value, 8),
                                  "average_cost": round(holding["total_cost"] / holding["quantity"], 8)
                                      if holding["quantity"] else None})
            all_days_sorted = sorted(all_days)
            _ = all_days_sorted
            events.append({"date": day.isoformat(), "type": "daily_valuation",
                           "cash": round(cash, 8), "equity": round(equity, 8),
                           "holdings": valuation})
    curve = [x for x in events if x["type"] == "daily_valuation"]
    return {
        "status": "completed_with_limitations",
        "classification": "corporate_action_adjusted_research_holdings_ledger_not_broker_statement",
        "as_of_date": end.isoformat(), "evidence_cutoff": cutoff.isoformat(),
        "ending_cash": round(cash, 8),
        "ending_holdings": [{"symbol": symbol, **holding,
                             "average_cost": round(holding["total_cost"] / holding["quantity"], 8)
                                 if holding["quantity"] else None}
                            for symbol, holding in sorted(holdings.items())],
        "ending_equity": curve[-1]["equity"] if curve else None,
        "equity_curve": curve, "event_log": events,
        "fractional_entitlements": "whole_shares_credited_fractional_remainders_reported_not_valued",
        "limitations": [
            "All actions, source IDs, availability timestamps, dates and price marks are caller supplied, not independently verified against NEPSE/CDSC.",
            "Bonus shares are credited only on supplied listing_date; rights shares only on supplied listing_date.",
            "Rights subscription is processed only when subscribe=true and sufficient cash exists; no financing or entitlement trading is modeled.",
            "Fractional bonus/rights entitlements are reported but not valued or credited; actual issuer-specific treatment may differ.",
            "Dividend cash is credited only on supplied payment_date using holdings captured on record_date.",
            "Split and bonus share cost basis is unchanged in total; rights subscription cost is capitalized when rights shares list.",
            "No taxes, fees, withholding, cash interest, delisting, merger consideration or corporate-action disputes are modeled.",
            "This is not a verified realized portfolio return or investment recommendation."
        ],
        "production_eligible": False,
    }
