"""Read-only liquidity evidence; never promote archive or upload rows."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
from .scanner_eligibility import assess, OPEN
from .session_calendar import load_calendar

CALENDAR = Path(__file__).resolve().parents[2] / "data/reference/nepse_session_calendar.csv"
CLOSED = {"verified_closed", "verified_exceptional_closed"}


def portfolio_volume(symbol, as_of, reviewed, calendar, decision_time, count=20):
    base = {"symbol": symbol, "as_of": str(as_of), "status": "unavailable",
            "average_daily_quantity": None, "rows": [], "production_eligible": False}
    def unavailable(reason):
        return dict(base, reason=reason)
    if not 1 <= count <= 252:
        return unavailable("invalid_window")
    days = []
    day = as_of
    cutoff = datetime.fromisoformat(decision_time.replace("Z", "+00:00"))
    if cutoff.tzinfo is None or as_of > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date():
        return unavailable("future_or_invalid_cutoff")
    for _ in range(800):
        item = calendar.get(day, {})
        if item.get("status") not in OPEN | CLOSED:
            return unavailable("calendar_gap_or_unverified")
        try:
            verified = datetime.fromisoformat(item["verified_at_utc"].replace("Z", "+00:00"))
            if verified.tzinfo is None or verified > cutoff:
                return unavailable("calendar_not_available")
        except (KeyError, ValueError, TypeError):
            return unavailable("calendar_not_available")
        if item.get("scope") not in ("all_securities", "*"):
            return unavailable("calendar_scope_unverified")
        if item["status"] in OPEN:
            days.append(day.isoformat())
            if len(days) == count:
                break
        day -= timedelta(days=1)
    if len(days) != count:
        return unavailable("insufficient_calendar")
    rows = []
    identities = set()
    for session in reversed(days):
        record = reviewed.get((symbol, session))
        if not record or record.get("canonical_promotion_allowed") is not True:
            return unavailable("canonical_record_missing")
        if record.get("finality_status") != "final":
            return unavailable("finality_unverified")
        if assess(symbol, [record], decision_time, reviewed):
            return unavailable("canonical_evidence_rejected")
        identities.add(record["security_id"])
        try:
            quantity = Decimal(str(record["volume"]))
            if not quantity.is_finite() or quantity < 0 or quantity != quantity.to_integral_value() or quantity > 9223372036854775807:
                return unavailable("invalid_quantity")
        except (InvalidOperation, KeyError, ValueError):
            return unavailable("invalid_quantity")
        rows.append({"symbol": symbol, "session_date": session, "quantity": int(quantity),
                     "source_id": record["source_id"], "source_payload_sha256": record["source_payload_sha256"],
                     "source_validation_status": "verified", "finality_status": "final"})
    if len(identities) != 1:
        return unavailable("security_identity_changed")
    average = sum(Decimal(r["quantity"]) for r in rows) / Decimal(count)
    return dict(base, status="research_only", rows=rows, average_daily_quantity=str(average),
                session_count=count)


def load_portfolio_volume(symbol, as_of, reviewed):
    try:
        calendar = load_calendar(CALENDAR)
    except (OSError, ValueError, TypeError):
        calendar = {}
    now = datetime.now(timezone.utc)
    return portfolio_volume(symbol, as_of, reviewed, calendar, now.isoformat())
