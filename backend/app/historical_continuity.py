"""Fail-closed historical segment preflight; not a canonical promotion authority."""
from datetime import date
from collections import Counter
from decimal import Decimal, InvalidOperation

def review_segment(symbol, start, end, calendar, lifecycle, rows, *, minimum_bars=120, warmup=0):
    """Inputs must be server-reviewed evidence. Every calendar day is classified.
    No-trade days are not candles; lifecycle breaks require separate segments.
    This function never authorizes canonical promotion.
    """
    from datetime import timedelta
    lo, hi = date.fromisoformat(start), date.fromisoformat(end)
    if lo > hi or minimum_bars < 1 or warmup < 0:
        raise ValueError("invalid segment bounds or bar requirement")
    reasons = []
    counts = Counter()
    by_day = {}
    for row in rows:
        day = date.fromisoformat(row["date"])
        if not lo <= day <= hi:
            reasons.append(f"{day}:outside_segment")
            continue
        if day in by_day:
            reasons.append(f"{day}:duplicate")
        by_day[day] = row
    identities, bases = set(), set()
    day = lo
    while day <= hi:
        key = day.isoformat()
        c, l, row = calendar.get(key, {}), lifecycle.get(key, {}), by_day.get(day)
        status = c.get("status")
        if not c.get("evidence_id") or status not in {"verified_open", "verified_exceptional_open", "verified_closed"}:
            reasons.append(f"{key}:calendar_unverified")
        elif status == "verified_closed":
            counts["closed"] += 1
            if row is not None:
                reasons.append(f"{key}:closed_day_candle")
        elif not l.get("evidence_id") or l.get("instrument_type") != "equity" or not l.get("security_id") or l.get("symbol") != symbol:
            reasons.append(f"{key}:lifecycle_unverified")
        elif l.get("status") != "active" or l.get("boundary") is not False:
            reasons.append(f"{key}:lifecycle_break_or_unknown")
        else:
            identities.add(l["security_id"])
            if row is None:
                if l.get("no_trade_evidence_id"):
                    counts["verified_no_trade"] += 1
                else:
                    reasons.append(f"{key}:missing_or_unverified_no_trade")
            else:
                try:
                    o,h,low,cl,v = (Decimal(str(row[k])) for k in ("open","high","low","close","volume"))
                    valid = all(x.is_finite() for x in (o,h,low,cl,v)) and 0 < low <= min(o,cl) <= max(o,cl) <= h and v > 0 and v == v.to_integral_value()
                except (KeyError, InvalidOperation, TypeError, ValueError):
                    valid = False
                if not valid:
                    reasons.append(f"{key}:invalid_ohlcv")
                elif (row.get("symbol") != symbol or row.get("security_id") != l["security_id"]
                      or not row.get("evidence_id") or not row.get("price_basis")
                      or row.get("canonical_promotion_allowed") is not True):
                    reasons.append(f"{key}:row_not_reviewed")
                else:
                    bases.add(row["price_basis"])
                    counts["reviewed_bars"] += 1
        day += timedelta(days=1)
    if len(identities) > 1 or len(bases) > 1:
        reasons.append("identity_or_price_basis_changed")
    if counts["reviewed_bars"] < minimum_bars + warmup:
        reasons.append("insufficient_reviewed_bars")
    return {"symbol": symbol, "start": start, "end": end, "counts": dict(counts),
            "reasons": reasons, "continuity_preflight_passed": not reasons,
            "canonical_promotion_allowed": False, "backtest_promotion_allowed": False}
