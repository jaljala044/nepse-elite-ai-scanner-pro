#!/usr/bin/env python3
"""Cross-check recent market dates using audited OHLCV and SocrateAI index rows.

Index file presence is a strong activity candidate, not exchange-certified calendar
evidence. No missing date is automatically labelled a holiday or a data failure.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
INDEX_REPO = "socrateai-official/nepse-open-data"
INDEX_RE = re.compile(r"^ohlc_index/adj_(\d{4}-\d{2}-\d{2})\.csv$")

def index_path_date(path: str) -> str | None:
    match = INDEX_RE.fullmatch(path)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)).isoformat()
    except ValueError:
        return None



def _get(client: httpx.Client, url: str) -> httpx.Response:
    response = client.get(url)
    response.raise_for_status()
    return response


def _num(value: Any) -> Decimal:
    number = Decimal(str(value).strip())
    if not number.is_finite():
        raise ValueError("non_finite_numeric")
    return number


def validate_index_csv(content: bytes, expected_date: str) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    required = {"date", "symbol", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError("index_csv_missing_required_columns")
    rows = []
    for raw in reader:
        if str(raw.get("symbol", "")).strip().upper() == "NEPSE_INDEX":
            rows.append(raw)
    if len(rows) != 1:
        raise ValueError(f"expected_exactly_one_NEPSE_index_row_found_{len(rows)}")
    row = rows[0]
    if str(row["date"]).strip() != expected_date:
        raise ValueError("index_row_date_mismatch")
    values = {key: _num(row[key]) for key in ("open", "high", "low", "close", "volume")}
    if any(values[k] <= 0 for k in ("open", "high", "low", "close")) or values["volume"] < 0:
        raise ValueError("index_non_positive_price_or_negative_volume")
    if values["high"] < max(values["open"], values["low"], values["close"]):
        raise ValueError("index_high_below_ohlc")
    if values["low"] > min(values["open"], values["high"], values["close"]):
        raise ValueError("index_low_above_ohlc")
    return {
        "date": expected_date,
        "nepse_index_row_valid": True,
        "nepse_index": {key: str(values[key]) for key in values},
        "file_bytes": len(content),
        "file_sha256": digest,
    }


def load_floorsheet_dates(paths: list[str | Path]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for manifest in paths:
        with Path(manifest).open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                day = date.fromisoformat(str(row["date"])).isoformat()
                source = str(row.get("repo_id") or row.get("repository") or row.get("source_id") or row.get("source") or "").strip()
                if not source or not row.get("path"):
                    raise ValueError(f"{manifest}:{line_no}: missing source or path")
                result[day][source] += 1
    return result


def build_crosscheck(
    audit: dict[str, Any],
    *,
    repo: str = INDEX_REPO,
    recent_index_dates: int = 120,
    floorsheet_manifests: list[str | Path] | None = None,
    workers: int = 8,
) -> dict[str, Any]:
    if recent_index_dates < 1 or workers < 1 or workers > 16:
        raise ValueError("recent_index_dates must be positive and workers must be 1..16")
    with httpx.Client(timeout=httpx.Timeout(45, connect=15), follow_redirects=True) as client:
        metadata = _get(client, f"{API}/repos/{repo}").json()
        branch = metadata["default_branch"]
        commit = _get(client, f"{API}/repos/{repo}/commits/{quote(branch, safe='')}").json()
        commit_sha = str(commit["sha"])
        tree_sha = str(commit["commit"]["tree"]["sha"])
        tree = _get(client, f"{API}/repos/{repo}/git/trees/{tree_sha}?recursive=1").json()
        if tree.get("truncated"):
            raise RuntimeError("index repository tree is truncated; refusing incomplete inventory")
        index_paths = {}
        for item in tree.get("tree", []):
            path = str(item.get("path", ""))
            day = index_path_date(path)
            if item.get("type") == "blob" and day:
                index_paths[day] = path
        selected_dates = sorted(index_paths)[-recent_index_dates:]
        index_rows: dict[str, dict[str, Any]] = {}
        errors = []
        def fetch_day(day: str) -> dict[str, Any]:
            path = index_paths[day]
            url = f"{RAW}/{repo}/{commit_sha}/{quote(path, safe='/')}"
            content = _get(client, url).content
            return validate_index_csv(content, day) | {"path": path, "url": url}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch_day, day): day for day in selected_dates}
            for future in as_completed(futures):
                day = futures[future]
                try:
                    index_rows[day] = future.result()
                except Exception as exc:
                    errors.append({"date": day, "error": f"{type(exc).__name__}: {exc}"})

    ohlcv_by_repo: dict[str, dict[str, Any]] = {}
    for source_repo, result in audit.get("repositories", {}).items():
        ohlcv_by_repo[source_repo] = {
            str(row["date"]): {"unique_symbols": int(row["unique_symbols"]), "symbols": row.get("symbols", [])}
            for row in result.get("date_coverage", [])
        }
    floorsheet = load_floorsheet_dates(floorsheet_manifests or [])
    rows = []
    for day in selected_dates:
        per_repo = {source: dates[day] for source, dates in ohlcv_by_repo.items() if day in dates}
        fs = dict(floorsheet.get(day, {}))
        rows.append({
            "date": day,
            "classification": "observed_index_session_candidate" if day in index_rows else "index_file_present_but_row_unverified",
            "index_row": index_rows.get(day),
            "ohlcv_sources": per_repo,
            "floorsheet_sources_file_count": fs,
            "cross_source_ohlcv_presence": len(per_repo),
        })
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "index_source": repo,
        "index_commit_sha": commit_sha,
        "index_files_in_tree": len(index_paths),
        "selected_recent_index_file_dates": len(selected_dates),
        "selected_start_date": selected_dates[0] if selected_dates else None,
        "selected_end_date": selected_dates[-1] if selected_dates else None,
        "valid_index_rows": len(index_rows),
        "index_download_or_validation_errors": errors,
        "ohlcv_source_commits": {
            source: result.get("commit_sha") for source, result in audit.get("repositories", {}).items()
        },
        "floorsheet_manifest_files": [str(p) for p in (floorsheet_manifests or [])],
        "dates": rows,
        "limitations": [
            "SocrateAI index files are third-party data, not an exchange-certified session calendar.",
            "Index file presence plus a valid NEPSE_index row is an observed-session candidate, not primary NEPSE evidence.",
            "OHLCV source dates and floorsheet filenames are cross-check signals, not proof of full market-wide completeness.",
            "Missing files are not automatically holidays; they may be publisher gaps, partial publication, or genuine closures.",
            "No date is promoted to verified_open or verified_closed by this report.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-report", type=Path, required=True)
    parser.add_argument("--floorsheet-manifest", action="append", default=[])
    parser.add_argument("--recent-index-dates", type=int, default=120)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("data/reports/market-date-crosscheck.json"))
    args = parser.parse_args()
    audit = json.loads(args.audit_report.read_text(encoding="utf-8"))
    report = build_crosscheck(
        audit, recent_index_dates=args.recent_index_dates,
        floorsheet_manifests=args.floorsheet_manifest, workers=args.workers,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "index_commit_sha": report["index_commit_sha"],
        "selected_dates": report["selected_recent_index_file_dates"],
        "valid_index_rows": report["valid_index_rows"],
        "index_errors": len(report["index_download_or_validation_errors"]),
        "date_range": [report["selected_start_date"], report["selected_end_date"]],
    }, indent=2))
    if report["index_download_or_validation_errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
