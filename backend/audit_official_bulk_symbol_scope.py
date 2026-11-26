"""Classify official NEPSE bulk daily traded symbols against dated instrument references.

The snapshot is current as of 2026-11-25 and is not historical effective-date proof.
Unmatched or ID-conflicting symbols remain UNKNOWN; this audit never promotes data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = "nepalstock.com.np"
BULK_SOURCE = "NEPSE_OFFICIAL_BULK_DAILY_PRICE_VOLUME"
SUMMARY_SOURCE = "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY"
BULK_PATH = "/api/nots/nepse-data/today-price"


def _decimal(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f"negative or nonfinite {label}: {value!r}")
    return result


def _url_ok(value: object, path: str) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and parsed.hostname == HOST and parsed.port in (None, 443) and parsed.path == path


def _csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def _unique(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol or symbol in result:
            raise ValueError(f"{label}: blank or duplicate symbol {symbol!r}")
        result[symbol] = row
    return result


def _market_rows(body_path: Path, report_path: Path) -> tuple[dict[str, dict], dict]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    raw = body_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if report.get("source_id") != SUMMARY_SOURCE or report.get("http_status") != 200:
        raise ValueError("official market-summary capture identity/status invalid")
    if report.get("response_origin_verified") is not True or not _url_ok(report.get("source_url"), "/api/nots/market-summary-history"):
        raise ValueError("market-summary capture origin/URL invalid")
    if report.get("response_sha256") != digest or report.get("response_bytes") != len(raw):
        raise ValueError("market-summary raw response hash/size mismatch")
    payload = json.loads(raw.decode("utf-8"))
    rows = payload.get("content") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("market-summary payload has no row list")
    indexed = {}
    for row in rows:
        day = str(row.get("businessDate", ""))[:10]
        if not day or day in indexed:
            raise ValueError(f"market-summary date blank/duplicate: {day!r}")
        indexed[day] = row
    return indexed, {"source_id": SUMMARY_SOURCE, "sha256": digest, "response_bytes": len(raw)}


def _classify(symbol: str, security_id: str, bulk_name: str, snapshot: dict, crosswalk: dict,
              candidates: dict) -> tuple[str, str, str | None]:
    sec = snapshot.get(symbol)
    candidate = candidates.get(symbol)
    cross = crosswalk.get(symbol)
    if sec is None:
        return "UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH", "no dated security snapshot row", None
    if str(sec.get("security_id", "")) != security_id:
        return "UNKNOWN_SECURITY_ID_MISMATCH", "bulk security ID differs from 2026-11-25 snapshot", sec.get("security_name")
    if str(sec.get("security_name", "")) != bulk_name:
        return "UNKNOWN_SECURITY_NAME_MISMATCH", "bulk security name differs from 2026-11-25 snapshot", sec.get("security_name")
    if cross:
        if str(cross.get("security_id", "")) == security_id:
            return "IN_SCOPE_EQUITY_CANDIDATE", "2026-11-26 equity crosswalk plus 2026-11-25 snapshot ID match", sec.get("security_name")
        return "UNKNOWN_SECURITY_ID_MISMATCH", "equity crosswalk ID differs from bulk/snapshot", sec.get("security_name")
    if candidate:
        candidate_id = str(candidate.get("official_snapshot_id", "")).strip()
        candidate_status = str(candidate.get("official_snapshot_status", "")).strip()
        if not candidate_id or candidate_id != security_id or candidate_status != str(sec.get("active_status", "")).strip():
            return "UNKNOWN_SECURITY_ID_MISMATCH", "target-candidate registry ID/status differs from bulk/snapshot", sec.get("security_name")
    candidate_class = str((candidate or {}).get("instrument_class_from_rendered_list", "")).strip().casefold()
    name = str(sec.get("security_name", "")).casefold()
    if candidate_class == "mutual fund":
        return "OUT_OF_SCOPE_MUTUAL_FUND", "dated target-candidate registry classifies mutual fund", sec.get("security_name")
    if "promoter share" in name or "promoter" in name:
        return "OUT_OF_SCOPE_PROMOTER_SHARE", "dated security snapshot name identifies promoter share", sec.get("security_name")
    if "debenture" in name:
        return "OUT_OF_SCOPE_DEBENTURE", "dated security snapshot name identifies debenture", sec.get("security_name")
    if re.search(r"\bbond\b", name):
        return "OUT_OF_SCOPE_BOND", "dated security snapshot name identifies bond", sec.get("security_name")
    if candidate_class == "equity":
        return "EQUITY_CANDIDATE_NOT_IN_CROSSWALK", "target registry says equity but approved crosswalk lacks symbol", sec.get("security_name")
    return "UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY", "dated security snapshot row has no approved class", sec.get("security_name")


def audit_bulk_scope(bulk_report_path: Path, raw_dir: Path, summary_body_path: Path,
                     summary_report_path: Path, snapshot_path: Path,
                     crosswalk_path: Path, candidates_path: Path,
                     expected_snapshot_date: str = "2026-11-25") -> dict:
    bulk = json.loads(bulk_report_path.read_text(encoding="utf-8"))
    if bulk.get("source_id") != BULK_SOURCE or bulk.get("endpoint_path") != BULK_PATH:
        raise ValueError("unexpected official bulk daily capture source/endpoint")
    summary, summary_identity = _market_rows(summary_body_path, summary_report_path)
    snapshot_rows = _csv(snapshot_path, {"symbol", "security_id", "security_name", "active_status", "snapshot_date"})
    cross_rows = _csv(crosswalk_path, {"symbol", "security_id", "security_name", "snapshot_date", "active_status", "crosswalk_status"})
    candidate_rows = _csv(candidates_path, {"symbol", "instrument_class_from_rendered_list", "official_snapshot_id", "official_snapshot_status"})
    snapshot = _unique(snapshot_rows, "security snapshot")
    crosswalk = _unique(cross_rows, "equity crosswalk")
    candidates = _unique(candidate_rows, "target candidate registry")
    for symbol, row in snapshot.items():
        if row["snapshot_date"] != expected_snapshot_date:
            raise ValueError(f"{symbol}: unexpected security snapshot date")
    for symbol, row in crosswalk.items():
        sec = snapshot.get(symbol)
        if (row["snapshot_date"] != expected_snapshot_date or row["active_status"] != "A"
                or row["crosswalk_status"] != "snapshot_id_match_active_status_A" or sec is None
                or row["security_id"] != sec["security_id"] or row["security_name"] != sec["security_name"]
                or sec["active_status"] != "A"):
            raise ValueError(f"{symbol}: equity crosswalk/current snapshot mismatch")
    date_reports = {}
    aggregate_scope_counts = Counter()
    for day, date_item in sorted(bulk.get("date_reports", {}).items()):
        event = date_item.get("capture_event", {})
        if (event.get("requested_date") != day or event.get("query_business_date") != day
                or event.get("status") != 200 or event.get("origin_verified") is not True
                or not _url_ok(event.get("url"), BULK_PATH)):
            raise ValueError(f"{day}: official bulk capture event invalid")
        if parse_qs(urlparse(event["url"]).query).get("businessDate") != [day]:
            raise ValueError(f"{day}: bulk endpoint date query mismatch")
        raw_name = event.get("raw_file")
        if not raw_name or Path(raw_name).name != raw_name:
            raise ValueError(f"{day}: invalid raw file name")
        raw_path = raw_dir / raw_name
        raw_bytes = raw_path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if digest != event.get("sha256") or len(raw_bytes) != date_item.get("response_bytes"):
            raise ValueError(f"{day}: official bulk raw response hash/size mismatch")
        payload = json.loads(raw_bytes.decode("utf-8"))
        raw_rows = payload.get("content") if isinstance(payload, dict) else payload
        if not isinstance(raw_rows, list):
            raise ValueError(f"{day}: bulk raw response has no row list")
        analysis = date_item.get("analysis", {})
        rows = analysis.get("rows")
        if analysis.get("status") != "ROWS_RETURNED_REVIEW_ONLY" or not isinstance(rows, list):
            raise ValueError(f"{day}: parsed bulk analysis not accepted")
        if len(raw_rows) != len(rows) or len(rows) != analysis.get("row_count") or len(rows) != analysis.get("unique_symbol_count"):
            raise ValueError(f"{day}: raw/parsed/unique row counts differ")
        raw_by_symbol = {}
        for row in raw_rows:
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol or symbol in raw_by_symbol:
                raise ValueError(f"{day}: raw bulk symbol blank/duplicate")
            raw_by_symbol[symbol] = row
        seen = set()
        counts = Counter()
        metrics = {key: Decimal("0") for key in ("trades", "volume", "turnover")}
        symbols = []
        for row in rows:
            symbol = str(row.get("symbol", "")).strip().upper()
            if not symbol or symbol in seen:
                raise ValueError(f"{day}: parsed bulk symbol blank/duplicate")
            seen.add(symbol)
            raw = raw_by_symbol.get(symbol)
            if raw is None:
                raise ValueError(f"{day}/{symbol}: parsed row absent from raw response")
            if str(row.get("businessDate", ""))[:10] != day or str(raw.get("businessDate", ""))[:10] != day:
                raise ValueError(f"{day}/{symbol}: row business date mismatch")
            security_id = str(row.get("securityId", "")).strip()
            if not security_id or security_id != str(raw.get("securityId", "")).strip():
                raise ValueError(f"{day}/{symbol}: security ID raw/parsed mismatch")
            if str(row.get("securityName", "")) != str(raw.get("securityName", "")):
                raise ValueError(f"{day}/{symbol}: raw/parsed security name mismatch")
            for key, raw_key in (("trades", "totalTrades"), ("volume", "totalTradedQuantity"), ("turnover", "totalTradedValue")):
                value = _decimal(row.get(raw_key), f"{day}/{symbol} {raw_key}")
                if value <= 0:
                    raise ValueError(f"{day}/{symbol}: bulk traded row has nonpositive {raw_key}")
                if value != _decimal(raw.get(raw_key), f"{day}/{symbol} raw {raw_key}"):
                    raise ValueError(f"{day}/{symbol}: raw/parsed {raw_key} mismatch")
                metrics[key] += value
            scope, evidence, security_name = _classify(symbol, security_id, str(row.get("securityName", "")), snapshot, crosswalk, candidates)
            counts[scope] += 1
            aggregate_scope_counts[scope] += 1
            symbols.append({
                "symbol": symbol, "bulk_security_id": security_id,
                "bulk_security_name": row.get("securityName"),
                "snapshot_security_name": security_name,
                "bulk_snapshot_name_match": str(row.get("securityName", "")) == str(security_name or ""),
                "scope_class": scope, "scope_evidence": evidence,
                "current_snapshot_date": expected_snapshot_date,
                "historical_instrument_identity_verified": False,
            })
        if set(raw_by_symbol) != seen:
            raise ValueError(f"{day}: raw/parsed symbol sets differ")
        market = summary.get(day)
        if market is None:
            raise ValueError(f"{day}: no official market-summary control row")
        expected = {
            "trades": _decimal(market.get("totalTransactions"), f"{day} market trades"),
            "volume": _decimal(market.get("totalTradedShares"), f"{day} market volume"),
            "turnover": _decimal(market.get("totalTurnover"), f"{day} market turnover"),
            "traded_symbols": _decimal(market.get("tradedScrips"), f"{day} traded symbols"),
        }
        if metrics != {key: expected[key] for key in metrics} or len(rows) != expected["traded_symbols"]:
            raise ValueError(f"{day}: bulk symbol/aggregate totals do not exactly match official market summary")
        date_reports[day] = {
            "bulk_symbol_count": len(rows),
            "scope_class_counts": dict(sorted(counts.items())),
            "symbols": sorted(symbols, key=lambda x: x["symbol"]),
            "bulk_totals": {key: str(value) for key, value in metrics.items()},
            "official_market_summary_totals": {key: str(value) for key, value in expected.items()},
            "exact_official_summary_match": True,
        }
    return {
        "schema_version": "1.0",
        "audit_status": "review_only_official_bulk_symbol_scope",
        "bulk_source_id": BULK_SOURCE,
        "official_market_summary_evidence": summary_identity,
        "security_snapshot_date": expected_snapshot_date,
        "dates": date_reports,
        "aggregate_scope_class_counts": dict(sorted(aggregate_scope_counts.items())),
        "historical_instrument_identity_verified": False,
        "official_session_completeness_verified": False,
        "source_independence_verified": False,
        "source_rights_verified": False,
        "full_market_universe_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "dated_current_snapshot_scope_hints_only_unmatched_or_id_mismatch_unknown_no_historical_identity_claim",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bulk-report", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--market-summary-body", type=Path, required=True)
    parser.add_argument("--market-summary-report", type=Path, required=True)
    parser.add_argument("--security-snapshot", type=Path, required=True)
    parser.add_argument("--equity-crosswalk", type=Path, required=True)
    parser.add_argument("--target-candidates", type=Path, required=True)
    parser.add_argument("--snapshot-date", default="2026-11-25")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_bulk_scope(args.bulk_report, args.raw_dir, args.market_summary_body,
                              args.market_summary_report, args.security_snapshot,
                              args.equity_crosswalk, args.target_candidates, args.snapshot_date)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "aggregate_scope_class_counts": report["aggregate_scope_class_counts"],
        "dates": {day: {"bulk_symbol_count": item["bulk_symbol_count"],
                         "scope_class_counts": item["scope_class_counts"]}
                  for day, item in report["dates"].items()},
        "historical_instrument_identity_verified": False,
        "coverage_admission_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
