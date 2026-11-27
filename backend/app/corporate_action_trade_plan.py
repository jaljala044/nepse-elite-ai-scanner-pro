"""Research-only mechanical price-basis conversion, not execution advice."""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from .unified_portfolio_event_engine import _available

def _number(value):
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid_plan_number") from None
    if not n.is_finite() or n <= 0:
        raise ValueError("invalid_plan_number")
    return n

def _time(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("timezone_required")
    return t

def rebase_trade_plan(*, signal, action, adjustment_time, quantity, cost_basis):
    now = _time(adjustment_time)
    decision = _time(signal["decision_time"])
    _available(action, now, "corporate_action")
    effective = _time(action["price_basis_effective_at"])
    if not decision < effective <= now:
        raise ValueError("action_not_between_decision_and_adjustment")
    if action["symbol"] != signal["symbol"]:
        raise ValueError("action_symbol_mismatch")
    if not action.get("action_id"):
        raise ValueError("action_id_required")
    if action.get("action_type") not in ("bonus", "split"):
        raise ValueError("rights_or_cash_action_requires_separate_valuation")
    factor = _number(action["ratio"])
    if action["action_type"] == "bonus":
        factor += 1
    original = deepcopy(signal)
    adjusted = deepcopy(signal)
    plan = adjusted["details"]["plan"]
    entry, stop = _number(plan["entry"]), _number(plan["stop"])
    targets = [_number(x) for x in plan["targets"]]
    if not stop < entry or not targets or any(t <= entry for t in targets):
        raise ValueError("invalid_long_plan_geometry")
    qty = _number(quantity)
    cost = _number(cost_basis)
    new_qty = qty * factor
    if qty != qty.to_integral_value() or new_qty != new_qty.to_integral_value():
        raise ValueError("fractional_entitlement_requires_evidence")
    plan.update(entry=str(entry/factor), stop=str(stop/factor),
                targets=[str(t/factor) for t in targets])
    return {"original_signal":original, "adjusted_signal":adjusted,
            "action_id":action["action_id"], "source_id":action["source_id"],
            "adjustment_time":now.isoformat(), "factor":str(factor),
            "theoretical_quantity":int(new_qty), "cost_basis":str(cost),
            "theoretical_average_cost":str(cost/new_qty),
            "reward_risk":[str((t-entry)/(entry-stop)) for t in targets],
            "classification":"mechanical_price_basis_research_only",
            "execution_eligible":False,
            "limitations":["Quantity assumes full entitlement; listing and custody not established.",
                           "No tick rounding, fees, tax or market execution confirmation."]}


def rebase_cash_action_plan(*, signal, action, adjustment_time, quantity, cost_basis,
                            available_cash, reference, subscribed_quantity=0):
    """Theoretical additive ex-price adjustment, not an exchange adjustment."""
    now = _time(adjustment_time)
    decision = _time(signal["decision_time"])
    _available(action, now, "corporate_action")
    _available(reference, now, "reference")
    effective = _time(action["price_basis_effective_at"])
    if not decision < effective <= now:
        raise ValueError("action_not_between_decision_and_adjustment")
    if action["symbol"] != signal["symbol"] or reference["symbol"] != signal["symbol"]:
        raise ValueError("action_symbol_mismatch")
    if not action.get("action_id"):
        raise ValueError("action_id_required")
    if not _time(reference["observed_at"]) < effective:
        raise ValueError("reference_must_precede_effective_time")
    if _time(reference["available_at"]) < _time(reference["observed_at"]):
        raise ValueError("reference_availability_precedes_observation")
    def nonnegative(value):
        return Decimal(0) if str(value) in ("0","0.0") else _number(value)
    qty, cost = _number(quantity), _number(cost_basis)
    cash = nonnegative(available_cash)
    subscribed = nonnegative(subscribed_quantity)
    if qty != qty.to_integral_value() or subscribed != subscribed.to_integral_value():
        raise ValueError("whole_share_quantity_required")
    close = _number(reference["close"])
    kind = action["action_type"]
    payment = dividend = Decimal(0)
    if kind == "rights":
        ratio, subscription = _number(action["ratio"]), _number(action["subscription_price"])
        if subscribed > qty * ratio:
            raise ValueError("subscription_exceeds_theoretical_entitlement")
        payment = subscribed * subscription
        if payment > cash:
            raise ValueError("insufficient_subscription_cash")
        ex_price = (close + ratio * subscription) / (1 + ratio)
    elif kind == "cash_dividend":
        if subscribed:
            raise ValueError("subscription_not_applicable")
        per_share = _number(action["cash_per_share"])
        dividend = qty * per_share
        ex_price = close - per_share
    else:
        raise ValueError("unsupported_cash_action")
    if ex_price <= 0:
        raise ValueError("nonpositive_ex_price")
    shift = close - ex_price
    adjusted = deepcopy(signal)
    plan = adjusted["details"]["plan"]
    entry, stop = _number(plan["entry"]), _number(plan["stop"])
    targets = [_number(x) for x in plan["targets"]]
    if not 0 < stop-shift < entry-shift or not targets or any(t <= entry for t in targets):
        raise ValueError("invalid_adjusted_plan_geometry")
    plan.update(entry=str(entry-shift), stop=str(stop-shift),
                targets=[str(t-shift) for t in targets])
    return {"original_signal":deepcopy(signal), "adjusted_signal":adjusted,
            "action_id":action["action_id"], "source_id":action["source_id"],
            "reference_source_id":reference["source_id"],
            "adjustment_time":now.isoformat(), "theoretical_ex_price":str(ex_price),
            "price_shift":str(shift), "subscription_cash":str(payment),
            "gross_dividend_receivable":str(dividend),
            "cash_after_subscription":str(cash-payment),
            "theoretical_quantity":int(qty+subscribed),
            "theoretical_cost_basis":str(cost+payment),
            "theoretical_average_cost":str((cost+payment)/(qty+subscribed)),
            "theoretical_position_value":str((qty+subscribed)*ex_price),
            "reward_risk":[str((t-entry)/(entry-stop)) for t in targets],
            "classification":"theoretical_cash_action_research_only",
            "execution_eligible":False,
            "limitations":["Assumes supplied holdings are entitled; no custody or listing proof.",
                           "Dividend is gross receivable, not spendable cash.",
                           "Additive price shift is a research convention, not official NEPSE adjustment.",
                           "No tax, rights sale value, tick rounding or sector exposure calculation."]}
