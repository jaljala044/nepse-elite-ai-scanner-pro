#!/usr/bin/env python3
"""Build a deterministic, review-only row ledger from the pinned candidate CSV."""
from __future__ import annotations
import argparse, csv, hashlib, json
from datetime import date
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
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"candidate input missing columns: {sorted(missing)}")
        for row in reader:
            key = (row["repository"], row["commit_sha"], row["path"],
                   row["previous_csv_line"], row["current_csv_line"])
            pair = (row["repository"], row["path"], row["previous_csv_line"], row["current_csv_line"])
            if key in seen_keys or pair in seen_pairs:
                raise ValueError(f"duplicate candidate occurrence: {key}")
            seen_keys.add(key); seen_pairs.add(pair)
            try:
                gap = int(row["calendar_day_gap"])
            except (TypeError, ValueError):
                gap = None
            geometry_ok = row["ohlc_bounds_valid"].strip().lower() == "true"
            geometry = "PASS_CLEAN" if geometry_ok else "REVIEW_REQUIRED"
            gap_status = "NO_INTERVENING_CALENDAR_DATE" if gap == 1 else "REVIEW_REQUIRED"
            reasons = []
            if not geometry_ok:
                reasons.append("invalid_ohlc_geometry")
            if gap != 1:
                reasons.append("calendar_day_gap_requires_session_calendar_join")
            reasons.append("full_source_session_and_duplicate_date_review_pending")
            rows.append({
                "repository": row["repository"], "symbol": row["symbol"],
                "previous_date": row["previous_date"], "current_date": row["current_date"],
                "previous_csv_line": int(row["previous_csv_line"]),
                "current_csv_line": int(row["current_csv_line"]),
                "calendar_day_gap": gap if gap is not None else "",
                "source_file_sha256": row["file_sha256"], "source_commit": row["commit_sha"],
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
        "multi_day_or_unparseable_date_gap": sum(r["date_gap_status"] != "NO_INTERVENING_CALENDAR_DATE" for r in rows),
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
