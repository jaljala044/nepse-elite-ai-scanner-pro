"""Read-only structural audit of the public binayabaral/nepal-market-data archive.

Downloads a pinned GitHub snapshot, filters ordinary listed equities from the
publisher's reference master, and audits every corresponding CSV. It never
imports data into the application or promotes rows to the canonical manifest.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
import os
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import httpx

REPOSITORY = "binayabaral/nepal-market-data"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
EXPECTED_HEADER = [
    "published_date", "open", "high", "low", "close", "per_change",
    "traded_quantity", "traded_amount", "status",
]
NUMERIC_FIELDS = ("open", "high", "low", "close", "traded_quantity", "traded_amount")


def _number(value: str) -> float:
    value = (value or "").strip()
    if not value:
        raise ValueError("blank numeric value")
    number = float(value)
    if not (number == number and abs(number) != float("inf")):
        raise ValueError("non-finite numeric value")
    return number


def audit_symbol_csv(content: bytes, symbol: str, path: str) -> dict:
    digest = hashlib.sha256(content).hexdigest()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    result = {
        "symbol": symbol, "path": path, "sha256": digest,
        "rows": 0, "valid_rows": 0, "duplicate_dates": 0,
        "invalid_dates": 0, "out_of_order_transitions": 0,
        "malformed_rows": 0, "nonfinite_or_blank_numeric": 0,
        "invalid_ohlc": 0, "negative_volume": 0,
        "fractional_volume": 0, "negative_turnover": 0,
        "zero_turnover_with_volume": 0, "invalid_per_change": 0,
        "first_date": None, "last_date": None, "row_errors": [],
        "row_error_samples": {},
    }

    def record_error(error: str, line_no: int, day_text: str | None = None, **details) -> None:
        result["row_errors"].append({"line": line_no, "error": error, **(
            {"date": day_text} if day_text else {}
        ), **details})
        samples = result["row_error_samples"].setdefault(error, [])
        if len(samples) < 5:
            samples.append({"line": line_no, **({"date": day_text} if day_text else {}), **details})

    if header != EXPECTED_HEADER:
        result["header_mismatch"] = {"expected": EXPECTED_HEADER, "actual": header}
        return result

    seen = set()
    previous = None
    valid_dates = []
    for line_no, row in enumerate(reader, start=2):
        result["rows"] += 1
        if None in row or any(row.get(k) is None for k in EXPECTED_HEADER):
            result["malformed_rows"] += 1
            record_error("column_count_mismatch", line_no, day_text=(row.get("published_date") or "").strip())
            continue
        day_text = (row["published_date"] or "").strip()
        try:
            day = date.fromisoformat(day_text)
            if day.isoformat() != day_text:
                raise ValueError("date_not_canonical_iso")
        except ValueError:
            result["invalid_dates"] += 1
            record_error("invalid_date", line_no, day_text=day_text)
            continue
        if day_text in seen:
            result["duplicate_dates"] += 1
            record_error("duplicate_date", line_no, day_text)
        seen.add(day_text)
        if previous is not None and day < previous:
            result["out_of_order_transitions"] += 1
        previous = day
        valid_dates.append(day_text)

        values = {}
        try:
            for field in NUMERIC_FIELDS:
                values[field] = _number(row[field])
        except ValueError as exc:
            result["nonfinite_or_blank_numeric"] += 1
            record_error("invalid_numeric", line_no, day_text, detail=str(exc))
            continue
        o, high, low, close = (values[k] for k in ("open", "high", "low", "close"))
        volume, turnover = values["traded_quantity"], values["traded_amount"]
        row_valid = True
        if min(o, high, low, close) <= 0 or high < max(o, low, close) or low > min(o, high, close):
            result["invalid_ohlc"] += 1
            record_error("invalid_ohlc_bounds", line_no, day_text, open=o, high=high, low=low, close=close)
            row_valid = False
        if volume < 0:
            result["negative_volume"] += 1
            record_error("negative_volume", line_no, day_text, volume=volume)
            row_valid = False
        if volume != int(volume):
            result["fractional_volume"] += 1
            record_error("fractional_volume", line_no, day_text, volume=volume)
            row_valid = False
        if turnover < 0:
            result["negative_turnover"] += 1
            record_error("negative_turnover", line_no, day_text, turnover=turnover)
            row_valid = False
        if volume > 0 and turnover == 0:
            result["zero_turnover_with_volume"] += 1
            record_error("zero_turnover_with_volume", line_no, day_text, volume=volume, turnover=turnover)
            row_valid = False
        change = (row["per_change"] or "").strip().lower()
        if change in ("nan", ""):
            if result["rows"] != 1:
                result["invalid_per_change"] += 1
                record_error("invalid_per_change", line_no, day_text, per_change=change)
                row_valid = False
        else:
            try:
                _number(change)
            except ValueError:
                result["invalid_per_change"] += 1
                record_error("invalid_per_change", line_no, day_text, per_change=change)
                row_valid = False
        if row_valid:
            result["valid_rows"] += 1

    if valid_dates:
        result["first_date"], result["last_date"] = min(valid_dates), max(valid_dates)
    return result


def crosscheck_official_history(public_csv_by_symbol: dict[str, bytes], official_root: Path) -> dict:
    """Compare public CSV fields against pinned official NEPSE per-security captures."""
    evidence_root = official_root.parent
    manifest_path = evidence_root / "SHA256SUMS"
    manifest = {}
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                manifest[parts[1].lstrip("* ")] = parts[0].lower()

    fields = {
        "high": ("high", "highPrice", Decimal("0.0001")),
        "low": ("low", "lowPrice", Decimal("0.0001")),
        "close": ("close", "closePrice", Decimal("0.0001")),
        "traded_quantity": ("traded_quantity", "totalTradedQuantity", Decimal("0")),
        "traded_amount": ("traded_amount", "totalTradedValue", Decimal("0.05")),
    }
    result = {
        "official_symbols_found": 0, "official_rows": 0,
        "public_rows_matched_by_date": 0, "fully_matching_rows": 0,
        "field_comparisons": 0, "field_mismatches": 0,
        "mismatches_by_field": {name: 0 for name in fields},
        "missing_public_symbol_files": [], "missing_public_active_rows": 0,
        "missing_public_zero_activity_rows": 0, "hash_or_parse_errors": [],
        "per_symbol": [], "mismatch_examples": [],
        "fields_compared": list(fields),
        "not_compared": ["open", "per_change", "status"],
    }
    if not official_root.exists():
        result["status"] = "OFFICIAL_CAPTURE_NOT_PRESENT"
        return result

    for symbol_dir in sorted(p for p in official_root.iterdir() if p.is_dir()):
        symbol = symbol_dir.name
        response_path = symbol_dir / "response-01.bin"
        if not response_path.exists():
            continue
        result["official_symbols_found"] += 1
        relative = str(response_path.relative_to(evidence_root)).replace("\\", "/")
        raw = response_path.read_bytes()
        expected_sha = manifest.get(relative)
        actual_sha = hashlib.sha256(raw).hexdigest()
        if not expected_sha or expected_sha != actual_sha:
            result["hash_or_parse_errors"].append({
                "symbol": symbol, "error": "official_response_sha256_missing_or_mismatched",
                "path": relative,
            })
            continue
        try:
            official_rows = json.loads(raw.decode("utf-8")).get("content")
            if not isinstance(official_rows, list):
                raise ValueError("official response missing content array")
        except Exception as exc:
            result["hash_or_parse_errors"].append({
                "symbol": symbol, "error": f"official_json_invalid:{type(exc).__name__}",
            })
            continue
        public_content = public_csv_by_symbol.get(symbol)
        if public_content is None:
            result["missing_public_symbol_files"].append(symbol)
            for row in official_rows:
                result["official_rows"] += 1
                if float(row.get("totalTradedQuantity") or 0) > 0 or float(row.get("totalTradedValue") or 0) > 0:
                    result["missing_public_active_rows"] += 1
                else:
                    result["missing_public_zero_activity_rows"] += 1
            continue

        public_rows = {}
        reader = csv.DictReader(io.StringIO(public_content.decode("utf-8-sig")))
        for row in reader:
            if row.get("published_date"):
                public_rows[row["published_date"]] = row
        symbol_summary = {
            "symbol": symbol, "official_rows": len(official_rows),
            "matched_dates": 0, "fully_matching_rows": 0,
            "field_mismatches": 0, "missing_public_active_rows": 0,
            "missing_public_zero_activity_rows": 0,
        }
        for official in official_rows:
            result["official_rows"] += 1
            day = str(official.get("businessDate", ""))[:10]
            public = public_rows.get(day)
            quantity = Decimal(str(official.get("totalTradedQuantity", 0) or 0))
            turnover = Decimal(str(official.get("totalTradedValue", 0) or 0))
            if public is None:
                if quantity > 0 or turnover > 0:
                    result["missing_public_active_rows"] += 1
                    symbol_summary["missing_public_active_rows"] += 1
                else:
                    result["missing_public_zero_activity_rows"] += 1
                    symbol_summary["missing_public_zero_activity_rows"] += 1
                continue
            result["public_rows_matched_by_date"] += 1
            symbol_summary["matched_dates"] += 1
            row_mismatches = []
            for field, (public_key, official_key, tolerance) in fields.items():
                try:
                    left = Decimal(str(public[public_key]))
                    right = Decimal(str(official[official_key]))
                    if not left.is_finite() or not right.is_finite():
                        raise InvalidOperation("non-finite value")
                    result["field_comparisons"] += 1
                    if abs(left - right) > tolerance:
                        result["field_mismatches"] += 1
                        result["mismatches_by_field"][field] += 1
                        row_mismatches.append({
                            "field": field, "public": str(left), "official": str(right),
                        })
                except (InvalidOperation, TypeError, ValueError) as exc:
                    result["field_mismatches"] += 1
                    result["mismatches_by_field"][field] += 1
                    row_mismatches.append({"field": field, "error": str(exc)})
            if row_mismatches:
                symbol_summary["field_mismatches"] += len(row_mismatches)
                if len(result["mismatch_examples"]) < 100:
                    result["mismatch_examples"].append({
                        "symbol": symbol, "date": day, "mismatches": row_mismatches,
                    })
            else:
                result["fully_matching_rows"] += 1
                symbol_summary["fully_matching_rows"] += 1
        result["per_symbol"].append(symbol_summary)

    result["status"] = "COMPLETED"
    result["match_rate_pct"] = round(
        result["fully_matching_rows"] / result["public_rows_matched_by_date"] * 100, 4
    ) if result["public_rows_matched_by_date"] else None
    return result


def audit_public_archive(*, workers: int = 8) -> dict:
    headers = {"User-Agent": "NEPSE-ELITE-public-archive-audit/1.0",
               "Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0),
                      headers=headers, follow_redirects=True) as client:
        meta = client.get(f"{API}/repos/{REPOSITORY}")
        meta.raise_for_status()
        branch = meta.json()["default_branch"]
        commit_response = client.get(f"{API}/repos/{REPOSITORY}/commits/{quote(branch, safe='')}")
        commit_response.raise_for_status()
        commit = commit_response.json()["sha"]
        tree_response = client.get(f"{API}/repos/{REPOSITORY}/git/trees/{commit}?recursive=1")
        tree_response.raise_for_status()
        tree_payload = tree_response.json()
        if tree_payload.get("truncated"):
            raise RuntimeError("Git tree is truncated; refusing incomplete archive audit")
        tree = tree_payload.get("tree", [])
        files = {
            Path(item["path"]).stem: item
            for item in tree
            if item.get("type") == "blob"
            and item.get("path", "").startswith("data/nepse/")
            and item.get("path", "").endswith(".csv")
            and Path(item["path"]).name != "NEPSE_INDEX.csv"
        }
        ref_url = f"{RAW}/{REPOSITORY}/{commit}/data/reference/nepse-symbols.csv"
        ref_response = client.get(ref_url)
        ref_response.raise_for_status()
        reference = list(csv.DictReader(io.StringIO(ref_response.text)))
        ordinary = [r for r in reference
                    if r.get("instrument_type") == "ordinary" and r.get("status") == "listed"]
        symbol_targets = []
        missing_files = []
        for row in ordinary:
            symbol = row["symbol"]
            file_key = symbol.replace("/", "-")
            item = files.get(file_key)
            if item is None:
                missing_files.append(symbol)
            else:
                symbol_targets.append((symbol, item["path"], item.get("sha")))

        def download_and_audit(target):
            symbol, path, blob_sha = target
            url = f"{RAW}/{REPOSITORY}/{commit}/{quote(path, safe='/')}"
            response = client.get(url)
            response.raise_for_status()
            if response.content.startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise ValueError("unexpected Git LFS pointer")
            result = audit_symbol_csv(response.content, symbol, path)
            result["git_blob_sha"] = blob_sha
            return result, response.content

        audited, errors, public_csv_by_symbol = [], [], {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(download_and_audit, target): target for target in symbol_targets}
            for future in as_completed(futures):
                try:
                    result, content = future.result()
                    audited.append(result)
                    public_csv_by_symbol[result["symbol"]] = content
                except Exception as exc:
                    symbol, path, _ = futures[future]
                    errors.append({"symbol": symbol, "path": path,
                                   "error": f"{type(exc).__name__}: {exc}"})
    audited.sort(key=lambda x: x["symbol"])
    totals = {key: sum(int(item.get(key, 0)) for item in audited) for key in (
        "rows", "valid_rows", "duplicate_dates", "invalid_dates",
        "out_of_order_transitions", "malformed_rows",
        "nonfinite_or_blank_numeric", "invalid_ohlc", "negative_volume",
        "fractional_volume", "negative_turnover", "zero_turnover_with_volume",
        "invalid_per_change",
    )}
    official_crosscheck = crosscheck_official_history(
        public_csv_by_symbol,
        Path("data/evidence/raw/nepse/security-history/2026-10-05_to_2026-11-26/symbols"),
    )
    bad_symbols = [item["symbol"] for item in audited if any(
        item.get(key, 0) for key in (
            "duplicate_dates", "invalid_dates", "out_of_order_transitions",
            "malformed_rows", "nonfinite_or_blank_numeric", "invalid_ohlc",
            "negative_volume", "fractional_volume", "negative_turnover",
            "zero_turnover_with_volume", "invalid_per_change",
        )
    ) or "header_mismatch" in item]
    dates = [item["first_date"] for item in audited if item.get("first_date")]
    last_dates = [item["last_date"] for item in audited if item.get("last_date")]
    quality_failed = bool(missing_files or errors or bad_symbols or len(audited) != len(ordinary))
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": REPOSITORY,
        "source_commit": commit,
        "source_tree_sha": tree_payload.get("sha"),
        "audit_mode": "read_only_public_secondary_archive_full_ordinary_listed_universe",
        "reference_master_rows": len(reference),
        "ordinary_listed_symbols_expected": len(ordinary),
        "ordinary_listed_files_audited": len(audited),
        "missing_files": missing_files,
        "download_errors": errors,
        "date_range": {"earliest_symbol_start": min(dates) if dates else None,
                       "latest_symbol_end": max(last_dates) if last_dates else None},
        "totals": totals,
        "symbols_with_any_quality_issue": len(set(bad_symbols)),
        "symbol_results": audited,
        "official_history_crosscheck": official_crosscheck,
        "gate": "FAIL" if quality_failed
                or official_crosscheck.get("status") != "COMPLETED"
                or official_crosscheck.get("field_mismatches", 0)
                or official_crosscheck.get("missing_public_active_rows", 0)
                or official_crosscheck.get("hash_or_parse_errors")
                or official_crosscheck.get("missing_public_symbol_files")
                else "STRUCTURAL_PASS_ONLY",
        "limitations": [
            "Publisher describes this as unofficial, best-effort data scraped from public sources; source completeness and correctness are not guaranteed.",
            "Publisher attributes NEPSE OHLCV to ShareSansar and historical backfill to Aabishkar2/nepse-data; upstream data sublicensing rights are not independently established by the repository's MIT code/data notice.",
            "Prices are unadjusted for bonus issues, rights issues and splits.",
            "This is a structural audit, not reconciliation against the official NEPSE exchange source or a verified trading-session calendar.",
            "A structural pass cannot authorize canonical promotion, production signals or backtesting.",
            "No source files are imported or modified by this audit.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("data/reports/public-nepse-archive-audit.json"))
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    report = audit_public_archive(workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "source_commit", "ordinary_listed_symbols_expected",
        "ordinary_listed_files_audited", "missing_files", "download_errors",
        "date_range", "totals", "symbols_with_any_quality_issue",
    )}, indent=2))
    print(json.dumps({"official_history_crosscheck": {
        key: report["official_history_crosscheck"].get(key)
        for key in ("status", "official_symbols_found", "official_rows",
                    "public_rows_matched_by_date", "fully_matching_rows",
                    "match_rate_pct", "field_comparisons", "field_mismatches",
                    "mismatches_by_field", "missing_public_active_rows",
                    "missing_public_zero_activity_rows", "missing_public_symbol_files",
                    "hash_or_parse_errors", "mismatch_examples")
    }, "gate": report["gate"]}, indent=2))


if __name__ == "__main__":
    main()
