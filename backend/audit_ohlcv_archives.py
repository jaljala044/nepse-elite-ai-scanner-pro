"""Pinned, read-only row-level audit of Jaljala OHLCV GitHub archives.

Downloads only per-symbol OHLCV CSVs from pinned Git commits. It writes an audit
report, never edits source repositories or imports data into the application DB.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
DEFAULT_REPOS = [
    "jaljala044/nepse-smc-data",
    "jaljala044/nepse-history-starter",
]
TIMEOUT = httpx.Timeout(45.0, connect=15.0)
REQUIRED = ("date", "open", "high", "low", "close", "volume")


def _decimal(value: str) -> Decimal:
    number = Decimal(str(value).strip())
    if not number.is_finite():
        raise InvalidOperation("non-finite number")
    return number


def _canonical(number: Decimal) -> str:
    normalized = number.normalize()
    return format(normalized, "f") if normalized else "0"


def audit_ohlcv_csv(content: bytes, path: str) -> dict[str, Any]:
    """Parse one source CSV and return normalized observations plus quality findings."""
    digest = hashlib.sha256(content).hexdigest()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError(f"{path}: CSV header is missing")
    header_map = {name.strip().lower(): name for name in reader.fieldnames if name}
    missing = [name for name in REQUIRED if name not in header_map]
    if missing:
        raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")

    symbol = Path(path).name.removesuffix("_OHLCV.csv").upper()
    observations: dict[str, list[dict[str, str]]] = defaultdict(list)
    invalid_rows: list[dict[str, Any]] = []
    ordered_dates: list[date] = []
    row_count = 0
    previous: tuple[date, tuple[str, ...]] | None = None
    repeated_adjacent_calendar_rows = 0

    for line_no, raw in enumerate(reader, start=2):
        row_count += 1
        try:
            trade_date = date.fromisoformat(raw[header_map["date"]].strip())
            values = {
                name: _decimal(raw[header_map[name]])
                for name in ("open", "high", "low", "close", "volume")
            }
            if values["volume"] < 0 or values["volume"] != values["volume"].to_integral_value():
                raise ValueError("volume must be a non-negative integer")
            if values["high"] < max(values["open"], values["low"], values["close"]):
                raise ValueError("high is below open, low or close")
            if values["low"] > min(values["open"], values["high"], values["close"]):
                raise ValueError("low is above open, high or close")
            normalized = {name: _canonical(value) for name, value in values.items()}
            record = {"symbol": symbol, "date": trade_date.isoformat(), **normalized}
            observations[trade_date.isoformat()].append(record)
            ordered_dates.append(trade_date)
            signature = tuple(normalized[name] for name in ("open", "high", "low", "close", "volume"))
            if previous and trade_date - previous[0] == timedelta(days=1) and signature == previous[1]:
                repeated_adjacent_calendar_rows += 1
            previous = (trade_date, signature)
        except (ValueError, InvalidOperation, TypeError) as exc:
            invalid_rows.append({"line": line_no, "error": str(exc), "row": raw})

    duplicates = [
        {"date": day, "count": len(rows)}
        for day, rows in sorted(observations.items()) if len(rows) > 1
    ]
    out_of_order = sum(
        1 for left, right in zip(ordered_dates, ordered_dates[1:]) if right < left
    )
    unique_dates = sorted(observations)
    return {
        "symbol": symbol,
        "path": path,
        "sha256": digest,
        "rows": row_count,
        "valid_rows": sum(len(rows) for rows in observations.values()),
        "unique_dates": len(unique_dates),
        "first_date": unique_dates[0] if unique_dates else None,
        "last_date": unique_dates[-1] if unique_dates else None,
        "duplicate_dates": duplicates,
        "out_of_order_transitions": out_of_order,
        "invalid_rows": invalid_rows,
        "repeated_adjacent_calendar_rows": repeated_adjacent_calendar_rows,
        "observations": dict(observations),
    }


def _get(client: httpx.Client, url: str) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.get(url)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                continue
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise
    raise RuntimeError(f"Request failed: {url}: {last_error}")


def _repository_snapshot(client: httpx.Client, repo: str) -> tuple[str, str, list[dict[str, Any]]]:
    metadata = _get(client, f"{API}/repos/{repo}").json()
    branch = metadata["default_branch"]
    commit = _get(client, f"{API}/repos/{repo}/commits/{quote(branch, safe='')}").json()
    commit_sha = commit["sha"]
    tree_sha = commit["commit"]["tree"]["sha"]
    tree = _get(client, f"{API}/repos/{repo}/git/trees/{tree_sha}?recursive=1").json()
    if tree.get("truncated"):
        raise RuntimeError(f"Git tree is truncated for {repo}; refusing incomplete audit")
    files = [
        item for item in tree.get("tree", [])
        if item.get("type") == "blob"
        and item.get("path", "").startswith("03_stock_charts_ohlcv/")
        and item.get("path", "").endswith("_OHLCV.csv")
    ]
    return commit_sha, tree_sha, files


def audit_repositories(
    repos: list[str] | None = None, *, workers: int = 8
) -> dict[str, Any]:
    selected = repos or DEFAULT_REPOS
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        "User-Agent": "NEPSE-ELITE-OHLCV-Archive-Audit/1.0",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repo_results: dict[str, Any] = {}
    cross_source: dict[str, dict[str, dict[str, list[dict[str, str]]]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    with httpx.Client(timeout=TIMEOUT, headers=headers, follow_redirects=True) as client:
        for repo in selected:
            commit_sha, tree_sha, files = _repository_snapshot(client, repo)
            audited: list[dict[str, Any]] = []
            errors: list[dict[str, str]] = []

            def fetch_and_audit(item: dict[str, Any]) -> dict[str, Any]:
                path = item["path"]
                url = f"{RAW}/{repo}/{commit_sha}/{quote(path, safe='/')}"
                response = _get(client, url)
                if response.content.startswith(b"version https://git-lfs.github.com/spec/v1"):
                    raise ValueError("Git LFS pointer encountered; source object not fetched")
                result = audit_ohlcv_csv(response.content, path)
                result["repository_blob_sha"] = item.get("sha")
                return result

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(fetch_and_audit, item): item for item in files}
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        result = future.result()
                        audited.append(result)
                        for day, rows in result["observations"].items():
                            cross_source[result["symbol"]][day][repo] = rows
                    except Exception as exc:
                        errors.append({"path": item["path"], "error": f"{type(exc).__name__}: {exc}"})

            audited.sort(key=lambda item: item["symbol"])
            date_coverage: dict[str, set[str]] = defaultdict(set)
            for item in audited:
                for day, rows in item.get("observations", {}).items():
                    if rows:
                        date_coverage[day].add(item["symbol"])
            repo_results[repo] = {
                "commit_sha": commit_sha,
                "tree_sha": tree_sha,
                "date_coverage": [
                    {"date": day, "unique_symbols": len(symbols), "symbols": sorted(symbols)}
                    for day, symbols in sorted(date_coverage.items())
                ],
                "file_count": len(files),
                "files_audited": len(audited),
                "download_errors": errors,
                "total_rows": sum(item["rows"] for item in audited),
                "total_unique_symbol_dates": sum(item["unique_dates"] for item in audited),
                "duplicate_date_count": sum(len(item["duplicate_dates"]) for item in audited),
                "out_of_order_transitions": sum(item["out_of_order_transitions"] for item in audited),
                "invalid_row_count": sum(len(item["invalid_rows"]) for item in audited),
                "repeated_adjacent_calendar_rows": sum(item["repeated_adjacent_calendar_rows"] for item in audited),
                "files": [
                    {key: value for key, value in item.items() if key != "observations"}
                    for item in audited
                ],
            }

    # Compare pinned repository blob identities separately from normalized row values.
    repo_file_maps = {
        repo: {item["path"]: item.get("repository_blob_sha") for item in result["files"]}
        for repo, result in repo_results.items()
    }
    repo_names = list(repo_file_maps)
    file_blob_differences = []
    file_path_sets = {repo: set(files) for repo, files in repo_file_maps.items()}
    common_paths = set.intersection(*(file_path_sets[r] for r in repo_names)) if repo_names else set()
    for path in sorted(common_paths):
        shas = {repo: repo_file_maps[repo][path] for repo in repo_names}
        if len(set(shas.values())) > 1:
            file_blob_differences.append({"path": path, "blob_shas": shas})

    conflicts = []
    overlap_dates = 0
    for symbol, dates in sorted(cross_source.items()):
        for day, sources in sorted(dates.items()):
            if len(sources) < 2:
                continue
            overlap_dates += 1
            source_rows = {repo: rows[0] for repo, rows in sources.items() if rows}
            signatures = {
                repo: tuple(row[name] for name in ("open", "high", "low", "close", "volume"))
                for repo, row in source_rows.items()
            }
            if len(set(signatures.values())) > 1 or any(len(rows) != 1 for rows in sources.values()):
                conflicts.append({
                    "symbol": symbol, "date": day,
                    "source_rows": source_rows,
                    "source_row_counts": {repo: len(rows) for repo, rows in sources.items()},
                })

    invalid_total = sum(item["invalid_row_count"] for item in repo_results.values())
    duplicate_total = sum(item["duplicate_date_count"] for item in repo_results.values())
    order_total = sum(item["out_of_order_transitions"] for item in repo_results.values())
    error_total = sum(len(item["download_errors"]) for item in repo_results.values())
    repeated_total = sum(item["repeated_adjacent_calendar_rows"] for item in repo_results.values())
    conflict_total = len(conflicts)
    file_difference_total = len(file_blob_differences)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "pinned_commit_read_only_row_level_audit",
        "repositories": repo_results,
        "file_level_comparison": {
            "common_paths": len(common_paths),
            "blob_difference_count": file_difference_total,
            "blob_differences": file_blob_differences,
        },
        "cross_source": {
            "shared_symbol_dates": overlap_dates,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
        },
        "quality_totals": {
            "invalid_rows": invalid_total,
            "duplicate_dates": duplicate_total,
            "out_of_order_transitions": order_total,
            "repeated_adjacent_calendar_rows": repeated_total,
            "cross_source_conflicts": conflict_total,
            "file_blob_differences": file_difference_total,
            "download_errors": error_total,
        },
        # Repeated rows require a verified calendar; conflicts require resolution.
        # Neither is auto-corrected or allowed through the canonical-data gate.
        "gate": "FAIL" if (
            invalid_total or duplicate_total or order_total or repeated_total
            or conflict_total or file_difference_total or error_total
        ) else "PASS",
        "limitations": [
            "Repeated adjacent calendar rows are review flags, not automatically invalid: an authoritative NEPSE session calendar is required.",
            "This audit validates source CSV structure and OHLCV arithmetic, not exchange completeness or data licensing.",
            "Cross-source conflicts are retained as unresolved evidence; no source is automatically selected as canonical.",
            "No corporate-action adjustment or back-adjustment is performed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", action="append", dest="repos")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("data/reports/ohlcv-archive-audit.json"))
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")
    report = audit_repositories(args.repos, workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "gate": report["gate"],
        "repositories": {
            repo: {
                "files": result["file_count"],
                "audited": result["files_audited"],
                "rows": result["total_rows"],
                "errors": len(result["download_errors"]),
            } for repo, result in report["repositories"].items()
        },
        "cross_source": report["cross_source"],
        "quality_totals": report["quality_totals"],
    }, indent=2))
    if report["gate"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
