"""Reconcile pinned floorsheet per-symbol quantity/turnover with dated EOD controls.

This is a third-party aggregate cross-check. It never upgrades either source to
official, independent, complete, or canonical and never admits coverage cells.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path


EOD_SOURCE_REPOSITORY = "srijankarki07/nepse-data"
EOD_SOURCE_REVISION = "688d59c03915dcee73ecad4230d2083a41c61764"
EOD_PINS = {
    "2026-11-19": {"size": 17912, "blob_sha1": "79fbb09935a1b704a3e247a06c1c2ed55220dcba"},
    "2026-11-20": {"size": 18191, "blob_sha1": "1ae56285d0f96d9c601e43a6a57562f00575cbf8"},
    "2026-11-24": {"size": 18042, "blob_sha1": "b9a33a5eb16d27c7ed6b1918062f336ee1fa1b6b"},
}


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def verify_pinned_eod(payload: bytes, day: str) -> dict:
    pin = EOD_PINS[day]
    if not payload:
        raise ValueError(f"{day}: EOD payload is empty")
    if len(payload) != pin["size"]:
        raise ValueError(f"{day}: EOD byte-size mismatch")
    observed = git_blob_sha1(payload)
    if observed != pin["blob_sha1"]:
        raise ValueError(f"{day}: EOD Git blob SHA-1 mismatch")
    return {
        "repository": EOD_SOURCE_REPOSITORY,
        "revision": EOD_SOURCE_REVISION,
        "path": f"data/daily/2026/{day}.csv",
        "byte_size": len(payload),
        "git_blob_sha1": observed,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _decimal(value: str, label: str, *, allow_zero: bool = False) -> Decimal:
    try:
        number = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if not number.is_finite() or (number < 0 if allow_zero else number <= 0):
        raise ValueError(f"nonpositive or nonfinite {label}: {value!r}")
    return number


def _read_floor(payload: bytes, day: str) -> dict[str, dict]:
    reader = csv.DictReader(payload.decode("utf-8-sig").splitlines())
    required = {"transaction", "symbol", "quantity", "amount", "date"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{day}: floorsheet missing columns {sorted(missing)}")
    result: dict[str, dict] = {}
    seen = set()
    for line, row in enumerate(reader, start=2):
        if row["date"].strip() != day:
            raise ValueError(f"{day}: floorsheet row {line} has date {row['date']!r}")
        contract = row["transaction"].strip()
        symbol = row["symbol"].strip().upper()
        if not contract or not symbol:
            raise ValueError(f"{day}: floorsheet row {line} missing contract/symbol")
        if contract in seen:
            raise ValueError(f"{day}: duplicate floorsheet contract {contract}")
        seen.add(contract)
        quantity = _decimal(row["quantity"], f"{day} {contract} quantity")
        amount = _decimal(row["amount"], f"{day} {contract} amount")
        item = result.setdefault(symbol, {
            "contract_count": 0, "volume": Decimal("0"), "turnover": Decimal("0")
        })
        item["contract_count"] += 1
        item["volume"] += quantity
        item["turnover"] += amount
    return result


def _read_eod(payload: bytes, day: str) -> dict[str, dict]:
    reader = csv.DictReader(payload.decode("utf-8-sig").splitlines())
    required = {"date", "symbol", "volume", "turnover"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{day}: EOD file missing columns {sorted(missing)}")
    result = {}
    for line, row in enumerate(reader, start=2):
        if row["date"].strip() != day:
            raise ValueError(f"{day}: EOD row {line} has date {row['date']!r}")
        symbol = row["symbol"].strip().upper()
        if not symbol or symbol in result:
            raise ValueError(f"{day}: blank or duplicate EOD symbol {symbol!r}")
        volume = _decimal(row["volume"], f"{day} {symbol} EOD volume", allow_zero=True)
        turnover = _decimal(row["turnover"], f"{day} {symbol} EOD turnover", allow_zero=True)
        if (volume == 0) != (turnover == 0):
            raise ValueError(f"{day}: {symbol} EOD zero volume/turnover inconsistency")
        result[symbol] = {"volume": volume, "turnover": turnover}
    return result


def compare_day(floorsheet_payload: bytes, eod_payload: bytes, day: str) -> dict:
    if day not in EOD_PINS:
        raise ValueError(f"unsupported pinned EOD date: {day}")
    eod_identity = verify_pinned_eod(eod_payload, day)
    floors = _read_floor(floorsheet_payload, day)
    eod = _read_eod(eod_payload, day)
    rows = []
    status_counts: Counter[str] = Counter()
    for symbol in sorted(set(floors) | set(eod)):
        floor = floors.get(symbol)
        control = eod.get(symbol)
        if floor is None:
            status = "EOD_ONLY"
        elif control is None:
            status = "FLOORSHEET_ONLY"
        elif floor["volume"] == control["volume"] and floor["turnover"] == control["turnover"]:
            status = "MATCH_EXACT"
        else:
            status = "MISMATCH"
        status_counts[status] += 1
        rows.append({
            "symbol": symbol,
            "status": status,
            "floorsheet_contract_count": floor["contract_count"] if floor else 0,
            "floorsheet_volume": str(floor["volume"]) if floor else "0",
            "floorsheet_turnover": str(floor["turnover"]) if floor else "0",
            "eod_volume": str(control["volume"]) if control else None,
            "eod_turnover": str(control["turnover"]) if control else None,
            "volume_difference": str(floor["volume"] - control["volume"]) if floor and control else None,
            "turnover_difference": str(floor["turnover"] - control["turnover"]) if floor and control else None,
        })
    floor_volume = sum((x["volume"] for x in floors.values()), Decimal("0"))
    floor_turnover = sum((x["turnover"] for x in floors.values()), Decimal("0"))
    eod_volume = sum((x["volume"] for x in eod.values()), Decimal("0"))
    eod_turnover = sum((x["turnover"] for x in eod.values()), Decimal("0"))
    return {
        "trade_date": day,
        "eod_identity": eod_identity,
        "floorsheet_symbol_count": len(floors),
        "eod_symbol_count": len(eod),
        "comparison_symbol_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "floorsheet_totals": {
            "volume": str(floor_volume), "turnover": str(floor_turnover),
            "contract_count": sum(x["contract_count"] for x in floors.values()),
        },
        "eod_totals": {"volume": str(eod_volume), "turnover": str(eod_turnover)},
        "total_differences": {
            "volume": str(floor_volume - eod_volume),
            "turnover": str(floor_turnover - eod_turnover),
        },
        "symbol_rows": rows,
    }


def audit_window(input_dir: str | Path, eod_dir: str | Path) -> dict:
    floor_root, eod_root = Path(input_dir), Path(eod_dir)
    reports = {}
    for day in EOD_PINS:
        floor_path = floor_root / f"socrateai-{day}.csv"
        eod_path = eod_root / f"eod-{day}.csv"
        reports[day] = compare_day(floor_path.read_bytes(), eod_path.read_bytes(), day)
    return {
        "schema_version": "1.0",
        "audit_status": "review_only_third_party_per_symbol_eod_crosscheck",
        "source_independence_verified": False,
        "official_nepse_controls": False,
        "daily_capture_completeness_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "date_reports": reports,
        "policy": "third_party_eod_aggregate_crosscheck_only_no_coverage_or_source_trust_inference",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--floorsheet-dir", type=Path, required=True)
    parser.add_argument("--eod-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit_window(args.floorsheet_dir, args.eod_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "dates": {
            day: {
                "status_counts": item["status_counts"],
                "total_differences": item["total_differences"],
                "floorsheet_symbol_count": item["floorsheet_symbol_count"],
                "eod_symbol_count": item["eod_symbol_count"],
            }
            for day, item in report["date_reports"].items()
        },
        "coverage_admission_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
