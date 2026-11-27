#!/usr/bin/env python3
"""Read-only extraction of identical adjacent OHLCV rows from pinned archive checkouts."""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from datetime import date
from pathlib import Path
import sys
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.session_calendar import load_calendar

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

def annotate_calendar(rows: list[dict], calendar_path: Path) -> dict:
    """Annotate candidates against the explicit project calendar without tier promotion."""
    evidence = load_calendar(calendar_path)
    open_statuses = {"verified_open", "verified_exceptional_open", "project_accepted_open"}
    closed_statuses = {"verified_closed", "verified_exceptional_closed"}
    open_dates = sorted(day for day, item in evidence.items() if item["status"] in open_statuses)
    session_index = {day: index for index, day in enumerate(open_dates)}
    counts: Counter[str] = Counter()
    for row in rows:
        parsed = {}
        for field in ("previous_date", "current_date"):
            raw = row.get(field, "")
            try:
                day = date.fromisoformat(raw)
                if day.isoformat() != raw:
                    raise ValueError("noncanonical date")
                parsed[field] = day
            except (TypeError, ValueError):
                parsed[field] = None
        previous = parsed["previous_date"]
        current = parsed["current_date"]
        prev_item = evidence.get(previous) if previous else None
        curr_item = evidence.get(current) if current else None
        prev_status = prev_item["status"] if prev_item else "not_listed_in_project_calendar"
        curr_status = curr_item["status"] if curr_item else "not_listed_in_project_calendar"
        gap = None
        if prev_status in closed_statuses or curr_status in closed_statuses:
            pair = "contains_explicit_closure_date"
        elif previous is None or current is None:
            pair = "unparseable_or_noncanonical_date"
        elif prev_item is None or curr_item is None:
            pair = "date_not_listed_in_project_calendar"
        elif prev_status in open_statuses and curr_status in open_statuses:
            gap = session_index[current] - session_index[previous]
            if gap <= 0:
                pair = "non_increasing_or_duplicate_session_order"
            elif gap == 1:
                pair = "adjacent_project_sessions"
            else:
                pair = "intervening_project_sessions_omitted_from_source_rows"
        else:
            pair = "session_evidence_incomplete"
        row.update({
            "previous_session_classification": prev_status,
            "current_session_classification": curr_status,
            "previous_project_session_index": session_index.get(previous, ""),
            "current_project_session_index": session_index.get(current, ""),
            "project_session_index_gap": gap if gap is not None else "",
            "session_pair_classification": pair,
            "session_evidence_ids": "|".join(
                item["source_id"] for item in (prev_item, curr_item) if item and item.get("source_id")
            ),
        })
        counts[pair] += 1
    return {
        "calendar_sha256": sha256(calendar_path),
        "calendar_row_count": len(evidence),
        "project_open_session_count": len(open_dates),
        "calendar_status_counts": dict(sorted(Counter(item["status"] for item in evidence.values()).items())),
        "session_pair_classifications": dict(sorted(counts.items())),
        "calendar_policy": "project_accepted_open remains ShareSansar-derived research evidence, not NEPSE certification; verified tiers remain distinct; absent dates and weekdays are never inferred; all candidates remain review-only",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", action="append", nargs=3, metavar=("REPO", "COMMIT", "ROOT"), required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--calendar", type=Path, required=True)
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
    calendar_summary = annotate_calendar(all_rows, args.calendar)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "repeated_adjacent_ohlcv_candidates.csv"
    fields = ["repository", "commit_sha", "path", "file_sha256", "symbol",
              "previous_date", "current_date", "previous_csv_line", "current_csv_line",
              "calendar_day_gap", "ohlc_bounds_valid", "baseline_metric_eligible",
              "review_reason", "ohlcv", "classification",
              "previous_session_classification", "current_session_classification",
              "previous_project_session_index", "current_project_session_index",
              "project_session_index_gap", "session_pair_classification", "session_evidence_ids"]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({**row, "ohlcv": json.dumps(row["ohlcv"], sort_keys=True)})
    summary = {
        "method": "identical OHLCV signatures on consecutive CSV rows; date gap and OHLC bounds reported separately",
        "source_counts": per_source,
        "total_candidates": len(all_rows),
        "candidate_csv_sha256": sha256(csv_path),
        "baseline_metric_eligible_total": sum(r["baseline_metric_eligible"] for r in all_rows),
        **calendar_summary,
        "calendar_status": "project_accepted_research_baseline_with_explicit_closures_not_exchange_certified",
        "classification": "review_only_not_invalid",
        "source_files_read_only": True,
    }
    (args.out / "repeated_adjacent_ohlcv_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
