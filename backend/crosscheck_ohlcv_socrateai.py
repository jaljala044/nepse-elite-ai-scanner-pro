"""Independently cross-check flagged Jaljala OHLCV rows against SocrateAI unadjusted EOD.

Only downloads daily unadjusted EOD files for dates already flagged by the Jaljala
archive audit. Keeps both candidate sources, never auto-selects a canonical value.
SocrateAI data is MIT-licensed; retain its attribution and license with any copy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
EXTERNAL_REPO = "socrateai-official/nepse-open-data"
FIELDS = ("open", "high", "low", "close", "volume")
TIMEOUT = httpx.Timeout(45.0, connect=15.0)


def canonical(value: Any) -> str | None:
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite():
            return None
        normalized = number.normalize()
        return format(normalized, "f") if normalized else "0"
    except (InvalidOperation, ValueError, TypeError):
        return None


def compare_ohlcv(source_row: dict[str, Any], external_row: dict[str, Any]) -> dict[str, Any]:
    differences = {}
    matches = []
    for field in FIELDS:
        left = canonical(source_row.get(field))
        right = canonical(external_row.get(field))
        if left is not None and right is not None and left == right:
            matches.append(field)
        else:
            differences[field] = {"jaljala": source_row.get(field), "socrateai": external_row.get(field)}
    if not differences:
        status = "full_match"
    elif matches:
        status = "partial_match"
    else:
        status = "mismatch"
    return {"status": status, "matched_fields": matches, "differences": differences}


def unmatched_classification(status: str) -> str:
    return {
        "download_error": "external_download_error",
        "not_published": "external_file_not_published",
        "symbol_not_in_external_file": "symbol_not_in_external_file",
    }.get(status, "unclassified_external_status")


def _source_row(raw: dict[str, Any]) -> dict[str, Any]:
    lower = {str(key).strip().lower(): value for key, value in raw.items()}
    return {field: lower.get(field) for field in FIELDS}


def load_candidates(audit: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    for repo, result in audit.get("repositories", {}).items():
        for file_result in result.get("files", []):
            symbol = file_result.get("symbol")
            for invalid in file_result.get("invalid_rows", []):
                raw = invalid.get("row", {})
                day = str(raw.get("Date") or raw.get("date") or "")
                if not symbol or not day:
                    continue
                item = candidates.setdefault((day, symbol), {
                    "date": day, "symbol": symbol, "reasons": [], "source_rows": {}
                })
                item["reasons"].append(invalid.get("error", "OHLCV validation failure"))
                item["source_rows"][repo] = _source_row(raw)

    for conflict in audit.get("cross_source", {}).get("conflicts", []):
        day, symbol = conflict.get("date"), conflict.get("symbol")
        if not day or not symbol:
            continue
        item = candidates.setdefault((day, symbol), {
            "date": day, "symbol": symbol, "reasons": [], "source_rows": {}
        })
        item["reasons"].append("cross_source_conflict")
        for repo, row in conflict.get("source_rows", {}).items():
            item["source_rows"][repo] = _source_row(row)
    return candidates


def _get(client: httpx.Client, url: str) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = client.get(url)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                continue
            if response.status_code == 404:
                return response
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise
    raise RuntimeError(f"Request failed: {url}: {last_error}")


def _external_commit(client: httpx.Client) -> str:
    response = _get(client, f"{API}/repos/{EXTERNAL_REPO}/commits/main")
    return str(response.json()["sha"])


def _fetch_external_day(
    client: httpx.Client, commit_sha: str, day: str
) -> dict[str, Any]:
    url = (
        f"{RAW}/{EXTERNAL_REPO}/{commit_sha}/"
        f"ohlc_unadjusted_stock/unadj_{quote(day, safe='')}.csv"
    )
    response = _get(client, url)
    if response.status_code == 404:
        return {"date": day, "status": "not_published", "rows": {}, "url": url}
    content = response.content
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows = {}
    for row in reader:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol:
            rows[symbol] = {field: row.get(field) for field in FIELDS}
    return {
        "date": day, "status": "downloaded", "rows": rows,
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content), "url": url,
    }


def crosscheck(
    audit: dict[str, Any], *, workers: int = 8
) -> dict[str, Any]:
    candidates = load_candidates(audit)
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {"User-Agent": "NEPSE-ELITE-SOCRATEAI-CROSSCHECK/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=TIMEOUT, headers=headers, follow_redirects=True) as client:
        commit_sha = _external_commit(client)
        days = sorted({day for day, _ in candidates})
        day_results = {}
        errors = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_fetch_external_day, client, commit_sha, day): day for day in days}
            for future in as_completed(futures):
                day = futures[future]
                try:
                    day_results[day] = future.result()
                except Exception as exc:
                    errors.append({"date": day, "error": f"{type(exc).__name__}: {exc}"})

    records = []
    status_counts = Counter()
    for (day, symbol), item in sorted(candidates.items()):
        external_day = day_results.get(day)
        if external_day is None:
            record = {
                **item, "external_status": "download_error",
                "classification": unmatched_classification("download_error"),
                "error": next((e["error"] for e in errors if e["date"] == day), "unknown error"),
                "source_comparisons": {},
            }
        elif external_day["status"] == "not_published":
            record = {**item, "external_status": "not_published",
                      "classification": unmatched_classification("not_published"), "source_comparisons": {}}
        elif symbol not in external_day["rows"]:
            record = {**item, "external_status": "symbol_not_in_external_file",
                      "classification": unmatched_classification("symbol_not_in_external_file"), "source_comparisons": {}}
        else:
            ext_row = external_day["rows"][symbol]
            comparisons = {
                repo: compare_ohlcv(row, ext_row)
                for repo, row in item["source_rows"].items()
            }
            statuses = [entry["status"] for entry in comparisons.values()]
            record = {
                **item, "external_status": "matched_symbol",
                "external_row": ext_row,
                "external_file_sha256": external_day["sha256"],
                "source_comparisons": comparisons,
                "classification": (
                    "all_sources_match_external" if all(x == "full_match" for x in statuses)
                    else "one_source_matches_external" if "full_match" in statuses
                    else "partial_or_conflicting" if "partial_match" in statuses
                    else "no_source_matches_external"
                ),
            }
        status_counts[record["classification"]] += 1
        records.append(record)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "targeted_external_eod_crosscheck_no_canonical_selection",
        "external_source": EXTERNAL_REPO,
        "external_commit_sha": commit_sha,
        "license": "MIT; retain copyright and permission notice",
        "candidate_count": len(candidates),
        "unique_dates_requested": len({day for day, _ in candidates}),
        "daily_files_downloaded": sum(1 for x in day_results.values() if x["status"] == "downloaded"),
        "daily_files_not_published": sum(1 for x in day_results.values() if x["status"] == "not_published"),
        "download_errors": errors,
        "classification_counts": dict(status_counts),
        "records": records,
        "limitations": [
            "SocrateAI is an independent published dataset, not a verified exchange-origin record.",
            "A match is corroboration, not proof of correctness; floorsheet/exchange evidence may still be required.",
            "Daily files may omit symbols or sessions; missing rows are not interpreted as zero activity.",
            "No value is selected, corrected, overwritten or imported into the canonical database.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/reports/ohlcv-archive-audit.json"))
    parser.add_argument("--output", type=Path, default=Path("data/reports/ohlcv-socrateai-crosscheck.json"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    audit = json.loads(args.input.read_text(encoding="utf-8"))
    result = crosscheck(audit, workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "candidate_count": result["candidate_count"],
        "unique_dates_requested": result["unique_dates_requested"],
        "daily_files_downloaded": result["daily_files_downloaded"],
        "daily_files_not_published": result["daily_files_not_published"],
        "download_errors": len(result["download_errors"]),
        "classification_counts": result["classification_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
