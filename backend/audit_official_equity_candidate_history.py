"""Compare captured official per-symbol history with equity-universe floorsheets.

A zero official activity row is reported separately and never promoted to NO_TRADE.
Missing source rows remain explicit review states.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATES = ("2026-11-19", "2026-11-20", "2026-11-24")


def _nonnegative(value: object, label: str) -> Decimal:
    try:
        number = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"negative or nonfinite {label}: {value!r}")
    return number


def load_floorsheet(path: Path, day: str, source: str) -> dict[str, dict]:
    fields = ({"contract": "contract_no", "symbol": "stock_symbol", "date": "date",
               "quantity": "quantity", "amount": "amount"}
              if source == "samir" else
              {"contract": "transaction", "symbol": "symbol", "date": "date",
               "quantity": "quantity", "amount": "amount"})
    result = {}
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(fields.values()) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{source} {day}: missing columns {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            if row[fields["date"]].strip()[:10] != day:
                raise ValueError(f"{source} {day}: wrong date at row {line}")
            contract = row[fields["contract"]].strip()
            symbol = row[fields["symbol"]].strip().upper()
            if not contract or not symbol or contract in seen:
                raise ValueError(f"{source} {day}: blank or duplicate contract at row {line}")
            seen.add(contract)
            item = result.setdefault(symbol, {"trades": Decimal("0"), "volume": Decimal("0"), "turnover": Decimal("0")})
            item["trades"] += 1
            item["volume"] += _nonnegative(row[fields["quantity"]], f"{source} {day} quantity")
            item["turnover"] += _nonnegative(row[fields["amount"]], f"{source} {day} amount")
    return result


def reconcile(capture_report_path: Path, floorsheet_dir: Path, expected_equity_count: int = 281) -> dict:
    capture = json.loads(capture_report_path.read_text(encoding="utf-8"))
    if capture.get("source_id") != "NEPSE_OFFICIAL_PER_SECURITY_PRICE_VOLUME":
        raise ValueError("unexpected per-security capture source ID")
    if capture.get("historical_security_identity_verified") is not False:
        raise ValueError("capture report must retain historical identity as unverified")
    symbols = capture.get("symbols")
    if not isinstance(symbols, list) or len(symbols) != expected_equity_count:
        raise ValueError("expected exactly 281 captured current equity candidates")
    by_symbol = {}
    for item in symbols:
        symbol = str(item.get("symbol", "")).strip().upper()
        if not symbol or symbol in by_symbol:
            raise ValueError("blank or duplicate symbol in per-security capture report")
        if item.get("status") != "ROWS_RETURNED_REVIEW_ONLY" or item.get("current_id_match") is not True:
            raise ValueError(f"{symbol}: capture status/current ID match not verified")
        rows = item.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"{symbol}: history rows missing")
        by_date = {}
        for row in rows:
            day = row.get("business_date")
            if day in by_date:
                raise ValueError(f"{symbol}: duplicate per-security history date {day}")
            by_date[day] = row
        by_symbol[symbol] = {"security_id": item.get("current_security_list_id"), "rows": by_date}

    reports = {}
    for day in DATES:
        source_reports = {}
        for source in ("samir", "socrateai"):
            floor = load_floorsheet(floorsheet_dir / f"{source}-{day}.csv", day, source)
            counts = Counter()
            rows = []
            for symbol in sorted(by_symbol):
                official_row = by_symbol[symbol]["rows"].get(day)
                if official_row is None:
                    status = "OFFICIAL_HISTORY_ROW_UNKNOWN"
                    official = None
                else:
                    official = {
                        "trades": _nonnegative(official_row.get("trades"), f"{day} {symbol} trades"),
                        "volume": _nonnegative(official_row.get("volume"), f"{day} {symbol} volume"),
                        "turnover": _nonnegative(official_row.get("turnover"), f"{day} {symbol} turnover"),
                    }
                floor_row = floor.get(symbol)
                if official is None:
                    pass
                elif floor_row is None and all(value == 0 for value in official.values()):
                    status = "OFFICIAL_ZERO_ACTIVITY_NO_FLOORSHEET_ROW"
                elif floor_row is None:
                    status = "OFFICIAL_POSITIVE_ACTIVITY_NO_FLOORSHEET_ROW"
                elif all(value == 0 for value in official.values()):
                    status = "MISMATCH_OFFICIAL_ZERO_FLOORSHEET_POSITIVE"
                elif all(official[key] == floor_row[key] for key in ("trades", "volume", "turnover")):
                    status = "MATCH_EXACT"
                else:
                    status = "MISMATCH"
                counts[status] += 1
                rows.append({
                    "symbol": symbol,
                    "security_id_current_snapshot": by_symbol[symbol]["security_id"],
                    "historical_security_identity_verified": False,
                    "status": status,
                    "official": {key: str(value) for key, value in official.items()} if official is not None else None,
                    "floorsheet": {key: str(value) for key, value in floor_row.items()} if floor_row else None,
                })
            source_reports[source] = {
                "equity_candidate_count": len(by_symbol),
                "floorsheet_symbol_count": len(floor),
                "status_counts": dict(sorted(counts.items())),
                "rows": rows,
            }
        reports[day] = source_reports
    return {
        "schema_version": "1.0",
        "audit_status": "review_only_official_equity_candidate_history_reconciliation",
        "per_security_capture_source": capture["source_id"],
        "requested_history_window": [capture["requested_start_date"], capture["requested_end_date"]],
        "equity_candidate_count": len(by_symbol),
        "dates": reports,
        "current_security_id_matches": len(by_symbol),
        "historical_security_identity_verified": False,
        "official_session_completeness_verified": False,
        "floorsheet_completeness_verified": False,
        "source_independence_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "official_zero_activity_is_not_no_trade_missing_rows_unknown_historical_identity_unverified",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-security-report", type=Path, required=True)
    parser.add_argument("--floorsheet-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = reconcile(args.per_security_report, args.floorsheet_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        day: {
            source: {
                "status_counts": value["status_counts"],
                "equity_candidate_count": value["equity_candidate_count"],
            } for source, value in sources.items()
        } for day, sources in report["dates"].items()
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
