#!/usr/bin/env python3
"""Build a deterministic, review-only row ledger from the pinned candidate CSV."""
from __future__ import annotations
import argparse, csv, hashlib, json, re
from datetime import date

REPOSITORIES = {
    "jaljala044/nepse-smc-data": "937cfcf93d78dfcf28a9f09bb13291447988157b",
    "jaljala044/nepse-history-starter": "b60728d39f34e0f9e428675d817fd52ed2784da6",
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")

def _date(value: str, field: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {field}: {value!r}") from None
    if parsed.isoformat() != value:
        raise ValueError(f"noncanonical {field}: {value!r}")
    return parsed
from pathlib import Path

FIELDS = [
    "repository", "symbol", "previous_date", "current_date",
    "previous_csv_line", "current_csv_line", "calendar_day_gap",
    "source_file_sha256", "source_commit", "ohlc_geometry_status",
    "row_structure_status", "date_gap_status", "session_completeness_status",
    "final_disposition", "review_reasons", "canonical_promotion_allowed",
    "training_promotion_allowed", "raw_source_modified",
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build(source: Path, output: Path) -> dict:
    rows = []
    seen_keys, seen_pairs = set(), set()
    with source.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"repository","commit_sha","path","file_sha256","symbol",
                    "previous_date","current_date","previous_csv_line","current_csv_line",
                    "calendar_day_gap","ohlc_bounds_valid"}
        headers = reader.fieldnames or []
        missing = required - set(headers)
        if missing:
            raise ValueError(f"candidate input missing columns: {sorted(missing)}")
        if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
            raise ValueError("candidate input headers must be nonblank and unique")
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"malformed candidate row at line {line}")
            repository = row["repository"].strip()
            symbol = row["symbol"].strip()
            path_value = row["path"].strip()
            commit = row["commit_sha"].strip()
            file_hash = row["file_sha256"].strip()
            if repository not in REPOSITORIES:
                raise ValueError(f"unknown candidate repository at line {line}")
            if commit != REPOSITORIES[repository] or not _COMMIT.fullmatch(commit):
                raise ValueError(f"candidate source commit is not approved at line {line}")
            if not symbol or symbol != symbol.upper() or not path_value:
                raise ValueError(f"invalid candidate identity at line {line}")
            if not _SHA256.fullmatch(file_hash):
                raise ValueError(f"invalid source file SHA-256 at line {line}")
            previous = _date(row["previous_date"], f"previous_date at line {line}")
            current = _date(row["current_date"], f"current_date at line {line}")
            if previous >= current:
                raise ValueError(f"previous_date must precede current_date at line {line}")
            try:
                previous_line = int(row["previous_csv_line"])
                current_line = int(row["current_csv_line"])
                gap = int(row["calendar_day_gap"])
            except (TypeError, ValueError):
                raise ValueError(f"invalid numeric candidate field at line {line}") from None
            if previous_line < 1 or current_line <= previous_line or gap < 1:
                raise ValueError(f"invalid source line or date-gap value at line {line}")
            geometry_value = row["ohlc_bounds_valid"].strip().lower()
            if geometry_value not in {"true", "false"}:
                raise ValueError(f"invalid OHLC geometry flag at line {line}")
            key = (repository, commit, path_value, str(previous_line), str(current_line))
            pair = (repository, path_value, str(previous_line), str(current_line))
            if key in seen_keys or pair in seen_pairs:
                raise ValueError(f"duplicate candidate occurrence: {key}")
            seen_keys.add(key); seen_pairs.add(pair)
            geometry_ok = geometry_value == "true"
            geometry = "PASS_CLEAN" if geometry_ok else "REVIEW_REQUIRED"
            gap_status = "NO_INTERVENING_CALENDAR_DATE" if gap == 1 else "REVIEW_REQUIRED"
            reasons = []
            if not geometry_ok:
                reasons.append("invalid_ohlc_geometry")
            if gap != 1:
                reasons.append("calendar_day_gap_requires_session_calendar_join")
            reasons.append("full_source_session_and_duplicate_date_review_pending")
            rows.append({
                "repository": repository, "symbol": symbol,
                "previous_date": previous.isoformat(), "current_date": current.isoformat(),
                "previous_csv_line": previous_line,
                "current_csv_line": current_line,
                "calendar_day_gap": gap,
                "source_file_sha256": file_hash, "source_commit": commit,
                "ohlc_geometry_status": geometry, "row_structure_status": "PASS_CLEAN",
                "date_gap_status": gap_status, "session_completeness_status": "REVIEW_REQUIRED",
                "final_disposition": "REVIEW_REQUIRED", "review_reasons": ";".join(reasons),
                "canonical_promotion_allowed": False, "training_promotion_allowed": False,
                "raw_source_modified": False,
            })
    # Preserve extractor order (source, path, source-line) for stable row identity.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    counts = {
        "candidate_rows": len(rows),
        "invalid_ohlc_geometry": sum(r["ohlc_geometry_status"] != "PASS_CLEAN" for r in rows),
        "multi_day_date_gap": sum(r["date_gap_status"] != "NO_INTERVENING_CALENDAR_DATE" for r in rows),
        "row_structure_pass": sum(r["row_structure_status"] == "PASS_CLEAN" for r in rows),
        "final_review_required": sum(r["final_disposition"] == "REVIEW_REQUIRED" for r in rows),
        "unique_source_occurrences": len(seen_keys),
        "canonical_promotion_allowed": False,
        "training_promotion_allowed": False,
        "source_rows_modified": False,
    }
    manifest = {
        "schema_version": "1.0",
        "input_file": str(source),
        "input_sha256": sha256(source),
        "output_file": str(output),
        "output_sha256": sha256(output),
        "output_bytes": output.stat().st_size,
        "counts": counts,
        "ordering": "preserved from deterministic pinned-source extractor",
        "review_status": "review_only_not_invalid",
        "limitations": [
            "Candidate structural checks do not establish full-source session completeness.",
            "Project calendar is a research baseline, not NEPSE certification.",
            "No source OHLCV row is modified, repaired, deleted, or promoted.",
        ],
    }
    return manifest

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    a = p.parse_args()
    manifest = build(a.input, a.output)
    a.manifest.parent.mkdir(parents=True, exist_ok=True)
    a.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
