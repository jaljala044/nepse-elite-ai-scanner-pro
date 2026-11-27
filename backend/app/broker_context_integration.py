"""P4.38 research-only broker/price/sector context. No execution or signal authority."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from hashlib import sha256
import json

VERSION = "p438.1"
POLICY = "complete_source_sessions_only_no_zero_filling_for_missing_sessions_point_in_time_descriptive_only"


def stamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed


def iso_day(value, field):
    try:
        parsed = date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != str(value):
        raise ValueError(f"{field} must use canonical YYYY-MM-DD")
    return parsed


def number(value, positive=False):
    result = Decimal(str(value))
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError("invalid numeric")
    return result


def evidence(row, cutoff, day):
    digest = row["source_payload_sha256"]
    return (
        row.get("status") == "verified"
        and bool(row.get("source_id"))
        and len(digest) == 64
        and all(char in "0123456789abcdef" for char in digest.lower())
        and stamp(row["available_at"]) <= cutoff
        and iso_day(day, "session_date")
        <= cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date()
    )


def build_context(snapshot, prices, memberships, sector_prices, *, decision_time, expected_sessions, quarantine_keys):
    """Caller-supplied research evidence; this module does not authenticate sources."""
    cutoff = stamp(decision_time)
    sessions = list(expected_sessions)
    parsed_sessions = [iso_day(day, "expected session") for day in sessions]
    if len(sessions) < 5 or len(set(sessions)) != len(sessions) or sessions != sorted(sessions):
        raise ValueError("invalid session window")
    if any(day.isoformat() != raw for day, raw in zip(parsed_sessions, sessions)):
        raise ValueError("invalid session window")
    if parsed_sessions[-1] > cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date():
        raise ValueError("future session")
    if snapshot.get("policy") != POLICY or stamp(snapshot["as_of_timestamp"]) > cutoff or snapshot["as_of_date"] != sessions[-1]:
        raise ValueError("invalid profile cutoff")

    # Validate all effective-dated intervals before matching any session.
    for membership in memberships:
        start = iso_day(membership["effective_from"], "membership effective_from")
        end_value = membership.get("effective_to")
        end = iso_day(end_value, "membership effective_to") if end_value is not None else None
        if end is not None and end < start:
            raise ValueError("membership effective_to precedes effective_from")

    quarantine = set(tuple(item) for item in quarantine_keys)

    def indexed(rows, fields):
        result = {}
        for row in rows:
            key = tuple(row[field] for field in fields)
            if key in result:
                raise ValueError("duplicate evidence key")
            result[key] = row
        return result

    price_index = indexed(prices, ("security_id", "session_date"))
    sector_index = indexed(sector_prices, ("sector_code", "session_date"))
    groups = {}
    for profile in snapshot["profiles"]:
        if profile.get("requested_sessions") != len(sessions):
            continue
        key = (profile["security_id"], profile["broker_id"])
        if key in groups:
            raise ValueError("duplicate broker profile")
        groups[key] = profile

    result = []
    for (security_id, broker_id), profile in sorted(groups.items()):
        base = {
            "security_id": security_id, "broker_id": broker_id,
            "status": "insufficient_evidence", "classification": "UNKNOWN",
            "production_eligible": False, "score_eligible": False,
        }
        try:
            daily = profile["daily"]
            if (
                profile["status"] != "descriptive_only"
                or number(profile["coverage_ratio"]) != 1
                or profile["expected_sessions"] != len(sessions)
                or profile["complete_source_sessions"] != len(sessions)
                or [item["session_date"] for item in daily] != sessions
            ):
                raise ValueError("incomplete broker window")

            bars, sectors, symbols = [], [], []
            for day in sessions:
                price = price_index[(security_id, day)]
                if not evidence(price, cutoff, day):
                    raise ValueError("unverified price evidence")
                symbol = price["symbol"].upper()
                if any(item[0] == symbol and sessions[0] <= item[1] <= sessions[-1] for item in quarantine):
                    raise ValueError("historical quarantine")

                matching = []
                for membership in memberships:
                    if membership["security_id"] != security_id or membership["symbol"].upper() != symbol:
                        continue
                    start = membership["effective_from"]
                    end = membership.get("effective_to")
                    if start <= day and (end is None or day <= end):
                        matching.append(membership)
                if len(matching) != 1 or not evidence(matching[0], cutoff, day):
                    raise ValueError("missing or ambiguous sector membership")
                sector_code = matching[0]["sector_code"]
                sector_price = sector_index[(sector_code, day)]
                if not evidence(sector_price, cutoff, day):
                    raise ValueError("unverified sector evidence")

                opening, high, low, close, volume = [
                    number(price[field], True) for field in ("open", "high", "low", "close", "volume")
                ]
                if low > min(opening, close) or high < max(opening, close) or volume != volume.to_integral_value():
                    raise ValueError("invalid OHLCV")
                bars.append((close, volume))
                sectors.append((sector_code, number(sector_price["close"], True)))
                symbols.append(symbol)

            if len(set(symbols)) != 1 or len({item[0] for item in sectors}) != 1:
                raise ValueError("identity or sector changed within window")
            buys = [number(item["buy_amount"]) for item in daily]
            sells = [number(item["sell_amount"]) for item in daily]
            net = [buy - sell for buy, sell in zip(buys, sells)]
            gross = sum(buys) + sum(sells)
            if gross <= 0:
                raise ValueError("no broker activity")
            participation = [number(item["broker_participation"]) for item in daily]
            if any(value > 1 for value in participation):
                raise ValueError("invalid participation")
            for item, buy, sell in zip(daily, buys, sells):
                if Decimal(str(item["net_amount"])) != buy - sell or number(item["gross_amount"]) != buy + sell:
                    raise ValueError("daily accounting mismatch")
            if number(profile["buy_amount"]) != sum(buys) or number(profile["sell_amount"]) != sum(sells):
                raise ValueError("profile accounting mismatch")

            positive_ratio = Decimal(sum(value > 0 for value in net)) / len(net)
            negative_ratio = Decimal(sum(value < 0 for value in net)) / len(net)
            price_return = bars[-1][0] / bars[0][0] - 1
            relative_return = price_return - (sectors[-1][1] / sectors[0][1] - 1)
            volume_ratio = bars[-1][1] / (sum(item[1] for item in bars[:-1]) / Decimal(len(bars) - 1))
            classification = "mixed_flow"
            if sum(net) > 0 and positive_ratio >= Decimal(".6") and price_return > 0 and relative_return > 0 and volume_ratio >= 1:
                classification = "accumulation_research_candidate"
            elif sum(net) < 0 and negative_ratio >= Decimal(".6") and price_return < 0 and relative_return < 0 and volume_ratio >= 1:
                classification = "distribution_research_candidate"

            base.update(
                status="descriptive_only", classification=classification, symbol=symbols[0],
                sector_code=sectors[0][0], net_amount=str(sum(net)),
                gross_broker_side_amount=str(gross), positive_session_ratio=str(positive_ratio),
                negative_session_ratio=str(negative_ratio),
                mean_participation=str(sum(participation) / len(participation)),
                peak_participation=str(max(participation)), price_return=str(price_return),
                sector_relative_return=str(relative_return), latest_volume_ratio=str(volume_ratio),
                sessions=sessions, source_authentication_performed=False,
            )
        except (KeyError, ValueError, TypeError, InvalidOperation, ArithmeticError, AttributeError) as exc:
            base["reason"] = str(exc)
        result.append(base)

    return {
        "methodology_version": VERSION, "decision_time": decision_time, "profiles": result,
        "status": "descriptive_only" if any(item["status"] == "descriptive_only" for item in result) else "insufficient_evidence",
        "reason": None if any(item["status"] == "descriptive_only" for item in result) else "no_eligible_profiles",
        "production_eligible": False, "signals_enabled": False, "source_authentication_performed": False,
        "input_sha256": sha256(json.dumps(
            [snapshot, prices, memberships, sector_prices, sessions, sorted(quarantine)],
            sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest(),
        "limitations": "Caller-supplied evidence and calendar are not independently authenticated; input digest is not source-byte provenance; broker codes are execution channels, not ownership; thresholds are uncalibrated research heuristics.",
    }
