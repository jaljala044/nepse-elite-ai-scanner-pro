"""Evidence-gated, retrospective adjudication for Issue #5 equity date gaps.

No absence is inferred from an empty floorsheet or provider response. Only
explicit, source-identified, date-scoped evidence can change a gap's label.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

GAP_REQUIRED = {"repository", "symbol", "trade_date", "gap_status"}
EVIDENCE_REQUIRED = {
    "symbol", "trade_date", "evidence_kind", "authority", "source_id",
    "source_url", "evidence_sha256", "captured_at", "available_at",
    "effective_from", "effective_to", "rights_status",
}
GAP_STATUS = "UNCLASSIFIED_NO_TRADE_OR_MISSING_OR_LIFECYCLE"
OFFICIAL_KINDS = {
    "official_security_no_trade",
    "official_suspension",
    "official_not_listed",
}
OBSERVATION_KINDS = {"floorsheet_execution", "counterpart_valid_bar"}
ALLOWED_AUTHORITIES = {"NEPSE", "SEBON"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _day(value: str, field: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be canonical YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be canonical YYYY-MM-DD")
    return parsed


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be timezone-aware ISO-8601") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware ISO-8601")
    return parsed


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("missing columns: " + ", ".join(sorted(missing)))
        return [{key: (value or "").strip() for key, value in row.items()}
                for row in reader]


def adjudicate(gap_csv: Path, evidence_csv: Path, *, decision_cutoff: str | None = None) -> dict:
    gaps = _read_csv(gap_csv, GAP_REQUIRED)
    evidence = _read_csv(evidence_csv, EVIDENCE_REQUIRED)
    if not gaps:
        raise ValueError("gap inventory must not be empty")
    if not evidence:
        raise ValueError("evidence register must not be empty; use an explicit empty-register file only after documenting the retrieval attempt")

    cutoff = _timestamp(decision_cutoff, "decision_cutoff") if decision_cutoff else None
    gap_map: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen_gaps = set()
    for line, row in enumerate(gaps, start=2):
        symbol = row["symbol"].upper()
        day = row["trade_date"]
        _day(day, f"gap line {line} trade_date")
        if not symbol or row["gap_status"] != GAP_STATUS:
            raise ValueError(f"invalid gap identity or status at line {line}")
        key = (symbol, day)
        source_key = (row["repository"], symbol, day)
        if source_key in seen_gaps:
            raise ValueError(f"duplicate gap source key at line {line}: {source_key}")
        seen_gaps.add(source_key)
        gap_map[key].append(row)

    evidence_map: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen_evidence = set()
    for line, row in enumerate(evidence, start=2):
        symbol = row["symbol"].upper()
        day = row["trade_date"]
        _day(day, f"evidence line {line} trade_date")
        if not symbol or row["evidence_kind"] not in OFFICIAL_KINDS | OBSERVATION_KINDS:
            raise ValueError(f"invalid evidence identity or kind at line {line}")
        if not all(row[field] for field in (
            "authority", "source_id", "source_url", "evidence_sha256",
            "captured_at", "available_at", "effective_from", "rights_status",
        )):
            raise ValueError(f"incomplete evidence provenance at line {line}")
        if not SHA256_RE.fullmatch(row["evidence_sha256"]):
            raise ValueError(f"invalid evidence SHA-256 at line {line}")
        captured = _timestamp(row["captured_at"], f"evidence line {line} captured_at")
        available = _timestamp(row["available_at"], f"evidence line {line} available_at")
        if available < captured:
            raise ValueError(f"evidence available_at precedes captured_at at line {line}")
        effective_from = _day(row["effective_from"], f"evidence line {line} effective_from")
        effective_to = _day(row["effective_to"], f"evidence line {line} effective_to") if row["effective_to"] else None
        target = _day(day, f"evidence line {line} trade_date")
        if effective_to and effective_to < effective_from:
            raise ValueError(f"invalid evidence effective range at line {line}")
        if target < effective_from or (effective_to and target > effective_to):
            raise ValueError(f"evidence effective range does not cover trade date at line {line}")
        kind = row["evidence_kind"]
        if kind in OFFICIAL_KINDS:
            if row["authority"] not in ALLOWED_AUTHORITIES:
                raise ValueError(f"official disposition requires NEPSE/SEBON authority at line {line}")
            if row["rights_status"] != "approved":
                raise ValueError(f"official disposition evidence rights not approved at line {line}")
        elif row["rights_status"] != "approved":
            raise ValueError(f"observation evidence rights not approved at line {line}")
        key = (symbol, day)
        if key not in gap_map:
            raise ValueError(f"orphan evidence has no matching gap at line {line}: {key}")
        if kind == "official_security_no_trade" and row["authority"] != "NEPSE":
            raise ValueError(f"explicit no-trade evidence requires NEPSE authority at line {line}")
        if not row["source_url"].startswith("https://"):
            raise ValueError(f"evidence source_url must use HTTPS at line {line}")
        identity = (key, kind, row["source_id"], row["evidence_sha256"])
        if identity in seen_evidence:
            raise ValueError(f"duplicate evidence identity at line {line}")
        seen_evidence.add(identity)
        item = dict(row)
        item["_available"] = available
        evidence_map[key].append(item)

    results = []
    for key, source_gap_rows in sorted(gap_map.items()):
        records = evidence_map.get(key, [])
        kinds = {item["evidence_kind"] for item in records}
        official = kinds & OFFICIAL_KINDS
        observations = kinds & OBSERVATION_KINDS
        if len(official) > 1 or (official and observations):
            disposition = "conflicting_evidence_quarantined"
            reason = "official_disposition_and_or_execution_or_counterpart_observation_conflict"
        elif official == {"official_security_no_trade"}:
            disposition = "verified_no_trade"
            reason = "explicit_date_scoped_official_no_trade_evidence"
        elif official == {"official_suspension"}:
            disposition = "verified_suspended"
            reason = "explicit_date_scoped_official_suspension_evidence"
        elif official == {"official_not_listed"}:
            disposition = "verified_not_listed"
            reason = "explicit_date_scoped_official_not_listed_evidence"
        elif "floorsheet_execution" in observations:
            disposition = "execution_evidence_without_source_bar"
            reason = "rights_cleared_contract_evidence_requires_bar_reconciliation"
        elif "counterpart_valid_bar" in observations:
            disposition = "counterpart_bar_present_not_authoritative"
            reason = "other_source_bar_does_not_establish_authoritative_value"
        else:
            disposition = "unresolved_no_qualifying_evidence"
            reason = "no_explicit_date_scoped_qualifying_evidence"

        latest_available = max((item["_available"] for item in records), default=None)
        point_in_time_eligible = bool(
            cutoff and records and latest_available and latest_available <= cutoff
        )
        results.append({
            "symbol": key[0],
            "trade_date": key[1],
            "gap_source_count": len(source_gap_rows),
            "gap_sources": ";".join(sorted({r["repository"] for r in source_gap_rows})),
            "evidence_count": len(records),
            "evidence_kinds": ";".join(sorted(kinds)),
            "disposition": disposition,
            "reason": reason,
            "latest_evidence_available_at": latest_available.isoformat() if latest_available else "",
            "point_in_time_eligible_at_cutoff": point_in_time_eligible,
            "evidence_refs": ";".join(sorted({r["source_id"] for r in records})),
            "canonical_promotion_allowed": False,
            "training_promotion_allowed": False,
            "raw_source_modified": False,
        })

    counts = {}
    for row in results:
        counts[row["disposition"]] = counts.get(row["disposition"], 0) + 1
    return {
        "report_type": "issue5_evidence_gated_gap_adjudication",
        "gap_csv_sha256": hashlib.sha256(gap_csv.read_bytes()).hexdigest(),
        "evidence_csv_sha256": hashlib.sha256(evidence_csv.read_bytes()).hexdigest(),
        "gap_source_rows": len(gaps),
        "unique_symbol_date_keys": len(results),
        "evidence_rows": len(evidence),
        "disposition_counts": dict(sorted(counts.items())),
        "decision_cutoff": decision_cutoff,
        "adjudication_complete": False,
        "independent_review_required": True,
        "canonical_or_training_promotion": False,
        "raw_source_modified": False,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gaps", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--decision-cutoff")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    report = adjudicate(args.gaps, args.evidence, decision_cutoff=args.decision_cutoff)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "issue5_gap_adjudication.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = report["results"]
    fields = list(rows[0])
    with (args.output_dir / "issue5_gap_adjudication.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "unique_symbol_date_keys": report["unique_symbol_date_keys"],
        "disposition_counts": report["disposition_counts"],
        "adjudication_complete": False,
        "output_dir": str(args.output_dir),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
