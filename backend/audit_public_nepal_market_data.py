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
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

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



def build_merged_official_history_root(
    capture_roots: list[Path],
    output_root: Path,
    expected_dates: list[str],
    lifecycle_path: Path,
) -> dict:
    """Verify and merge overlapping official capture windows for read-only cross-checks."""
    if len(capture_roots) < 2:
        raise ValueError("at least two independent capture windows are required")
    merged: dict[str, dict[str, dict]] = {}
    security_ids: dict[str, str] = {}
    capture_windows = []
    overlap_rows = 0
    overlap_mismatch_rows = 0
    mismatch_examples = []
    raw_hash_errors = []
    rows_by_capture = []
    capture_symbol_sets = []

    for root in capture_roots:
        evidence_root = root.parent
        report_path = evidence_root / "capture-report.json"
        manifest_path = evidence_root / "SHA256SUMS"
        if not report_path.is_file() or not manifest_path.is_file():
            raise ValueError(f"capture report or SHA256SUMS missing under {evidence_root}")
        capture = json.loads(report_path.read_text(encoding="utf-8"))
        if capture.get("source_id") != "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME_HISTORY":
            raise ValueError(f"unexpected official history source in {report_path}")
        if capture.get("endpoint_path") != "/api/nots/market/history/security/{security_id}":
            raise ValueError(f"unexpected official history endpoint in {report_path}")
        if capture.get("security_list_error") is not None:
            raise ValueError(f"official security-list capture reported an error in {report_path}")
        start_date = capture.get("requested_start_date")
        end_date = capture.get("requested_end_date")
        date.fromisoformat(start_date)
        date.fromisoformat(end_date)
        capture_windows.append({"start_date": start_date, "end_date": end_date})
        manifest = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                manifest[parts[1].lstrip("* ").replace("\\", "/")] = parts[0].lower()
        security_list_events = capture.get("security_list_capture")
        if not isinstance(security_list_events, list) or not security_list_events:
            raise ValueError(f"official security-list evidence missing in {report_path}")
        for event in security_list_events:
            parsed_security_url = urlparse(str(event.get("url", "")))
            relative = str(event.get("raw_file", "")).replace("\\", "/")
            raw_path = evidence_root / relative
            if not relative or not raw_path.is_file():
                raw_hash_errors.append({"symbol": "__SECURITY_LIST__", "capture_start": start_date,
                                        "capture_end": end_date, "path": relative})
                continue
            raw = raw_path.read_bytes()
            actual_sha = hashlib.sha256(raw).hexdigest()
            if (manifest.get(relative) != actual_sha or event.get("sha256") != actual_sha
                    or event.get("status") != 200 or event.get("origin_verified") is not True
                    or parsed_security_url.scheme != "https"
                    or parsed_security_url.hostname not in {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
                    or parsed_security_url.path != "/api/nots/security"):
                raw_hash_errors.append({"symbol": "__SECURITY_LIST__", "capture_start": start_date,
                                        "capture_end": end_date, "path": relative})

        symbols = capture.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            raise ValueError(f"official symbol rows missing in {report_path}")
        capture_row_count = 0
        capture_symbols = set()
        for item in symbols:
            symbol = str(item.get("symbol", "")).strip().upper()
            security_id = str(item.get("current_security_list_id", "")).strip()
            if not symbol or symbol in capture_symbols:
                raise ValueError(f"blank or duplicate symbol in {report_path}")
            capture_symbols.add(symbol)
            if (item.get("status") != "ROWS_RETURNED_REVIEW_ONLY"
                    or item.get("current_id_match") is not True
                    or item.get("historical_security_identity_verified") is not False):
                raise ValueError(f"{symbol}: capture status or identity flags are not review-only")
            if not security_id or str(item.get("crosswalk_security_id", "")).strip() != security_id:
                raise ValueError(f"{symbol}: current security ID missing")
            if symbol in security_ids and security_ids[symbol] != security_id:
                raise ValueError(f"{symbol}: security ID differs across capture windows")
            security_ids[symbol] = security_id
            events = item.get("responses")
            if not isinstance(events, list) or len(events) != 1:
                raise ValueError(f"{symbol}: expected exactly one official history response")
            event = events[0]
            parsed_url = urlparse(str(event.get("url", "")))
            query = parse_qs(parsed_url.query)
            if (event.get("status") != 200 or event.get("origin_verified") is not True
                    or parsed_url.scheme != "https"
                    or parsed_url.hostname not in {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
                    or parsed_url.path != f"/api/nots/market/history/security/{security_id}"
                    or query.get("startDate") != [start_date]
                    or query.get("endDate") != [end_date]):
                raise ValueError(f"{symbol}: response origin, ID path or requested date window is invalid")
            relative = str(event.get("raw_file", "")).replace("\\", "/")
            raw_path = evidence_root / relative
            if not relative or not raw_path.is_file():
                raise ValueError(f"{symbol}: official raw response file is missing")
            raw = raw_path.read_bytes()
            actual_sha = hashlib.sha256(raw).hexdigest()
            if (manifest.get(relative) != actual_sha
                    or event.get("sha256") != actual_sha
                    or item.get("response_sha256") != actual_sha):
                raw_hash_errors.append({"symbol": symbol, "capture_start": start_date,
                                        "capture_end": end_date, "path": relative})
                continue
            payload = json.loads(raw.decode("utf-8"))
            raw_rows = payload.get("content") if isinstance(payload, dict) else None
            if not isinstance(raw_rows, list):
                raise ValueError(f"{symbol}: official raw response has no content array")
            report_rows = item.get("rows")
            if not isinstance(report_rows, list) or len(report_rows) != len(raw_rows):
                raise ValueError(f"{symbol}: normalized capture report row count differs from raw response")
            report_raw_by_date = {
                str(row.get("business_date", "")): row.get("raw")
                for row in report_rows
            }
            per_symbol = merged.setdefault(symbol, {})
            seen_capture_dates = set()
            for row in raw_rows:
                day = str(row.get("businessDate", ""))[:10]
                date.fromisoformat(day)
                if not start_date <= day <= end_date or day in seen_capture_dates:
                    raise ValueError(f"{symbol}: duplicate or out-of-range raw history date {day}")
                seen_capture_dates.add(day)
                if report_raw_by_date.get(day) != row:
                    raise ValueError(f"{symbol} {day}: report row does not match hash-verified raw response")
                capture_row_count += 1
                if day in per_symbol:
                    overlap_rows += 1
                    if per_symbol[day] != row:
                        overlap_mismatch_rows += 1
                        if len(mismatch_examples) < 100:
                            mismatch_examples.append({
                                "symbol": symbol, "date": day,
                                "existing": per_symbol[day], "new": row,
                            })
                else:
                    per_symbol[day] = row
        capture_symbol_sets.append(capture_symbols)
        rows_by_capture.append({
            "start_date": start_date, "end_date": end_date,
            "symbols": len(capture_symbols), "rows": capture_row_count,
        })

    if any(symbol_set != capture_symbol_sets[0] for symbol_set in capture_symbol_sets[1:]):
        raise ValueError("official capture windows do not contain the same security universe")
    if not merged:
        raise ValueError("no verified official rows could be merged")
    lifecycle = {}
    with lifecycle_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            symbol = (row.get("symbol") or "").strip().upper()
            if symbol:
                lifecycle[symbol] = {
                    "valid_from": (row.get("valid_from") or "").strip(),
                    "valid_from_evidence_status": (row.get("valid_from_evidence_status") or "unverified").strip(),
                }
    if set(lifecycle) != set(merged):
        raise ValueError("lifecycle symbol universe does not match merged official capture universe")

    expected_dates = sorted(set(expected_dates))
    missing_pre_valid = 0
    missing_unexplained = 0
    for symbol, by_date in merged.items():
        context = lifecycle[symbol]
        valid_from = context["valid_from"]
        evidence_status = context["valid_from_evidence_status"]
        if valid_from:
            date.fromisoformat(valid_from)
        for day in expected_dates:
            if day not in by_date:
                if valid_from and evidence_status != "unverified" and day < valid_from:
                    missing_pre_valid += 1
                else:
                    missing_unexplained += 1

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_lines = []
    total_rows = 0
    all_dates = set()
    for symbol, by_date in sorted(merged.items()):
        rows = [by_date[day] for day in sorted(by_date)]
        all_dates.update(by_date)
        total_rows += len(rows)
        raw = json.dumps({"content": rows}, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        folder = output_root / symbol
        folder.mkdir(parents=True, exist_ok=True)
        filename = folder / "response-01.bin"
        filename.write_bytes(raw)
        relative = str(filename.relative_to(output_root.parent)).replace("\\", "/")
        manifest_lines.append(f"{hashlib.sha256(raw).hexdigest()}  {relative}\n")
    (output_root.parent / "SHA256SUMS").write_text("".join(manifest_lines), encoding="utf-8")

    expected_pairs = len(expected_dates) * len(merged)
    expected_date_set = set(expected_dates)
    unexpected_dates = sorted(all_dates - expected_date_set)
    missing_expected_dates = sorted(expected_date_set - all_dates)
    missing_pairs = expected_pairs - sum(
        1 for by_date in merged.values() for day in by_date if day in expected_date_set
    )
    return {
        "status": "REVIEW_ONLY",
        "capture_windows": capture_windows,
        "rows_by_capture": rows_by_capture,
        "official_symbols": len(merged),
        "official_dates_expected": len(expected_dates),
        "official_dates_present": len(all_dates),
        "official_first_date": min(all_dates) if all_dates else None,
        "official_last_date": max(all_dates) if all_dates else None,
        "unexpected_dates": unexpected_dates,
        "missing_expected_dates": missing_expected_dates,
        "official_rows_after_merge": total_rows,
        "expected_symbol_date_pairs": expected_pairs,
        "missing_symbol_date_pairs": missing_pairs,
        "missing_pre_valid_from_rows": missing_pre_valid,
        "unexplained_missing_rows": missing_unexplained,
        "overlap_rows_compared": overlap_rows,
        "overlap_mismatch_rows": overlap_mismatch_rows,
        "overlap_mismatch_examples": mismatch_examples,
        "raw_hash_errors": raw_hash_errors,
        "open_price_available": False,
        "historical_security_identity_verified": False,
        "source_rights_verified": False,
        "canonical_promotion_allowed": False,
        "gate": "FAIL" if (
            raw_hash_errors or overlap_mismatch_rows or missing_unexplained
            or missing_pairs != missing_pre_valid
            or unexpected_dates or missing_expected_dates
        ) else "RECONCILED_REVIEW_ONLY",
    }


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



def compare_socrateai_daily_csvs(official_rows: list[dict], daily_csv_by_date: dict[str, bytes]) -> dict:
    """Compare a public daily OHLC archive against pinned official NEPSE captures."""
    fields = {
        "high": ("high", "highPrice", Decimal("0.0001")),
        "low": ("low", "lowPrice", Decimal("0.0001")),
        "close": ("close", "closePrice", Decimal("0.0001")),
        "volume": ("volume", "totalTradedQuantity", Decimal("0")),
    }
    result = {
        "official_rows": len(official_rows),
        "public_dates_expected": len({str(r.get("businessDate", ""))[:10] for r in official_rows}),
        "public_files_found": len(daily_csv_by_date),
        "missing_public_files": [],
        "public_rows": 0,
        "duplicate_symbol_rows": 0,
        "malformed_rows": 0,
        "invalid_ohlc_rows": 0,
        "official_rows_matched_by_date": 0,
        "fully_matching_rows": 0,
        "field_comparisons": 0,
        "field_mismatches": 0,
        "mismatches_by_field": {key: 0 for key in fields},
        "field_error_accumulators": {
            key: {"absolute_difference_sum": 0.0, "max_absolute_difference": 0.0,
                  "max_relative_difference_pct": 0.0}
            for key in fields
        },
        "missing_public_active_rows": 0,
        "missing_public_zero_activity_rows": 0,
        "mismatch_examples": [],
        "per_day": [],
        "fields_compared": list(fields),
        "not_compared": ["open", "turnover", "per_change", "status"],
    }
    public_by_date = {}
    expected_dates = sorted({str(r.get("businessDate", ""))[:10] for r in official_rows})
    for day in expected_dates:
        content = daily_csv_by_date.get(day)
        if content is None:
            result["missing_public_files"].append(day)
            public_by_date[day] = {}
            continue
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            if reader.fieldnames != ["date", "close", "open", "high", "low", "volume", "symbol"]:
                result["malformed_rows"] += 1
                public_by_date[day] = {}
                continue
            rows = {}
            for row in reader:
                result["public_rows"] += 1
                symbol = (row.get("symbol") or "").strip()
                if not symbol or row.get("date") != day:
                    result["malformed_rows"] += 1
                    continue
                if symbol in rows:
                    result["duplicate_symbol_rows"] += 1
                    continue
                try:
                    values = {key: Decimal(str(row[key])) for key in
                              ("open", "high", "low", "close", "volume")}
                    if any(not value.is_finite() for value in values.values()):
                        raise InvalidOperation("non-finite value")
                except (InvalidOperation, TypeError, ValueError, KeyError):
                    result["malformed_rows"] += 1
                    continue
                if min(values["open"], values["high"], values["low"], values["close"]) <= 0 or (
                    values["high"] < max(values["open"], values["low"], values["close"])
                    or values["low"] > min(values["open"], values["high"], values["close"])
                    or values["volume"] < 0
                ):
                    result["invalid_ohlc_rows"] += 1
                rows[symbol] = values
            public_by_date[day] = rows
        except (UnicodeDecodeError, csv.Error):
            result["malformed_rows"] += 1
            public_by_date[day] = {}

    for day in expected_dates:
        day_official = [r for r in official_rows if str(r.get("businessDate", ""))[:10] == day]
        day_result = {"date": day, "official_rows": len(day_official), "matched": 0, "mismatches": 0}
        public_rows = public_by_date.get(day, {})
        for official in day_official:
            symbol = str(official.get("symbol", "")).strip()
            public = public_rows.get(symbol)
            quantity = Decimal(str(official.get("totalTradedQuantity", 0) or 0))
            turnover = Decimal(str(official.get("totalTradedValue", 0) or 0))
            if public is None:
                if quantity > 0 or turnover > 0:
                    result["missing_public_active_rows"] += 1
                else:
                    result["missing_public_zero_activity_rows"] += 1
                continue
            result["official_rows_matched_by_date"] += 1
            day_result["matched"] += 1
            mismatches = []
            for field, (public_key, official_key, tolerance) in fields.items():
                try:
                    left = public[public_key]
                    right = Decimal(str(official[official_key]))
                    result["field_comparisons"] += 1
                    difference = abs(left - right)
                    if difference > tolerance:
                        result["field_mismatches"] += 1
                        result["mismatches_by_field"][field] += 1
                        stats = result["field_error_accumulators"][field]
                        absolute = float(difference)
                        relative_pct = float(difference / abs(right) * 100) if right else None
                        stats["absolute_difference_sum"] += absolute
                        stats["max_absolute_difference"] = max(stats["max_absolute_difference"], absolute)
                        if relative_pct is not None:
                            stats["max_relative_difference_pct"] = max(
                                stats["max_relative_difference_pct"], relative_pct
                            )
                        mismatches.append({"field": field, "public": str(left), "official": str(right)})
                except (InvalidOperation, TypeError, ValueError, KeyError) as exc:
                    result["field_mismatches"] += 1
                    result["mismatches_by_field"][field] += 1
                    mismatches.append({"field": field, "error": str(exc)})
            if mismatches:
                day_result["mismatches"] += 1
                if len(result["mismatch_examples"]) < 100:
                    result["mismatch_examples"].append({
                        "symbol": symbol, "date": day, "mismatches": mismatches,
                    })
            else:
                result["fully_matching_rows"] += 1
        result["per_day"].append(day_result)
    result["field_error_stats"] = {
        field: {
            "count": result["mismatches_by_field"][field],
            "mean_absolute_difference": round(
                values["absolute_difference_sum"] / result["mismatches_by_field"][field], 6
            ) if result["mismatches_by_field"][field] else 0,
            "max_absolute_difference": round(values["max_absolute_difference"], 6),
            "max_relative_difference_pct": round(values["max_relative_difference_pct"], 6),
        }
        for field, values in result["field_error_accumulators"].items()
    }
    del result["field_error_accumulators"]
    result["match_rate_pct"] = round(
        result["fully_matching_rows"] / result["official_rows_matched_by_date"] * 100, 4
    ) if result["official_rows_matched_by_date"] else None
    result["status"] = "COMPLETED"
    return result


def crosscheck_socrateai_history(official_root: Path) -> dict:
    """Fetch pinned free SocrateAI daily files and compare them to official captures."""
    evidence_root = official_root.parent
    manifest_path = evidence_root / "SHA256SUMS"
    manifest = {}
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                manifest[parts[1].lstrip("* ")] = parts[0].lower()
    official_rows = []
    hash_errors = []
    for symbol_dir in sorted(p for p in official_root.iterdir() if p.is_dir()):
        response_path = symbol_dir / "response-01.bin"
        if not response_path.exists():
            continue
        relative = str(response_path.relative_to(evidence_root)).replace("\\", "/")
        raw = response_path.read_bytes()
        if manifest.get(relative) != hashlib.sha256(raw).hexdigest():
            hash_errors.append({"symbol": symbol_dir.name, "error": "official_sha256_missing_or_mismatch"})
            continue
        try:
            rows = json.loads(raw.decode("utf-8")).get("content")
            if not isinstance(rows, list):
                raise ValueError("missing content array")
            for row in rows:
                official_rows.append({**row, "symbol": symbol_dir.name})
        except Exception as exc:
            hash_errors.append({"symbol": symbol_dir.name, "error": f"official_json_invalid:{type(exc).__name__}"})
    dates = sorted({str(r.get("businessDate", ""))[:10] for r in official_rows if r.get("businessDate")})
    if not dates:
        return {"status": "OFFICIAL_CAPTURE_NOT_PRESENT", "hash_errors": hash_errors}
    headers = {"User-Agent": "NEPSE-ELITE-public-source-crosscheck/1.0"}
    with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0),
                      headers=headers, follow_redirects=True) as client:
        commit_response = client.get("https://api.github.com/repos/socrateai-official/nepse-open-data/commits/main")
        commit_response.raise_for_status()
        source_commit = commit_response.json()["sha"]
        daily_files = {}
        download_errors = []
        for day in dates:
            url = f"https://raw.githubusercontent.com/socrateai-official/nepse-open-data/{source_commit}/ohlc_unadjusted_stock/unadj_{day}.csv"
            response = client.get(url)
            if response.status_code == 404:
                download_errors.append({"date": day, "error": "daily_file_missing"})
                continue
            response.raise_for_status()
            daily_files[day] = response.content
    result = compare_socrateai_daily_csvs(official_rows, daily_files)
    result["source_repository"] = "socrateai-official/nepse-open-data"
    result["source_commit"] = source_commit
    result["official_hash_errors"] = hash_errors
    result["download_errors"] = download_errors
    result["gate"] = "FAIL" if (
        hash_errors or download_errors or result["missing_public_files"]
        or result["duplicate_symbol_rows"] or result["malformed_rows"]
        or result["invalid_ohlc_rows"] or result["missing_public_active_rows"]
        or result["field_mismatches"]
    ) else "RECONCILED_WINDOW_ONLY"
    return result



def compare_srijankarki_daily_csvs(official_rows: list[dict],
                                    daily_csv_by_date: dict[str, bytes]) -> dict:
    """Compare a free ShareSansar-derived daily archive to official NEPSE rows."""
    fields = {
        "high": ("high", "highPrice", Decimal("0.0001")),
        "low": ("low", "lowPrice", Decimal("0.0001")),
        "close": ("close", "closePrice", Decimal("0.0001")),
        "volume": ("volume", "totalTradedQuantity", Decimal("0")),
        "turnover": ("turnover", "totalTradedValue", Decimal("0.05")),
    }
    result = {
        "official_rows": len(official_rows),
        "public_dates_expected": len({str(r.get("businessDate", ""))[:10] for r in official_rows}),
        "public_files_found": len(daily_csv_by_date),
        "missing_public_files": [],
        "public_rows": 0,
        "duplicate_symbol_rows": 0,
        "malformed_rows": 0,
        "invalid_ohlc_rows": 0,
        "official_rows_matched_by_date": 0,
        "fully_matching_rows": 0,
        "field_comparisons": 0,
        "field_mismatches": 0,
        "mismatches_by_field": {key: 0 for key in fields},
        "field_error_accumulators": {
            key: {"absolute_difference_sum": 0.0, "max_absolute_difference": 0.0,
                  "max_relative_difference_pct": 0.0}
            for key in fields
        },
        "missing_public_active_rows": 0,
        "missing_public_zero_activity_rows": 0,
        "mismatch_examples": [],
        "per_day": [],
        "fields_compared": list(fields),
        "not_compared": ["open"],
        "open_values_observed": 0,
    }
    official_by_day = {}
    expected_symbols = set()
    for row in official_rows:
        day = str(row.get("businessDate", ""))[:10]
        symbol = str(row.get("symbol", "")).strip().upper()
        if not day or not symbol:
            continue
        expected_symbols.add(symbol)
        official_by_day.setdefault(day, []).append(row)

    for day in sorted(official_by_day):
        content = daily_csv_by_date.get(day)
        if content is None:
            result["missing_public_files"].append(day)
            public_rows = {}
        else:
            try:
                reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
                if reader.fieldnames != ["date", "symbol", "open", "high", "low", "close", "volume", "turnover"]:
                    result["malformed_rows"] += 1
                    public_rows = {}
                else:
                    public_rows = {}
                    for row in reader:
                        symbol = (row.get("symbol") or "").strip().upper()
                        if symbol not in expected_symbols:
                            continue
                        result["public_rows"] += 1
                        if row.get("date") != day or not symbol:
                            result["malformed_rows"] += 1
                            continue
                        if symbol in public_rows:
                            result["duplicate_symbol_rows"] += 1
                            continue
                        try:
                            values = {
                                key: Decimal(str(row[key]))
                                for key in ("open", "high", "low", "close", "volume", "turnover")
                            }
                            if any(not value.is_finite() for value in values.values()):
                                raise InvalidOperation("non-finite value")
                        except (InvalidOperation, TypeError, ValueError, KeyError):
                            result["malformed_rows"] += 1
                            continue
                        result["open_values_observed"] += 1
                        if (min(values["open"], values["high"], values["low"], values["close"]) <= 0
                                or values["high"] < max(values["open"], values["low"], values["close"])
                                or values["low"] > min(values["open"], values["high"], values["close"])
                                or values["volume"] < 0 or values["turnover"] < 0):
                            result["invalid_ohlc_rows"] += 1
                        public_rows[symbol] = values
            except (UnicodeDecodeError, csv.Error):
                result["malformed_rows"] += 1
                public_rows = {}

        day_result = {"date": day, "official_rows": len(official_by_day[day]),
                      "matched": 0, "mismatches": 0}
        for official in official_by_day[day]:
            symbol = str(official.get("symbol", "")).strip().upper()
            public = public_rows.get(symbol)
            quantity = Decimal(str(official.get("totalTradedQuantity", 0) or 0))
            turnover = Decimal(str(official.get("totalTradedValue", 0) or 0))
            if public is None:
                if quantity > 0 or turnover > 0:
                    result["missing_public_active_rows"] += 1
                else:
                    result["missing_public_zero_activity_rows"] += 1
                continue
            result["official_rows_matched_by_date"] += 1
            day_result["matched"] += 1
            row_mismatches = []
            for field, (public_key, official_key, tolerance) in fields.items():
                try:
                    left = public[public_key]
                    right = Decimal(str(official[official_key]))
                    if not left.is_finite() or not right.is_finite():
                        raise InvalidOperation("non-finite value")
                    result["field_comparisons"] += 1
                    difference = abs(left - right)
                    if difference > tolerance:
                        result["field_mismatches"] += 1
                        result["mismatches_by_field"][field] += 1
                        stats = result["field_error_accumulators"][field]
                        absolute = float(difference)
                        relative_pct = float(difference / abs(right) * 100) if right else None
                        stats["absolute_difference_sum"] += absolute
                        stats["max_absolute_difference"] = max(stats["max_absolute_difference"], absolute)
                        if relative_pct is not None:
                            stats["max_relative_difference_pct"] = max(
                                stats["max_relative_difference_pct"], relative_pct
                            )
                        row_mismatches.append({
                            "field": field, "public": str(left), "official": str(right),
                        })
                except (InvalidOperation, TypeError, ValueError, KeyError) as exc:
                    result["field_mismatches"] += 1
                    result["mismatches_by_field"][field] += 1
                    row_mismatches.append({"field": field, "error": str(exc)})
            if row_mismatches:
                day_result["mismatches"] += 1
                if len(result["mismatch_examples"]) < 100:
                    result["mismatch_examples"].append({
                        "symbol": symbol, "date": day, "mismatches": row_mismatches,
                    })
            else:
                result["fully_matching_rows"] += 1
        result["per_day"].append(day_result)

    result["field_error_stats"] = {
        field: {
            "count": result["mismatches_by_field"][field],
            "mean_absolute_difference": round(
                values["absolute_difference_sum"] / result["mismatches_by_field"][field], 6
            ) if result["mismatches_by_field"][field] else 0,
            "max_absolute_difference": round(values["max_absolute_difference"], 6),
            "max_relative_difference_pct": round(values["max_relative_difference_pct"], 6),
        }
        for field, values in result["field_error_accumulators"].items()
    }
    del result["field_error_accumulators"]
    result["match_rate_pct"] = round(
        result["fully_matching_rows"] / result["official_rows_matched_by_date"] * 100, 4
    ) if result["official_rows_matched_by_date"] else None
    result["status"] = "COMPLETED"
    result["gate"] = "RECONCILED_REVIEW_ONLY" if (
        not result["missing_public_files"] and not result["duplicate_symbol_rows"]
        and not result["malformed_rows"] and not result["invalid_ohlc_rows"]
        and not result["missing_public_active_rows"] and not result["field_mismatches"]
    ) else "FAIL"
    return result


def crosscheck_srijankarki_history(official_root: Path) -> dict:
    """Fetch pinned public ShareSansar-derived daily CSVs and compare official fields."""
    evidence_root = official_root.parent
    manifest_path = evidence_root / "SHA256SUMS"
    manifest = {}
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                manifest[parts[1].lstrip("* ")] = parts[0].lower()
    official_rows = []
    hash_errors = []
    for symbol_dir in sorted(p for p in official_root.iterdir() if p.is_dir()):
        response_path = symbol_dir / "response-01.bin"
        if not response_path.exists():
            continue
        relative = str(response_path.relative_to(evidence_root)).replace("\\", "/")
        raw = response_path.read_bytes()
        if manifest.get(relative) != hashlib.sha256(raw).hexdigest():
            hash_errors.append({"symbol": symbol_dir.name, "error": "official_response_sha256_missing_or_mismatched"})
            continue
        try:
            rows = json.loads(raw.decode("utf-8")).get("content")
            if not isinstance(rows, list):
                raise ValueError("official response missing content array")
            for row in rows:
                official_rows.append({**row, "symbol": symbol_dir.name})
        except Exception as exc:
            hash_errors.append({"symbol": symbol_dir.name, "error": f"official_json_invalid:{type(exc).__name__}"})
    dates = sorted({str(r.get("businessDate", ""))[:10] for r in official_rows if r.get("businessDate")})
    if not dates:
        return {"status": "OFFICIAL_CAPTURE_NOT_PRESENT", "official_hash_errors": hash_errors}
    headers = {"User-Agent": "NEPSE-ELITE-public-source-crosscheck/1.0",
               "Accept": "application/vnd.github+json"}
    with httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0),
                      headers=headers, follow_redirects=True) as client:
        commit_response = client.get("https://api.github.com/repos/srijankarki07/nepse-data/commits/main")
        commit_response.raise_for_status()
        source_commit = commit_response.json()["sha"]
        daily_files = {}
        download_errors = []
        for day in dates:
            url = (f"https://raw.githubusercontent.com/srijankarki07/nepse-data/{source_commit}"
                   f"/data/daily/{day[:4]}/{day}.csv")
            response = client.get(url)
            if response.status_code == 404:
                download_errors.append({"date": day, "error": "daily_file_missing"})
                continue
            response.raise_for_status()
            daily_files[day] = response.content
    result = compare_srijankarki_daily_csvs(official_rows, daily_files)
    result["source_repository"] = "srijankarki07/nepse-data"
    result["source_commit"] = source_commit
    result["official_hash_errors"] = hash_errors
    result["download_errors"] = download_errors
    result["source_provenance"] = "publisher states all data was scraped from ShareSansar; not direct NEPSE data"
    result["source_rights_verified"] = False
    result["corporate_action_adjustments_verified"] = False
    result["open_price_independently_verified"] = False
    result["gate"] = "FAIL" if (
        hash_errors or download_errors or result["gate"] != "RECONCILED_REVIEW_ONLY"
    ) else "RECONCILED_REVIEW_ONLY"
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
    from audit_official_security_history_window import load_expected_market_dates
    market_body_path = Path("data/evidence/raw/nepse/market-summary-history/2026-11-26/response-body.bin")
    market_report_path = Path("data/evidence/raw/nepse/market-summary-history/2026-11-26/capture-report.json")
    expected_official_dates, _ = load_expected_market_dates(
        market_body_path, market_report_path, "2025-11-26", "2026-11-26"
    )
    official_capture_roots = [
        Path("data/evidence/raw/nepse/security-history/2025-11-26_to_2026-11-26/symbols"),
        Path("data/evidence/raw/nepse/security-history/2026-10-05_to_2026-11-26/symbols"),
    ]
    with tempfile.TemporaryDirectory(prefix="nepse-official-merged-") as temp_dir:
        merged_official_root = Path(temp_dir) / "merged" / "symbols"
        official_capture_merge = build_merged_official_history_root(
            official_capture_roots,
            merged_official_root,
            expected_official_dates,
            Path("data/reference/nepse_equity_lifecycle_coverage_input_2026-11-26.csv"),
        )
        official_crosscheck = crosscheck_official_history(
            public_csv_by_symbol, merged_official_root
        )
        socrateai_crosscheck = crosscheck_socrateai_history(merged_official_root)
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
        "official_capture_merge": official_capture_merge,
        "official_history_crosscheck": official_crosscheck,
        "socrateai_history_crosscheck": socrateai_crosscheck,
        "gate": "FAIL" if quality_failed
                or official_capture_merge.get("gate") != "RECONCILED_REVIEW_ONLY"
                or socrateai_crosscheck.get("gate") != "RECONCILED_WINDOW_ONLY"
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
            "The audit cross-checks official NEPSE high, low, close, volume and turnover for the captured review window; opening price is not present in the official per-security history endpoint response.",
            "Current security-list IDs are not proven historical identities, and the official capture does not establish the complete historical instrument universe.",
            "The public archive and official source comparisons do not establish upstream data sublicensing rights or corporate-action adjustment methodology.",
            "A reconciliation result is review-only and cannot authorize canonical promotion, production signals or backtesting.",
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
    print(json.dumps({"official_capture_merge": report["official_capture_merge"],
        "official_history_crosscheck": {
        key: report["official_history_crosscheck"].get(key)
        for key in ("status", "official_symbols_found", "official_rows",
                    "public_rows_matched_by_date", "fully_matching_rows",
                    "match_rate_pct", "field_comparisons", "field_mismatches",
                    "mismatches_by_field", "field_error_stats", "missing_public_active_rows",
                    "missing_public_zero_activity_rows", "missing_public_symbol_files",
                    "hash_or_parse_errors", "mismatch_examples")
    }, "socrateai_history_crosscheck": {
        key: report["socrateai_history_crosscheck"].get(key)
        for key in ("status", "source_commit", "official_rows",
                    "public_dates_expected", "public_files_found", "missing_public_files",
                    "official_rows_matched_by_date", "fully_matching_rows",
                    "match_rate_pct", "field_comparisons", "field_mismatches",
                    "mismatches_by_field", "field_error_stats", "missing_public_active_rows",
                    "missing_public_zero_activity_rows", "mismatch_examples",
                    "official_hash_errors", "download_errors", "gate")
    }, "gate": report["gate"]}, indent=2))


if __name__ == "__main__":
    main()
