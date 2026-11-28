"""Read-only, date-scoped symbol and security-ID reconciliation for Issue #6."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED = {"symbol", "security_id", "instrument_type", "status"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_date(value: str, field: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be canonical YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be canonical YYYY-MM-DD")
    return value


def _load(path: str | Path):
    p = Path(path)
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with p.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{p}: missing columns: {', '.join(sorted(missing))}")
        rows = []
        for line, row in enumerate(reader, start=2):
            item = {k: (v or "").strip() for k, v in row.items()}
            if not item["symbol"] or item["symbol"] != item["symbol"].upper():
                raise ValueError(f"{p}:{line}: symbol must be non-empty uppercase text")
            if not item["security_id"] or not item["instrument_type"] or not item["status"]:
                raise ValueError(f"{p}:{line}: security_id, instrument_type and status are required")
            rows.append(item)
    if not rows:
        raise ValueError(f"{p}: snapshot must not be empty")
    return rows, digest


def _validate_rows(rows, label):
    if not rows:
        raise ValueError(f"{label} snapshot must not be empty")
    for line, row in enumerate(rows, start=1):
        missing = REQUIRED - set(row)
        if missing:
            raise ValueError(f"{label} row {line} missing fields: {', '.join(sorted(missing))}")
        if (not row["symbol"] or row["symbol"] != row["symbol"].upper()
                or not row["security_id"] or not row["instrument_type"] or not row["status"]):
            raise ValueError(f"{label} row {line} has invalid identity fields")


def reconcile_snapshots(candidate_rows, provider_rows, *, candidate_sha256, provider_sha256,
                        candidate_observed_on, provider_observed_on) -> dict[str, Any]:
    _canonical_date(candidate_observed_on, "candidate_observed_on")
    _canonical_date(provider_observed_on, "provider_observed_on")
    for label, digest in (("candidate_sha256", candidate_sha256), ("provider_sha256", provider_sha256)):
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    _validate_rows(candidate_rows, "candidate")
    _validate_rows(provider_rows, "provider")

    left, right = defaultdict(list), defaultdict(list)
    for row in candidate_rows:
        left[row["symbol"]].append(row)
    for row in provider_rows:
        right[row["symbol"]].append(row)

    def id_to_symbols(rows):
        mapping = defaultdict(set)
        for row in rows:
            mapping[row["security_id"]].add(row["symbol"])
        return {key: sorted(value) for key, value in mapping.items() if len(value) > 1}

    candidate_id_collisions = id_to_symbols(candidate_rows)
    provider_id_collisions = id_to_symbols(provider_rows)
    matrix = []
    for symbol in sorted(set(left) | set(right)):
        a, b = left.get(symbol, []), right.get(symbol, [])
        if not a:
            classification = "provider_only"
        elif not b:
            classification = "candidate_only"
        else:
            conflicts = [field for field in ("security_id", "instrument_type", "status")
                         if {row[field] for row in a} != {row[field] for row in b}]
            classification = "matched" if not conflicts else "identity_or_scope_conflict:" + ",".join(conflicts)
        if len(a) > 1:
            classification += "|duplicate_candidate_rows"
        if len(b) > 1:
            classification += "|duplicate_provider_rows"
        candidate_reused = sorted({row["security_id"] for row in a
                                   if row["security_id"] in candidate_id_collisions})
        provider_reused = sorted({row["security_id"] for row in b
                                  if row["security_id"] in provider_id_collisions})
        if candidate_reused:
            classification += "|candidate_security_id_reused_across_symbols"
        if provider_reused:
            classification += "|provider_security_id_reused_across_symbols"
        matrix.append({
            "symbol": symbol,
            "classification": classification,
            "candidate_rows": len(a),
            "provider_rows": len(b),
            "candidate_security_ids": sorted({row["security_id"] for row in a}),
            "provider_security_ids": sorted({row["security_id"] for row in b}),
            "candidate_reused_security_ids": candidate_reused,
            "provider_reused_security_ids": provider_reused,
            "candidate_instrument_types": sorted({row["instrument_type"] for row in a}),
            "provider_instrument_types": sorted({row["instrument_type"] for row in b}),
            "candidate_statuses": sorted({row["status"] for row in a}),
            "provider_statuses": sorted({row["status"] for row in b}),
        })
    counts = Counter(row["classification"].split("|", 1)[0] for row in matrix)
    return {
        "schema_version": "1.1",
        "candidate_snapshot": {
            "observed_on": candidate_observed_on, "sha256": candidate_sha256,
            "row_count": len(candidate_rows), "unique_symbol_count": len(left),
        },
        "provider_snapshot": {
            "observed_on": provider_observed_on, "sha256": provider_sha256,
            "row_count": len(provider_rows), "unique_symbol_count": len(right),
        },
        "summary": {
            "union_symbol_count": len(matrix),
            "matched_symbol_count": counts["matched"],
            "candidate_only_count": counts["candidate_only"],
            "provider_only_count": counts["provider_only"],
            "identity_or_scope_conflict_count": counts["identity_or_scope_conflict"],
            "duplicate_candidate_symbol_count": sum(len(value) > 1 for value in left.values()),
            "duplicate_provider_symbol_count": sum(len(value) > 1 for value in right.values()),
            "candidate_security_id_collision_count": len(candidate_id_collisions),
            "provider_security_id_collision_count": len(provider_id_collisions),
            "candidate_security_id_collisions": candidate_id_collisions,
            "provider_security_id_collisions": provider_id_collisions,
            "membership_authoritatively_verified": False,
            "canonical_promotion_allowed": False,
        },
        "matrix": matrix,
        "limitations": [
            "Current snapshots do not establish historical listing or delisting intervals.",
            "Symbol equality does not prove stable security identity across time.",
            "A security ID reused across symbols is flagged, not automatically reconciled.",
            "Secondary-provider snapshots do not certify exchange membership.",
            "No target count is forced; unmatched and conflicting rows remain visible.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--provider", required=True, type=Path)
    parser.add_argument("--candidate-date", required=True)
    parser.add_argument("--provider-date", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    candidate, candidate_hash = _load(args.candidate)
    provider, provider_hash = _load(args.provider)
    report = reconcile_snapshots(
        candidate, provider, candidate_sha256=candidate_hash,
        provider_sha256=provider_hash, candidate_observed_on=args.candidate_date,
        provider_observed_on=args.provider_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
