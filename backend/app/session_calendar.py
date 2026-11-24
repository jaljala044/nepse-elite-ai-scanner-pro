"""Evidence-led NEPSE session calendar and OHLCV integrity audit.

A weekday schedule is only a candidate generator. A date becomes a verified
session/closure only through an explicit evidence row in the calendar CSV.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

CALENDAR_FIELDS = ("date", "status", "source_id", "evidence_uri", "verified_at_utc", "notes")
OHLCV_FIELDS = ("symbol", "date", "open", "high", "low", "close", "volume")
REGIMES = (
    # The 2026 schedule transition is a candidate rule only; dates still need evidence.
    (date.min, date(2026, 4, 5), {6}, "Sunday-Thursday candidate; Friday/Saturday excluded"),
    (date(2026, 4, 6), date.max, {5, 6}, "Monday-Friday candidate; Saturday/Sunday excluded"),
)


def schedule_candidate(day: date) -> tuple[bool, str]:
    for start, end, closed_weekdays, note in REGIMES:
        if start <= day <= end:
            return day.weekday() not in closed_weekdays, note
    return False, "no schedule regime"


def load_calendar(path: str | Path) -> dict[date, dict[str, str]]:
    entries: dict[date, dict[str, str]] = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(CALENDAR_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("calendar missing columns: " + ", ".join(sorted(missing)))
        for line, raw in enumerate(reader, 2):
            day = date.fromisoformat(raw["date"].strip())
            status = raw["status"].strip()
            if status not in {"verified_open", "verified_closed"}:
                raise ValueError(f"line {line}: status must be verified_open or verified_closed")
            if not raw["source_id"].strip() or not raw["evidence_uri"].strip() or not raw["verified_at_utc"].strip():
                raise ValueError(f"line {line}: verified calendar rows require source_id, evidence_uri and verified_at_utc")
            if day in entries:
                raise ValueError(f"line {line}: duplicate calendar date {day}")
            entries[day] = {k: (v or "").strip() for k, v in raw.items()}
    return entries


def classify_date(day: date, evidence: dict[date, dict[str, str]]) -> dict[str, Any]:
    explicit = evidence.get(day)
    if explicit:
        return {"classification": explicit["status"], "evidence": explicit["evidence_uri"],
                "source_id": explicit["source_id"], "reason": explicit["notes"]}
    candidate, note = schedule_candidate(day)
    return {"classification": "unverified_session_candidate" if candidate else "unverified_non_session_candidate",
            "evidence": None, "source_id": None, "reason": note}


def audit_ohlcv(paths: list[str | Path], calendar_path: str | Path) -> dict[str, Any]:
    evidence = load_calendar(calendar_path)
    rows_seen = 0
    accepted = 0
    quarantined: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], dict[str, str]] = {}
    repeats: list[dict[str, Any]] = []
    per_file: list[dict[str, Any]] = []
    for input_path in paths:
        path = Path(input_path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        file_rows = 0
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = set(OHLCV_FIELDS) - set(reader.fieldnames or [])
            if missing:
                quarantined.append({"file": str(path), "line": 1, "reason": "missing_columns:" + ",".join(sorted(missing))})
                per_file.append({"file": str(path), "sha256": digest, "rows": 0})
                continue
            for line, raw in enumerate(reader, 2):
                rows_seen += 1
                file_rows += 1
                row = {k: (raw.get(k) or "").strip() for k in OHLCV_FIELDS}
                try:
                    day = date.fromisoformat(row["date"])
                    symbol = row["symbol"].upper()
                    if not symbol:
                        raise ValueError("missing_symbol")
                    nums = {k: float(row[k].replace(",", "")) for k in ("open", "high", "low", "close", "volume")}
                    if any(v < 0 for v in nums.values()) or any(nums[k] <= 0 for k in ("open", "high", "low", "close")):
                        raise ValueError("non_positive_price_or_negative_volume")
                    if nums["high"] < max(nums["open"], nums["close"], nums["low"]) or nums["low"] > min(nums["open"], nums["close"], nums["high"]):
                        raise ValueError("invalid_ohlc_bounds")
                    cls = classify_date(day, evidence)
                    if cls["classification"] != "verified_open":
                        raise ValueError("date_not_verified_open:" + cls["classification"])
                    key = (symbol, day.isoformat())
                    comparable = {k: row[k] for k in OHLCV_FIELDS if k != "symbol"}
                    if key in seen:
                        if seen[key] == comparable:
                            raise ValueError("exact_duplicate_symbol_date")
                        raise ValueError("conflicting_duplicate_symbol_date")
                    seen[key] = comparable
                    accepted += 1
                except Exception as exc:
                    quarantined.append({"file": str(path), "line": line, "symbol": row.get("symbol"),
                                        "date": row.get("date"), "reason": str(exc), "raw": raw})
        per_file.append({"file": str(path), "sha256": digest, "rows": file_rows})
    return {
        "calendar_file": str(calendar_path),
        "calendar_sha256": hashlib.sha256(Path(calendar_path).read_bytes()).hexdigest(),
        "rows_seen": rows_seen, "rows_accepted": accepted, "rows_quarantined": len(quarantined),
        "verified_calendar_dates": len(evidence), "files": per_file, "quarantine": quarantined,
        "gate_pass": rows_seen > 0 and not quarantined,
        "gate_note": "A pass applies only to supplied files and explicit calendar evidence; it is not proof of archive completeness.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calendar", required=True, help="Evidence-backed CSV calendar")
    parser.add_argument("--input", required=True, help="CSV file or directory of CSV files")
    parser.add_argument("--output", default="data/reports/ohlcv-session-integrity.json")
    args = parser.parse_args()
    root = Path(args.input)
    files = sorted(root.glob("*.csv")) if root.is_dir() else [root]
    report = audit_ohlcv(files, args.calendar)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("rows_seen", "rows_accepted", "rows_quarantined", "verified_calendar_dates", "gate_pass", "gate_note")}, indent=2))
    if not report["gate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
