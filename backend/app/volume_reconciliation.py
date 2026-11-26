"""Read-only volume observations; no source is silently substituted."""
from decimal import Decimal, InvalidOperation
from datetime import date

def _volume(value):
    if value is None or value == "":
        return None
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid volume") from exc
    if not n.is_finite() or n < 0 or n != n.to_integral_value():
        raise ValueError("volume must be a nonnegative integer")
    return int(n)

def reconcile_volume(symbol, day, *, chart_volume=None, floorsheet_volume=None,
                     chart_evidence=None, floorsheet_evidence=None,
                     corroborated_volume=None, corroboration_evidence=None):
    """Evidence pointers are caller-supplied; this function does not authenticate them."""
    if not symbol or symbol != symbol.strip().upper():
        raise ValueError("invalid symbol")
    day = date.fromisoformat(day).isoformat()
    chart, floor, external = map(_volume, (chart_volume, floorsheet_volume, corroborated_volume))
    for value, evidence in ((chart, chart_evidence), (floor, floorsheet_evidence), (external, corroboration_evidence)):
        if value is not None and (not isinstance(evidence, str) or not evidence.strip()):
            raise ValueError("volume evidence required")
    delta = floor - chart if chart is not None and floor is not None else None
    if chart is None or floor is None:
        status = "missing_observation"
    elif delta != 0:
        status = "volume_conflict"
    else:
        status = "numeric_match"
    return dict(symbol=symbol, date=day, chart_volume=chart, floorsheet_volume=floor,
                corroborated_volume=external, verified_market_volume=None,
                chart_evidence=chart_evidence, floorsheet_evidence=floorsheet_evidence,
                corroboration_evidence=corroboration_evidence,
                volume_difference=delta, reconciliation_status=status,
                external_matches_floorsheet=(external == floor if external is not None and floor is not None else None),
                canonical_promotion_allowed=False, backtest_promotion_allowed=False)
