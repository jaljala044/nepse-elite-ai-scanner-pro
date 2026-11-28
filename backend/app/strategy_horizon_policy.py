"""Research holding-duration policy, distinct from signal observation windows.

Calendar days are an explicit research convention, not trading-session counts.
Protective exits are never prohibited by minimum planned holding durations.
"""
from datetime import date
from types import MappingProxyType

HOLDING_BANDS = MappingProxyType({"swing": (3, 15), "positional": (14, 56)})
POLICY_VERSION = "calendar-holding-v1"


def _day(value):
    if not isinstance(value, str):
        raise ValueError("canonical_date_required")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("canonical_date_required")
    return parsed


def assess_holding_duration(horizon, entry_date, exit_date, *, protective_exit=False):
    if horizon not in HOLDING_BANDS:
        raise ValueError("unsupported_holding_policy")
    if type(protective_exit) is not bool:
        raise ValueError("protective_exit_boolean_required")
    days = (_day(exit_date) - _day(entry_date)).days
    if days < 0:
        raise ValueError("exit_before_entry")
    lower, upper = HOLDING_BANDS[horizon]
    in_band = lower <= days <= upper
    return {
        "policy_version": POLICY_VERSION,
        "horizon": horizon,
        "unit": "elapsed_calendar_days",
        "minimum_days": lower,
        "maximum_days": upper,
        "holding_days": days,
        "within_planned_band": in_band,
        "duration_status": "within_band" if in_band else
            ("below_minimum" if days < lower else "above_maximum"),
        "protective_exit": protective_exit,
        "duration_policy_allows_exit": in_band or protective_exit,
        "production_eligible": False,
        "settlement_and_execution_verified": False,
    }
