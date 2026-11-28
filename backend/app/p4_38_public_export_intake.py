"""Steps 130-139: public-page/manual-export evidence intake without paid API access.

This module consumes user/provider-exported CSV or JSON rows. It does not scrape,
authenticate to, or bypass subscription-only services. Every import is research-only
until independent coverage, identity, calendar and quality gates are satisfied.
"""
from __future__ import annotations
import csv, hashlib, io, math
from datetime import date, datetime, timezone
from typing import Any

PROFILES = {
    "sharehub": {
        "date": ("date", "trading_date", "session_date"),
        "open": ("open", "open_price"), "high": ("high", "high_price"),
        "low": ("low", "low_price"), "close": ("close", "close_price"),
        "volume": ("volume", "total_traded_quantity", "quantity"),
    },
    "chukul": {
        "date": ("trading_date", "session_date", "date"),
        "open": ("openPrice", "open_price", "open"),
        "high": ("highPrice", "high_price", "high"),
        "low": ("lowPrice", "low_price", "low"),
        "close": ("closePrice", "close_price", "close"),
        "volume": ("totalVolume", "total_traded_quantity", "volume", "quantity"),
    },
    "sharesansar": {
        "date": ("trade_date", "trading_date", "session_date", "date"),
        "open": ("open", "open_price"), "high": ("high", "high_price"),
        "low": ("low", "low_price"), "close": ("closing_price", "close"),
        "volume": ("quantity", "total_traded_quantity", "volume"),
    },
}
FLOORSHEET_ALIASES = {
    "date": ("trade_date", "trading_date", "session_date", "date"),
    "symbol": ("symbol", "stock_symbol", "scrip"),
    "quantity": ("quantity", "qty", "contract_quantity"),
    "price": ("rate", "price", "contract_rate"),
    "buyer": ("buyer", "buyer_broker", "buyer_broker_no"),
    "seller": ("seller", "seller_broker", "seller_broker_no"),
}

def _pick(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for key in names:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None

def _day(value: Any) -> str:
    return date.fromisoformat(str(value).strip()).isoformat()

def _capture_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("captured_at_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc).isoformat()

def parse_csv_bytes(raw: bytes) -> list[dict[str, str]]:
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("empty_export")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("export_must_be_utf8_or_utf8_bom") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""), restkey="__extra_fields__", strict=True)
    if not reader.fieldnames:
        raise ValueError("csv_header_required")
    rows = []
    try:
        for line, row in enumerate(reader, start=2):
            if row.get("__extra_fields__") is not None or any(row.get(key) is None for key in reader.fieldnames):
                raise ValueError(f"malformed_csv_row_{line}")
            rows.append(dict(row))
    except csv.Error as exc:
        raise ValueError("malformed_csv:" + str(exc)) from exc
    return rows

def build_import_manifest(*, provider: str, symbol: str, filename: str, raw: bytes,
                          source_url: str | None, captured_at: str,
                          imported_by: str = "manual_export") -> dict[str, Any]:
    provider = provider.strip().lower()
    if provider not in PROFILES:
        raise ValueError("unsupported_provider")
    if not filename.strip() or not imported_by.strip():
        raise ValueError("filename_and_import_actor_required")
    return {
        "provider_id": provider, "symbol": symbol.strip().upper(),
        "filename": filename, "source_url": source_url,
        "captured_at": _capture_time(captured_at), "imported_by": imported_by,
        "raw_sha256": hashlib.sha256(raw).hexdigest(), "raw_bytes": len(raw),
        "access_mode": "public_or_user_export", "subscription_bypass": False,
        "research_only": True, "production_admission_allowed": False,
    }

def normalize_ohlcv_rows(*, provider: str, symbol: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    provider = provider.strip().lower()
    if provider not in PROFILES:
        raise ValueError("unsupported_provider")
    accepted, rejected, seen = [], [], {}
    for idx, row in enumerate(rows):
        try:
            fields = PROFILES[provider]
            day = _day(_pick(row, fields["date"]))
            if day in seen:
                prior = seen[day]
                prior_record = next((item for item in accepted if item["session_date"] == day), None)
                if prior_record is not None:
                    accepted.remove(prior_record)
                    rejected.append({"row_index": prior["row_index"], "reason": "duplicate_symbol_session",
                                     "raw_row": prior["raw_row"]})
                elif not any(item["row_index"] == prior["row_index"] and
                             item["reason"] == "duplicate_symbol_session" for item in rejected):
                    prior_rejection = next((item for item in rejected if item["row_index"] == prior["row_index"]), None)
                    if prior_rejection is not None:
                        prior_rejection["reason"] = "duplicate_symbol_session"
                    else:
                        rejected.append({"row_index": prior["row_index"], "reason": "duplicate_symbol_session",
                                         "raw_row": prior["raw_row"]})
                rejected.append({"row_index": idx, "reason": "duplicate_symbol_session", "raw_row": row})
                continue
            seen[day] = {"row_index": idx, "raw_row": row}
            raw_values = {key: _pick(row, aliases) for key, aliases in fields.items() if key != "date"}
            if any(value is None for value in raw_values.values()):
                raise ValueError("missing_ohlcv_field")
            vals = {key: float(value) for key, value in raw_values.items()}
            if any(v is None for v in vals.values()):
                raise ValueError("missing_ohlcv_field")
            if any(not math.isfinite(v) for v in vals.values()):
                raise ValueError("non_finite_ohlcv_value")
            if any(v < 0 for v in vals.values()):
                raise ValueError("negative_ohlcv_value")
            if vals["low"] > min(vals["open"], vals["close"]) or vals["high"] < max(vals["open"], vals["close"]) or vals["low"] > vals["high"]:
                raise ValueError("invalid_ohlc_relationship")
            accepted.append({"symbol": symbol.strip().upper(), "session_date": day, **vals,
                             "provider_id": provider, "row_index": idx})
        except (ValueError, TypeError) as exc:
            rejected.append({"row_index": idx, "reason": str(exc)})
    return {"provider_id": provider, "symbol": symbol.strip().upper(),
            "records": accepted, "rejected": rejected,
            "field_scope": "daily_ohlcv", "research_only": True,
            "production_admission_allowed": False}

def normalize_close_only_rows(*, provider: str, symbol: str,
                              rows: list[dict[str, Any]]) -> dict[str, Any]:
    accepted, rejected, seen = [], [], set()
    for idx, row in enumerate(rows):
        try:
            day = _day(_pick(row, ("date", "trade_date", "trading_date", "session_date")))
            close = float(_pick(row, ("close", "closing_price", "ltp")))
            if not math.isfinite(close):
                raise ValueError("non_finite_close")
            if close <= 0 or day in seen:
                raise ValueError("non_positive_close_or_duplicate_session")
            seen.add(day)
            accepted.append({"symbol": symbol.strip().upper(), "session_date": day,
                             "close": close, "field_coverage": ["close"],
                             "provider_id": provider})
        except (ValueError, TypeError) as exc:
            rejected.append({"row_index": idx, "reason": str(exc)})
    return {"provider_id": provider, "symbol": symbol.strip().upper(),
            "records": accepted, "rejected": rejected, "field_scope": "daily_close_only",
            "ohlcv_eligible": False, "floorsheet_eligible": False,
            "production_admission_allowed": False}

def reconcile_provider_rows(captures: list[dict[str, Any]], tolerance: float = 0.0) -> list[dict[str, Any]]:
    if tolerance < 0:
        raise ValueError("negative_tolerance")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for capture in captures:
        for row in capture.get("records", []):
            grouped.setdefault(row["session_date"], []).append(row)
    result = []
    for day, rows in sorted(grouped.items()):
        by_provider = {r.get("provider_id"): r for r in rows}
        conflicts = {}
        if len(by_provider) > 1:
            for field in ("open", "high", "low", "close", "volume"):
                values = [float(r[field]) for r in by_provider.values() if field in r]
                if len(values) > 1 and max(values) - min(values) > tolerance:
                    conflicts[field] = values
        result.append({"session_date": day, "provider_count": len(by_provider),
                       "conflicts": conflicts,
                       "status": "CONFLICT_REVIEW" if conflicts else
                                 ("SINGLE_PROVIDER" if len(by_provider) == 1 else "MATCHED")})
    return result

def normalize_floorsheet_rows(*, symbol: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    daily: dict[str, dict[str, Any]] = {}
    rejected = []
    for idx, row in enumerate(rows):
        try:
            row_symbol = str(_pick(row, FLOORSHEET_ALIASES["symbol"]) or symbol).strip().upper()
            if row_symbol != symbol.strip().upper():
                continue
            day = _day(_pick(row, FLOORSHEET_ALIASES["date"]))
            qty = float(_pick(row, FLOORSHEET_ALIASES["quantity"]))
            price = float(_pick(row, FLOORSHEET_ALIASES["price"]))
            if not math.isfinite(qty) or not math.isfinite(price):
                raise ValueError("non_finite_quantity_or_price")
            if qty <= 0 or price <= 0:
                raise ValueError("non_positive_quantity_or_price")
            item = daily.setdefault(day, {"symbol": row_symbol, "session_date": day,
                "trade_count": 0, "volume": 0.0, "turnover": 0.0,
                "buyer_brokers": set(), "seller_brokers": set()})
            item["trade_count"] += 1
            item["volume"] += qty
            item["turnover"] += qty * price
            buyer = _pick(row, FLOORSHEET_ALIASES["buyer"])
            seller = _pick(row, FLOORSHEET_ALIASES["seller"])
            if buyer not in (None, ""): item["buyer_brokers"].add(str(buyer))
            if seller not in (None, ""): item["seller_brokers"].add(str(seller))
        except (ValueError, TypeError) as exc:
            rejected.append({"row_index": idx, "reason": str(exc)})
    records = []
    for day in sorted(daily):
        item = daily[day]
        item["buyer_brokers"] = sorted(item["buyer_brokers"])
        item["seller_brokers"] = sorted(item["seller_brokers"])
        records.append(item)
    return {"symbol": symbol.strip().upper(), "records": records, "rejected": rejected,
            "coverage_start": records[0]["session_date"] if records else None,
            "coverage_end": records[-1]["session_date"] if records else None,
            "coverage_verified": False, "broker_numbers_are_execution_channels_not_owners": True,
            "production_admission_allowed": False}

def find_session_gaps(*, expected_sessions: list[str], observed_sessions: list[str]) -> list[str]:
    expected = {_day(x) for x in expected_sessions}
    observed = {_day(x) for x in observed_sessions}
    return sorted(expected - observed)

def evaluate_first_trade_evidence(*, listing_date: str, scheduled_trade_date: str,
                                  first_observed_trade_date: str | None,
                                  archive_complete_from: str | None,
                                  archive_complete_through: str | None,
                                  primary_exchange_evidence: bool) -> dict[str, Any]:
    listing, scheduled = _day(listing_date), _day(scheduled_trade_date)
    observed = _day(first_observed_trade_date) if first_observed_trade_date else None
    complete_from = _day(archive_complete_from) if archive_complete_from else None
    complete_through = _day(archive_complete_through) if archive_complete_through else None
    archive_covers = bool(complete_from and complete_through and complete_from <= scheduled <= complete_through)
    verified = bool(primary_exchange_evidence and archive_covers and observed == scheduled)
    return {"listing_date": listing, "scheduled_trade_date": scheduled,
            "first_observed_trade_date": observed, "archive_covers_scheduled_date": archive_covers,
            "primary_exchange_evidence": bool(primary_exchange_evidence),
            "status": "VERIFIED" if verified else "PARTIAL_EVIDENCE",
            "first_trade_date_verified": verified, "production_admission_allowed": False}

def assess_identity_evidence(*, symbol: str, security_id: str | None,
                             effective_from: str | None, effective_to: str | None,
                             evidence_refs: list[str], primary_evidence: bool) -> dict[str, Any]:
    start = _day(effective_from) if effective_from else None
    end = _day(effective_to) if effective_to else None
    if start and end and end < start:
        raise ValueError("effective_date_order_invalid")
    ready = bool(security_id and start and evidence_refs and primary_evidence)
    return {"symbol": symbol.strip().upper(), "security_id": security_id,
            "effective_from": start, "effective_to": end, "evidence_refs": evidence_refs,
            "status": "PRIMARY_EVIDENCE_REVIEW" if ready else "UNRESOLVED",
            "production_identity_approved": False}

def build_no_api_readiness() -> dict[str, Any]:
    return {"api_required": False, "supported_ingest_modes": ["public_page_capture", "manual_csv_export", "manual_json_export"],
            "sharehub": "manual_export_if_available; licensed API not assumed",
            "chukul": "public_page_or_manual_export; dynamic page may require user-provided export",
            "sharesansar": "public_page_or_manual_export; historical tab availability varies",
            "unavailable_data_policy": "record ACCESS_BLOCKED or NOT_ACQUIRED; never synthesize rows",
            "secrets_required": False, "production_admission_allowed": False}
