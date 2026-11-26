"""Compare official NEPSE per-security daily statistics with pinned floorsheets.

Official missing symbol rows remain UNKNOWN; they are never interpreted as zero
trading. Security master joins are current-snapshot hints only.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATES = ("2026-11-19", "2026-11-20", "2026-11-24")


def _positive(value: object, label: str) -> Decimal:
    try:
        number = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"nonpositive/nonfinite {label}: {value!r}")
    return number


def load_official_rows(path: Path, day: str) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("content") or payload.get("data") or payload.get("securityDailyTradeStatVos")
        if isinstance(rows, dict):
            rows = rows.get("content")
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError(f"{day}: official payload has no row list")
    result = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{day}: official row {index} is not an object")
        symbol = str(row.get("symbol", "")).strip().upper()
        row_date = str(row.get("businessDate", row.get("business_date", "")))[:10]
        if not symbol or row_date != day:
            raise ValueError(f"{day}: official row {index} has blank symbol or mismatched date")
        if symbol in result:
            raise ValueError(f"{day}: duplicate official symbol {symbol}")
        result[symbol] = {
            "security_id": str(row.get("securityId", "")).strip(),
            "security_name": row.get("securityName"),
            "trades": _positive(row.get("totalTrades"), f"{day} {symbol} totalTrades"),
            "volume": _positive(row.get("totalTradedQuantity"), f"{day} {symbol} totalTradedQuantity"),
            "turnover": _positive(row.get("totalTradedValue"), f"{day} {symbol} totalTradedValue"),
            "open": row.get("openPrice"),
            "high": row.get("highPrice"),
            "low": row.get("lowPrice"),
            "close": row.get("closePrice"),
            "raw": row,
        }
    return result


def load_floorsheet(path: Path, day: str, source: str) -> dict[str, dict]:
    if source == "samir":
        fields = {"contract": "contract_no", "symbol": "stock_symbol", "date": "date",
                  "quantity": "quantity", "amount": "amount"}
    else:
        fields = {"contract": "transaction", "symbol": "symbol", "date": "date",
                  "quantity": "quantity", "amount": "amount"}
    result = {}
    contracts = set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(fields.values()) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{source} {day}: missing columns {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            if row[fields["date"]].strip()[:10] != day:
                raise ValueError(f"{source} {day}: row {line} has wrong date")
            contract = row[fields["contract"]].strip()
            symbol = row[fields["symbol"]].strip().upper()
            if not contract or not symbol or contract in contracts:
                raise ValueError(f"{source} {day}: blank or duplicate contract at row {line}")
            contracts.add(contract)
            item = result.setdefault(symbol, {"trades": Decimal("0"), "volume": Decimal("0"), "turnover": Decimal("0")})
            item["trades"] += 1
            item["volume"] += _positive(row[fields["quantity"]], f"{source} {day} {symbol} quantity")
            item["turnover"] += _positive(row[fields["amount"]], f"{source} {day} {symbol} amount")
    return result


def load_snapshot(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for row in rows:
        symbol = row.get("symbol", "").strip().upper()
        if not symbol or symbol in result:
            raise ValueError("security snapshot has blank or duplicate symbols")
        result[symbol] = row
    return result


def reconcile(official_dir: Path, floorsheet_dir: Path, snapshot_path: Path) -> dict:
    snapshot = load_snapshot(snapshot_path)
    reports = {}
    for day in DATES:
        official = load_official_rows(official_dir / f"{day}-parsed-response.json", day)
        source_reports = {}
        for source in ("samir", "socrateai"):
            floors = load_floorsheet(floorsheet_dir / f"{source}-{day}.csv", day, source)
            rows = []
            counts = Counter()
            for symbol in sorted(set(official) | set(floors)):
                off = official.get(symbol)
                floor = floors.get(symbol)
                if off is None:
                    status = "FLOORSHEET_ONLY_OFFICIAL_ROW_UNKNOWN"
                elif floor is None:
                    status = "OFFICIAL_ONLY_FLOORSHEET_ROW_MISSING"
                else:
                    matches = all(off[key] == floor[key] for key in ("trades", "volume", "turnover"))
                    status = "MATCH_EXACT" if matches else "MISMATCH"
                counts[status] += 1
                snap = snapshot.get(symbol)
                snapshot_id_match = bool(off and snap and str(snap.get("security_id", "")).strip() == off["security_id"])
                rows.append({
                    "symbol": symbol,
                    "status": status,
                    "official": {key: str(off[key]) for key in ("trades", "volume", "turnover")} if off else None,
                    "floorsheet": {key: str(floor[key]) for key in ("trades", "volume", "turnover")} if floor else None,
                    "differences": {
                        key: str(floor[key] - off[key]) for key in ("trades", "volume", "turnover")
                    } if floor and off else None,
                    "official_security_id": off["security_id"] if off else None,
                    "snapshot_security_id": snap.get("security_id") if snap else None,
                    "snapshot_id_match": snapshot_id_match,
                    "snapshot_security_name": snap.get("security_name") if snap else None,
                    "historical_security_identity_verified": False,
                })
            source_reports[source] = {
                "official_symbol_count": len(official),
                "floorsheet_symbol_count": len(floors),
                "status_counts": dict(sorted(counts.items())),
                "exact_match_count": counts["MATCH_EXACT"],
                "rows": rows,
            }
        reports[day] = source_reports
    return {
        "schema_version": "1.0",
        "audit_status": "review_only_official_per_security_vs_floorsheet_reconciliation",
        "dates": reports,
        "security_snapshot_date": "2026-11-25",
        "security_snapshot_is_current_hint_only": True,
        "historical_security_identity_verified": False,
        "official_session_completeness_verified": False,
        "floorsheet_source_independence_verified": False,
        "per_security_completeness_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "per_security_daily_stats_crosscheck_only_missing_rows_unknown_no_zero_trade_or_identity_inference",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-dir", type=Path, required=True)
    parser.add_argument("--floorsheet-dir", type=Path, required=True)
    parser.add_argument("--security-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = reconcile(args.official_dir, args.floorsheet_dir, args.security_snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        day: {
            source: {
                "status_counts": data["status_counts"],
                "exact_match_count": data["exact_match_count"],
                "official_symbol_count": data["official_symbol_count"],
                "floorsheet_symbol_count": data["floorsheet_symbol_count"],
            } for source, data in sources.items()
        } for day, sources in report["dates"].items()
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
