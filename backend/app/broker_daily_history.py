"""Immutable, point-in-time daily broker/security observation ledger.

Only P4.33 memory-eligible batches accompanied by P4.35 complete-source and
identity-coverage attestations may be appended. Missing records are not converted
to zero here; P4.37 may infer zero activity only for dates with a complete manifest.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb

from app.broker_ingestion import IngestionReport


class DailyHistoryRejected(ValueError):
    """A daily batch did not meet the evidence admission contract."""


class DailyHistoryConflict(ValueError):
    """A natural key was replayed with changed immutable content."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _aware_timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        raise DailyHistoryRejected(f"invalid_{field}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DailyHistoryRejected(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise DailyHistoryRejected(f"invalid_{field}") from None
    if not parsed.is_finite() or parsed < 0:
        raise DailyHistoryRejected(f"invalid_{field}")
    return parsed


class BrokerDailyHistoryStore:
    """Append-only DuckDB ledger and complete-session evidence manifest."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        con = self._connect()
        try:
            con.execute("""
                CREATE TABLE IF NOT EXISTS broker_daily_observations (
                    observation_id VARCHAR PRIMARY KEY,
                    natural_key VARCHAR NOT NULL UNIQUE,
                    security_id VARCHAR NOT NULL,
                    broker_id VARCHAR NOT NULL,
                    session_date DATE NOT NULL,
                    side VARCHAR NOT NULL,
                    amount DECIMAL(38, 8) NOT NULL,
                    quantity DECIMAL(38, 8) NOT NULL,
                    source_id VARCHAR NOT NULL,
                    evidence_id VARCHAR NOT NULL,
                    source_payload_sha256 VARCHAR NOT NULL,
                    source_row_count INTEGER NOT NULL,
                    coverage_ratio DECIMAL(12, 10) NOT NULL,
                    batch_id VARCHAR NOT NULL,
                    available_at TIMESTAMPTZ NOT NULL,
                    status VARCHAR NOT NULL CHECK (status = 'descriptive_only'),
                    payload_json VARCHAR NOT NULL,
                    inserted_at TIMESTAMPTZ NOT NULL
                )
            """)
            for column, sql_type in (
                ("raw_capture_sha256", "VARCHAR"),
                ("raw_capture_batch_id", "VARCHAR"),
                ("raw_capture_captured_at", "TIMESTAMPTZ"),
                ("raw_capture_available_at", "TIMESTAMPTZ"),
                ("parser_name", "VARCHAR"),
                ("parser_version", "VARCHAR"),
                ("reconciliation_sha256", "VARCHAR"),
            ):
                con.execute(
                    f"ALTER TABLE broker_daily_observations ADD COLUMN IF NOT EXISTS {column} {sql_type}"
                )
            con.execute("""
                CREATE TABLE IF NOT EXISTS broker_daily_session_manifests (
                    session_date DATE PRIMARY KEY,
                    batch_id VARCHAR NOT NULL,
                    source_coverage_status VARCHAR NOT NULL,
                    source_coverage_ratio DECIMAL(12, 10) NOT NULL,
                    source_control_reconciled BOOLEAN NOT NULL,
                    identity_coverage_status VARCHAR NOT NULL,
                    identity_coverage_rows INTEGER NOT NULL,
                    identity_coverage_min DECIMAL(12, 10) NOT NULL,
                    verified_session BOOLEAN NOT NULL,
                    available_at TIMESTAMPTZ NOT NULL,
                    manifest_sha256 VARCHAR NOT NULL,
                    manifest_json VARCHAR NOT NULL
                )
            """)
        finally:
            con.close()

    def _connect(self):
        return duckdb.connect(self.database_path)

    def append_validated_daily_batch(
        self, report: IngestionReport, *, coverage_manifest: dict,
        raw_capture_manifest: dict | None = None,
        reconciliation_sha256: str | None = None,
    ) -> dict:
        """Atomically append one fully reconciled session and its completeness proof.

        coverage_manifest is the P4.35 adapter result's coverage attestation:
        source_coverage_status='complete', source_control_reconciled=True,
        identity_coverage_status='complete', all identity coverage rows >= 0.95,
        verified_session=True, and a timezone-aware available_at.
        """
        if not isinstance(report, IngestionReport) or not report.memory_eligible:
            raise DailyHistoryRejected("batch_not_memory_eligible")
        if not isinstance(coverage_manifest, dict):
            raise DailyHistoryRejected("coverage_manifest_required")
        required = ("session_date", "source_coverage_status", "source_coverage_ratio",
                    "source_control_reconciled", "identity_coverage_status",
                    "identity_coverage_rows", "identity_coverage_min",
                    "verified_session", "available_at")
        if any(key not in coverage_manifest for key in required):
            raise DailyHistoryRejected("coverage_manifest_missing_fields")

        try:
            session = date.fromisoformat(coverage_manifest["session_date"])
        except (TypeError, ValueError):
            raise DailyHistoryRejected("invalid_manifest_session_date") from None
        if coverage_manifest["source_coverage_status"] != "complete":
            raise DailyHistoryRejected("source_coverage_not_complete")
        if coverage_manifest["identity_coverage_status"] != "complete":
            raise DailyHistoryRejected("identity_coverage_not_complete")
        if coverage_manifest["source_control_reconciled"] is not True:
            raise DailyHistoryRejected("source_controls_not_reconciled")
        if coverage_manifest["verified_session"] is not True:
            raise DailyHistoryRejected("exchange_session_not_verified")
        try:
            source_ratio = Decimal(str(coverage_manifest["source_coverage_ratio"]))
            identity_min = Decimal(str(coverage_manifest["identity_coverage_min"]))
            identity_rows = int(coverage_manifest["identity_coverage_rows"])
        except (InvalidOperation, TypeError, ValueError):
            raise DailyHistoryRejected("invalid_manifest_coverage") from None
        if (not source_ratio.is_finite() or source_ratio < Decimal("0.95")
                or source_ratio > 1 or not identity_min.is_finite()
                or identity_min < Decimal("0.95") or identity_min > 1
                or identity_rows < 1):
            raise DailyHistoryRejected("manifest_coverage_below_threshold")
        available_at = _aware_timestamp(coverage_manifest["available_at"], "available_at")
        if available_at.date() < session:
            raise DailyHistoryRejected("manifest_available_before_session_date")

        lineage = None
        if raw_capture_manifest is not None:
            lineage_required = ("source_id", "trade_date", "raw_sha256", "parser_name",
                                "parser_version", "capture_id")
            if any(not isinstance(raw_capture_manifest.get(k), str)
                   or not raw_capture_manifest[k].strip() for k in lineage_required):
                raise DailyHistoryRejected("raw_capture_lineage_missing_fields")
            if raw_capture_manifest["trade_date"] != session.isoformat():
                raise DailyHistoryRejected("raw_capture_trade_date_mismatch")
            if len(raw_capture_manifest["raw_sha256"]) != 64 or any(
                    ch not in "0123456789abcdef" for ch in raw_capture_manifest["raw_sha256"].lower()):
                raise DailyHistoryRejected("invalid_raw_capture_sha256")
            if not isinstance(reconciliation_sha256, str) or len(reconciliation_sha256) != 64 or any(
                    ch not in "0123456789abcdef" for ch in reconciliation_sha256.lower()):
                raise DailyHistoryRejected("invalid_reconciliation_sha256")
            lineage = {
                "raw_capture_sha256": raw_capture_manifest["raw_sha256"].lower(),
                "raw_capture_batch_id": raw_capture_manifest["capture_id"],
                "raw_capture_captured_at": _aware_timestamp(
                    raw_capture_manifest["captured_at"], "raw_capture_captured_at").isoformat(),
                "raw_capture_available_at": _aware_timestamp(
                    raw_capture_manifest["available_at"], "raw_capture_available_at").isoformat(),
                "parser_name": raw_capture_manifest["parser_name"],
                "parser_version": raw_capture_manifest["parser_version"],
                "reconciliation_sha256": reconciliation_sha256.lower(),
            }

        if not report.accepted:
            raise DailyHistoryRejected("empty_daily_batch_is_unknown_not_zero")
        normalized = []
        seen_keys = {}
        for index, row in enumerate(report.accepted):
            if row.get("status") != "descriptive_only":
                raise DailyHistoryRejected("non_descriptive_observation")
            try:
                row_date = date.fromisoformat(row["session_date"])
            except (KeyError, TypeError, ValueError):
                raise DailyHistoryRejected(f"invalid_observation_session:{index}") from None
            if row_date != session:
                raise DailyHistoryRejected("batch_must_contain_exactly_one_session")
            if not all(isinstance(row.get(k), str) and row[k].strip()
                       for k in ("security_id", "broker_id", "source_id", "evidence_id",
                                 "source_payload_sha256", "batch_id")):
                raise DailyHistoryRejected(f"missing_observation_identity:{index}")
            if row["batch_id"] != report.batch_id:
                raise DailyHistoryRejected("batch_id_mismatch")
            if raw_capture_manifest is not None and row["source_id"] != raw_capture_manifest["source_id"]:
                raise DailyHistoryRejected("observation_source_capture_mismatch")
            side = str(row.get("side", "")).upper()
            if side not in {"BUY", "SELL"}:
                raise DailyHistoryRejected("invalid_observation_side")
            amount = _decimal(row.get("amount"), "amount")
            quantity = _decimal(row.get("quantity"), "quantity")
            coverage = _decimal(row.get("coverage_ratio"), "coverage_ratio")
            if coverage < Decimal("0.95") or coverage > 1:
                raise DailyHistoryRejected("observation_coverage_below_threshold")
            row_count = row.get("source_row_count")
            if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 1:
                raise DailyHistoryRejected("invalid_source_row_count")
            digest = row["source_payload_sha256"].lower()
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise DailyHistoryRejected("invalid_source_payload_hash")
            key_obj = [row["security_id"], row["broker_id"], session.isoformat(),
                       side, row["source_id"], row["evidence_id"]]
            natural_key = _canonical(key_obj)
            payload = {
                "natural_key": key_obj, "amount": str(amount), "quantity": str(quantity),
                "source_payload_sha256": digest, "source_row_count": row_count,
                "coverage_ratio": str(coverage), "batch_id": report.batch_id,
                "available_at": available_at.isoformat(), "status": "descriptive_only",
                **(lineage or {}),
            }
            payload_json = _canonical(payload)
            if natural_key in seen_keys and seen_keys[natural_key] != payload_json:
                raise DailyHistoryConflict("conflicting_duplicate_inside_batch")
            seen_keys[natural_key] = payload_json
            normalized.append((natural_key, payload, payload_json, amount, quantity,
                               coverage, row_count, key_obj, row))

        manifest = {
            "session_date": session.isoformat(), "batch_id": report.batch_id,
            "source_coverage_status": "complete", "source_coverage_ratio": str(source_ratio),
            "source_control_reconciled": True, "identity_coverage_status": "complete",
            "identity_coverage_rows": identity_rows, "identity_coverage_min": str(identity_min),
            "verified_session": True, "available_at": available_at.isoformat(),
        }
        manifest_json = _canonical(manifest)
        manifest_hash = _sha(manifest_json)

        con = self._connect()
        inserted = replayed = 0
        try:
            con.execute("BEGIN TRANSACTION")
            existing_manifest = con.execute(
                "SELECT manifest_sha256 FROM broker_daily_session_manifests WHERE session_date=?",
                [session],
            ).fetchone()
            if existing_manifest and existing_manifest[0] != manifest_hash:
                raise DailyHistoryConflict("session_manifest_conflict")
            for natural_key, payload, payload_json, amount, quantity, coverage, row_count, key_obj, row in normalized:
                old = con.execute(
                    "SELECT payload_json FROM broker_daily_observations WHERE natural_key=?",
                    [natural_key],
                ).fetchone()
                if old:
                    if old[0] != payload_json:
                        raise DailyHistoryConflict("daily_observation_conflict")
                    replayed += 1
                    continue
                observation_id = _sha(natural_key)
                con.execute("""
                    INSERT INTO broker_daily_observations (
                        observation_id, natural_key, security_id, broker_id, session_date,
                        side, amount, quantity, source_id, evidence_id, source_payload_sha256,
                        source_row_count, coverage_ratio, batch_id, available_at, status,
                        payload_json, inserted_at, raw_capture_sha256, raw_capture_batch_id,
                        raw_capture_captured_at, raw_capture_available_at,
                        parser_name, parser_version, reconciliation_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    observation_id, natural_key, row["security_id"], row["broker_id"],
                    session, str(row["side"]).upper(), amount, quantity, row["source_id"],
                    row["evidence_id"], row["source_payload_sha256"].lower(), row_count,
                    coverage, report.batch_id, available_at, "descriptive_only",
                    payload_json, datetime.now(timezone.utc),
                    (lineage or {}).get("raw_capture_sha256"),
                    (lineage or {}).get("raw_capture_batch_id"),
                    (lineage or {}).get("raw_capture_captured_at"),
                    (lineage or {}).get("raw_capture_available_at"),
                    (lineage or {}).get("parser_name"),
                    (lineage or {}).get("parser_version"),
                    (lineage or {}).get("reconciliation_sha256"),
                ])
                inserted += 1
            if not existing_manifest:
                con.execute("""
                    INSERT INTO broker_daily_session_manifests VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    session, report.batch_id, "complete", source_ratio, True, "complete",
                    identity_rows, identity_min, True, available_at, manifest_hash, manifest_json,
                ])
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()
        return {"session_date": session.isoformat(), "batch_id": report.batch_id,
                "inserted": inserted, "replayed": replayed,
                "manifest_inserted": existing_manifest is None,
                "status": "descriptive_only"}

    def observations_as_of(self, *, as_of_date: str, as_of_timestamp: str) -> list[dict]:
        cutoff_date = date.fromisoformat(as_of_date)
        cutoff_time = _aware_timestamp(as_of_timestamp, "as_of_timestamp")
        con = self._connect()
        try:
            rows = con.execute("""
                SELECT security_id, broker_id, CAST(session_date AS VARCHAR), side,
                       CAST(amount AS VARCHAR), CAST(quantity AS VARCHAR), source_id,
                       evidence_id, source_payload_sha256, source_row_count,
                       CAST(coverage_ratio AS VARCHAR), batch_id,
                       CAST(available_at AS VARCHAR), status, raw_capture_sha256,
                       raw_capture_batch_id, CAST(raw_capture_captured_at AS VARCHAR),
                       CAST(raw_capture_available_at AS VARCHAR), parser_name, parser_version,
                       reconciliation_sha256
                FROM broker_daily_observations
                WHERE session_date <= ? AND available_at <= ?
                ORDER BY session_date, security_id, broker_id, side, source_id, evidence_id
            """, [cutoff_date, cutoff_time]).fetchall()
        finally:
            con.close()
        keys = ("security_id", "broker_id", "session_date", "side", "amount", "quantity",
                "source_id", "evidence_id", "source_payload_sha256", "source_row_count",
                "coverage_ratio", "batch_id", "available_at", "status",
                "raw_capture_sha256", "raw_capture_batch_id", "raw_capture_captured_at",
                "raw_capture_available_at", "parser_name", "parser_version",
                "reconciliation_sha256")
        return [dict(zip(keys, row)) for row in rows]

    def complete_sessions_as_of(self, *, as_of_date: str, as_of_timestamp: str) -> list[str]:
        cutoff_date = date.fromisoformat(as_of_date)
        cutoff_time = _aware_timestamp(as_of_timestamp, "as_of_timestamp")
        con = self._connect()
        try:
            rows = con.execute("""
                SELECT CAST(session_date AS VARCHAR)
                FROM broker_daily_session_manifests
                WHERE session_date <= ? AND available_at <= ?
                  AND source_coverage_status='complete'
                  AND identity_coverage_status='complete'
                  AND source_control_reconciled=TRUE AND verified_session=TRUE
                ORDER BY session_date
            """, [cutoff_date, cutoff_time]).fetchall()
        finally:
            con.close()
        return [row[0] for row in rows]

    def count(self) -> int:
        con = self._connect()
        try:
            return con.execute("SELECT COUNT(*) FROM broker_daily_observations").fetchone()[0]
        finally:
            con.close()
