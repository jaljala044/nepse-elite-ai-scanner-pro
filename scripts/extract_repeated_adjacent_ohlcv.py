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
        if prior in open_index and current in open_index:
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
        "calendar_status": "not_verified_primary_exchange_evidence_missing",
        "classification": "review_only_not_invalid",
        "source_files_read_only": True,
    }
    if calendar_summary:
        summary["project_calendar_join"] = calendar_summary
    (args.out / "repeated_adjacent_ohlcv_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
