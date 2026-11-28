"""Read-only, point-in-time symbol reconciliation for Issue #6."""
from __future__ import annotations
import argparse, csv, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REQUIRED = {"symbol", "security_id", "instrument_type", "status"}

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
    return rows, digest

def reconcile_snapshots(candidate_rows, provider_rows, *, candidate_sha256, provider_sha256,
                        candidate_observed_on, provider_observed_on) -> dict[str, Any]:
    left, right = defaultdict(list), defaultdict(list)
    for row in candidate_rows: left[row["symbol"]].append(row)
    for row in provider_rows: right[row["symbol"]].append(row)
    matrix = []
    for symbol in sorted(set(left) | set(right)):
        a, b = left.get(symbol, []), right.get(symbol, [])
        if not a: classification = "provider_only"
        elif not b: classification = "candidate_only"
        else:
            conflicts = [f for f in ("security_id", "instrument_type", "status")
                         if {x[f] for x in a} != {x[f] for x in b}]
            classification = "matched" if not conflicts else "identity_or_scope_conflict:" + ",".join(conflicts)
        if len(a) > 1: classification += "|duplicate_candidate_rows"
        if len(b) > 1: classification += "|duplicate_provider_rows"
        matrix.append({
            "symbol": symbol, "classification": classification,
            "candidate_rows": len(a), "provider_rows": len(b),
            "candidate_security_ids": sorted({x["security_id"] for x in a}),
            "provider_security_ids": sorted({x["security_id"] for x in b}),
            "candidate_instrument_types": sorted({x["instrument_type"] for x in a}),
            "provider_instrument_types": sorted({x["instrument_type"] for x in b}),
            "candidate_statuses": sorted({x["status"] for x in a}),
            "provider_statuses": sorted({x["status"] for x in b}),
        })
    counts = Counter(x["classification"].split("|", 1)[0] for x in matrix)
    return {
        "schema_version": "1.0",
        "candidate_snapshot": {"observed_on": candidate_observed_on, "sha256": candidate_sha256,
                               "row_count": len(candidate_rows), "unique_symbol_count": len(left)},
        "provider_snapshot": {"observed_on": provider_observed_on, "sha256": provider_sha256,
                              "row_count": len(provider_rows), "unique_symbol_count": len(right)},
        "summary": {
            "union_symbol_count": len(matrix), "matched_symbol_count": counts["matched"],
            "candidate_only_count": counts["candidate_only"], "provider_only_count": counts["provider_only"],
            "identity_or_scope_conflict_count": counts["identity_or_scope_conflict"],
            "duplicate_candidate_symbol_count": sum(len(v) > 1 for v in left.values()),
            "duplicate_provider_symbol_count": sum(len(v) > 1 for v in right.values()),
            "membership_authoritatively_verified": False, "canonical_promotion_allowed": False,
        },
        "matrix": matrix,
        "limitations": [
            "Current snapshots do not establish historical listing or delisting intervals.",
            "Symbol equality does not prove stable security identity across time.",
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
    candidate, ch = _load(args.candidate)
    provider, ph = _load(args.provider)
    report = reconcile_snapshots(candidate, provider, candidate_sha256=ch, provider_sha256=ph,
                                  candidate_observed_on=args.candidate_date,
                                  provider_observed_on=args.provider_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
