"""Steps 110-119: provider history capture, floorsheet evidence and predecessor identity.

These adapters normalize supplied captures; they do not scrape websites or assert that
an archive is complete. Raw payload hashes and capture metadata remain attached.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, date, timezone
from hashlib import sha256
import math
from typing import Any

PROVIDERS = {
    "sharehub": {"date": ("date", "trading_date", "session_date"), "open": ("open", "open_price"), "high": ("high", "high_price"), "low": ("low", "low_price"), "close": ("close", "close_price", "ltp"), "volume": ("volume", "total_traded_quantity", "quantity")},
    "chukul": {"date": ("date", "trading_date", "session_date"), "open": ("open", "openPrice", "open_price"), "high": ("high", "highPrice", "high_price"), "low": ("low", "lowPrice", "low_price"), "close": ("close", "closePrice", "close_price", "ltp"), "volume": ("volume", "totalVolume", "total_traded_quantity")},
    "sharesansar": {"date": ("date", "trade_date", "trading_date", "session_date"), "open": ("open", "open_price"), "high": ("high", "high_price"), "low": ("low", "low_price"), "close": ("close", "closing_price", "ltp"), "volume": ("volume", "quantity", "total_traded_quantity")},
}
PREDECESSORS = ("BPW", "JALPA", "KLBSL", "MKLB")

def _first(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if row.get(name) not in (None, ""):
            return row[name]
    return None

def _session(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        for fmt in ("%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                pass
    raise ValueError("unparseable_session_date")

def capture_chart_history(*, provider_id: str, symbol: str, rows: list[dict[str, Any]],
                          raw_payload: str, source_url: str, captured_at: str) -> dict[str, Any]:
    provider = provider_id.strip().lower()
    if provider not in PROVIDERS:
        raise ValueError("unsupported_provider")
    captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    if captured.tzinfo is None:
        raise ValueError("captured_at_must_be_timezone_aware")
    if not source_url.strip() or not raw_payload:
        raise ValueError("source_url_and_raw_payload_required")
    mapping = PROVIDERS[provider]
    accepted, rejected = [], []
    for index, row in enumerate(rows):
        try:
            values = {field: _first(row, aliases) for field, aliases in mapping.items()}
            session = _session(values.pop("date"))
            numbers = {k: float(v) for k, v in values.items()}
            if any(v is None for v in values.values()) or any(not math.isfinite(v) for v in numbers.values()):\n                raise ValueError("non_finite_ohlcv")\n            if any(v < 0 for v in numbers.values()):
                raise ValueError("missing_or_negative_ohlcv")
            if numbers["low"] > min(numbers["open"], numbers["close"]) or numbers["high"] < max(numbers["open"], numbers["close"]) or numbers["low"] > numbers["high"]:
                raise ValueError("invalid_ohlcv_relationship")
            accepted.append({"symbol": symbol.strip().upper(), "session_date": session, **numbers,
                             "provider_id": provider, "capture_index": index})
        except (ValueError, TypeError) as exc:
            rejected.append({"row_index": index, "reason": str(exc)})
    return {"provider_id": provider, "symbol": symbol.strip().upper(), "source_url": source_url,
            "captured_at": captured.astimezone(timezone.utc).isoformat(),
            "raw_payload_sha256": sha256(raw_payload.encode("utf-8")).hexdigest(),
            "records": accepted, "rejected": rejected, "status": "CAPTURED" if accepted else "NO_VALID_ROWS",
            "production_admission_allowed": False}

def parse_sharehub_chart(*, symbol: str, rows: list[dict[str, Any]], raw_payload: str, source_url: str, captured_at: str) -> dict[str, Any]:
    return capture_chart_history(provider_id="sharehub", symbol=symbol, rows=rows, raw_payload=raw_payload, source_url=source_url, captured_at=captured_at)

def parse_chukul_chart(*, symbol: str, rows: list[dict[str, Any]], raw_payload: str, source_url: str, captured_at: str) -> dict[str, Any]:
    return capture_chart_history(provider_id="chukul", symbol=symbol, rows=rows, raw_payload=raw_payload, source_url=source_url, captured_at=captured_at)

def parse_sharesansar_chart(*, symbol: str, rows: list[dict[str, Any]], raw_payload: str, source_url: str, captured_at: str) -> dict[str, Any]:
    return capture_chart_history(provider_id="sharesansar", symbol=symbol, rows=rows, raw_payload=raw_payload, source_url=source_url, captured_at=captured_at)

def aggregate_floorsheet(*, symbol: str, trades: list[dict[str, Any]], raw_payload: str,
                         source_url: str, captured_at: str) -> dict[str, Any]:
    captured = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
    if captured.tzinfo is None or not raw_payload or not source_url.strip():
        raise ValueError("timezone_aware_capture_and_raw_evidence_required")
    daily = defaultdict(lambda: {"trade_count": 0, "volume": 0.0, "turnover": 0.0})
    rejected = []
    for i, trade in enumerate(trades):
        try:
            day = _session(_first(trade, ("date", "trade_date", "trading_date", "session_date")))
            qty = float(_first(trade, ("quantity", "qty", "contract_quantity")))
            price = float(_first(trade, ("rate", "price", "contract_rate")))
            if not math.isfinite(qty) or not math.isfinite(price):\n                raise ValueError("non_finite_trade_quantity_or_price")\n            if qty <= 0 or price <= 0:
                raise ValueError("non_positive_trade_quantity_or_price")
            daily[day]["trade_count"] += 1
            daily[day]["volume"] += qty
            daily[day]["turnover"] += qty * price
        except (ValueError, TypeError) as exc:
            rejected.append({"row_index": i, "reason": str(exc)})
    records = [{"symbol": symbol.strip().upper(), "session_date": day, **vals} for day, vals in sorted(daily.items())]
    return {"symbol": symbol.strip().upper(), "records": records, "rejected": rejected,
            "raw_payload_sha256": sha256(raw_payload.encode("utf-8")).hexdigest(),
            "source_url": source_url, "captured_at": captured.astimezone(timezone.utc).isoformat(),
            "coverage_start": records[0]["session_date"] if records else None,
            "coverage_end": records[-1]["session_date"] if records else None,
            "coverage_verified": False, "production_admission_allowed": False}

def reconcile_history_sources(*, chart_captures: list[dict[str, Any]], floorsheet: dict[str, Any] | None) -> dict[str, Any]:
    rows = [r for capture in chart_captures for r in capture.get("records", [])]
    by_day = defaultdict(list)
    for row in rows:
        by_day[row["session_date"]].append(row)
    comparisons = []
    for day, group in sorted(by_day.items()):
        fields = ("open", "high", "low", "close", "volume")
        conflicts = {f: sorted({r[f] for r in group}) for f in fields if len({r[f] for r in group}) > 1}
        comparisons.append({"session_date": day, "providers": sorted({r["provider_id"] for r in group}),
                            "conflicts": conflicts, "status": "CONFLICT_REVIEW" if conflicts else "MATCHED"})
    chart_first = min((r["session_date"] for r in rows), default=None)
    floor_rows = (floorsheet or {}).get("records", [])
    floor_first = min((r["session_date"] for r in floor_rows if r.get("trade_count", 0) > 0), default=None)
    complete = bool(floorsheet and floorsheet.get("coverage_verified") is True)
    agrees = bool(chart_first and floor_first and chart_first == floor_first)
    status = "FIRST_TRADE_CORROBORATED" if agrees and complete else ("PARTIAL_EVIDENCE" if chart_first or floor_first else "NO_EVIDENCE")
    return {"symbol": "BENH", "chart_first_session": chart_first, "floorsheet_first_trade_session": floor_first,
            "chart_floorsheet_agree": agrees, "floorsheet_coverage_verified": complete,
            "provider_comparisons": comparisons, "status": status,
            "first_trade_date_verified": status == "FIRST_TRADE_CORROBORATED",
            "official_listing_date": None, "listing_date_verified": False,
            "production_admission_allowed": False}

def assess_predecessor_identity(*, symbol: str, security_id: str | None,
                                effective_from: str | None, effective_to: str | None,
                                evidence_refs: list[str], evidence_type: str | None) -> dict[str, Any]:
    code = symbol.strip().upper()
    if code not in PREDECESSORS:
        return {"symbol": code, "status": "NOT_IN_TARGET_PREDECESSOR_SET", "production_identity_approved": False}
    try:
        start = _session(effective_from) if effective_from else None
        end = _session(effective_to) if effective_to else None
        if start and end and end < start:
            raise ValueError("effective_date_order_invalid")
    except ValueError as exc:
        return {"symbol": code, "status": "BLOCKED", "errors": [str(exc)], "production_identity_approved": False}
    ready = bool(security_id and start and evidence_refs and evidence_type in {"official_listing", "official_renaming", "cdsc_security_master", "issuer_notice"})
    return {"symbol": code, "security_id": security_id, "effective_from": start, "effective_to": end,
            "evidence_refs": evidence_refs, "evidence_type": evidence_type,
            "status": "EVIDENCE_BACKED_CANDIDATE" if ready else "UNRESOLVED",
            "production_identity_approved": False}
