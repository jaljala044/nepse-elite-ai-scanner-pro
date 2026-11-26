"""Append-only DuckDB persistence for research signals and horizon outcomes.

Records are immutable, content-addressed and explicitly research-only. This
store does not authorize recommendations, fills, or production trading.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from .database import connect
from .signal_tracking import verify_signal, HORIZONS


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed


def _ensure_tables(con) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS research_signals (
            signal_id VARCHAR PRIMARY KEY,
            decision_time TIMESTAMPTZ NOT NULL,
            symbol VARCHAR NOT NULL,
            horizon VARCHAR NOT NULL,
            record_json JSON NOT NULL,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS research_outcomes (
            outcome_id VARCHAR PRIMARY KEY,
            signal_id VARCHAR NOT NULL,
            horizon VARCHAR NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL,
            outcome_json JSON NOT NULL,
            stored_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
        )
    """)


def store_signal(envelope: dict) -> dict:
    """Insert a verified immutable signal; identical retries are idempotent."""
    if not isinstance(envelope, dict) or not verify_signal(envelope):
        raise ValueError("signal envelope hash verification failed")
    record = envelope["record"]
    if record.get("classification") != "research_only_not_execution":
        raise ValueError("only research-only signal records may be stored")
    if record.get("action") != "NO TRADE":
        raise ValueError("production recommendations are not authorized")
    encoded = _canonical(record)
    decision_time = _aware(record["decision_time"])
    con = connect()
    try:
        _ensure_tables(con)
        con.execute("BEGIN TRANSACTION")
        existing = con.execute(
            "SELECT record_json FROM research_signals WHERE signal_id = ?",
            [envelope["signal_id"]],
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != encoded:
                raise ValueError("signal ID collision or immutable-record conflict")
            con.execute("COMMIT")
            return {"status": "already_stored", "signal_id": envelope["signal_id"]}
        con.execute(
            """INSERT INTO research_signals
               (signal_id, decision_time, symbol, horizon, record_json)
               VALUES (?, ?, ?, ?, ?::JSON)""",
            [envelope["signal_id"], decision_time, record["symbol"],
             record["horizon"], encoded],
        )
        con.execute("COMMIT")
        return {"status": "stored", "signal_id": envelope["signal_id"]}
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def store_outcome(*, signal_id: str, horizon: str, observed_at: str,
                  outcome: dict) -> dict:
    """Append one immutable, point-in-time research outcome for a stored signal."""
    if not isinstance(signal_id, str) or len(signal_id) != 64:
        raise ValueError("invalid signal_id")
    if horizon not in HORIZONS or not isinstance(outcome, dict):
        raise ValueError("invalid horizon or outcome")
    observed = _aware(observed_at)
    encoded_outcome = _canonical(outcome)
    con = connect()
    try:
        _ensure_tables(con)
        con.execute("BEGIN TRANSACTION")
        signal = con.execute(
            "SELECT decision_time, horizon FROM research_signals WHERE signal_id = ?",
            [signal_id],
        ).fetchone()
        if signal is None:
            raise ValueError("outcome requires an existing frozen signal")
        if signal[1] != horizon:
            raise ValueError("outcome horizon must match frozen signal horizon")
        if observed < signal[0]:
            raise ValueError("outcome cannot predate the signal decision")
        payload = {
            "signal_id": signal_id,
            "horizon": horizon,
            "observed_at": observed.isoformat(),
            "outcome": outcome,
            "classification": "research_outcome_not_execution",
        }
        outcome_id = hashlib.sha256(_canonical(payload).encode()).hexdigest()
        existing = con.execute(
            "SELECT outcome_json FROM research_outcomes WHERE outcome_id = ?",
            [outcome_id],
        ).fetchone()
        if existing is not None:
            if str(existing[0]) != _canonical(payload):
                raise ValueError("outcome ID collision or immutable-record conflict")
            con.execute("COMMIT")
            return {"status": "already_stored", "outcome_id": outcome_id}
        con.execute(
            """INSERT INTO research_outcomes
               (outcome_id, signal_id, horizon, observed_at, outcome_json)
               VALUES (?, ?, ?, ?, ?::JSON)""",
            [outcome_id, signal_id, horizon, observed, _canonical(payload)],
        )
        con.execute("COMMIT")
        return {"status": "stored", "outcome_id": outcome_id}
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def get_signal(signal_id: str) -> dict | None:
    con = connect()
    try:
        _ensure_tables(con)
        row = con.execute(
            "SELECT record_json FROM research_signals WHERE signal_id = ?",
            [signal_id],
        ).fetchone()
        return json.loads(str(row[0])) if row else None
    finally:
        con.close()


def list_signal_outcomes(signal_id: str) -> list[dict]:
    con = connect()
    try:
        _ensure_tables(con)
        rows = con.execute(
            """SELECT outcome_json FROM research_outcomes
               WHERE signal_id = ? ORDER BY observed_at, outcome_id""",
            [signal_id],
        ).fetchall()
        return [json.loads(str(row[0])) for row in rows]
    finally:
        con.close()


def list_signals(*, symbol: str | None = None, horizon: str | None = None,
                 limit: int = 500) -> list[dict]:
    """List frozen signal records in decision-time order; no mutable latest-state view."""
    if not 1 <= limit <= 5000:
        raise ValueError("limit_out_of_range")
    con = connect()
    try:
        _ensure_tables(con)
        clauses, params = [], []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.upper())
        if horizon:
            if horizon not in HORIZONS:
                raise ValueError("invalid_horizon")
            clauses.append("horizon = ?")
            params.append(horizon)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = con.execute(
            "SELECT record_json FROM research_signals" + where +
            " ORDER BY decision_time DESC, signal_id LIMIT ?", params + [limit]
        ).fetchall()
        return [json.loads(str(row[0])) for row in rows]
    finally:
        con.close()


def list_all_outcomes(*, horizon: str | None = None, limit: int = 2000) -> list[dict]:
    """List immutable outcome snapshots for research-only aggregate reporting."""
    if not 1 <= limit <= 10000:
        raise ValueError("limit_out_of_range")
    con = connect()
    try:
        _ensure_tables(con)
        if horizon is not None and horizon not in HORIZONS:
            raise ValueError("invalid_horizon")
        if horizon:
            rows = con.execute(
                "SELECT outcome_json FROM research_outcomes WHERE horizon = ? "
                "ORDER BY observed_at, outcome_id LIMIT ?", [horizon, limit]
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT outcome_json FROM research_outcomes "
                "ORDER BY observed_at, outcome_id LIMIT ?", [limit]
            ).fetchall()
        return [json.loads(str(row[0])) for row in rows]
    finally:
        con.close()
