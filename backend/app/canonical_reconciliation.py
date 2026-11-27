"""Cross-source OHLCV reconciliation and immutable canonical review ledger."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

_FIELDS = ("open", "high", "low", "close", "volume", "turnover")

def _aware(value):
    if not isinstance(value, str): return None
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None
    if parsed.tzinfo is None or parsed.utcoffset() is None: return None
    return parsed.astimezone(timezone.utc)

def _values(values):
    if not isinstance(values, Mapping): return None
    result = {}
    for field in _FIELDS:
        try: number = Decimal(str(values[field]))
        except (KeyError, InvalidOperation, TypeError, ValueError): return None
        if not number.is_finite() or (field != "turnover" and number <= 0) or (field == "turnover" and number < 0): return None
        result[field] = format(number.normalize(), "f")
    return result

def reconcile_ohlcv_batches(*, batches, expected_pairs, decision_cutoff, minimum_independent_sources=2):
    cutoff = _aware(decision_cutoff)
    if cutoff is None: raise ValueError("decision_cutoff_must_be_timezone_aware")
    if isinstance(minimum_independent_sources, bool) or not isinstance(minimum_independent_sources, int) or minimum_independent_sources < 1:
        raise ValueError("minimum_independent_sources_must_be_positive_integer")
    expected, reasons = set(), []
    for item in expected_pairs if isinstance(expected_pairs, list) else []:
        if not isinstance(item, Mapping) or not item.get("security_id") or not item.get("session_date"):
            reasons.append("expected_pair_malformed")
            continue
        expected.add((str(item["security_id"]), str(item["session_date"])))
    if not expected: reasons.append("expected_security_session_pairs_missing")
    observations, accepted_sources, rejected_sources, seen_source_ids = {}, [], [], set()
    for batch in batches if isinstance(batches, list) else []:
        if not isinstance(batch, Mapping):
            rejected_sources.append({"source_id": None, "reason": "batch_not_object"})
            continue
        source_id = batch.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip() or source_id in seen_source_ids:
            rejected_sources.append({"source_id": source_id, "reason": "source_id_missing_or_duplicate"})
            continue
        seen_source_ids.add(source_id)
        available, failures = _aware(batch.get("available_at")), []
        if batch.get("source_validation_status") != "verified": failures.append("source_not_verified")
        if batch.get("rights_status") != "approved": failures.append("rights_not_approved")
        if batch.get("finality_status") != "final": failures.append("source_finality_not_verified")
        if available is None: failures.append("available_at_invalid")
        elif available > cutoff: failures.append("source_available_after_cutoff")
        group = batch.get("independence_group")
        if batch.get("independence_review_status") != "approved" or not isinstance(group, str) or not group.strip():
            failures.append("source_independence_not_reviewed")
        raw_hash = str(batch.get("raw_sha256", "")).lower()
        if len(raw_hash) != 64 or any(ch not in "0123456789abcdef" for ch in raw_hash):
            failures.append("raw_sha256_invalid")
        rows = batch.get("rows")
        if not isinstance(rows, list): failures.append("rows_missing")
        if failures:
            rejected_sources.append({"source_id": source_id, "reasons": failures})
            continue
        accepted_sources.append(source_id)
        seen_keys = set()
        for row in rows:
            if not isinstance(row, Mapping) or row.get("status") != "valid_candidate": continue
            key = (str(row.get("security_id", "")), str(row.get("session_date", "")))
            if key not in expected: continue
            if key in seen_keys:
                rejected_sources.append({"source_id": source_id, "reasons": ["duplicate_security_session_in_batch"], "key": list(key)})
                continue
            seen_keys.add(key)
            values, line = _values(row.get("values")), row.get("line_number")
            if values is None or isinstance(line, bool) or not isinstance(line, int) or line < 2:
                rejected_sources.append({"source_id": source_id, "reasons": ["row_values_or_lineage_invalid"], "key": list(key)})
                continue
            observations.setdefault(key, []).append({
                "source_id": source_id, "independence_group": group,
                "raw_sha256": raw_hash, "source_row_number": line,
                "available_at": available.isoformat(), "values": values,
            })
    reconciled, quarantined, missing = [], [], []
    for key in sorted(expected):
        records = observations.get(key, [])
        if not records:
            missing.append({"security_id": key[0], "session_date": key[1], "reason": "no_admitted_source_observation"})
            continue
        groups = {}
        for record in records:
            signature = json.dumps(record["values"], sort_keys=True, separators=(",", ":"))
            groups.setdefault(signature, []).append(record)
        if len(groups) > 1:
            quarantined.append({"security_id": key[0], "session_date": key[1],
                "reason": "cross_source_value_conflict", "source_observations": records})
            continue
        independent = {record["independence_group"] for record in records}
        if len(independent) < minimum_independent_sources:
            quarantined.append({"security_id": key[0], "session_date": key[1],
                "reason": "insufficient_independently_reviewed_sources",
                "independent_source_count": len(independent), "source_observations": records})
            continue
        reconciled.append({"security_id": key[0], "session_date": key[1],
            "values": records[0]["values"],
            "source_ids": sorted({r["source_id"] for r in records}),
            "evidence_sha256": sorted({r["raw_sha256"] for r in records}),
            "source_row_numbers": sorted(
                [{"source_id": r["source_id"], "line_number": r["source_row_number"]} for r in records],
                key=lambda x: (x["source_id"], x["line_number"])),
            "independent_source_count": len(independent),
            "status": "cross_source_reconciled_research_only"})
    coverage = len(reconciled) / len(expected) if expected else 0.0
    clear = bool(expected) and not missing and not quarantined and not rejected_sources and not reasons
    body = {
        "schema_version": 1,
        "status": "research_only_reconciled" if clear else "partial_or_quarantined",
        "expected_pair_count": len(expected), "reconciled_pair_count": len(reconciled),
        "quarantined_pair_count": len(quarantined), "missing_pair_count": len(missing),
        "rejected_source_count": len(rejected_sources), "coverage_ratio": coverage,
        "reconciled": reconciled, "quarantined": quarantined, "missing": missing,
        "rejected_sources": rejected_sources, "reasons": reasons,
        "canonical_promotion_allowed": False, "production_promotion_allowed": False,
        "policy": "independent_source_groups_required_conflicts_quarantined_no_source_winner_no_production_promotion",
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**body, "ledger_sha256": digest}

def persist_reconciliation_ledger(root, ledger):
    if not isinstance(ledger, Mapping): raise ValueError("ledger_must_be_object")
    digest = ledger.get("ledger_sha256")
    body = {k: v for k, v in ledger.items() if k != "ledger_sha256"}
    actual = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if not isinstance(digest, str) or digest != actual: raise ValueError("ledger_sha256_mismatch")
    directory = Path(root).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (digest + ".ledger.json")
    encoded = (json.dumps(dict(ledger), sort_keys=True, indent=2) + "\n").encode()
    if path.exists():
        if path.is_symlink() or path.read_bytes() != encoded: raise RuntimeError("content_addressed_ledger_conflict")
        return {"path": str(path), "ledger_sha256": digest, "idempotent": True}
    with path.open("xb") as stream: stream.write(encoded)
    return {"path": str(path), "ledger_sha256": digest, "idempotent": False}
