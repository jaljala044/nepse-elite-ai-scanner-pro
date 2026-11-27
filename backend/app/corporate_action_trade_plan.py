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
