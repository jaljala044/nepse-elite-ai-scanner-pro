"""Five-year all-equity collection planning and two-source evidence resolution."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json

PROVIDERS = ("sharehub", "nepsealpha", "chukul", "sharesansar")
DIAGNOSTIC_PROVIDERS = ("merolagani",)
DATA_TYPES = ("floorsheet", "chart")
FLOORSHEET_FIELDS = (
    "trade_date", "contract_id", "symbol", "buyer_broker_code",
    "seller_broker_code", "quantity", "rate", "amount",
)
CHART_FIELDS = ("session_date", "symbol", "open", "high", "low", "close", "volume")
REQUIRED_PROVENANCE = (
    "source_url", "retrieved_utc", "payload_sha256", "parser_version",
    "source_revision", "upstream_feed",
)


def five_year_start(as_of_date: str) -> str:
    try:
        end = date.fromisoformat(as_of_date)
        start = end.replace(year=end.year - 5)
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_date must be a valid ISO date at least five years after year 1") from exc
    return start.isoformat()


def build_five_year_collection_plan(*, as_of_date: str, equities: list[dict]) -> dict:
    """Create a coverage plan; it does not claim data was acquired."""
    start = five_year_start(as_of_date)
    if not isinstance(equities, list) or not equities:
        raise ValueError("complete equity universe is required")
    normalized = []
    seen = set()
    for item in equities:
        if not isinstance(item, dict):
            raise ValueError("each equity must be an object")
        symbol = str(item.get("symbol", "")).strip().upper()
        security_id = str(item.get("security_id", "")).strip()
        if not symbol or not security_id or (symbol, security_id) in seen:
            raise ValueError("each equity requires a unique symbol/security_id pair")
        seen.add((symbol, security_id))
        normalized.append({"symbol": symbol, "security_id": security_id})
    normalized.sort(key=lambda item: (item["symbol"], item["security_id"]))
    return {
        "schema_version": 1,
        "as_of_date": as_of_date,
        "period_start": start,
        "period_end": as_of_date,
        "equity_count": len(normalized),
        "equities": normalized,
        "required_collections": [
            {"provider": provider, "data_type": data_type,
             "period_start": start, "period_end": as_of_date,
             "equity_count": len(normalized), "status": "BLOCKED_ACCESS"}
            for provider in PROVIDERS for data_type in DATA_TYPES
        ],
        "diagnostic_sources": list(DIAGNOSTIC_PROVIDERS),
        "collection_status": "PARTIAL_EVIDENCED",
        "note": "Plan only; source payloads, rights, per-equity coverage and hashes are not asserted.",
    }


def _canonical(value):
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError("invalid_numeric_value") from exc
        if not number.is_finite():
            raise ValueError("non_finite_numeric_value")
        return format(number.normalize(), "f")
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def _signature(record_type: str, record: dict) -> tuple:
    fields = FLOORSHEET_FIELDS if record_type == "floorsheet" else CHART_FIELDS
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValueError("missing_record_fields:" + ",".join(missing))
    values = []
    for field in fields:
        value = _canonical(record[field])
        if field in {"quantity", "rate", "amount", "open", "high", "low", "close", "volume"}:
            try:
                value = Decimal(str(value))
            except InvalidOperation as exc:
                raise ValueError("invalid_numeric_field:" + field) from exc
            if not value.is_finite():
                raise ValueError("non_finite_numeric_field:" + field)
        values.append(value)
    if record_type == "chart":
        opened, high, low, close, volume = (
            dict(zip(fields, values))[key] for key in ("open", "high", "low", "close", "volume")
        )
        if low <= 0 or not low <= min(opened, close) <= max(opened, close) <= high:
            raise ValueError("invalid_ohlc_bounds")
        if volume < 0 or volume != volume.to_integral_value():
            raise ValueError("invalid_volume")
    return tuple(str(value) for value in values)


def _lineage_groups(valid: list[dict]) -> list[list[int]]:
    parent = list(range(len(valid)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left in range(len(valid)):
        for right in range(left + 1, len(valid)):
            a, b = valid[left], valid[right]
            union = a["session_dates"] | b["session_dates"]
            overlap = len(a["session_dates"] & b["session_dates"]) / len(union) if union else 0
            if overlap > 0.98 and a["upstream_feed"] == b["upstream_feed"]:
                root_a, root_b = find(left), find(right)
                if root_a != root_b:
                    parent[root_b] = root_a
    groups = defaultdict(list)
    for index in range(len(valid)):
        groups[find(index)].append(index)
    return list(groups.values())


def resolve_record_by_two_source_match(
    *, record_type: str, record_key: str, observations: list[dict],
    mismatch_investigation: dict | None = None,
) -> dict:
    """Resolve exact row observations; a matching independent pair is required.

    A mismatch is never majority-voted. All observations are retained, and an
    investigation record is required before a conflicting pair can be marked
    COMPLETE_EVIDENCED.
    """
    if record_type not in DATA_TYPES:
        raise ValueError("record_type must be floorsheet or chart")
    if not isinstance(record_key, str) or not record_key.strip():
        raise ValueError("record_key is required")
    if not isinstance(observations, list) or len(observations) < 2:
        return {"status": "PARTIAL_EVIDENCED", "record_key": record_key,
                "selected_record": None, "reason_codes": ["fewer_than_two_observations"],
                "promotion": "BLOCKED"}
    valid, rejected = [], []
    for item in observations:
        try:
            if not isinstance(item, dict):
                raise ValueError("observation_not_object")
            for field in REQUIRED_PROVENANCE:
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError("missing_provenance:" + field)
            digest = item["payload_sha256"].lower()
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("invalid_payload_sha256")
            dates = item.get("session_dates")
            if not isinstance(dates, list) or not dates:
                raise ValueError("missing_source_session_dates")
            date_set = set(dates)
            if len(date_set) != len(dates):
                raise ValueError("duplicate_source_session_dates")
            for day in date_set:
                date.fromisoformat(day)
            if not item.get("source_id") or not item.get("record"):
                raise ValueError("missing_source_or_record")
            sig = _signature(record_type, item["record"])
            valid.append({
                "source_id": item["source_id"], "upstream_feed": item["upstream_feed"],
                "session_dates": date_set, "signature": sig,
                "record": item["record"], "source_url": item["source_url"],
                "payload_sha256": digest,
            })
        except (ValueError, TypeError, KeyError) as exc:
            rejected.append({"source_id": item.get("source_id") if isinstance(item, dict) else None,
                             "reason": str(exc)})

    lineages = _lineage_groups(valid)
    signature_groups = defaultdict(list)
    for lineage_index, members in enumerate(lineages):
        signatures = {valid[index]["signature"] for index in members}
        # Conflicting rows within one upstream lineage cannot create a vote.
        if len(signatures) != 1:
            continue
        signature = next(iter(signatures))
        signature_groups[signature].append(lineage_index)

    qualifying = [(signature, groups) for signature, groups in signature_groups.items()
                  if len(groups) >= 2]
    if len(qualifying) != 1:
        reasons = ["no_unique_two_lineage_independent_match"]
        if len(qualifying) > 1:
            reasons.append("multiple_competing_two_source_matches")
        if rejected:
            reasons.append("invalid_source_observations")
        return {
            "status": "PARTIAL_EVIDENCED", "record_key": record_key,
            "selected_record": None, "reason_codes": reasons,
            "rejected_observations": rejected,
            "lineage_independent_source_count": len(lineages),
            "source_observations": observations, "promotion": "BLOCKED",
        }

    signature, groups = qualifying[0]
    selected_lineages = [lineages[index] for index in groups]
    selected_indices = [index for group in selected_lineages for index in group]
    selected = valid[selected_indices[0]]["record"]
    conflicts = [
        {"source_id": item["source_id"], "record": item["record"],
         "reason": "field_values_differ_from_two_source_match"}
        for index, item in enumerate(valid) if item["signature"] != signature
    ]
    investigation = mismatch_investigation or {}
    investigation_complete = (
        isinstance(investigation.get("reason"), str) and investigation["reason"].strip()
        and isinstance(investigation.get("evidence_refs"), list)
        and len(investigation["evidence_refs"]) > 0
    )
    status = "COMPLETE_EVIDENCED" if not conflicts or investigation_complete else "PARTIAL_EVIDENCED"
    return {
        "status": status, "record_key": record_key,
        "selected_record": selected,
        "selected_source_ids": sorted({valid[index]["source_id"] for index in selected_indices}),
        "matching_lineage_count": len(groups),
        "lineage_independent_source_count": len(lineages),
        "conflicts": conflicts,
        "mismatch_investigation": investigation if conflicts else None,
        "reason_codes": (["two_independent_sources_match"] if not conflicts else
                         ["two_independent_sources_match", "source_mismatch_investigation_recorded"
                          if investigation_complete else "source_mismatch_investigation_required"]),
        "source_observations": observations,
        "canonical_candidate": status == "COMPLETE_EVIDENCED",
        "promotion": "BLOCKED",
    }
