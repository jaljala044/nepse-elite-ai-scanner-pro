"""Compare pinned floorsheet aggregates with a captured official NEPSE summary-history response.

The official summary is aggregate-only. This audit does not establish per-security
completeness, floorsheet source lineage, or historical instrument identity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

OFFICIAL_HOSTS = {"nepalstock.com.np", "www.nepalstock.com.np", "newweb.nepalstock.com"}
ENDPOINT_PATH = "/api/nots/market-summary-history"
DATES = ("2026-11-19", "2026-11-20", "2026-11-24")
SUMMARY_FIELDS = {
    "turnover": ("totalTurnover", "total_turnover"),
    "volume": ("totalTradedShares", "total_traded_shares"),
    "transactions": ("totalTransactions", "total_transactions", "totalTransaction"),
    "traded_scrips": ("tradedScrips", "traded_scrips"),
}


def _number(value: object, label: str) -> Decimal:
    try:
        result = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"nonpositive or nonfinite {label}: {value!r}")
    return result


def load_official_summary(capture_dir: Path) -> tuple[dict, dict]:
    report = json.loads((capture_dir / "capture-report.json").read_text(encoding="utf-8"))
    raw = (capture_dir / "response-body.bin").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    url = urlparse(report.get("source_url", ""))
    if report.get("source_id") != "NEPSE_OFFICIAL_MARKET_SUMMARY_HISTORY":
        raise ValueError("unexpected official capture source ID")
    if report.get("http_status") != 200 or report.get("response_origin_verified") is not True:
        raise ValueError("official capture status/origin is not verified")
    if url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS or url.path.rstrip("/") != ENDPOINT_PATH:
        raise ValueError("official capture URL is outside the approved NEPSE endpoint")
    if report.get("response_sha256") != digest or report.get("response_bytes") != len(raw):
        raise ValueError("official response body digest/size does not match capture report")
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("official summary-history payload must be a JSON list")
    by_date = {}
    for index, row in enumerate(payload):
        if not isinstance(row, dict):
            raise ValueError(f"official summary row {index} is not an object")
        day_value = row.get("businessDate", row.get("business_date", row.get("date")))
        if not isinstance(day_value, str):
            raise ValueError(f"official summary row {index} has no date")
        day = day_value[:10]
        if day in by_date:
            raise ValueError(f"duplicate official summary date {day}")
        metrics = {}
        for key, aliases in SUMMARY_FIELDS.items():
            value = next((row[name] for name in aliases if name in row), None)
            metrics[key] = _number(value, f"{day} official {key}")
        by_date[day] = metrics
    return report, by_date


def _aggregate_floorsheet(path: Path, day: str, source: str) -> dict:
    columns = {
        "samir": {"contract": "contract_no", "symbol": "stock_symbol", "quantity": "quantity", "amount": "amount", "date": "date"},
        "socrateai": {"contract": "transaction", "symbol": "symbol", "quantity": "quantity", "amount": "amount", "date": "date"},
    }[source]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(columns.values()) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{source} {day}: missing columns {sorted(missing)}")
        contracts = set()
        symbols = set()
        volume = Decimal("0")
        turnover = Decimal("0")
        for line, row in enumerate(reader, start=2):
            if row[columns["date"]].strip()[:10] != day:
                raise ValueError(f"{source} {day}: row {line} has mismatched date")
            contract = row[columns["contract"]].strip()
            symbol = row[columns["symbol"]].strip().upper()
            if not contract or not symbol or contract in contracts:
                raise ValueError(f"{source} {day}: blank or duplicate contract/symbol at row {line}")
            contracts.add(contract)
            symbols.add(symbol)
            volume += _number(row[columns["quantity"]], f"{source} {day} quantity row {line}")
            turnover += _number(row[columns["amount"]], f"{source} {day} amount row {line}")
    if not contracts:
        raise ValueError(f"{source} {day}: empty floorsheet is not accepted")
    return {
        "transactions": Decimal(len(contracts)),
        "volume": volume,
        "turnover": turnover,
        "traded_scrips": Decimal(len(symbols)),
        "symbol_count": len(symbols),
    }


def reconcile(official_capture_dir: Path, floorsheet_dir: Path) -> dict:
    capture, official_by_date = load_official_summary(official_capture_dir)
    reports = {}
    for day in DATES:
        official = official_by_date.get(day)
        if official is None:
            raise ValueError(f"official summary has no row for required date {day}")
        sources = {}
        for source in ("samir", "socrateai"):
            floor = _aggregate_floorsheet(floorsheet_dir / f"{source}-{day}.csv", day, source)
            comparisons = {}
            for metric in ("transactions", "volume", "turnover", "traded_scrips"):
                observed = floor[metric]
                expected = official[metric]
                comparisons[metric] = {
                    "floorsheet": str(observed),
                    "official_nepse": str(expected),
                    "difference": str(observed - expected),
                    "match": observed == expected,
                }
            sources[source] = {
                "aggregates": {key: str(floor[key]) for key in ("transactions", "volume", "turnover", "traded_scrips")},
                "symbol_count": floor["symbol_count"],
                "comparisons": comparisons,
                "all_aggregate_metrics_match": all(item["match"] for item in comparisons.values()),
                "date_semantics": (
                    "publisher_capture_date_field_not_exchange_issued"
                    if source == "samir" else
                    "publisher_trade_date_field_lineage_not_independently_verified"
                ),
            }
        reports[day] = {"official_nepse": {k: str(v) for k, v in official.items()}, "sources": sources}
    return {
        "schema_version": "1.0",
        "audit_status": "review_only_official_aggregate_control_reconciliation",
        "official_capture": {
            "source_id": capture["source_id"],
            "source_url": capture["source_url"],
            "retrieved_at_utc": capture["retrieved_at_utc"],
            "response_sha256": capture["response_sha256"],
            "response_bytes": capture["response_bytes"],
            "http_status": capture["http_status"],
            "response_origin_verified": capture["response_origin_verified"],
        },
        "date_reports": reports,
        "official_aggregate_control_verified": True,
        "floorsheet_source_independence_verified": False,
        "per_security_completeness_verified": False,
        "session_completeness_verified": False,
        "historical_instrument_identity_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "official_daily_aggregate_control_only_not_per_security_coverage_or_source_lineage_proof",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-capture-dir", type=Path, required=True)
    parser.add_argument("--floorsheet-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = reconcile(args.official_capture_dir, args.floorsheet_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "official_aggregate_control_verified": report["official_aggregate_control_verified"],
        "dates": {
            day: {
                source: {
                    "all_aggregate_metrics_match": result["all_aggregate_metrics_match"],
                    "comparisons": result["comparisons"],
                }
                for source, result in item["sources"].items()
            }
            for day, item in report["date_reports"].items()
        },
        "coverage_admission_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
