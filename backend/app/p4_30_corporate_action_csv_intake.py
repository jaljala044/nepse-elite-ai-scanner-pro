"""Step 95: strict CSV intake for source-level corporate-action assertions.

The loader preserves provenance and raw hashes; it does not fetch, reconcile,
approve, calculate factors, admit events, or mutate OHLCV.
"""
from __future__ import annotations
import csv
import hashlib
import io
from datetime import datetime
from typing import Any

REQUIRED_COLUMNS = {
    "action_id", "symbol", "security_id", "action_type", "announced_at",
    "available_at", "ex_date", "status", "publisher_id", "source_id",
    "source_tier", "evidence_sha256", "reviewer_id", "review_status",
}
OPTIONAL_COLUMNS = {"adjustment_factor", "factor_methodology_id"}

def _aware(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field}_invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed

def load_corporate_action_csv(*, raw_bytes: bytes, publisher_id: str, source_id: str,
                              source_tier: str, retrieved_at: str,
                              decision_cutoff: str) -> dict[str, Any]:
    """Parse one immutable CSV export and attach file-level provenance."""
    digest = hashlib.sha256(raw_bytes).hexdigest()
    errors: list[dict[str, Any]] = []
    try:
        retrieved = _aware(retrieved_at, "retrieved_at")
        cutoff = _aware(decision_cutoff, "decision_cutoff")
        if retrieved > cutoff:
            raise ValueError("csv_retrieved_after_decision_cutoff")
        if not publisher_id.strip() or not source_id.strip():
            raise ValueError("publisher_or_source_id_missing")
        if source_tier not in {"primary_nepse_or_cdsc", "independent_secondary"}:
            raise ValueError("source_tier_invalid")
        text = raw_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - headers)
        extra = sorted(headers - REQUIRED_COLUMNS - OPTIONAL_COLUMNS)
        if missing:
            raise ValueError("required_columns_missing:" + ",".join(missing))
        if extra:
            errors.append({"reason":"unrecognized_columns","columns":extra})
        records = []
        seen = set()
        for line, raw in enumerate(reader, start=2):
            row = {str(k).strip(): (v.strip() if isinstance(v,str) else v) for k,v in raw.items() if k}
            try:
                if any(not row.get(k) for k in REQUIRED_COLUMNS):
                    raise ValueError("required_cell_missing")
                if row["publisher_id"] != publisher_id or row["source_id"] != source_id:
                    raise ValueError("row_provenance_differs_from_file_manifest")
                if row["source_tier"] != source_tier:
                    raise ValueError("row_source_tier_differs_from_file_manifest")
                available = _aware(row["available_at"], "available_at")
                announced = _aware(row["announced_at"], "announced_at")
                if available > cutoff or announced > cutoff:
                    raise ValueError("row_after_decision_cutoff")
                if available < announced:
                    raise ValueError("available_at_precedes_announced_at")
                key = (row["action_id"], publisher_id, source_id)
                if key in seen:
                    raise ValueError("duplicate_action_source_row")
                seen.add(key)
                row["evidence_sha256"] = row["evidence_sha256"].lower()
                row["raw_file_sha256"] = digest
                row["raw_file_line"] = line
                row["retrieved_at"] = retrieved.isoformat()
                records.append(row)
            except ValueError as exc:
                errors.append({"line":line,"reason":str(exc)})
        status = "CSV_INTAKE_VERIFIED" if records and not errors else "CSV_INTAKE_BLOCKED"
        return {"status":status,"publisher_id":publisher_id,"source_id":source_id,
                "source_tier":source_tier,"retrieved_at":retrieved.isoformat(),
                "raw_file_sha256":digest,"byte_count":len(raw_bytes),
                "record_count":len(records),"records":records,"errors":errors,
                "event_admission_allowed":False,"price_adjustment_allowed":False}
    except (ValueError, UnicodeDecodeError) as exc:
        return {"status":"CSV_INTAKE_BLOCKED","publisher_id":publisher_id,
                "source_id":source_id,"raw_file_sha256":digest,"byte_count":len(raw_bytes),
                "record_count":0,"records":[],"errors":[{"reason":str(exc)}],
                "event_admission_allowed":False,"price_adjustment_allowed":False}
