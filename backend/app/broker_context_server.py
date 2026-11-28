"""Conservative P4.38 server-owned evidence gate.

The project-accepted archive calendar is not exchange-certified. This gate
therefore refuses to calculate broker/price context until every expected
session is backed by an explicitly verified open/exceptional-open calendar
record available by the decision cutoff.
"""
from pathlib import Path
from datetime import date, timedelta
import json

from .session_calendar import load_calendar, schedule_candidate
from .broker_context_integration import stamp, iso_day, build_context

ROOT = Path(__file__).resolve().parents[2]
OPEN = {"verified_open", "verified_exceptional_open"}
CLOSED = {"verified_closed", "verified_exceptional_closed"}


def unavailable(reason, *, calendar_tier="unknown"):
    return {
        "status": "insufficient_evidence",
        "reason": reason,
        "profiles": [],
        "calendar_tier": calendar_tier,
        "production_eligible": False,
        "signals_enabled": False,
        "source_authentication_performed": False,
    }


def server_context(snapshot, prices, memberships, sector_prices, *, decision_time, expected_sessions):
    cutoff = stamp(decision_time)
    sessions = list(expected_sessions)
    if not 5 <= len(sessions) <= 252:
        raise ValueError("session window must contain 5 to 252 sessions")
    parsed = [iso_day(value, "expected session") for value in sessions]
    if len(set(parsed)) != len(parsed) or parsed != sorted(parsed):
        raise ValueError("invalid sessions")
    local_cutoff = cutoff.astimezone(__import__("zoneinfo").ZoneInfo("Asia/Kathmandu")).date()
    if parsed[-1] > local_cutoff:
        raise ValueError("future session")
    start, end = parsed[0], parsed[-1]
    if (end - start).days > 3660:
        raise ValueError("window too long")

    registry_path = ROOT / "data/reference/p443_equity_quarantine.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    q = {
        (r["symbol"], iso_day(r["date"], "quarantine date").isoformat())
        for r in registry["records"]
    }
    if registry.get("schema_version") != 1 or len(q) != 1329 or len(registry["records"]) != 1329:
        raise ValueError("invalid quarantine registry")

    calendar = load_calendar(ROOT / "data/reference/nepse_session_calendar.csv")
    expected = []
    day = start
    while day <= end:
        row = calendar.get(day)
        if row is not None:
            state = row["status"]
            if state == "project_accepted_open":
                return unavailable("calendar_project_accepted_not_exchange_verified",
                                   calendar_tier="project_accepted_not_exchange_certified")
            if state in OPEN:
                try:
                    verified_at = stamp(row["verified_at_utc"])
                except (KeyError, TypeError, ValueError):
                    return unavailable("calendar_verification_timestamp_missing")
                if verified_at > cutoff:
                    return unavailable("trusted_calendar_incomplete")
                expected.append(day.isoformat())
            elif state in CLOSED:
                pass
            else:
                return unavailable("calendar_status_unrecognized")
        else:
            candidate, _ = schedule_candidate(day)
            if candidate:
                return unavailable("trusted_calendar_candidate_missing")
        day += timedelta(days=1)

    if expected != sessions:
        raise ValueError("client calendar differs from server")
    result = build_context(
        snapshot, prices, memberships, sector_prices,
        decision_time=decision_time, expected_sessions=expected, quarantine_keys=q,
    )
    result["calendar_tier"] = "exchange_verified"
    result["production_eligible"] = False
    result["signals_enabled"] = False
    return result
