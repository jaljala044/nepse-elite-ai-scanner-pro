"""Append-only DuckDB persistence for broker behaviour memory snapshots.

This repository stores descriptive memory only. It never updates/deletes a
previous snapshot and never promotes broker flow into ownership or intent.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Iterable

import duckdb


class IdempotencyConflict(ValueError):
    """An idempotency key was reused with a different immutable payload."""


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class BrokerMemoryStore:
    """Append-only snapshot store; caller owns the database path."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return duckdb.connect(self.database_path)

    def _initialize(self):
        con = self._connect()
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS broker_memory_snapshots (
                    snapshot_id VARCHAR PRIMARY KEY,
                    idempotency_key VARCHAR NOT NULL UNIQUE,
                    as_of_date DATE NOT NULL,
                    available_at TIMESTAMPTZ NOT NULL,
                    security_id VARCHAR NOT NULL,
                    broker_entity_id VARCHAR NOT NULL,
                    window_name VARCHAR NOT NULL,
                    payload_json VARCHAR NOT NULL,
                    payload_sha256 VARCHAR NOT NULL,
                    methodology_version VARCHAR NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_broker_memory_lookup
                ON broker_memory_snapshots
                (security_id, broker_entity_id, as_of_date, window_name)
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS broker_memory_store_meta (
                    key VARCHAR PRIMARY KEY,
                    value VARCHAR NOT NULL
                )
            """)
            con.execute("""
                INSERT INTO broker_memory_store_meta VALUES
                ('schema_version', '1')
                ON CONFLICT (key) DO NOTHING
            """)
        finally:
            con.close()

    @staticmethod
    def _validate_snapshot(snapshot: dict):
        required = (
            "as_of_date", "security_id", "broker_entity_id", "window",
            "buy_amount", "sell_amount", "net_amount", "source_ids",
            "evidence_ids", "payload_hashes", "status",
        )
        if not isinstance(snapshot, dict) or any(k not in snapshot for k in required):
            raise ValueError("snapshot missing required broker memory fields")
        if snapshot["status"] != "descriptive_only":
            raise ValueError("only descriptive_only snapshots may be persisted")
        if not all(isinstance(snapshot[k], str) and snapshot[k].strip()
                   for k in ("security_id", "broker_entity_id")):
            raise ValueError("security_id and broker_entity_id must be nonblank strings")
        try:
            date.fromisoformat(snapshot["as_of_date"])
            for field in ("buy_amount", "sell_amount", "net_amount"):
                number = Decimal(str(snapshot[field]))
                if not number.is_finite():
                    raise ValueError(f"{field} must be finite")
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("invalid snapshot date or decimal") from exc
        if snapshot["window"] not in {"daily", "weekly", "monthly", "yearly"}:
            raise ValueError("unsupported snapshot window")
        for field in ("source_ids", "evidence_ids", "payload_hashes"):
            if not isinstance(snapshot[field], list) or not snapshot[field]:
                raise ValueError(f"{field} must be a non-empty list")

    def append(self, snapshot: dict, *, idempotency_key: str,
               methodology_version: str = "p4.31-v1",
               available_at: datetime | None = None) -> dict:
        """Append once. Exact replay is a no-op; key reuse with changed data fails."""
        self._validate_snapshot(snapshot)
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ValueError("idempotency_key must be nonblank")
        if not isinstance(methodology_version, str) or not methodology_version.strip():
            raise ValueError("methodology_version must be nonblank")
        available_at = available_at or datetime.now(timezone.utc)
        if available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")
        payload = _canonical_json(snapshot)
        payload_hash = _sha256(payload)
        snapshot_id = _sha256(idempotency_key + ":" + payload_hash)
        created_at = datetime.now(timezone.utc)
        con = self._connect()
        try:
            con.execute("BEGIN TRANSACTION")
            existing = con.execute("""
                SELECT snapshot_id, payload_sha256 FROM broker_memory_snapshots
                WHERE idempotency_key = ?
            """, [idempotency_key]).fetchone()
            if existing:
                if existing[1] != payload_hash:
                    raise IdempotencyConflict(
                        "idempotency key already exists with different immutable content"
                    )
                con.execute("COMMIT")
                return {"snapshot_id": existing[0], "inserted": False,
                        "idempotent_replay": True, "payload_sha256": payload_hash}
            con.execute("""
                INSERT INTO broker_memory_snapshots VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                snapshot_id, idempotency_key, date.fromisoformat(snapshot["as_of_date"]),
                available_at, snapshot["security_id"], snapshot["broker_entity_id"],
                snapshot["window"], payload, payload_hash, methodology_version, created_at,
            ])
            con.execute("COMMIT")
            return {"snapshot_id": snapshot_id, "inserted": True,
                    "idempotent_replay": False, "payload_sha256": payload_hash}
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def append_many(self, snapshots: Iterable[dict], *, key_prefix: str,
                    methodology_version: str = "p4.31-v1",
                    available_at: datetime | None = None) -> dict:
        """Append snapshots individually; repeated batches are idempotent."""
        results = []
        for index, snapshot in enumerate(snapshots):
            identity = "|".join((
                key_prefix, str(snapshot.get("security_id", "")),
                str(snapshot.get("broker_entity_id", "")),
                str(snapshot.get("as_of_date", "")), str(snapshot.get("window", "")),
            ))
            results.append(self.append(
                snapshot, idempotency_key=identity,
                methodology_version=methodology_version, available_at=available_at,
            ))
        return {
            "received": len(results),
            "inserted": sum(x["inserted"] for x in results),
            "replayed": sum(x["idempotent_replay"] for x in results),
            "results": results,
        }

    def append_many_atomic(self, snapshots: Iterable[dict], *, key_prefix: str,
                           methodology_version: str = "p4.34-v1",
                           available_at: datetime | None = None) -> dict:
        """Atomically append a complete set; any conflict rolls back every insert."""
        if not isinstance(key_prefix, str) or not key_prefix.strip():
            raise ValueError("key_prefix must be nonblank")
        if not isinstance(methodology_version, str) or not methodology_version.strip():
            raise ValueError("methodology_version must be nonblank")
        available_at = available_at or datetime.now(timezone.utc)
        if available_at.tzinfo is None or available_at.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")
        prepared = {}
        received = 0
        for snapshot in snapshots:
            received += 1
            self._validate_snapshot(snapshot)
            identity = "|".join((key_prefix, str(snapshot["security_id"]),
                str(snapshot["broker_entity_id"]), str(snapshot["as_of_date"]),
                str(snapshot["window"])))
            payload = _canonical_json(snapshot)
            digest = _sha256(payload)
            snapshot_id = _sha256(identity + ":" + digest)
            if identity in prepared and prepared[identity]["payload_sha256"] != digest:
                raise IdempotencyConflict("batch contains conflicting duplicate snapshot keys")
            prepared[identity] = {"snapshot": snapshot, "payload": payload,
                "payload_sha256": digest, "snapshot_id": snapshot_id}
        con = self._connect()
        inserted, replayed, results = 0, 0, []
        try:
            con.execute("BEGIN TRANSACTION")
            for identity, item in prepared.items():
                existing = con.execute(
                    "SELECT snapshot_id, payload_sha256 FROM broker_memory_snapshots WHERE idempotency_key = ?",
                    [identity]).fetchone()
                if existing and existing[1] != item["payload_sha256"]:
                    raise IdempotencyConflict(
                        "idempotency key already exists with different immutable content")
                item["existing"] = existing
            created_at = datetime.now(timezone.utc)
            for identity, item in prepared.items():
                if item["existing"]:
                    replayed += 1
                    results.append({"snapshot_id": item["existing"][0], "inserted": False,
                        "idempotent_replay": True, "payload_sha256": item["payload_sha256"]})
                    continue
                snap = item["snapshot"]
                con.execute("INSERT INTO broker_memory_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                    item["snapshot_id"], identity, date.fromisoformat(snap["as_of_date"]),
                    available_at, snap["security_id"], snap["broker_entity_id"], snap["window"],
                    item["payload"], item["payload_sha256"], methodology_version, created_at])
                inserted += 1
                results.append({"snapshot_id": item["snapshot_id"], "inserted": True,
                    "idempotent_replay": False, "payload_sha256": item["payload_sha256"]})
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()
        return {"received": received, "unique_snapshots": len(prepared),
            "inserted": inserted, "replayed": replayed, "results": results}

    def get_as_of(self, *, security_id: str, broker_entity_id: str,
                  as_of_date: str, available_by: datetime | None = None) -> list[dict]:
        """Return snapshots visible by both event cutoff and availability cutoff."""
        cutoff = date.fromisoformat(as_of_date)
        available_by = available_by or datetime.now(timezone.utc)
        if available_by.tzinfo is None:
            raise ValueError("available_by must be timezone-aware")
        con = self._connect()
        try:
            rows = con.execute("""
                SELECT payload_json, payload_sha256, methodology_version,
                       available_at, created_at
                FROM broker_memory_snapshots
                WHERE security_id = ? AND broker_entity_id = ?
                  AND as_of_date <= ? AND available_at <= ?
                ORDER BY as_of_date, window_name, created_at
            """, [security_id, broker_entity_id, cutoff, available_by]).fetchall()
        finally:
            con.close()
        return [{
            "snapshot": json.loads(row[0]), "payload_sha256": row[1],
            "methodology_version": row[2], "available_at": row[3].isoformat(),
            "created_at": row[4].isoformat(),
        } for row in rows]

    def count(self) -> int:
        con = self._connect()
        try:
            return con.execute("SELECT COUNT(*) FROM broker_memory_snapshots").fetchone()[0]
        finally:
            con.close()
