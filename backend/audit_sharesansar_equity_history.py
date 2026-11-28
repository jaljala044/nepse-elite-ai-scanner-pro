"""Build a pinned, per-equity coverage inventory for the public ShareSansar-derived archive.

This is a source-coverage measurement only. It does not validate OHLCV correctness,
trading sessions, historical security identity, source rights, or canonical eligibility.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Any

import httpx

REPOSITORY = "OmitNomis/ShareSansarScraper"
BRANCH = "master"
ARCHIVE_PREFIX = "docs/api/history/"
RAW_BASE = "https://raw.githubusercontent.com"
API_BASE = "https://api.github.com"
USER_AGENT = "NEPSE-ELITE-AI-SCANNER/0.4 (read-only archive coverage inventory)"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)
MAX_FILE_BYTES = 20 * 1024 * 1024


def _anniversary(start: date, years: int) -> date:
    try:
        return start.replace(year=start.year + years)
    except ValueError:  # 29-February
        return start.replace(year=start.year + years, day=28)


def classify_span(first: date | None, last: date | None) -> dict[str, Any]:
    if first is None or last is None or last < first:
        return {"calendar_days": None, "meets_3_years": False, "meets_5_years": False}
    return {
        "calendar_days": (last - first).days + 1,
        "meets_3_years": last >= _anniversary(first, 3),
        "meets_5_years": last >= _anniversary(first, 5),
    }


def summarize_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, list):
        raise ValueError("history payload root must be a JSON array")
    parsed: list[date] = []
    malformed = 0
    for row in payload:
        if not isinstance(row, dict):
            malformed += 1
            continue
        raw_day = row.get("d")
        try:
            parsed.append(date.fromisoformat(str(raw_day)[:10]))
        except (TypeError, ValueError):
            malformed += 1
    first = min(parsed) if parsed else None
    last = max(parsed) if parsed else None
    return {
        "row_count": len(payload),
        "dated_row_count": len(parsed),
        "malformed_date_or_row_count": malformed,
        "first_date": first.isoformat() if first else "",
        "last_date": last.isoformat() if last else "",
        **classify_span(first, last),
    }


def load_crosswalk(path: Path, expected_count: int = 281) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"symbol", "security_id", "snapshot_date", "active_status", "crosswalk_status"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"crosswalk missing columns: {sorted(missing)}")
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    symbols = [row["symbol"].upper() for row in rows]
    if len(rows) != expected_count:
        raise ValueError(f"crosswalk has {len(rows)} rows; expected {expected_count}")
    if any(not re.fullmatch(r"[A-Z0-9.-]{1,24}", symbol) for symbol in symbols):
        raise ValueError("crosswalk contains blank or invalid symbols")
    if len(set(symbols)) != len(symbols):
        raise ValueError("crosswalk contains duplicate symbols")
    if any(not row["security_id"] for row in rows):
        raise ValueError("crosswalk contains blank current security IDs")
    return sorted(rows, key=lambda row: row["symbol"].upper())


def _git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\\0".encode("ascii") + content).hexdigest()


def _fetch_one(client: httpx.Client, revision: str, symbol: str,
               tree_by_path: dict[str, dict]) -> dict[str, Any]:
    path = f"{ARCHIVE_PREFIX}{symbol}.json"
    tree_item = tree_by_path.get(path)
    base = {
        "symbol": symbol, "source_repository": REPOSITORY,
        "source_revision": revision, "source_path": path,
        "source_url": f"{RAW_BASE}/{REPOSITORY}/{revision}/{path}",
        "source_git_blob_sha": tree_item.get("sha", "") if tree_item else "",
    }
    if not tree_item or tree_item.get("type") != "blob":
        return {**base, "retrieval_status": "missing_source_path"}
    size = int(tree_item.get("size", -1))
    if size < 0 or size > MAX_FILE_BYTES:
        return {**base, "retrieval_status": "rejected_file_size", "source_bytes": size}
    response = client.get(base["source_url"])
    response.raise_for_status()
    content = response.content
    git_sha = _git_blob_sha(content)
    if len(content) != size or git_sha != tree_item.get("sha"):
        return {**base, "retrieval_status": "source_blob_mismatch",
                "source_bytes": len(content), "observed_git_blob_sha": git_sha}
    digest = hashlib.sha256(content).hexdigest()
    try:
        payload = json.loads(content.decode("utf-8"))
        coverage = summarize_payload(payload)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return {**base, "retrieval_status": "invalid_json_or_schema",
                "source_bytes": len(content), "source_sha256": digest,
                "parse_error": f"{type(exc).__name__}: {exc}"}
    if coverage["dated_row_count"] == 0:
        parse_status = "no_parseable_dates"
    elif coverage["malformed_date_or_row_count"]:
        parse_status = "partial_dates"
    else:
        parse_status = "all_rows_date_parseable"
    return {
        **base, "retrieval_status": "retrieved_and_blob_verified",
        "source_bytes": len(content), "source_sha256": digest,
        "parse_status": parse_status, **coverage,
        "coverage_class": (
            "at_least_5_years" if coverage["meets_5_years"] else
            "at_least_3_years" if coverage["meets_3_years"] else
            "below_3_years_or_unknown"
        ),
        "canonical_data_eligible": False,
    }


def build_inventory(crosswalk_path: Path, output_dir: Path,
                    expected_count: int = 281, workers: int = 8) -> dict[str, Any]:
    rows = load_crosswalk(crosswalk_path, expected_count)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    with httpx.Client(timeout=TIMEOUT, headers=headers, follow_redirects=False) as client:
        commit_response = client.get(f"{API_BASE}/repos/{REPOSITORY}/commits/{BRANCH}")
        commit_response.raise_for_status()
        revision = commit_response.json().get("sha", "")
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("archive branch did not resolve to an immutable commit SHA")
        tree_response = client.get(f"{API_BASE}/repos/{REPOSITORY}/git/trees/{revision}?recursive=1")
        tree_response.raise_for_status()
        tree_payload = tree_response.json()
        if tree_payload.get("truncated") is not False:
            raise ValueError("archive Git tree is truncated; completeness cannot be established")
        tree_by_path = {
            item["path"]: item for item in tree_payload.get("tree", [])
            if item.get("type") == "blob" and isinstance(item.get("path"), str)
        }
        results: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max(1, min(workers, 16))) as pool:
            futures = {
                pool.submit(_fetch_one, client, revision, row["symbol"].upper(), tree_by_path):
                row["symbol"].upper() for row in rows
            }
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    result = {
                        "symbol": symbol, "source_repository": REPOSITORY,
                        "source_revision": revision,
                        "source_path": f"{ARCHIVE_PREFIX}{symbol}.json",
                        "retrieval_status": "request_failed",
                        "error": f"{type(exc).__name__}: {exc}",
                        "canonical_data_eligible": False,
                    }
                results.append(result)
    results.sort(key=lambda item: item["symbol"])
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "sharesansar_equity_history_coverage.csv"
    fields = sorted({key for item in results for key in item})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    counts: dict[str, int] = {}
    for item in results:
        key = item.get("retrieval_status", "unknown")
        counts[key] = counts.get(key, 0) + 1
    qualifying_3y = sum(item.get("meets_3_years") is True for item in results)
    qualifying_5y = sum(item.get("meets_5_years") is True for item in results)
    report = {
        "source_repository": REPOSITORY, "source_branch_resolved": BRANCH,
        "source_revision": revision, "crosswalk_path": str(crosswalk_path),
        "crosswalk_rows": len(rows), "result_rows": len(results),
        "retrieval_status_counts": counts,
        "equities_with_at_least_3_years": qualifying_3y,
        "equities_with_at_least_5_years": qualifying_5y,
        "three_to_five_year_target_met": qualifying_3y,
        "limitations": [
            "ShareSansar-derived archive; not independent corroboration against another ShareSansar-derived mirror.",
            "Coverage dates are first/last parseable archive row dates, not verified exchange sessions.",
            "No row-level OHLCV validation, corporate-action review, historical identity proof, or completeness certification is performed.",
            "Source terms and redistribution rights are not approved by this inventory.",
            "No data is promoted to canonical storage or model training.",
        ],
        "csv_path": str(csv_path),
    }
    json_path = output_dir / "sharesansar_equity_history_coverage.json"
    json_path.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path,
                        default=Path("../data/reference/nepse_equity_security_id_crosswalk_2026-11-26.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("../data/reports"))
    parser.add_argument("--expected-count", type=int, default=281)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(build_inventory(args.crosswalk, args.output_dir,
                                     args.expected_count, args.workers), indent=2))


if __name__ == "__main__":
    main()
