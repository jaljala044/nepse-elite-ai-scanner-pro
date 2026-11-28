"""Shared explicit quarantine-marker gate; not a substitute for evidence validation."""
from collections.abc import Mapping
from datetime import date
import hashlib
import json
import os
from pathlib import Path

EXPECTED_QUARANTINE_REPOSITORIES = frozenset({
    "jaljala044/nepse-smc-data", "jaljala044/nepse-history-starter",
})


def is_quarantined(row: Mapping) -> bool:
    """Reject explicit quarantine markers, including unresolved ledger dispositions."""
    for key in ("row_status", "status", "disposition", "quarantine_status"):
        value = str(row.get(key, "")).strip().lower()
        if value.startswith("quarantin"):
            return True
    return bool(row.get("quarantined") or row.get("quarantine_reasons"))


def _canonical_day(value):
    """Accept canonical evidence strings or native date values from database rows."""
    # DuckDB returns DATE columns as datetime.date objects; preserve that typed
    # internal representation while rejecting datetime and noncanonical strings.
    if type(value) is date:
        return value.isoformat()
    if not isinstance(value, str):
        raise ValueError("date must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("date must be canonical YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError("date must be canonical YYYY-MM-DD")
    return value


def quarantine_keys(path, expected_sha256, *, expected_source_commits=None):
    """Load a pinned OHLCV exception ledger. Reject malformed or changed input."""
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_sha256.lower()):
        raise ValueError("invalid quarantine ledger digest")
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256.lower():
        raise ValueError("quarantine ledger hash mismatch")
    ledger = json.loads(raw)
    if not isinstance(ledger, dict):
        raise ValueError("invalid quarantine ledger schema")
    rows = ledger.get("exceptions") if isinstance(ledger, dict) else None
    source_audit = ledger.get("source_audit") if isinstance(ledger, dict) else None
    repositories = source_audit.get("repositories") if isinstance(source_audit, dict) else None
    report_digest = source_audit.get("source_audit_report_sha256") if isinstance(source_audit, dict) else None
    if ledger.get("schema_version") != "1.0" or not isinstance(rows, list):
        raise ValueError("invalid quarantine ledger schema")
    if (not isinstance(repositories, dict) or set(repositories) != EXPECTED_QUARANTINE_REPOSITORIES
            or not isinstance(report_digest, str) or len(report_digest) != 64
            or any(ch not in "0123456789abcdef" for ch in report_digest.lower())):
        raise ValueError("invalid quarantine ledger source audit")
    actual_source_commits = {}
    for repository, metadata in repositories.items():
        commit = metadata.get("commit_sha") if isinstance(metadata, dict) else None
        if not isinstance(repository, str) or not isinstance(commit, str) or len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit.lower()):
            raise ValueError("invalid quarantine ledger source commit")
        actual_source_commits[repository] = commit.lower()
    if expected_source_commits is not None and actual_source_commits != expected_source_commits:
        raise ValueError("quarantine ledger source commits stale")
    counts = ledger.get("counts")
    if (not isinstance(counts, dict) or type(counts.get("total_exception_records")) is not int
            or counts.get("total_exception_records") != len(rows)):
        raise ValueError("quarantine ledger count mismatch")
    keys = set()
    ids = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid runtime quarantine ledger record")
        identity = row.get("exception_id")
        symbol_value = row.get("symbol")
        disposition = row.get("disposition")
        if (not isinstance(identity, str) or not identity.strip() or identity in ids
                or not isinstance(symbol_value, str) or not symbol_value.strip()
                or not isinstance(disposition, str) or not disposition.strip()):
            raise ValueError("invalid runtime quarantine ledger record")
        ids.add(identity)
        symbol = symbol_value.strip().upper()
        try:
            day = _canonical_day(row.get("trade_date"))
        except ValueError as exc:
            raise ValueError("invalid runtime quarantine ledger record") from exc
        # No automatic release: every listed exception remains blocked.
        keys.add((symbol, day))
    return frozenset(keys)


def quarantine_gap_symbols(rows, keys):
    """Return symbols whose observed date span intersects a blocked session.

    A missing blocked candle must not silently bridge an indicator window.
    Only dates inside the observed inclusive span count; this does not certify
    the completeness of other sessions.
    """
    if not keys:
        return set()
    spans = {}
    for symbol, day in rows:
        symbol = symbol.strip().upper()
        day = _canonical_day(day)
        lo, hi = spans.get(symbol, (day, day))
        spans[symbol] = (min(lo, day), max(hi, day))
    return {symbol for symbol, day in keys if symbol in spans
            and spans[symbol][0] <= day <= spans[symbol][1]}


def reject_quarantined_history(rows, symbol, keys):
    """Reject entire history rather than bridging a missing candle."""
    symbol = symbol.strip().upper()
    rows = list(rows)
    if quarantine_gap_symbols(((symbol, row.get("session_date", row.get("trade_date", row.get("date")))) for row in rows), keys):
        raise ValueError("quarantined historical input or missing blocked session")
    for row in rows:
        day = row.get("session_date", row.get("trade_date", row.get("date")))
        if is_quarantined(row) or (symbol, _canonical_day(day)) in keys:
            raise ValueError("quarantined historical input")


def runtime_quarantine_keys(*, required=False):
    """Server-owned, digest- and source-version-pinned quarantine configuration."""
    required = required or os.environ.get("NEPSE_REQUIRE_QUARANTINE_LEDGER") == "1"
    path = os.environ.get("NEPSE_QUARANTINE_LEDGER")
    digest = os.environ.get("NEPSE_QUARANTINE_LEDGER_SHA256")
    source_commits_raw = os.environ.get("NEPSE_QUARANTINE_SOURCE_COMMITS")
    if not path and not digest and not source_commits_raw and not required:
        return None
    if not path or not digest:
        raise ValueError("pinned quarantine ledger required")
    if required and not source_commits_raw:
        raise ValueError("pinned quarantine source commits required")
    expected_source_commits = None
    if source_commits_raw:
        try:
            expected_source_commits = json.loads(source_commits_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid quarantine source commit pin") from exc
        if (not isinstance(expected_source_commits, dict) or set(expected_source_commits) != EXPECTED_QUARANTINE_REPOSITORIES
                or any(not isinstance(repo, str) or not isinstance(commit, str) or len(commit) != 40
                       or any(ch not in "0123456789abcdef" for ch in commit.lower())
                       for repo, commit in expected_source_commits.items())):
            raise ValueError("invalid quarantine source commit pin")
        expected_source_commits = {repo: commit.lower() for repo, commit in expected_source_commits.items()}
    try:
        return quarantine_keys(path, digest, expected_source_commits=expected_source_commits)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError("invalid runtime quarantine ledger") from exc


def ledger_blocked(row, keys, symbol=None):
    if is_quarantined(row):
        return True
    if keys is None:
        return False
    name = symbol if symbol is not None else row.get("symbol")
    day = row.get("session_date", row.get("trade_date", row.get("date")))
    if not isinstance(name, str) or not name.strip():
        raise ValueError("missing quarantine lookup symbol")
    return (name.strip().upper(), _canonical_day(day)) in keys


def filter_quarantined_feature_rows(rows, keys):
    """Withhold all price and broker observations for any affected symbol."""
    rows = list(rows)
    market_types = {"ohlcv", "broker"}

    def symbol(row):
        return str(row.get("symbol", "")).strip().upper()

    def blocked(row):
        return is_quarantined(row) or (
            row.get("record_type") in market_types and ledger_blocked(row, keys))

    affected = {symbol(row) for row in rows
                if row.get("record_type") in market_types and blocked(row)}
    affected.update(quarantine_gap_symbols(
        ((symbol(row), row.get("session_date", row.get("trade_date", row.get("date"))))
         for row in rows if row.get("record_type") in market_types and not is_quarantined(row)), keys))
    return [row for row in rows if not blocked(row) and not (
        row.get("record_type") in market_types and symbol(row) in affected)]
