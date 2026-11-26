"""Corporate-action portfolio ledger using reconciled entitlement quantities.

The caller must provide verified, custody-reconciled entitlement quantities. This
module never infers ownership from OHLCV or assumes automatic rights subscription.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime


def _date(value, field):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ValueError("invalid_" + field) from None


def _number(value, field, allow_zero=False):
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("invalid_" + field) from None
    if result != result or result in (float("inf"), float("-inf")):
        raise ValueError("invalid_" + field)
    if result < 0 or (result == 0 and not allow_zero):
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


def apply_corporate_actions_to_portfolio(*, holdings, cash, actions, as_of_date, evidence_cutoff):
    """Replay verified corporate-action entitlements against a supplied holdings snapshot.

    Holdings: {SYMBOL: {quantity, average_cost}}. Entitlement quantity must be
    explicit and custody-reconciled in each action. Bonus/split shares are
    credited on listing_date. Rights are subscribed only for subscribed_quantity,
    debited on subscription_payment_date, and credited on listing_date. Dividends
    are credited on payment_date. All resulting events must be effective by as_of.
    """
    as_of = _date(as_of_date, "as_of_date")
    try:
        cutoff = datetime.fromisoformat(str(evidence_cutoff).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("evidence_cutoff_invalid") from None
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        raise ValueError("evidence_cutoff_timezone_required")
    if not isinstance(holdings, dict) or not holdings:
        raise ValueError("holdings_required")
    balance = _number(cash, "cash", allow_zero=True)
    positions = {}
    for symbol, holding in holdings.items():
        if not isinstance(symbol, str) or not symbol.strip() or not isinstance(holding, dict):
            raise ValueError("holding_record_invalid")
        quantity = _number(holding.get("quantity"), "holding_quantity")
        cost = _number(holding.get("average_cost"), "holding_average_cost")
        positions[symbol] = {"quantity": quantity, "average_cost": cost,
                             "cost_basis": quantity * cost}
    events = []
    prepared = []
    seen = set()
    for action in actions or []:
        if not isinstance(action, dict):
            raise ValueError("corporate_action_record_invalid")
        _verify(action, cutoff)
        action_id = action.get("action_id")
        if not isinstance(action_id, str) or not action_id.strip() or action_id in seen:
            raise ValueError("corporate_action_id_missing_or_duplicate")
        seen.add(action_id)
        symbol = action.get("symbol")
        if symbol not in positions:
            raise ValueError("corporate_action_symbol_not_in_holdings")
        entitlement = _number(action.get("entitlement_quantity"), "entitlement_quantity", allow_zero=True)
        kind = action.get("action_type")
        if kind in ("bonus", "split"):
            ratio = _number(action.get("ratio"), "ratio")
            effective = _date(action.get("listing_date"), "listing_date")
            prepared.append((effective, action, entitlement * ratio, 0.0))
        elif kind == "dividend":
            rate = _number(action.get("cash_per_share"), "cash_per_share", allow_zero=True)
            effective = _date(action.get("payment_date"), "payment_date")
            prepared.append((effective, action, 0.0, entitlement * rate))
        elif kind == "rights":
            subscribed = _number(action.get("subscribed_quantity"), "subscribed_quantity", allow_zero=True)
            if subscribed > entitlement:
                raise ValueError("rights_subscription_exceeds_entitlement")
            price = _number(action.get("subscription_price"), "subscription_price")
            payment_date = _date(action.get("subscription_payment_date"), "subscription_payment_date")
            listing_date = _date(action.get("listing_date"), "listing_date")
            if payment_date > as_of and listing_date <= as_of:
                raise ValueError("rights_listing_precedes_subscription_payment")
            prepared.append((payment_date, action, 0.0, -subscribed * price))
            prepared.append((listing_date, action, subscribed, 0.0))
        else:
            raise ValueError("unsupported_portfolio_action_type")
    prepared.sort(key=lambda item: (item[0], item[1]["action_id"], item[1]["action_type"]))
    for effective, action, share_delta, cash_delta in prepared:
        if effective > as_of:
            continue
        symbol = action["symbol"]
        position = positions[symbol]
        if float(action["entitlement_quantity"]) > position["quantity"]:
            raise ValueError("entitlement_exceeds_reconciled_holding_at_event")
        if cash_delta < 0 and balance + cash_delta < -1e-8:
            raise ValueError("insufficient_cash_for_rights_subscription")
        balance += cash_delta
        if share_delta:
            if action["action_type"] in ("bonus", "split"):
                # Preserve aggregate cost basis; new shares reduce average cost.
                position["quantity"] += share_delta
                position["average_cost"] = position["cost_basis"] / position["quantity"]
            elif action["action_type"] == "rights":
                position["quantity"] += share_delta
                position["cost_basis"] += share_delta * float(action["subscription_price"])
                position["average_cost"] = position["cost_basis"] / position["quantity"]
        event_type = {
            "bonus": "bonus_shares_credited",
            "split": "split_shares_credited",
            "dividend": "dividend_cash_credited",
            "rights": "rights_subscription_cash_debited" if cash_delta < 0 else "rights_shares_credited",
        }[action["action_type"]]
        events.append({"action_id": action["action_id"], "symbol": symbol,
                       "action_type": action["action_type"], "event_type": event_type,
                       "effective_date": effective.isoformat(),
                       "share_delta": share_delta, "cash_delta": cash_delta,
                       "source_id": action["source_id"],
                       "classification": "caller_attested_custody_reconciled_entitlement"})
    return {
        "status": "ledger_applied_with_limitations",
        "as_of_date": as_of.isoformat(),
        "cash": round(balance, 8),
        "holdings": {
            symbol: {"quantity": round(value["quantity"], 8),
                     "average_cost": round(value["average_cost"], 8),
                     "cost_basis": round(value["cost_basis"], 8)}
            for symbol, value in positions.items()
        },
        "events": events,
        "event_count": len(events),
        "classification": "research_corporate_action_ledger_not_custodian_statement",
        "limitations": [
            "Entitlement quantities and corporate-action terms are caller supplied and must be reconciled to CDSC/custodian records.",
            "No record-date ownership is inferred; holdings must represent the entitlement snapshot.",
            "Rights subscription is applied only to explicit subscribed_quantity; no default election is assumed.",
            "Bonus/split listing, rights payment/listing and dividend payment dates are caller supplied.",
            "Tax, withholding, fractional-share cash-in-lieu, renunciation, oversubscription and failed allotments are not modeled.",
            "Events are replayed from the supplied holdings snapshot; this is not a complete transaction-level custody ledger."
        ],
        "production_eligible": False,
    }
