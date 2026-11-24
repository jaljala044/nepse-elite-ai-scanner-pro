#!/usr/bin/env python3
"""Select a recent 90–120-session acquisition window using explicit calendar evidence.

This tool never equates a dated source file or weekday with a verified NEPSE
trading session. Only calendar rows marked verified_open count toward the target.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


def load_calendar(path: str | Path) -> dict[date, dict[str, str]]:
    result: dict[date, dict[str, str]] = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        import csv
        for line_no, row in enumerate(csv.DictReader(handle), 2):
            try:
                day = date.fromisoformat(row["date"])
                status = row["status"].strip()
                source_id = row["source_id"].strip()
                evidence_uri = row["evidence_uri"].strip()
                if status not in {"verified_open", "verified_closed"}:
                    raise ValueError("status must be verified_open or verified_closed")
                if not source_id or not evidence_uri:
                    raise ValueError("verified calendar rows require source_id and evidence_uri")
                if day in result:
                    raise ValueError(f"duplicate calendar date {day}")
                result[day] = {"status": status, "source_id": source_id, "evidence_uri": evidence_uri}
            except (KeyError, ValueError, AttributeError) as exc:
                raise ValueError(f"{path}:{line_no}: invalid calendar row: {exc}") from exc
    return result


def load_source_dates(paths: list[str | Path]) -> dict[date, dict[str, list[str]]]:
    result: dict[date, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, str]] = set()
    for manifest in paths:
        with Path(manifest).open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    day = date.fromisoformat(str(row["date"]))
                    source = str(row.get("repo_id") or row.get("repository") or row.get("source_id") or row.get("source") or "").strip()
                    path = str(row["path"]).strip()
                    if not source or not path:
                        raise ValueError("source identifier and path are required")
                    key = (source, path)
                    if key in seen:
                        raise ValueError(f"duplicate source/path entry: {source}:{path}")
                    seen.add(key)
                    result[day][source].append(path)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(f"{manifest}:{line_no}: invalid manifest row: {exc}") from exc
    return result


def build_target(
    manifests: list[str | Path],
    calendar_path: str | Path,
    minimum_sessions: int = 90,
    target_sessions: int = 120,
) -> dict[str, Any]:
    if minimum_sessions < 1 or target_sessions < minimum_sessions:
        raise ValueError("require 1 <= minimum_sessions <= target_sessions")
    calendar = load_calendar(calendar_path)
    source_dates = load_source_dates(manifests)
    verified_open = sorted(
        (day for day, row in calendar.items() if row["status"] == "verified_open"),
        reverse=True,
    )
    selected = verified_open[:target_sessions]
    selected_set = set(selected)
    rows = []
    for day in sorted(selected):
        by_source = source_dates.get(day, {})
        rows.append({
            "date": day.isoformat(),
            "calendar_evidence": calendar[day],
            "sources_present": sorted(by_source),
            "source_file_count": sum(len(v) for v in by_source.values()),
            "files": {source: sorted(paths) for source, paths in sorted(by_source.items())},
            "missing_from_sources": sorted({
                source for observed in source_dates.values() for source in observed
            } - set(by_source)),
        })
    all_observed_dates = sorted(source_dates)
    available_sources = sorted({source for by_source in source_dates.values() for source in by_source})
    recent_source_dates = []
    for day in all_observed_dates[-target_sessions:]:
        evidence = calendar.get(day)
        recent_source_dates.append({
            "date": day.isoformat(),
            "calendar_status": evidence["status"] if evidence else "unverified",
            "sources_present": sorted(source_dates[day]),
            "source_file_count": sum(len(paths) for paths in source_dates[day].values()),
        })
    return {
        "minimum_sessions": minimum_sessions,
        "target_sessions": target_sessions,
        "verified_open_sessions_available": len(verified_open),
        "verified_sessions_selected": len(selected),
        "minimum_target_met": len(selected) >= minimum_sessions,
        "preferred_target_met": len(selected) >= target_sessions,
        "selected_start_date": min(selected).isoformat() if selected else None,
        "selected_end_date": max(selected).isoformat() if selected else None,
        "source_manifest_date_count": len(all_observed_dates),
        "source_manifest_start_date": all_observed_dates[0].isoformat() if all_observed_dates else None,
        "source_manifest_end_date": all_observed_dates[-1].isoformat() if all_observed_dates else None,
        "sources": available_sources,
        "latest_source_dates_preview": recent_source_dates,
        "selected_sessions": rows,
        "interpretation": (
            "Only explicit verified_open calendar rows count. Source files on other dates "
            "are inventory evidence, not proof of trading sessions. Missing source files "
            "are reported and must be reconciled; they are never synthesized."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True)
    parser.add_argument("--calendar", required=True)
    parser.add_argument("--minimum-sessions", type=int, default=90)
    parser.add_argument("--target-sessions", type=int, default=120)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_target(args.manifest, args.calendar, args.minimum_sessions, args.target_sessions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "verified_open_sessions_available", "verified_sessions_selected",
        "minimum_target_met", "preferred_target_met", "selected_start_date", "selected_end_date"
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
