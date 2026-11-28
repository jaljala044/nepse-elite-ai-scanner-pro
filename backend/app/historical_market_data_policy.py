"""Five-year all-equity collection planning and two-source evidence resolution."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.parse import urlparse

PROVIDERS = ("sharehub", "nepsealpha", "chukul", "sharesansar")
REFERENCE_PROVIDERS = ("nepse_official",)
DIAGNOSTIC_PROVIDERS = ("merolagani",)
ALLOWED_EVIDENCE_SOURCES = set(PROVIDERS) | set(REFERENCE_PROVIDERS) | set(DIAGNOSTIC_PROVIDERS)
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
        try:
            start = end.replace(year=end.year - 5)
        except ValueError:
            start = end.replace(year=end.year - 5, day=28)
    except (TypeError, ValueError) as exc:
        raise ValueError("as_of_date must be a valid ISO date") from exc
    return start.isoformat()


def build_five_year_collection_plan(*, as_of_date: str, equities: list[dict],
                                    session_dates: list[str] | None = None) -> dict:
    """Create a coverage plan; it does not claim data was acquired."""
    start = five_year_start(as_of_date)
    if not isinstance(equities, list) or not equities:
        raise ValueError("complete equity universe is required")
    normalized, seen = [], set()
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
    if session_dates is not None:
        if not isinstance(session_dates, list) or any(not isinstance(day, str) for day in session_dates):
            raise ValueError("session_dates must be a list of ISO dates")
        for day in session_dates:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError("session_dates must be zero-padded ISO dates")
        if len(session_dates) != len(set(session_dates)):
            raise ValueError("session_dates must not contain duplicates")
    providers = (*PROVIDERS, *REFERENCE_PROVIDERS)
    return {
        "schema_version": 1, "as_of_date": as_of_date,
        "period_start": start, "period_end": as_of_date,
        "equity_count": len(normalized), "equities": normalized,
        "session_calendar_count": len(session_dates or []),
        "required_collections": [
            {"provider": provider, "data_type": data_type,
             "period_start": start, "period_end": as_of_date,
             "equity_count": len(normalized),
             "role": "reference" if provider in REFERENCE_PROVIDERS else "secondary_collection",
             "status": ("BLOCKED_DEPENDENCY" if data_type == "floorsheet" and not session_dates
                        else "BLOCKED_ACCESS")}
            for provider in providers for data_type in DATA_TYPES
        ],
        "coverage_matrix": [
            {"symbol": equity["symbol"], "security_id": equity["security_id"],
             "provider": provider, "data_type": data_type,
             "period_start": start, "period_end": as_of_date,
             "status": ("BLOCKED_DEPENDENCY" if data_type == "floorsheet" and not session_dates
                        else "BLOCKED_ACCESS")}
            for equity in normalized for provider in providers for data_type in DATA_TYPES
        ],
        "diagnostic_sources": list(DIAGNOSTIC_PROVIDERS),
        "collection_status": "PARTIAL_EVIDENCED",
        "note": "Plan only; raw payloads, rights, per-session coverage and hashes are not asserted.",
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
        mapped = dict(zip(fields, values))
        opened, high, low, close, volume = (
            mapped[key] for key in ("open", "high", "low", "close", "volume")
        )
        if low <= 0 or not low <= min(opened, close) <= max(opened, close) <= high:
            raise ValueError("invalid_ohlc_bounds")
        if volume < 0 or volume != volume.to_integral_value():
            raise ValueError("invalid_volume")
    if record_type == "floorsheet":
        mapped = dict(zip(fields, values))
        if mapped["quantity"] <= 0 or mapped["rate"] <= 0 or mapped["amount"] < 0:
            raise ValueError("invalid_floorsheet_numeric_bounds")
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
    """Resolve exact rows; a matching pair of independent lineages is required.

    Conflicts remain visible. A mismatching observation requires an investigation
    reason and evidence references before the selected pair is COMPLETE_EVIDENCED.
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
            if item.get("source_id") not in ALLOWED_EVIDENCE_SOURCES:
                raise ValueError("source_not_allowlisted")
            if not isinstance(item.get("record"), dict):
                raise ValueError("missing_source_record")
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
        if len(signatures) == 1:
            signature_groups[next(iter(signatures))].append(lineage_index)
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
    fields = FLOORSHEET_FIELDS if record_type == "floorsheet" else CHART_FIELDS
    selected_values = dict(zip(fields, signature))
    cause_map = ({
        "session_date": "session_or_timezone_alignment", "symbol": "security_mapping",
        "open": "price_basis_corporate_action_or_parser",
        "high": "price_basis_corporate_action_or_parser",
        "low": "price_basis_corporate_action_or_parser",
        "close": "price_basis_corporate_action_or_parser",
        "volume": "volume_unit_or_parser",
    } if record_type == "chart" else {
        "trade_date": "trade_date_or_session_alignment",
        "contract_id": "contract_identity_or_duplicate", "symbol": "security_mapping",
        "buyer_broker_code": "broker_code_mapping", "seller_broker_code": "broker_code_mapping",
        "quantity": "quantity_unit_or_parser", "rate": "price_rounding_or_parser",
        "amount": "gross_amount_or_rounding",
    })
    conflicts = []
    for item in valid:
        if item["signature"] == signature:
            continue
        differing = [field for field in fields
                     if str(_canonical(item["record"].get(field))) != selected_values[field]]
        conflicts.append({
            "source_id": item["source_id"], "record": item["record"],
            "differing_fields": differing,
            "possible_causes": sorted({cause_map[field] for field in differing}),
        })
    investigation = mismatch_investigation or {}
    investigation_complete = (
        isinstance(investigation.get("reason"), str) and investigation["reason"].strip()
        and isinstance(investigation.get("evidence_refs"), list)
        and bool(investigation["evidence_refs"])
    )
    status = "COMPLETE_EVIDENCED" if not conflicts or investigation_complete else "PARTIAL_EVIDENCED"
    return {
        "status": status, "record_key": record_key, "selected_record": selected,
        "selected_source_ids": sorted({valid[index]["source_id"] for index in selected_indices}),
        "matching_lineage_count": len(groups),
        "lineage_independent_source_count": len(lineages),
        "conflicts": conflicts,
        "mismatch_investigation": investigation if conflicts else None,
        "reason_codes": (["two_independent_sources_match"] if not conflicts else
                         ["two_independent_sources_match",
                          "source_mismatch_investigation_recorded" if investigation_complete
                          else "source_mismatch_investigation_required"]),
        "source_observations": observations,
        "canonical_candidate": status == "COMPLETE_EVIDENCED",
        "promotion": "BLOCKED",
    }
