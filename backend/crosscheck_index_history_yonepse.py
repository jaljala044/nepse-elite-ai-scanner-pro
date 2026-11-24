#!/usr/bin/env python3
"""Cross-check SocrateAI index rows against YONEPSE's NEPSE-API-derived index mirror.

YONEPSE documents its recent index history as sourced from the NEPSE official
history API. It is still a third-party mirror, not an exchange-issued signed
record. All source values and differences are retained; none are auto-corrected.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
YONEPSE_REPO = "Shubhamnpk/yonepse"
INDEX_CODE = "NEPSE"
# NEPSE's official /api/nots/index/history/{id} uses ID 58 in the publisher code.
OFFICIAL_NEPSE_INDEX_ID = 58
FIELD_PAIRS = {
    "close": ("close", "close"),
    "open": ("open", "open"),
    "high": ("high", "high"),
    "low": ("low", "low"),
    # SocrateAI's index CSV labels turnoverValue as "volume".
    "turnover_vs_socrateai_volume": ("turnover", "volume"),
}


def _get(client: httpx.Client, url: str) -> bytes:
    response = client.get(url)
    response.raise_for_status()
    return response.content


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("non_finite_number")
    return result


def extract_yonepse_rows(
    manifest: dict[str, Any],
    month_payloads: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows_by_date: dict[str, dict[str, Any]] = {}
    for month, payload in sorted(month_payloads.items()):
        if payload.get("month") != month:
            raise ValueError(f"{month}: month field mismatch")
        dates = payload.get("dates")
        series = payload.get("series")
        if not isinstance(dates, list) or not isinstance(series, dict):
            raise ValueError(f"{month}: missing dates or series")
        nepse = series.get(INDEX_CODE)
        if not isinstance(nepse, list):
            raise ValueError(f"{month}: missing NEPSE series")
        for sparse in nepse:
            if not isinstance(sparse, list) or len(sparse) < 5:
                raise ValueError(f"{month}: malformed NEPSE sparse row")
            date_index = sparse[0]
            if not isinstance(date_index, int) or date_index < 0 or date_index >= len(dates):
                raise ValueError(f"{month}: invalid dateIndex {date_index!r}")
            day = str(dates[date_index])
            if not day.startswith(month + "-"):
                raise ValueError(f"{month}: date index points outside month: {day}")
            if day in rows_by_date:
                raise ValueError(f"duplicate YONEPSE NEPSE date: {day}")
            values = list(sparse[1:])
            values.extend([None] * (7 - len(values)))
            row = {
                "close": values[0],
                "open": values[1],
                "high": values[2],
                "low": values[3],
                "turnover": values[4],
                "volume": values[5],
                "trades": values[6],
            }
            rows_by_date[day] = {
                "date": day,
                "row": row,
                "updated_at": payload.get("updatedAt"),
                "month": month,
            }

    latest_date = str(manifest.get("latestDate") or "")
    latest_status = str(manifest.get("latestStatus") or "unmarked").lower()
    for day, entry in rows_by_date.items():
        entry["finality_status"] = (
            "provisional" if day == latest_date and latest_status == "provisional"
            else "unmarked"
        )
    return rows_by_date


def compare_rows(
    socrateai_rows: list[dict[str, Any]],
    yonepse_entry: dict[str, Any] | None,
    socrateai_errors: list[str] | None = None,
) -> dict[str, Any]:
    if yonepse_entry is None:
        return {"status": "yonepse_row_missing"}
    if len(socrateai_rows) != 1 or socrateai_errors:
        return {
            "status": "socrateai_row_anomaly",
            "socrateai_row_count": len(socrateai_rows),
            "socrateai_validation_errors": list(socrateai_errors or []),
            "socrateai_rows": socrateai_rows,
            "yonepse": yonepse_entry,
        }
    if yonepse_entry.get("finality_status") == "provisional":
        return {
            "status": "yonepse_latest_provisional",
            "socrateai_rows": socrateai_rows,
            "yonepse": yonepse_entry,
        }

    soc = socrateai_rows[0]
    yon = yonepse_entry["row"]
    differences = {}
    compared = {}
    for label, (y_key, s_key) in FIELD_PAIRS.items():
        y_value = _decimal(yon.get(y_key))
        s_value = _decimal(soc.get(s_key))
        if y_value is None or s_value is None:
            compared[label] = {"yonepse": str(y_value) if y_value is not None else None,
                               "socrateai": str(s_value) if s_value is not None else None,
                               "status": "missing_value"}
            continue
        delta = y_value - s_value
        compared[label] = {
            "yonepse": str(y_value),
            "socrateai": str(s_value),
            "absolute_difference": str(abs(delta)),
            "signed_difference_yonepse_minus_socrateai": str(delta),
            "status": "exact_match" if delta == 0 else "different",
        }
        if delta != 0:
            differences[label] = compared[label]
    return {
        "status": "exact_match" if not differences else "numeric_differences",
        "compared_fields": compared,
        "differences": differences,
        "yonepse_finality": yonepse_entry.get("finality_status", "unmarked"),
        "yonepse_updated_at": yonepse_entry.get("updated_at"),
    }


def build_report(
    input_report: dict[str, Any],
    *,
    repo: str = YONEPSE_REPO,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    with httpx.Client(timeout=httpx.Timeout(45, connect=15), follow_redirects=True) as client:
        metadata = json.loads(_get(client, f"{API}/repos/{repo}"))
        if commit_sha is None:
            commit_data = json.loads(_get(client, f"{API}/repos/{repo}/commits/{quote(metadata['default_branch'], safe='')}"))
            commit_sha = str(commit_data["sha"])
        manifest_url = f"{RAW}/{repo}/{commit_sha}/data/indices/manifest.json"
        manifest_bytes = _get(client, manifest_url)
        manifest = json.loads(manifest_bytes)
        candidate_dates = [
            str(row["date"]) for row in input_report.get("dates", [])
        ]
        months = sorted({day[:7] for day in candidate_dates})
        month_payloads = {}
        month_hashes = {}
        month_metadata = {}
        errors = []
        for month in months:
            url = f"{RAW}/{repo}/{commit_sha}/data/indices/monthly/{month}.json"
            try:
                raw = _get(client, url)
                month_payloads[month] = json.loads(raw)
                month_hashes[month] = hashlib.sha256(raw).hexdigest()
                dates = month_payloads[month].get("dates") or []
                month_metadata[month] = {
                    "updated_at": month_payloads[month].get("updatedAt"),
                    "date_count": len(dates),
                    "first_date": dates[0] if dates else None,
                    "last_date": dates[-1] if dates else None,
                }
            except Exception as exc:
                errors.append({"month": month, "error": f"{type(exc).__name__}: {exc}"})

    yonepse_rows = extract_yonepse_rows(manifest, month_payloads)
    source_dates = {str(row["date"]): row for row in input_report.get("dates", [])}
    results = []
    for day in candidate_dates:
        source_row = source_dates[day].get("index_row") or {}
        socrateai_rows = source_row.get("nepse_index_rows", [])
        comparison = compare_rows(
            socrateai_rows, yonepse_rows.get(day),
            source_row.get("validation_errors", []),
        )
        results.append({
            "date": day,
            "socrateai_classification": source_dates[day].get("classification"),
            "socrateai_row_validation_errors": source_row.get("validation_errors", []),
            "comparison": comparison,
        })

    status_counts: dict[str, int] = {}
    for row in results:
        status = row["comparison"]["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "yonepse_repository": repo,
        "yonepse_commit_sha": commit_sha,
        "yonepse_manifest_url": manifest_url,
        "yonepse_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "yonepse_latest_date": manifest.get("latestDate"),
        "yonepse_latest_status": manifest.get("latestStatus", "unmarked"),
        "yonepse_finalized_through": manifest.get("finalizedThrough"),
        "upstream_claim": {
            "source": "NEPSE official API",
            "endpoint": f"/api/nots/index/history/{OFFICIAL_NEPSE_INDEX_ID}",
            "publisher_statement": "YONEPSE sources recent index history from the NEPSE official API",
            "independent_verification": "not performed; this is a third-party mirror",
        },
        "monthly_files": [
            {
                "month": month,
                "url": f"{RAW}/{repo}/{commit_sha}/data/indices/monthly/{month}.json",
                "sha256": digest,
                **month_metadata.get(month, {}),
            }
            for month, digest in sorted(month_hashes.items())
        ],
        "selected_dates": len(results),
        "comparison_status_counts": status_counts,
        "month_download_errors": errors,
        "dates": results,
        "limitations": [
            "YONEPSE is a third-party mirror that attributes recent index history to the NEPSE official API; it is not an exchange-issued signed record.",
            "The publisher's history builder documents that the API ignores startDate/endDate and returns roughly the trailing year; the mirror filters client-side.",
            "The publisher's API client instantiates the NEPSE scraper with TLS verification disabled; treat this lineage as corroboration, not sole canonical evidence.",
            "Latest provisional date is retained but excluded from numeric comparison.",
            "SocrateAI's index CSV field named volume is compared to YONEPSE turnoverValue/turnover, not to YONEPSE share volume.",
            "All numeric differences and source anomalies are retained; no source is automatically selected or corrected.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/reports/yonepse-index-crosscheck.json"))
    parser.add_argument("--repo", default=YONEPSE_REPO)
    parser.add_argument("--commit-sha")
    args = parser.parse_args()
    report = build_report(
        json.loads(args.input.read_text(encoding="utf-8")),
        repo=args.repo,
        commit_sha=args.commit_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "yonepse_commit_sha": report["yonepse_commit_sha"],
        "selected_dates": report["selected_dates"],
        "comparison_status_counts": report["comparison_status_counts"],
        "month_download_errors": len(report["month_download_errors"]),
    }, indent=2))
    if report["month_download_errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
