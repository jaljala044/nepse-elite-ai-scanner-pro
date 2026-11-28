"""Evidence gate for secondary-source OHLCV fallback when NEPSE has no record.

A secondary row can be considered for canonical OHLCV only when the official
absence is evidenced and at least three lineage-independent approved secondary
publishers provide the same complete OHLCV tuple. This is unanimity, not voting.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

ALLOWED_SECONDARY_SOURCES = {"sharehub", "nepsealpha", "chukul", "sharesansar", "sharesansar_archive"}
OHLCV_FIELDS = ("open", "high", "low", "close", "volume")
VALID_ABSENCE_RESULTS = {"200_no_record", "204_no_content", "404_not_found"}


def _valid_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _decimal(value: object, field: str) -> Decimal:
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValueError(f"invalid_{field}") from exc
    if not number.is_finite():
        raise ValueError(f"non_finite_{field}")
    return number


def _row_tuple(values: object) -> tuple[Decimal, ...]:
    if not isinstance(values, dict) or any(field not in values for field in OHLCV_FIELDS):
        raise ValueError("incomplete_ohlcv_tuple")
    numbers = tuple(_decimal(values[field], field) for field in OHLCV_FIELDS)
    opened, high, low, closed, volume = numbers
    if low <= 0 or not low <= min(opened, closed) <= max(opened, closed) <= high:
        raise ValueError("invalid_ohlc_bounds")
    if volume < 0 or volume != volume.to_integral_value():
        raise ValueError("invalid_volume")
    return numbers


def validate_secondary_ohlcv_consensus(consensus: object, *, session_date: str) -> list[str]:
    """Return fail-closed reason codes; [] means the fallback evidence gate passed."""
    reasons: list[str] = []
    if not _valid_iso_date(session_date):
        return ["invalid_target_session_date"]
    if not isinstance(consensus, dict):
        return ["secondary_consensus_missing"]

    absence = consensus.get("official_source_absence")
    required_absence = ("url", "query_string", "retrieved_utc", "http_result",
                        "blocker_class", "owner", "due_date", "session_date")
    if not isinstance(absence, dict) or any(
        not isinstance(absence.get(key), str) or not absence[key].strip()
        for key in required_absence
    ):
        reasons.append("official_absence_evidence_incomplete")
    else:
        parsed_url = urlparse(absence["url"])
        try:
            retrieved = datetime.fromisoformat(absence["retrieved_utc"].replace("Z", "+00:00"))
        except ValueError:
            retrieved = None
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            reasons.append("official_absence_url_invalid")
        if retrieved is None or retrieved.tzinfo is None or retrieved.utcoffset() is None:
            reasons.append("official_absence_retrieval_time_invalid")
        if absence["http_result"] not in VALID_ABSENCE_RESULTS:
            reasons.append("official_source_absence_not_proven")
        if not _valid_iso_date(absence["due_date"]):
            reasons.append("official_absence_due_date_invalid")
        if absence["session_date"] != session_date:
            reasons.append("official_absence_session_mismatch")

    observations = consensus.get("observations")
    if not isinstance(observations, list):
        return sorted(set(reasons + ["secondary_observations_missing"]))
    if len(observations) < 3:
        reasons.append("fewer_than_three_secondary_observations")

    normalized = []
    seen_sources = set()
    for item in observations:
        if not isinstance(item, dict):
            reasons.append("invalid_secondary_observation")
            continue
        source_id = item.get("source_id")
        upstream = item.get("upstream_feed")
        dates = item.get("session_dates")
        if not isinstance(source_id, str) or source_id not in ALLOWED_SECONDARY_SOURCES:
            reasons.append("secondary_source_not_allowlisted")
            continue
        if source_id in seen_sources:
            reasons.append("duplicate_secondary_source")
            continue
        seen_sources.add(source_id)
        if not isinstance(upstream, str) or not upstream.strip():
            reasons.append("upstream_lineage_missing")
            continue
        source_url = item.get("source_url")
        source_hash = item.get("payload_sha256")
        retrieved_at = item.get("retrieved_utc")
        if not isinstance(source_url, str) or urlparse(source_url).scheme != "https" or not urlparse(source_url).netloc:
            reasons.append("secondary_source_url_invalid")
            continue
        if not isinstance(source_hash, str) or len(source_hash) != 64 or any(ch not in "0123456789abcdef" for ch in source_hash.lower()):
            reasons.append("secondary_payload_sha256_invalid")
            continue
        try:
            captured = datetime.fromisoformat(str(retrieved_at).replace("Z", "+00:00"))
        except ValueError:
            captured = None
        if captured is None or captured.tzinfo is None or captured.utcoffset() is None:
            reasons.append("secondary_retrieval_time_invalid")
            continue
        if any(not isinstance(item.get(key), str) or not item[key].strip()
               for key in ("parser_version", "source_revision", "security_id")):
            reasons.append("secondary_source_lineage_metadata_missing")
            continue
        if item.get("session_date") != session_date:
            reasons.append("secondary_target_session_mismatch")
            continue
        if not isinstance(dates, list) or not dates or any(not _valid_iso_date(day) for day in dates):
            reasons.append("invalid_source_session_date_set")
            continue
        date_set = set(dates)
        if len(date_set) != len(dates):
            reasons.append("duplicate_source_session_date")
            continue
        if session_date not in date_set:
            reasons.append("target_session_absent_from_secondary_source")
            continue
        try:
            row = _row_tuple(item.get("ohlcv"))
        except ValueError as exc:
            reasons.append(str(exc))
            continue
        normalized.append({"source_id": source_id, "upstream_feed": upstream,
                           "dates": date_set, "row": row})

    # Collapse providers only when date-set Jaccard overlap is >0.98 and
    # they declare the same upstream feed.
    parent = list(range(len(normalized)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left in range(len(normalized)):
        for right in range(left + 1, len(normalized)):
            a, b = normalized[left], normalized[right]
            union_size = len(a["dates"] | b["dates"])
            overlap = len(a["dates"] & b["dates"]) / union_size if union_size else 0.0
            if overlap > 0.98 and a["upstream_feed"] == b["upstream_feed"]:
                root_a, root_b = find(left), find(right)
                if root_a != root_b:
                    parent[root_b] = root_a

    independent_count = len({find(index) for index in range(len(normalized))})
    if independent_count < 3:
        reasons.append("fewer_than_three_lineage_independent_sources")

    # All observations must agree. No majority selection or silent winner.
    if normalized and len({item["row"] for item in normalized}) != 1:
        reasons.append("secondary_ohlcv_source_conflict")
    if len(normalized) < 3:
        reasons.append("fewer_than_three_valid_secondary_observations")
    return sorted(set(reasons))
