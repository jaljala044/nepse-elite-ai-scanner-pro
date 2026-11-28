#!/usr/bin/env python3
"""Read-only extraction of identical adjacent OHLCV rows from pinned archive checkouts."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from datetime import date
from pathlib import Path

FIELDS = ("Open", "High", "Low", "Close", "Volume")

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def ohlc_bounds_valid(values: dict[str, str]) -> bool:
    try:
        op, hi, lo, cl = (float(values[k]) for k in ("Open", "High", "Low", "Close"))
    except (KeyError, TypeError, ValueError):
        return False
    if not all(math.isfinite(v) for v in (op, hi, lo, cl)):
        return False
    return hi >= max(op, lo, cl) and lo <= min(op, hi, cl)

def extract(repo: str, commit: str, root: Path) -> list[dict]:
    out = []
    files = sorted(root.rglob("*_OHLCV.csv"))
    for path in files:
        rel = path.relative_to(root).as_posix()
        digest = sha256(path)
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            previous = None
            previous_line = None
            for line, row in enumerate(reader, start=2):
                current = {k: (row.get(k) or "").strip() for k in FIELDS}
                date_text = (row.get("Date") or row.get("date") or "").strip()
                symbol = (row.get("Symbol") or row.get("symbol") or path.stem.replace("_OHLCV", "")).strip()
                complete = all(current.values())
                if complete and previous is not None and current == previous["ohlcv"]:
                    try:
                        gap_days = (date.fromisoformat(date_text) - date.fromisoformat(previous["date"])).days
                    except (TypeError, ValueError):
                        gap_days = None
                    bounds_valid = ohlc_bounds_valid(current)
                    if gap_days == 1 and bounds_valid:
                        reason = "consecutive_calendar_date_valid_ohlc_bounds"
                    elif gap_days != 1:
                        reason = "adjacent_rows_but_calendar_date_gap_or_unparseable"
                    else:
                        reason = "repeated_signature_has_invalid_ohlc_bounds"
                    out.append({
                        "repository": repo, "commit_sha": commit, "path": rel,
                        "file_sha256": digest, "symbol": symbol,
                        "previous_date": previous["date"], "current_date": date_text,
                        "previous_csv_line": previous_line, "current_csv_line": line,
                        "calendar_day_gap": gap_days,
                        "ohlc_bounds_valid": bounds_valid,
                        "baseline_metric_eligible": gap_days == 1 and bounds_valid,
                        "review_reason": reason,
                        "ohlcv": current,
                        "classification": "calendar_status_unverified_review_flag",
                    })
                previous = {"date": date_text, "ohlcv": current} if complete else None
                previous_line = line
    return out


def join_project_calendar(rows: list[dict], calendar_path: Path) -> tuple[list[dict], dict]:
    """Join candidate date pairs to the explicit project calendar without promoting rows."""
    calendar_sha = sha256(calendar_path)
    status_by_date: dict[str, str] = {}
    with calendar_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"date", "status"}.issubset(reader.fieldnames or []):
            raise ValueError("project calendar must contain date and status columns")
        for row in reader:
            day = (row.get("date") or "").strip()
            status = (row.get("status") or "").strip()
            if not day or day in status_by_date:
                raise ValueError(f"missing or duplicate project calendar date: {day!r}")
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError(f"noncanonical project calendar date: {day!r}")
            if status not in {"project_accepted_open", "verified_open", "verified_exceptional_open",
                              "verified_closed", "verified_exceptional_closed"}:
                raise ValueError(f"unsupported project calendar status: {status!r}")
            status_by_date[day] = status
    open_statuses = {"project_accepted_open", "verified_open", "verified_exceptional_open"}
    ordered_open = sorted(day for day, status in status_by_date.items() if status in open_statuses)
    open_index = {day: i for i, day in enumerate(ordered_open)}
    counts: dict[str, int] = {}
    by_source: dict[str, dict[str, int]] = {}
    for row in rows:
        prior, current = row["previous_date"], row["current_date"]
        prior_status = status_by_date.get(prior, "not_listed")
        current_status = status_by_date.get(current, "not_listed")
        gap = None
        try:
            prior_valid = date.fromisoformat(prior).isoformat() == prior
        except (TypeError, ValueError):
            prior_valid = False
        try:
            current_valid = date.fromisoformat(current).isoformat() == current
        except (TypeError, ValueError):
            current_valid = False
        if not prior_valid or not current_valid:
            classification = "malformed_candidate_date_review"
        elif prior in open_index and current in open_index:
            gap = open_index[current] - open_index[prior]
            if gap == 1:
                classification = "adjacent_project_sessions_review"
            elif gap > 1:
                classification = "intervening_project_sessions_missing_from_source_review"
            else:
                classification = "non_increasing_or_duplicate_session_order_review"
        elif prior_status.endswith("closed") or current_status.endswith("closed"):
            classification = "explicit_closure_date_conflict_review"
        else:
            classification = "date_not_in_project_calendar_review"
        row["previous_calendar_status"] = prior_status
        row["current_calendar_status"] = current_status
        row["project_session_gap"] = gap if gap is not None else ""
        row["session_join_classification"] = classification
        counts[classification] = counts.get(classification, 0) + 1
        source_counts = by_source.setdefault(row["repository"], {})
        source_counts[classification] = source_counts.get(classification, 0) + 1
    summary = {
        "calendar_file_sha256": calendar_sha,
        "calendar_dates_total": len(status_by_date),
        "project_accepted_open_dates": sum(v == "project_accepted_open" for v in status_by_date.values()),
        "verified_open_dates": sum(v in {"verified_open", "verified_exceptional_open"} for v in status_by_date.values()),
        "explicit_closure_dates": sum(v in {"verified_closed", "verified_exceptional_closed"} for v in status_by_date.values()),
        "session_join_counts": counts,
        "session_join_counts_by_source": by_source,
        "classification_policy": "calendar join only; all repeated OHLCV records remain review-only and no source data is modified",
    }
    return rows, summary

def unlisted_date_queue(rows: list[dict]) -> list[dict]:
    """Rank distinct missing calendar dates by affected pairs; never infer closure."""
    pending = {}
    for row in rows:
        if row.get("session_join_classification") not in {
            "date_not_in_project_calendar_review", "malformed_candidate_date_review"
        }:
            continue
        missing = {row[side + "_date"] for side, status in
                   (("previous", "previous_calendar_status"), ("current", "current_calendar_status"))
                   if row.get(status) == "not_listed"}
        for day in missing:
            item = pending.setdefault(day, {"pairs": 0, "symbols": set(), "repositories": set()})
            item["pairs"] += 1
            item["symbols"].add(row["symbol"])
            item["repositories"].add(row["repository"])
    result = []
    for day, item in pending.items():
        try:
            canonical = date.fromisoformat(day).isoformat() == day
        except ValueError:
            canonical = False
        result.append({"date": day, "valid_iso_date": canonical,
                       "affected_pairs": item["pairs"],
                       "distinct_symbols": len(item["symbols"]),
                       "repositories": sorted(item["repositories"]),
                       "disposition": "evidence_required" if canonical else "malformed_date_review",
                       "canonical_promotion_allowed": False})
    return sorted(result, key=lambda item: (-item["affected_pairs"], item["date"]))

def schedule_review_queue(queue: list[dict]) -> tuple[list[dict], dict]:
    """Apply the shared historical schedule as context, not closure evidence."""
    import sys
    backend = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend))
    from app.session_calendar import schedule_candidate
    reviewed, counts = [], {}
    for item in queue:
        if not item["valid_iso_date"]:
            label, note, weekday = "malformed_date_review", "", None
        else:
            day = date.fromisoformat(item["date"])
            expected_open, note = schedule_candidate(day)
            weekday = day.strftime("%A")
            label = "scheduled_open_evidence_required" if expected_open else "scheduled_non_session_evidence_required"
        reviewed.append({**item, "weekday": weekday, "schedule_classification": label,
                         "schedule_note": note, "independently_verified": False,
                         "canonical_promotion_allowed": False})
        bucket = counts.setdefault(label, {"dates": 0, "pair_date_incidences": 0})
        bucket["dates"] += 1
        bucket["pair_date_incidences"] += item["affected_pairs"]
    return reviewed, counts

def partition_integrity(rows: list[dict], calendar_applied: bool) -> dict:
    """Verify source-occurrence uniqueness, not cross-provider independence."""
    seen, counts = set(), {}
    allowed = {"adjacent_project_sessions_review", "intervening_project_sessions_missing_from_source_review",
               "non_increasing_or_duplicate_session_order_review", "explicit_closure_date_conflict_review",
               "date_not_in_project_calendar_review", "malformed_candidate_date_review"}
    for row in rows:
        key = tuple(row[k] for k in ("repository", "commit_sha", "path", "previous_csv_line", "current_csv_line"))
        if key in seen:
            raise ValueError(f"duplicate source occurrence: {key!r}")
        seen.add(key)
        label = row.get("session_join_classification", "calendar_join_not_applied")
        if calendar_applied and label not in allowed:
            raise ValueError(f"missing or invalid partition label: {label!r}")
        counts[label] = counts.get(label, 0) + 1
    if sum(counts.values()) != len(seen):
        raise ValueError("partition count mismatch")
    return {"source_occurrence_count": len(seen), "duplicate_source_occurrences": 0,
            "partition_counts": counts, "partition_total": sum(counts.values()),
            "scope": "source occurrence keys; economic security-date duplicates across sources are not deduplicated",
            "canonical_promotion_allowed": False}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", action="append", nargs=3, metavar=("REPO", "COMMIT", "ROOT"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--calendar", type=Path, help="Project-accepted NEPSE session calendar CSV")
    args = p.parse_args()
    all_rows = []
    per_source = {}
    for repo, commit, root in args.source:
        rows = extract(repo, commit, Path(root))
        per_source[repo] = {
            "total_adjacent_signature_candidates": len(rows),
            "baseline_metric_eligible": sum(r["baseline_metric_eligible"] for r in rows),
            "date_gap_or_unparseable": sum(r["review_reason"] == "adjacent_rows_but_calendar_date_gap_or_unparseable" for r in rows),
            "invalid_ohlc_bounds": sum(r["review_reason"] == "repeated_signature_has_invalid_ohlc_bounds" for r in rows),
        }
        all_rows.extend(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    calendar_summary = None
    if args.calendar:
        all_rows, calendar_summary = join_project_calendar(all_rows, args.calendar)
    integrity = partition_integrity(all_rows, calendar_summary is not None)
    csv_path = args.out / "repeated_adjacent_ohlcv_candidates.csv"
    fields = ["repository", "commit_sha", "path", "file_sha256", "symbol",
              "previous_date", "current_date", "previous_csv_line", "current_csv_line",
              "calendar_day_gap", "ohlc_bounds_valid", "baseline_metric_eligible",
              "review_reason", "ohlcv", "classification", "previous_calendar_status",
              "current_calendar_status", "project_session_gap", "session_join_classification"]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({**row, "ohlcv": json.dumps(row["ohlcv"], sort_keys=True)})
    summary = {
        "method": "identical OHLCV signatures on consecutive CSV rows; date gap and OHLC bounds reported separately",
        "source_counts": per_source,
        "total_candidates": len(all_rows),
        "baseline_metric_eligible_total": sum(r["baseline_metric_eligible"] for r in all_rows),
        "calendar_status": ("project_accepted_calendar_join_applied_not_exchange_certified"
                            if calendar_summary is not None else "calendar_join_not_applied"),
        "classification": "review_only_not_invalid",
        "source_files_read_only": True,
        "partition_integrity": integrity,
    }
    if calendar_summary:
        summary["project_calendar_join"] = calendar_summary
        queue = unlisted_date_queue(all_rows)
        (args.out / "unlisted_date_evidence_queue.json").write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
        reviewed, schedule_counts = schedule_review_queue(queue)
        (args.out / "unlisted_date_schedule_review.json").write_text(json.dumps(reviewed, indent=2) + "\n", encoding="utf-8")
        with (args.out / "unlisted_date_schedule_review.csv").open("w", encoding="utf-8", newline="") as stream:
            fields_review = ["date", "valid_iso_date", "affected_pairs", "distinct_symbols", "repositories", "disposition", "canonical_promotion_allowed", "weekday", "schedule_classification", "schedule_note", "independently_verified"]
            writer = csv.DictWriter(stream, fieldnames=fields_review)
            writer.writeheader()
            for item in reviewed:
                writer.writerow({**item, "repositories": json.dumps(item["repositories"])})
        summary["unlisted_date_schedule_review"] = {"counts": schedule_counts, "independently_verified_dates": 0, "promotion_allowed": False}
        summary["unlisted_date_queue"] = {"distinct_date_labels": len(queue),
            "valid_iso_dates": sum(item["valid_iso_date"] for item in queue),
            "top_10": queue[:10], "promotion_allowed": False}
    (args.out / "repeated_adjacent_ohlcv_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    from datetime import datetime, timezone
    files = ["repeated_adjacent_ohlcv_candidates.csv", "repeated_adjacent_ohlcv_summary.json"]
    if calendar_summary is not None:
        files += ["unlisted_date_evidence_queue.json", "unlisted_date_schedule_review.json", "unlisted_date_schedule_review.csv"]
    manifest = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "files": [{"path": name, "sha256": sha256(args.out / name), "bytes": (args.out / name).stat().st_size} for name in files], "canonical_promotion_allowed": False}
    (args.out / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
