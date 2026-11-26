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
from typing import Any

from .database import connect
from .footprint_features import broker_footprint_features

HORIZONS = {"1D": 1, "1W": 5, "1M": 21, "1Y": 252}
REQUIRED = (
    "trade_date", "symbol", "side", "amount", "quantity",
    "identity_status", "broker_entity_id", "source_broker_code",
    "source_id", "source_payload_sha256", "source_row_number",
    "evidence_id", "available_at", "source_validation_status",
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
            available_at TIMESTAMPTZ NOT NULL,
            source_id VARCHAR NOT NULL,
            source_payload_sha256 VARCHAR NOT NULL,
            source_row_number BIGINT NOT NULL,
            evidence_id VARCHAR NOT NULL,
            record_json JSON NOT NULL,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
        )
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
    allowed = set(sessions)
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
        if day not in allowed:
            raise ValueError(f"row {index} trade_date is not in the supplied verified session calendar")
        if row["source_validation_status"] != "verified":
            raise ValueError(f"row {index} source is not verified")
        if row["session_calendar_status"] != "confirmed_open":
            raise ValueError(f"row {index} session is not confirmed open")
        if row["floorsheet_coverage_status"] != "verified_complete":
            raise ValueError(f"row {index} floorsheet coverage is not verified complete")
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
        if not row["symbol"]:
            raise ValueError(f"row {index} symbol is required")
        key = (row["source_id"], digest, row_number)
        if key in seen:
            raise ValueError(f"duplicate source lineage row: {key}")
        seen.add(key)
        clean.append(row)
    return clean


def persist_broker_memory(rows: list[dict], *, session_dates: list[str],
                          decision_time: str, minimum_amount_coverage: float = 0.80,
                          minimum_sessions: int = 5) -> dict:
    """Persist eligible observations and a reproducible as-of horizon snapshot.

    The caller must supply rows from the canonical evidence-admission pipeline;
    this function independently enforces the required admission metadata but
    does not itself establish source rights or independently verify source claims.
    """
    clean = _validate_observations(rows, session_dates, decision_time)
    cutoff = _aware(decision_time, "decision_time")
    features = broker_footprint_features(
        clean, minimum_amount_coverage=minimum_amount_coverage,
        minimum_sessions=minimum_sessions,
    )
    body = {
        "schema_version": 1,
        "feature_version": "broker-footprint-v1",
        "decision_time": cutoff.isoformat(),
        "as_of_trade_date": max(row["trade_date"] for row in clean),
        "session_calendar": session_dates,
        "observation_count": len(clean),
        "source_count": len({row["source_id"] for row in clean}),
        "source_payload_hashes": sorted({row["source_payload_sha256"] for row in clean}),
        "features": features,
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
    con = connect()
    try:
        _ensure_tables(con)
        con.execute("BEGIN TRANSACTION")
        for row in clean:
            record_json = _canonical(row)
            observation_id = hashlib.sha256(record_json.encode()).hexdigest()
            existing = con.execute(
                "SELECT record_json FROM broker_memory_observations WHERE observation_id = ?",
                [observation_id],
            ).fetchone()
            if existing is not None:
                if str(existing[0]) != record_json:
                    raise ValueError("broker observation immutable-record conflict")
                continue
            con.execute(
                """INSERT INTO broker_memory_observations
                   (observation_id, trade_date, symbol, available_at, source_id,
                    source_payload_sha256, source_row_number, evidence_id, record_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?::JSON)""",
                [observation_id, date.fromisoformat(row["trade_date"]),
                 row["symbol"], _aware(row["available_at"], "available_at"),
                 row["source_id"], row["source_payload_sha256"],
                 row["source_row_number"], row["evidence_id"], record_json],
            )
        existing_snapshot = con.execute(
            "SELECT snapshot_json FROM broker_memory_snapshots WHERE snapshot_id = ?",
            [snapshot_id],
        ).fetchone()
        if existing_snapshot is not None:
            if str(existing_snapshot[0]) != encoded:
                raise ValueError("broker memory snapshot hash conflict")
            con.execute("COMMIT")
            return {"status": "already_stored", "snapshot_id": snapshot_id,
                    "observation_count": len(clean), "features": features}
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
            "observation_count": len(clean), "features": features}


def get_latest_broker_memory(*, symbol: str | None = None,
                             broker_entity_id: str | None = None,
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
            "production_recommendations_enabled": False,
        }
    finally:
        con.close()
