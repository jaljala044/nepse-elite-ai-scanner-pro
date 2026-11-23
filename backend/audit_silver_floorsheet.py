"""Audit normalized daily floorsheet partitions using independent row-level checks."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "silver" / "floorsheet"

def audit(root: Path) -> dict:
    files = sorted(root.glob("date=*/floorsheet.csv"))
    sessions = []
    global_keys = set()
    symbols = Counter()
    buyer_brokers = Counter()
    seller_brokers = Counter()
    total_qty = 0
    total_turnover = Decimal("0")
    duplicate_keys = []
    arithmetic_errors = []
    for file in files:
        session = file.parent.name.split("=", 1)[-1]
        rows = 0
        date_mismatches = 0
        session_qty = 0
        session_turnover = Decimal("0")
        with file.open("r", encoding="utf-8-sig", newline="") as handle:
            for line_no, row in enumerate(csv.DictReader(handle), start=2):
                rows += 1
                trade_date = row["trade_date"]
                contract = row["contract_no"]
                if trade_date != session:
                    date_mismatches += 1
                key = (trade_date, contract)
                if key in global_keys:
                    duplicate_keys.append({"date": trade_date, "contract_no": contract})
                global_keys.add(key)
                qty = int(row["quantity"])
                price = Decimal(row["price"])
                amount = Decimal(row["amount"])
                if abs(Decimal(qty) * price - amount) > Decimal("1.00"):
                    arithmetic_errors.append({"file": str(file), "line": line_no, "contract_no": contract})
                session_qty += qty
                session_turnover += amount
                symbols[row["symbol"]] += qty
                if row["buyer_broker_code"]:
                    buyer_brokers[row["buyer_broker_code"]] += amount
                if row["seller_broker_code"]:
                    seller_brokers[row["seller_broker_code"]] += amount
        total_qty += session_qty
        total_turnover += session_turnover
        sessions.append({
            "session": session, "rows": rows, "date_mismatches": date_mismatches,
            "shares": session_qty, "turnover": str(session_turnover),
        })
    return {
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_layer": "silver_normalized_floorsheet",
        "partition_files": len(files),
        "sessions": sessions,
        "total_rows": sum(s["rows"] for s in sessions),
        "total_shares": total_qty,
        "total_turnover": str(total_turnover),
        "duplicate_trade_keys": duplicate_keys,
        "date_mismatches": sum(s["date_mismatches"] for s in sessions),
        "arithmetic_errors": arithmetic_errors,
        "top_symbols_by_volume": symbols.most_common(20),
        "top_buyer_broker_codes_by_amount": buyer_brokers.most_common(20),
        "top_seller_broker_codes_by_amount": seller_brokers.most_common(20),
        "limitations": [
            "Broker codes are execution-channel identifiers, not beneficial-owner identities.",
            "A buy-side or sell-side broker amount is not proof of accumulation or distribution.",
            "This audit checks arithmetic, duplicate keys and date consistency, not exchange completeness."
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "reports" / "floorsheet-audit.json")
    args = parser.parse_args()
    result = audit(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "partition_files": result["partition_files"],
        "sessions": len(result["sessions"]),
        "total_rows": result["total_rows"],
        "duplicates": len(result["duplicate_trade_keys"]),
        "date_mismatches": result["date_mismatches"],
        "arithmetic_errors": len(result["arithmetic_errors"]),
        "output": str(args.output),
    }, indent=2))
    if result["partition_files"] == 0 or result["total_rows"] == 0:
        raise SystemExit("No normalized floorsheet data found")
    if result["duplicate_trade_keys"] or result["date_mismatches"] or result["arithmetic_errors"]:
        raise SystemExit("Floorsheet audit failed quality gates")

if __name__ == "__main__":
    main()
