"""Chronological research portfolio ledger for trades and corporate actions.

Caller-attested source records are never represented as independently verified
exchange/custody records. Buy shares settle before record-date entitlement snapshots;
sell proceeds remain receivables until the supplied settlement date.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from math import floor


def _day(value, name):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValueError("invalid_" + name) from None


def _positive(value, name, zero=False):
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ValueError("invalid_" + name) from None
    if x != x or x in (float("inf"), float("-inf")) or x < 0 or (x == 0 and not zero):
        raise ValueError("invalid_" + name)
    return x


def _available(record, cutoff, prefix):
    if record.get("status") != "verified":
        raise ValueError(prefix + "_not_verified")
    if not isinstance(record.get("source_id"), str) or not record["source_id"].strip():
        raise ValueError(prefix + "_source_id_required")
    try:
        available = datetime.fromisoformat(str(record.get("available_at", "")).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(prefix + "_available_at_invalid") from None
    if available.tzinfo is None or available.utcoffset() is None:
        raise ValueError(prefix + "_timezone_required")
    if available > cutoff:
        raise ValueError(prefix + "_lookahead")


def run_unified_portfolio_event_ledger(*, initial_cash, initial_holdings, trades,
                                       corporate_actions, price_rows_by_symbol,
                                       portfolio_sessions, as_of_date, evidence_cutoff,
                                       benchmark_rows=None, benchmark_symbol=None,
                                       risk_limits=None, sector_by_symbol=None):
    as_of = _day(as_of_date, "as_of_date")
    try:
        cutoff = datetime.fromisoformat(str(evidence_cutoff).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("evidence_cutoff_invalid") from None
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("evidence_cutoff_timezone_required")
    cash = _positive(initial_cash, "initial_cash", zero=True)
    starting_cash = cash
    limits = risk_limits or {}
    sectors = sector_by_symbol or {}
    for key in ("max_position_pct", "max_sector_pct", "max_drawdown_pct", "risk_per_trade_pct"):
        if key in limits and not 0 < _positive(limits[key], key) <= 1:
            raise ValueError("invalid_" + key)
    if "max_positions" in limits and (type(limits["max_positions"]) is not int or limits["max_positions"] < 1):
        raise ValueError("invalid_max_positions")
    peak_equity = None
    circuit_breaker = False
    if not isinstance(portfolio_sessions, list) or len(portfolio_sessions) < 2:
        raise ValueError("verified_portfolio_sessions_required")
    days = [_day(x, "portfolio_session") for x in portfolio_sessions]
    if days != sorted(days) or len(days) != len(set(days)) or days[-1] != as_of:
        raise ValueError("portfolio_sessions_must_be_sorted_unique_and_end_on_as_of")
    if not isinstance(initial_holdings, dict):
        raise ValueError("initial_holdings_invalid")
    positions = {}
    for symbol, item in initial_holdings.items():
        if not isinstance(symbol, str) or not symbol.strip() or not isinstance(item, dict):
            raise ValueError("initial_holding_invalid")
        qty = _positive(item.get("quantity"), "initial_quantity", zero=True)
        cost = _positive(item.get("average_cost"), "initial_average_cost", zero=True)
        positions[symbol] = {"quantity": qty, "cost_basis": qty * cost}
    bars = {}
    for symbol, rows in price_rows_by_symbol.items():
        if not isinstance(rows, list) or not rows:
            raise ValueError("price_rows_missing:" + str(symbol))
        lookup = {}
        prior = None
        for row in rows:
            d = _day(row.get("date"), "price_date")
            if prior is not None and d <= prior:
                raise ValueError("price_rows_must_be_unique_and_ordered:" + str(symbol))
            prior = d
            close = _positive(row.get("close"), "price_close")
            lookup[d] = close
        bars[symbol] = lookup
    seen_trade, seen_action = set(), set()
    trades_by_day = defaultdict(list)
    for trade in trades or []:
        if not isinstance(trade, dict):
            raise ValueError("trade_record_invalid")
        _available(trade, cutoff, "trade")
        tid = trade.get("trade_id")
        if not isinstance(tid, str) or not tid.strip() or tid in seen_trade:
            raise ValueError("trade_id_missing_or_duplicate")
        seen_trade.add(tid)
        symbol = trade.get("symbol")
        side = trade.get("side")
        if symbol not in bars or side not in ("BUY", "SELL"):
            raise ValueError("trade_symbol_or_side_invalid")
        trade_day = _day(trade.get("trade_date"), "trade_date")
        settle_day = _day(trade.get("settlement_date"), "trade_settlement_date")
        if settle_day < trade_day or trade_day > as_of:
            raise ValueError("trade_settlement_or_date_invalid")
        qty = _positive(trade.get("quantity"), "trade_quantity")
        price = _positive(trade.get("price"), "trade_price")
        fees = _positive(trade.get("fees", 0), "trade_fees", zero=True)
        if trade_day not in days or settle_day not in days:
            raise ValueError("trade_dates_must_be_verified_portfolio_sessions")
        if days.index(settle_day) - days.index(trade_day) != 2:
            raise ValueError("trade_settlement_must_be_t_plus_two")
        trades_by_day[trade_day].append({**trade, "_qty": qty, "_price": price,
                                         "_fees": fees, "_settle": settle_day})
    actions_by_day = defaultdict(list)
    entitlement_by_action = {}
    for action in corporate_actions or []:
        if not isinstance(action, dict):
            raise ValueError("corporate_action_record_invalid")
        _available(action, cutoff, "corporate_action")
        aid = action.get("action_id")
        if not isinstance(aid, str) or not aid.strip() or aid in seen_action:
            raise ValueError("corporate_action_id_missing_or_duplicate")
        seen_action.add(aid)
        symbol = action.get("symbol")
        if symbol not in bars:
            raise ValueError("corporate_action_symbol_price_history_missing")
        kind = action.get("action_type")
        record_day = _day(action.get("record_date"), "record_date")
        if record_day > as_of:
            continue
        if kind in ("bonus", "split"):
            effective = _day(action.get("listing_date"), "listing_date")
            factor = _positive(action.get("ratio"), "corporate_action_ratio")
            event = ("split" if kind == "split" else "shares", effective, factor)
        elif kind == "dividend":
            effective = _day(action.get("payment_date"), "payment_date")
            amount = _positive(action.get("cash_per_share"), "cash_per_share", zero=True)
            event = ("dividend", effective, amount)
        elif kind == "rights":
            effective = _day(action.get("subscription_payment_date"), "rights_payment_date")
            listing = _day(action.get("listing_date"), "rights_listing_date")
            subscribed = _positive(action.get("subscribed_quantity"), "rights_subscribed_quantity", zero=True)
            price = _positive(action.get("subscription_price"), "rights_subscription_price")
            event = ("rights_payment", effective, (subscribed, price, listing))
        else:
            raise ValueError("unsupported_corporate_action_type")
        if effective not in days and effective <= as_of:
            raise ValueError("corporate_action_effective_date_not_verified_session")
        if kind == "rights" and listing not in days and listing <= as_of:
            raise ValueError("rights_listing_date_not_verified_session")
        if record_day not in days or effective < record_day or (kind == "rights" and listing <= effective):
            raise ValueError("corporate_action_dates_must_follow_verified_record_date")
        actions_by_day[record_day].append(action)
        entitlement_by_action[aid] = {"symbol": symbol, "event": event,
                                      "source_id": action["source_id"], "action": action}
    # Events are keyed to their actual economic dates after record-date entitlement is known.
    pending_events = defaultdict(list)
    curve = []
    receivables = 0.0
    rights_paid = 0.0
    audit = []
    sized_trades = []
    executed_trades = []
    linked_entries = {}
    pending_buys = defaultdict(float)
    pending_sales = defaultdict(float)
    for day in days:
        # Settlement of purchases adds shares; sale proceeds become spendable cash.
        for trade in trades_by_day.get(day, []):
            if trade["side"] == "BUY" and trade["_settle"] == day:
                pass
        for trade_day, records in list(trades_by_day.items()):
            for trade in records:
                if trade["side"] == "BUY" and trade["_settle"] == day:
                    symbol = trade["symbol"]
                    pos = positions.setdefault(symbol, {"quantity": 0.0, "cost_basis": 0.0})
                    pending_buys[symbol] -= trade["_qty"]
                    pos["quantity"] += trade["_qty"]
                    pos["cost_basis"] += trade["_qty"] * trade["_price"] + trade["_fees"]
                    pending_events[day].append({"type": "buy_shares_settled", "trade_id": trade["trade_id"],
                                                "symbol": symbol, "quantity": trade["_qty"],
                                                "source_id": trade["source_id"]})
        # Corporate-action entitlement is determined from settled holdings at record-date close.
        for action in actions_by_day.get(day, []):
            symbol = action["symbol"]
            # A trade-date disposal is not proof of record-date custody eligibility.
            if pending_sales[symbol] > 1e-8:
                raise ValueError("record_date_unsettled_sale_requires_custody_evidence:" + symbol)
            entitlement = positions.get(symbol, {"quantity": 0.0})["quantity"]
            aid = action["action_id"]
            kind, effective, terms = entitlement_by_action[aid]["event"]
            if kind == "rights_payment" and terms[0] > entitlement * _positive(action.get("ratio"), "rights_ratio") + 1e-8:
                raise ValueError("rights_subscription_exceeds_record_date_entitlement:" + aid)
            entitlement_by_action[aid]["quantity"] = entitlement
            entitlement_by_action[aid]["terms"] = terms
            active = [(tid, lot) for tid, lot in linked_entries.items()
                      if lot["symbol"] == symbol and not lot["closed"] and lot["settlement"] <= day]
            if kind != "dividend" and active:
                if len(active) != 1 or abs(active[0][1]["quantity"] - entitlement) > 1e-8:
                    raise ValueError("corporate_action_requires_unambiguous_single_lot")
                active[0][1]["pending_actions"].add(aid)
                entitlement_by_action[aid]["linked_entry_id"] = active[0][0]
            if kind == "split":
                pending_events[effective].append({"type": "split_conversion", "action_id": aid,
                                                  "symbol": symbol, "factor": terms,
                                                  "source_id": action["source_id"]})
            elif kind == "shares":
                pending_events[effective].append({"type": action["action_type"] + "_shares", "action_id": aid,
                                                  "symbol": symbol, "quantity": entitlement * terms,
                                                  "source_id": action["source_id"]})
            elif kind == "dividend":
                pending_events[effective].append({"type": "dividend_cash", "action_id": aid,
                                                  "symbol": symbol, "quantity": entitlement,
                                                  "cash_delta": entitlement * terms,
                                                  "source_id": action["source_id"]})
            else:
                subscribed, price, listing = terms
                pending_events[effective].append({"type": "rights_subscription_payment", "action_id": aid,
                                                  "symbol": symbol, "quantity": subscribed,
                                                  "cash_delta": -subscribed * price, "price": price,
                                                  "listing_date": listing, "source_id": action["source_id"]})
        # Apply due corporate-action events before trades executed on this date.
        for event in pending_events.pop(day, []):
            if event["type"] == "sell_proceeds_settled":
                cash += event["cash_delta"]
                receivables -= event["cash_delta"]
                pending_sales[event["symbol"]] -= event["quantity"]
                continue
            if event["type"] in ("trade_settlement_audit", "buy_shares_settled"):
                continue
            symbol = event["symbol"]
            pos = positions.setdefault(symbol, {"quantity": 0.0, "cost_basis": 0.0})
            if event["type"] == "split_conversion":
                if abs(pending_buys[symbol]) > 1e-8 or any(t["symbol"] == symbol for t in trades_by_day.get(day, [])):
                    raise ValueError("split_with_overlapping_trade_requires_custody_reconciliation")
                converted = pos["quantity"] * event["factor"]
                if abs(converted - round(converted)) > 1e-8:
                    raise ValueError("fractional_split_requires_cash_in_lieu_evidence")
                pos["quantity"] = round(converted)
            elif event["type"] == "dividend_cash":
                cash += event["cash_delta"]
            elif event["type"] == "rights_subscription_payment":
                if cash + event["cash_delta"] < -1e-8:
                    raise ValueError("insufficient_cash_for_rights_subscription:" + event["action_id"])
                cash += event["cash_delta"]
                rights_paid -= event["cash_delta"]
                pending_events[event["listing_date"]].append({
                    "type": "rights_shares", "action_id": event["action_id"], "symbol": symbol,
                    "quantity": event["quantity"], "price": event["price"], "source_id": event["source_id"]})
            else:
                pos["quantity"] += event["quantity"]
                if event["type"] == "rights_shares":
                    pos["cost_basis"] += event["quantity"] * event["price"]
                    rights_paid -= event["quantity"] * event["price"]
            if event["type"] in ("split_conversion", "bonus_shares", "rights_shares"):
                lot_id = entitlement_by_action[event["action_id"]].get("linked_entry_id")
                if lot_id is not None:
                    lot = linked_entries[lot_id]
                    if lot["closed"] or abs(pending_buys[symbol]) > 1e-8:
                        raise ValueError("corporate_action_lot_changed_before_credit")
                    lot["quantity"] = pos["quantity"]
                    lot["pending_actions"].discard(event["action_id"])
            if event["type"] != "dividend_cash":
                pos["average_cost"] = pos["cost_basis"] / pos["quantity"] if pos["quantity"] else 0.0
            event["effective_date"] = day.isoformat()
            audit.append({**event, "effective_date": day.isoformat()})
        # Execute trades after record-date snapshots and corporate-action credits.
        for trade in trades_by_day.get(day, []):
            symbol, qty = trade["symbol"], trade["_qty"]
            gross = qty * trade["_price"]
            if any(lot["symbol"] == symbol and lot["pending_actions"] for lot in linked_entries.values()):
                raise ValueError("trade_during_pending_lot_corporate_action")
            if trade["side"] == "BUY":
                if trade.get("auto_size") is True:
                    if not all(k in limits for k in ("max_position_pct", "max_sector_pct", "risk_per_trade_pct", "max_positions", "max_drawdown_pct")):
                        raise ValueError("complete_auto_size_risk_limits_required")
                if limits:
                    if circuit_breaker:
                        raise ValueError("portfolio_drawdown_circuit_breaker_active")
                    if not curve:
                        if any(p["quantity"] > 0 for p in positions.values()):
                            raise ValueError("opening_risk_marks_required")
                        sizing_equity = starting_cash
                        exposure = {sym: n * bars[sym][day] for sym, n in pending_buys.items() if n > 1e-8}
                    else:
                        sizing_equity = curve[-1]["equity"]
                        previous = days[days.index(day) - 1]
                        exposure = {}
                        for sym in set(positions) | set(pending_buys):
                            held = positions.get(sym, {}).get("quantity", 0) + pending_buys[sym]
                            if held > 1e-8:
                                if previous not in bars.get(sym, {}):
                                    raise ValueError("prior_risk_mark_missing:" + sym)
                                exposure[sym] = held * bars[sym][previous]
                    if trade.get("auto_size") is True:
                        if any(not sectors.get(sym) for sym in set(exposure) | {symbol}):
                            raise ValueError("sector_mapping_required")
                        stop = _positive(trade.get("stop"), "trade_stop")
                        capacity = _positive(trade.get("liquidity_quantity_cap"), "liquidity_quantity_cap")
                        if stop >= trade["_price"]:
                            raise ValueError("invalid_stop_geometry")
                        sector_value = sum(v for sym, v in exposure.items() if sectors[sym] == sectors[symbol])
                        price = trade["_price"]
                        fees = trade["_fees"]  # conservative fixed upper bound, not prorated
                        qty = floor(min(qty, capacity, (cash-fees)/price,
                            (sizing_equity*limits["max_position_pct"]-exposure.get(symbol,0))/price,
                            (sizing_equity*limits["max_sector_pct"]-sector_value)/price,
                            (sizing_equity*limits["risk_per_trade_pct"]-fees)/(price-stop)))
                        if qty < 1:
                            raise ValueError("auto_size_no_affordable_quantity")
                        trade["_qty"] = qty
                        gross = qty * price
                        sized_trades.append({"trade_id": trade["trade_id"], "quantity": qty})
                    if len(set(exposure) | {symbol}) > limits.get("max_positions", float("inf")):
                        raise ValueError("max_positions_exceeded")
                    if exposure.get(symbol, 0) + gross > sizing_equity * limits.get("max_position_pct", 1):
                        raise ValueError("position_cap_exceeded")
                    if "max_sector_pct" in limits:
                        if any(not sectors.get(sym) for sym in set(exposure) | {symbol}):
                            raise ValueError("sector_mapping_required")
                        sector_value = sum(v for sym, v in exposure.items() if sectors[sym] == sectors[symbol])
                        if sector_value + gross > sizing_equity * limits["max_sector_pct"]:
                            raise ValueError("sector_cap_exceeded")
                    if "risk_per_trade_pct" in limits:
                        stop = _positive(trade.get("stop"), "trade_stop")
                        if stop >= trade["_price"] or qty * (trade["_price"] - stop) + trade["_fees"] > sizing_equity * limits["risk_per_trade_pct"]:
                            raise ValueError("trade_risk_budget_exceeded")
                debit = gross + trade["_fees"]
                if debit > cash + 1e-8:
                    raise ValueError("insufficient_cash_for_buy:" + trade["trade_id"])
                cash -= debit
                pending_buys[symbol] += qty
                linked_entries[trade["trade_id"]] = {"symbol": symbol, "quantity": qty, "settlement": trade["_settle"], "closed": False, "pending_actions": set()}
                # Shares enter holdings only on settlement date.
            else:
                if trade.get("exit_entry_id") is not None:
                    entry = linked_entries.get(trade["exit_entry_id"])
                    if not entry or entry["symbol"] != symbol or entry["settlement"] > day or entry["closed"]:
                        raise ValueError("linked_exit_entry_unavailable")
                    if entry["pending_actions"]:
                        raise ValueError("linked_exit_pending_corporate_action")
                    if any(a.get("symbol") == symbol for a in corporate_actions or []) and abs(positions.get(symbol, {}).get("quantity", 0) - entry["quantity"]) > 1e-8:
                        raise ValueError("linked_exit_corporate_action_requires_lot_reconciliation")
                    qty = entry["quantity"]
                    gross = qty * trade["_price"]
                    entry["closed"] = True
                pos = positions.setdefault(symbol, {"quantity": 0.0, "cost_basis": 0.0})
                if qty > pos["quantity"] + 1e-8:
                    raise ValueError("sell_exceeds_settled_holdings:" + trade["trade_id"])
                old_qty = pos["quantity"]
                average_cost = pos["cost_basis"] / old_qty if old_qty else 0.0
                pos["quantity"] -= qty
                pos["cost_basis"] -= average_cost * qty
                realized_cost = average_cost * qty
                proceeds = gross - trade["_fees"]
                if proceeds < 0:
                    raise ValueError("negative_sale_proceeds")
                receivables += proceeds
                pending_sales[symbol] += qty
                pending_events[trade["_settle"]].append({"type": "sell_proceeds_settled",
                                                          "trade_id": trade["trade_id"],
                                                          "symbol": symbol, "cash_delta": proceeds, "quantity": qty,
                                                          "source_id": trade["source_id"]})
            executed_trades.append({"allocated_cost": realized_cost if trade["side"] == "SELL" else None, "realized_pnl": proceeds-realized_cost if trade["side"] == "SELL" else None, "trade_id": trade["trade_id"], "signal_id": trade.get("signal_id"), "side": trade["side"], "symbol": symbol, "quantity": qty, "price": trade["_price"], "fees": trade["_fees"], "date": day.isoformat()})
            pending_events[trade["_settle"]].append({"type": "trade_settlement_audit",
                                                      "trade_id": trade["trade_id"], "symbol": symbol,
                                                      "side": trade["side"], "source_id": trade["source_id"]})
        # Credit sell proceeds on settlement date; they are not spendable before this point.
        # Process settlements posted today after today's trades to prevent same-day reuse
        # of proceeds where a caller supplies same-day settlement.
        for event in pending_events.pop(day, []):
            if event["type"] == "sell_proceeds_settled":
                cash += event["cash_delta"]
        # Mark holdings at same-date close; every held symbol needs a point-in-time close.
        market_value = 0.0
        for symbol, pos in positions.items():
            if pos["quantity"] <= 1e-8:
                continue
            if day not in bars.get(symbol, {}):
                raise ValueError("portfolio_mark_missing:" + symbol + ":" + day.isoformat())
            market_value += bars[symbol][day] * pos["quantity"]
        for symbol, qty in pending_buys.items():
            if qty > 1e-8:
                if day not in bars.get(symbol, {}):
                    raise ValueError("pending_buy_mark_missing:" + symbol)
                market_value += qty * bars[symbol][day]
        equity = cash + market_value + receivables + rights_paid
        if equity <= 0:
            raise ValueError("nonpositive_portfolio_equity")
        peak_equity = max(peak_equity or equity, equity, starting_cash)
        drawdown = (peak_equity - equity) / peak_equity
        if "max_drawdown_pct" in limits and drawdown >= limits["max_drawdown_pct"]:
            circuit_breaker = True
        curve.append({"drawdown_pct": drawdown * 100, "date": day.isoformat(), "cash": round(cash, 8),
                      "market_value": round(market_value, 8), "sale_receivables": round(receivables, 8), "rights_paid_at_cost": round(rights_paid, 8), "equity": round(equity, 8),
                      "holdings": {s: round(v["quantity"], 8) for s, v in positions.items() if v["quantity"] > 1e-8}})
    # Any pending event effective on/before as_of indicates a missing replay event/session.
    late = [d.isoformat() for d, events in pending_events.items() if events and d <= as_of]
    if late:
        raise ValueError("unprocessed_effective_events:" + ",".join(sorted(late)))
    benchmark = None
    if benchmark_rows is not None:
        if not isinstance(benchmark_rows, list) or len(benchmark_rows) < 2:
            raise ValueError("benchmark_rows_required")
        benchmark_by_day = {}
        prior = None
        for row in benchmark_rows:
            d = _day(row.get("date"), "benchmark_date")
            if prior is not None and d <= prior:
                raise ValueError("benchmark_rows_must_be_unique_and_ordered")
            prior = d
            benchmark_by_day[d.isoformat()] = _positive(row.get("close"), "benchmark_close")
        common = [(x["date"], x["equity"], benchmark_by_day[x["date"]])
                  for x in curve if x["date"] in benchmark_by_day]
        if len(common) < 2:
            raise ValueError("insufficient_common_benchmark_dates")
        portfolio_return = common[-1][1] / common[0][1] - 1
        benchmark_return = common[-1][2] / common[0][2] - 1
        benchmark = {"symbol": benchmark_symbol, "common_date_count": len(common),
                     "first_common_date": common[0][0], "last_common_date": common[-1][0],
                     "portfolio_return_pct": portfolio_return * 100,
                     "benchmark_return_pct": benchmark_return * 100,
                     "excess_return_pct": (portfolio_return - benchmark_return) * 100,
                     "classification": "descriptive_exact_common_date_comparison"}
    return {
        "status": "completed_with_limitations",
        "classification": "caller_attested_transaction_and_corporate_action_research_ledger",
        "methodology_version": "p4.48_unified_portfolio_event_engine_v1",
        "as_of_date": as_of.isoformat(), "initial_cash": starting_cash,
        "ending_equity": curve[-1]["equity"], "equity_curve": curve,
        "benchmark_comparison": benchmark,
        "ending_cost_basis": {s: v["cost_basis"] for s,v in positions.items() if v["quantity"] > 1e-8},
        "sized_trades": sized_trades,
        "executed_trade_scenarios": executed_trades,
        "risk_limits": limits, "circuit_breaker_triggered": circuit_breaker,
        "corporate_action_entitlements": [
            {"action_id": aid, "symbol": v["symbol"], "record_date": v["action"].get("record_date"),
             "entitlement_quantity": v.get("quantity"), "source_id": v["source_id"]}
            for aid, v in entitlement_by_action.items() if "quantity" in v
        ],
        "corporate_action_audit": audit,
        "trade_count": len(seen_trade), "corporate_action_count": len(seen_action),
        "limitations": [
            "Trade, settlement, entitlement and corporate-action evidence is caller supplied and not independently verified against NEPSE/CDSC/custodian records.",
            "Initial holdings must be a reconciled opening snapshot; transactions before the first supplied session are outside this replay.",
            "Buy shares enter holdings on supplied settlement date; sale proceeds become spendable cash on supplied settlement date.",
            "Corporate-action entitlement is calculated from settled holdings at the supplied record date; record-date/ex-date eligibility conventions must be confirmed against official event terms.",
            "Record-date overlap with unsettled sales (including same-day settlement before custody confirmation) is rejected rather than guessing entitlement.",
            "Rights subscribed quantity and allotment/listing are caller supplied; no default election is inferred.",
            "Split ratio is new shares per old share; effective-date conversion preserves total cost basis. Overlapping unsettled buys or same-day trades and fractional shares are rejected.",
            "Paid unlisted rights are carried at subscription cost, not fair value; unpaid entitlements are not valued.",
            "Taxes, fractional cash-in-lieu, renunciation, oversubscription, failed allotment, interest and financing are not modeled.",
            "Marks use supplied close prices, not verified executable fills; benchmark excess is descriptive, not evidence of alpha.",
            "Auto-sizing uses caller-attested liquidity caps and fixed upper-bound fees; sell quantities must match resulting holdings. Not an order generator.",
            "Research only; no broker order routing or production eligibility."
        ],
        "production_eligible": False,
    }
