"""Durable, append-only broker behaviour memory.

This module accepts only broker-party observations already admitted by the
authoritative source/session/floorsheet evidence gate. It stores immutable
row lineage and content-addressed point-in-time profiles. It does not infer
beneficial ownership, broker intent, or production trading signals.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

from .database import connect
from .footprint_features import broker_footprint_features
from .broker_early_patterns import evaluate_broker_early_pattern

HORIZONS = {"1D": 1, "1W": 5, "1M": 21, "1Y": 252}
REQUIRED = (
    "trade_date", "symbol", "side", "amount", "quantity",
    "identity_status", "broker_entity_id", "source_broker_code",
    "source_id", "source_payload_sha256", "source_row_number",
    "evidence_id", "available_at", "source_validation_status",
    "source_rights_status", "rights_evidence_id",
    "session_calendar_status", "floorsheet_coverage_status",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _aware(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return parsed


def _ensure_tables(con) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS broker_memory_observations (
            observation_id VARCHAR PRIMARY KEY,
            trade_date DATE NOT NULL,
            symbol VARCHAR NOT NULL,
            side VARCHAR NOT NULL,
            available_at TIMESTAMPTZ NOT NULL,
            source_id VARCHAR NOT NULL,
            source_payload_sha256 VARCHAR NOT NULL,
            source_row_number BIGINT NOT NULL,
            evidence_id VARCHAR NOT NULL,
            record_json JSON NOT NULL,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
            UNIQUE (source_id, source_payload_sha256, source_row_number, side)
        )
    """)
    con.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS broker_memory_source_lineage_idx
        ON broker_memory_observations(source_id, source_payload_sha256, source_row_number, side)
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS broker_memory_snapshots (
            snapshot_id VARCHAR PRIMARY KEY,
            as_of_trade_date DATE NOT NULL,
            decision_time TIMESTAMPTZ NOT NULL,
            schema_version INTEGER NOT NULL,
            feature_version VARCHAR NOT NULL,
            snapshot_json JSON NOT NULL,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
        )
    """)


def _validate_observations(rows: list[dict], session_dates: list[str], decision_time: str) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("at least one broker-party observation is required")
    if not isinstance(session_dates, list) or not session_dates:
        raise ValueError("verified canonical session_dates are required")
    try:
        sessions = [date.fromisoformat(str(item)).isoformat() for item in session_dates]
    except (TypeError, ValueError) as exc:
        raise ValueError("session_dates must contain ISO YYYY-MM-DD dates") from exc
    if sessions != sorted(set(sessions)):
        raise ValueError("session_dates must be sorted and unique")
    cutoff = _aware(decision_time, "decision_time")
    cutoff_session = cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date().isoformat()
    allowed = {item for item in sessions if item <= cutoff_session}
    seen = set()
    clean = []
    for index, source in enumerate(rows):
        if not isinstance(source, dict):
            raise ValueError(f"row {index} must be an object")
        missing = [key for key in REQUIRED if key not in source]
        if missing:
            raise ValueError(f"row {index} missing required evidence fields: {', '.join(missing)}")
        row = dict(source)
        try:
            day = date.fromisoformat(str(row["trade_date"])).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError(f"row {index} trade_date must be YYYY-MM-DD") from exc
        if day > cutoff_session:
            raise ValueError(f"row {index} trade_date is after the decision-time session")
        if day not in allowed:
            raise ValueError(f"row {index} trade_date is not in the supplied verified session calendar")
        if row["source_validation_status"] != "verified":
            raise ValueError(f"row {index} source is not verified")
        if row["session_calendar_status"] != "confirmed_open":
            raise ValueError(f"row {index} session is not confirmed open")
        if row["floorsheet_coverage_status"] != "verified_complete":
            raise ValueError(f"row {index} floorsheet coverage is not verified complete")
        rights_status = row["source_rights_status"]
        if rights_status not in {"research_only", "internal_use", "redistribution_permitted"}:
            raise ValueError(f"row {index} source rights are not cleared for research use")
        if rights_status == "redistribution_permitted" and (
            not isinstance(row["rights_evidence_id"], str) or not row["rights_evidence_id"].strip()
        ):
            raise ValueError(f"row {index} redistribution permission requires rights evidence")
        for key in ("source_id", "evidence_id"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise ValueError(f"row {index} {key} must be nonblank")
        digest = str(row["source_payload_sha256"]).lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError(f"row {index} source_payload_sha256 must be a SHA-256 hex digest")
        row_number = row["source_row_number"]
        if isinstance(row_number, bool) or not isinstance(row_number, int) or row_number < 1:
            raise ValueError(f"row {index} source_row_number must be a positive integer")
        available = _aware(row["available_at"], f"row {index} available_at")
        if available > cutoff:
            raise ValueError(f"row {index} was not available at the decision time")
        row["trade_date"] = day
        row["symbol"] = str(row["symbol"]).strip().upper()
        row["source_payload_sha256"] = digest
        if row["source_broker_code"] is not None:
            row["source_broker_code"] = str(row["source_broker_code"]).strip()
        if not row["symbol"]:
            raise ValueError(f"row {index} symbol is required")
        key = (row["source_id"], digest, row_number, row["side"])
        if key in seen:
            raise ValueError(f"duplicate party observation source lineage: {key}")
        seen.add(key)
        clean.append(row)
    return clean



def _execution_channel_features(rows: list[dict], session_dates: list[str],
                                minimum_amount_coverage: float = 0.80) -> dict:
    """Describe source broker codes as execution channels, never as owners."""
    from decimal import Decimal, InvalidOperation

    normalized_sessions = [date.fromisoformat(str(item)).isoformat() for item in session_dates]
    scopes = {"market": rows}
    for symbol in sorted({str(row["symbol"]).upper() for row in rows}):
        scopes[symbol] = [row for row in rows if str(row["symbol"]).upper() == symbol]
    output = {"market": {}, "securities": {}}
    for scope_name, scope_rows in scopes.items():
        target = output["market"] if scope_name == "market" else output["securities"].setdefault(scope_name, {})
        for horizon, count in HORIZONS.items():
            selected_sessions = normalized_sessions[-count:]
            session_set = set(selected_sessions)
            window_rows = [row for row in scope_rows if row["trade_date"] in session_set]
            coded = [row for row in window_rows if row.get("source_broker_code") not in (None, "")]
            try:
                gross_all = sum((Decimal(str(row["amount"])) for row in window_rows), Decimal("0"))
                gross_coded = sum((Decimal(str(row["amount"])) for row in coded), Decimal("0"))
            except (InvalidOperation, TypeError) as exc:
                raise ValueError("broker execution-channel amounts must be valid decimals") from exc
            coverage = gross_coded / gross_all if gross_all else None
            totals = {
                code: {
                    "buy_amount": Decimal("0"), "sell_amount": Decimal("0"),
                    "buy_quantity": Decimal("0"), "sell_quantity": Decimal("0"),
                    "active_sessions": set(), "party_observation_count": 0,
                }
                for code in sorted({str(row["source_broker_code"]).strip()
                                    for row in scope_rows
                                    if row.get("source_broker_code") not in (None, "")})
            }
            for row in coded:
                code = str(row["source_broker_code"]).strip()
                if not code:
                    continue
                if row["side"] not in {"buy", "sell"}:
                    raise ValueError("broker execution-channel side must be buy or sell")
                item = totals.setdefault(code, {
                    "buy_amount": Decimal("0"), "sell_amount": Decimal("0"),
                    "buy_quantity": Decimal("0"), "sell_quantity": Decimal("0"),
                    "active_sessions": set(), "party_observation_count": 0,
                })
                item[row["side"] + "_amount"] += Decimal(str(row["amount"]))
                item[row["side"] + "_quantity"] += Decimal(str(row["quantity"]))
                item["active_sessions"].add(row["trade_date"])
                item["party_observation_count"] += 1
            profiles = []
            baseline_sessions = normalized_sessions[-21:-1]
            latest_session = normalized_sessions[-1] if normalized_sessions else None
            for code, item in totals.items():
                gross = item["buy_amount"] + item["sell_amount"]
                net = item["buy_amount"] - item["sell_amount"]
                daily_by_session = {
                    day: {"buy": Decimal("0"), "sell": Decimal("0")}
                    for day in baseline_sessions + ([latest_session] if latest_session else [])
                }
                for row in scope_rows:
                    if row.get("source_broker_code") == code and row["trade_date"] in daily_by_session:
                        daily_by_session[row["trade_date"]][row["side"]] += Decimal(str(row["amount"]))
                prior_buy_values = [daily_by_session[day]["buy"] for day in baseline_sessions]
                prior_sell_values = [daily_by_session[day]["sell"] for day in baseline_sessions]
                prior_buy_avg = (sum(prior_buy_values, Decimal("0")) / Decimal("20")
                                 if len(prior_buy_values) == 20 else None)
                prior_sell_avg = (sum(prior_sell_values, Decimal("0")) / Decimal("20")
                                  if len(prior_sell_values) == 20 else None)
                latest_buy = daily_by_session[latest_session]["buy"] if latest_session else Decimal("0")
                latest_sell = daily_by_session[latest_session]["sell"] if latest_session else Decimal("0")
                daily_activity = [
                    {
                        "session_date": day,
                        "buy_amount": str(daily_by_session[day]["buy"]),
                        "sell_amount": str(daily_by_session[day]["sell"]),
                        "net_amount": str(daily_by_session[day]["buy"] - daily_by_session[day]["sell"]),
                        "gross_amount": str(daily_by_session[day]["buy"] + daily_by_session[day]["sell"]),
                    }
                    for day in baseline_sessions + ([latest_session] if latest_session else [])
                ]
                profiles.append({
                    "execution_channel_code": code,
                    "identity_status": "execution_channel_only",
                    "buy_amount": str(item["buy_amount"]),
                    "sell_amount": str(item["sell_amount"]),
                    "net_amount": str(net),
                    "buy_quantity": str(item["buy_quantity"]),
                    "sell_quantity": str(item["sell_quantity"]),
                    "net_quantity": str(item["buy_quantity"] - item["sell_quantity"]),
                    "gross_participation_pct": round(float(gross / gross_coded * 100), 4) if gross_coded else None,
                    "active_sessions": len(item["active_sessions"]),
                    "party_observation_count": item["party_observation_count"],
                    "latest_session": latest_session,
                    "latest_buy_amount": str(latest_buy),
                    "latest_sell_amount": str(latest_sell),
                    "prior_20_session_count": len(baseline_sessions),
                    "prior_20_avg_buy_amount": str(prior_buy_avg) if prior_buy_avg is not None else None,
                    "prior_20_avg_sell_amount": str(prior_sell_avg) if prior_sell_avg is not None else None,
                    "daily_activity": daily_activity,
                    "latest_buy_vs_prior_20_avg_ratio": float(latest_buy / prior_buy_avg) if prior_buy_avg is not None and prior_buy_avg > 0 else None,
                    "latest_sell_vs_prior_20_avg_ratio": float(latest_sell / prior_sell_avg) if prior_sell_avg is not None and prior_sell_avg > 0 else None,
                    "flow_class": "net_buyer" if net > 0 else "net_seller" if net < 0 else "balanced",
                })
            profiles.sort(key=lambda item: (Decimal(item["net_amount"]), item["execution_channel_code"]), reverse=True)
            target[horizon] = {
                "window": horizon,
                "window_sessions": count,
                "calendar_sessions_available": len(selected_sessions),
                "observed_sessions": len({row["trade_date"] for row in window_rows}),
                "window_complete": len(selected_sessions) == count,
                "party_observation_count": len(window_rows),
                "coded_party_observation_count": len(coded),
                "uncoded_party_observation_count": len(window_rows) - len(coded),
                "coded_amount_coverage_pct": round(float(coverage * 100), 4) if coverage is not None else None,
                "status": "observed" if coverage is not None and float(coverage) >= minimum_amount_coverage else "insufficient_code_coverage",
                "execution_channels": profiles,
                "interpretation": "observed floorsheet execution-channel activity; not broker proprietary holdings, beneficial ownership or intent",
            }
    return output


def persist_broker_memory(rows: list[dict], *, session_dates: list[str],
                          decision_time: str, minimum_amount_coverage: float = 0.80,
                          minimum_sessions: int = 5,
                          market_context_by_symbol: dict | None = None,
                          minimum_daily_flow_multiple: float = 1.5) -> dict:
    """Append eligible observations and rebuild profiles from all prior known evidence.

    The caller supplies rows from the canonical evidence-admission pipeline.
    Previously stored rows are replayed as-of decision_time, so memory persists
    across sessions rather than only describing the latest upload.
    """
    clean = _validate_observations(rows, session_dates, decision_time)
    cutoff = _aware(decision_time, "decision_time")
    cutoff_session = cutoff.astimezone(ZoneInfo("Asia/Kathmandu")).date().isoformat()
    covered_sessions = [date.fromisoformat(str(item)).isoformat() for item in session_dates
                        if date.fromisoformat(str(item)).isoformat() <= cutoff_session]
    allowed_sessions = set(covered_sessions)
    con = connect()
    try:
        _ensure_tables(con)
        con.execute("BEGIN TRANSACTION")
        for row in clean:
            record_json = _canonical(row)
            observation_id = hashlib.sha256(record_json.encode()).hexdigest()
            existing = con.execute(
                """SELECT observation_id, record_json FROM broker_memory_observations
                   WHERE source_id = ? AND source_payload_sha256 = ? AND source_row_number = ? AND side = ?""",
                [row["source_id"], row["source_payload_sha256"], row["source_row_number"], row["side"]],
            ).fetchone()
            if existing is not None:
                if existing[0] != observation_id or str(existing[1]) != record_json:
                    raise ValueError("broker observation immutable-record conflict for source lineage")
                continue
            con.execute(
                """INSERT INTO broker_memory_observations
                   (observation_id, trade_date, symbol, side, available_at, source_id,
                    source_payload_sha256, source_row_number, evidence_id, record_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::JSON)""",
                [observation_id, date.fromisoformat(row["trade_date"]),
                 row["symbol"], row["side"], _aware(row["available_at"], "available_at"),
                 row["source_id"], row["source_payload_sha256"],
                 row["source_row_number"], row["evidence_id"], record_json],
            )

        # Rebuild from every immutable observation available at this decision
        # time and covered by the supplied verified canonical session calendar.
        stored = con.execute(
            """SELECT record_json FROM broker_memory_observations
               WHERE available_at <= ? ORDER BY trade_date, source_id, source_row_number""",
            [cutoff],
        ).fetchall()
        historical_rows = [
            json.loads(str(item[0])) for item in stored
            if json.loads(str(item[0])).get("trade_date") in allowed_sessions
        ]
        if not historical_rows:
            raise ValueError("no stored broker observations fall within the verified session calendar")
        features = broker_footprint_features(
            historical_rows, minimum_amount_coverage=minimum_amount_coverage,
            minimum_sessions=minimum_sessions, session_dates=covered_sessions,
        )
        channel_features = _execution_channel_features(
            historical_rows, covered_sessions, minimum_amount_coverage
        )
        if market_context_by_symbol is not None and not isinstance(market_context_by_symbol, dict):
            raise ValueError("market_context_by_symbol must be an object keyed by stock symbol")
        body_as_of_session = covered_sessions[-1]
        early_patterns = []
        normalized_context = {
            str(key).strip().upper(): value
            for key, value in (market_context_by_symbol or {}).items()
        }
        for symbol, symbol_windows in channel_features["securities"].items():
            broker_windows = {
                horizon: symbol_windows.get(horizon, {})
                for horizon in ("1D", "1W", "1M")
            }
            latest_channels = broker_windows["1D"].get("execution_channels", [])
            context = normalized_context.get(symbol, {})
            for channel in latest_channels:
                early_patterns.append(evaluate_broker_early_pattern(
                    broker_code=channel["execution_channel_code"],
                    symbol=symbol,
                    execution_channel_windows=broker_windows,
                    market_context=context,
                    decision_time=decision_time,
                    as_of_session=body_as_of_session,
                    minimum_daily_flow_multiple=minimum_daily_flow_multiple,
                ))
        body = {
            "schema_version": 1,
            "feature_version": "broker-footprint-v1",
            "decision_time": cutoff.isoformat(),
            "as_of_trade_date": body_as_of_session,
            "session_calendar": covered_sessions,
            "observation_count": len(historical_rows),
            "source_count": len({row["source_id"] for row in historical_rows}),
            "source_payload_hashes": sorted({row["source_payload_sha256"] for row in historical_rows}),
            "features": features,
            "execution_channel_features": channel_features,
            "early_patterns": early_patterns,
            "early_pattern_status": ("research_candidates" if any(item["status"] in {"EARLY_ENTRY_CANDIDATE", "EARLY_EXIT_RISK"} for item in early_patterns) else "insufficient_evidence" if not market_context_by_symbol else "watch_or_insufficient_evidence"),
            "early_pattern_rule_config": {
                "rule_version": "nepse-broker-flow-candidate-v1",
                "minimum_daily_flow_multiple": minimum_daily_flow_multiple,
                "calibration_status": "uncalibrated_research_rule",
            },
            "horizon_contract": {
                "1D": "latest verified session",
                "1W": "latest 5 verified sessions",
                "1M": "latest 21 verified sessions",
                "1Y": "latest 252 verified sessions",
                "incomplete_windows_remain_explicit": True,
            },
            "status": features["status"],
            "production_recommendations_enabled": False,
        }
        snapshot_id = hashlib.sha256(_canonical(body).encode()).hexdigest()
        encoded = _canonical(body)
        existing_snapshot = con.execute(
            "SELECT snapshot_json FROM broker_memory_snapshots WHERE snapshot_id = ?",
            [snapshot_id],
        ).fetchone()
        if existing_snapshot is not None:
            if str(existing_snapshot[0]) != encoded:
                raise ValueError("broker memory snapshot hash conflict")
            con.execute("COMMIT")
            return {"status": "already_stored", "snapshot_id": snapshot_id,
                    "observation_count": len(historical_rows), "features": features}
        con.execute(
            """INSERT INTO broker_memory_snapshots
               (snapshot_id, as_of_trade_date, decision_time, schema_version,
                feature_version, snapshot_json)
               VALUES (?, ?, ?, 1, 'broker-footprint-v1', ?::JSON)""",
            [snapshot_id, date.fromisoformat(body["as_of_trade_date"]), cutoff, encoded],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return {"status": "stored", "snapshot_id": snapshot_id,
            "observation_count": len(historical_rows), "features": features}


def get_latest_broker_memory(*, symbol: str | None = None,
                             broker_entity_id: str | None = None,
                             broker_code: str | None = None,
                             as_of: str | None = None) -> dict | None:
    """Return latest immutable profile matching filters; no data means None."""
    con = connect()
    try:
        _ensure_tables(con)
        conditions = []
        params: list[Any] = []
        if as_of:
            cutoff = date.fromisoformat(as_of)
            conditions.append("as_of_trade_date <= ?")
            params.append(cutoff)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = con.execute(
            "SELECT snapshot_id, snapshot_json FROM broker_memory_snapshots" +
            where + " ORDER BY as_of_trade_date DESC, decision_time DESC",
            params,
        ).fetchall()
        for snapshot_id, raw in rows:
            snapshot = json.loads(str(raw))
            features = snapshot.get("features", {})
            if symbol:
                selected = features.get("security_features", {}).get(symbol.upper())
                if selected is None:
                    continue
                snapshot["selected_symbol"] = symbol.upper()
                snapshot["selected_features"] = selected
                snapshot["selected_early_patterns"] = [
                    item for item in snapshot.get("early_patterns", [])
                    if item.get("symbol") == symbol.upper()
                ]
            if broker_code:
                channel_matches = []
                if snapshot.get("selected_symbol"):
                    scopes = [snapshot["selected_symbol"]]
                else:
                    scopes = list(snapshot.get("execution_channel_features", {}).get("securities", {}).keys())
                for scope_name in scopes:
                    scope = snapshot.get("execution_channel_features", {}).get("securities", {}).get(scope_name, {})
                    for horizon, window in scope.items():
                        for channel in window.get("execution_channels", []):
                            if channel.get("execution_channel_code") == broker_code:
                                channel_matches.append({"scope": scope_name, "horizon": horizon, **channel})
                for horizon, window in snapshot.get("execution_channel_features", {}).get("market", {}).items():
                    for channel in window.get("execution_channels", []):
                        if channel.get("execution_channel_code") == broker_code:
                            channel_matches.append({"scope": "market", "horizon": horizon, **channel})
                if not channel_matches:
                    continue
                snapshot["selected_execution_channel_code"] = broker_code
                snapshot["execution_channel_matches"] = channel_matches
                snapshot["selected_early_patterns"] = [
                    item for item in snapshot.get("early_patterns", [])
                    if item.get("execution_channel_code") == broker_code
                    and (not symbol or item.get("symbol") == symbol.upper())
                ]
            if broker_entity_id:
                matches = []
                for scope in ([snapshot.get("selected_features")] if snapshot.get("selected_features")
                              else list(features.get("security_features", {}).values()) + [features.get("market_windows", {})]):
                    if not scope:
                        continue
                    for horizon, window in scope.items():
                        if not isinstance(window, dict):
                            continue
                        for position in window.get("broker_positions", []):
                            if position.get("broker_entity_id") == broker_entity_id:
                                matches.append({"horizon": horizon, **position})
                if not matches:
                    continue
                snapshot["selected_broker_entity_id"] = broker_entity_id
                snapshot["broker_matches"] = matches
            snapshot["snapshot_id"] = snapshot_id
            return snapshot
        return None
    finally:
        con.close()


def broker_memory_status() -> dict:
    con = connect()
    try:
        _ensure_tables(con)
        observations, snapshots, latest = con.execute(
            """SELECT (SELECT count(*) FROM broker_memory_observations),
                      (SELECT count(*) FROM broker_memory_snapshots),
                      (SELECT max(as_of_trade_date) FROM broker_memory_snapshots)"""
        ).fetchone()
        return {
            "status": "observed" if snapshots else "insufficient_evidence",
            "observation_count": observations,
            "snapshot_count": snapshots,
            "latest_as_of_trade_date": str(latest) if latest else None,
            "horizons": list(HORIZONS),
            "live_ingestion_connected": False,
            "early_pattern_engine": "uncalibrated_research_rule_not_yet_wired_to_live_context",
            "production_recommendations_enabled": False,
        }
    finally:
        con.close()
