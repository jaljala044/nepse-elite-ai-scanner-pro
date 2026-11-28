import argparse
import csv
import json
from pathlib import Path

from app.source_collector import collect


def main():
    parser = argparse.ArgumentParser(description="Collect five-year NEPSE historical evidence archives")
    parser.add_argument("--source", action="append", dest="sources",
                        help="Source name; repeat to select multiple. Defaults to all.")
    parser.add_argument("--as-of-date", help="Explicit ISO date ending the five-year collection window")
    parser.add_argument("--equity-universe", type=Path,
                        help="JSON array or CSV manifest containing symbol and security_id; current active-equity CSVs should include instrument_type and status")
    parser.add_argument("--session-calendar", type=Path,
                        help="JSON array of exchange-verified ISO trading dates for daily floorsheet capture")
    args = parser.parse_args()
    equities = None
    if args.equity_universe:
        if args.equity_universe.suffix.lower() == ".csv":
            with args.equity_universe.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or not {"symbol", "security_id"} <= set(reader.fieldnames):
                    parser.error("equity CSV must contain symbol and security_id columns")
                rows = list(reader)
            if {"instrument_type", "status"} <= set(reader.fieldnames):
                rows = [row for row in rows if row["instrument_type"].strip().casefold() == "equity"
                        and row["status"].strip().casefold() == "active"]
            equities = [{"symbol": row["symbol"], "security_id": row["security_id"]}
                        for row in rows]
        else:
            equities = json.loads(args.equity_universe.read_text(encoding="utf-8"))
    session_dates = None
    if args.session_calendar:
        calendar_payload = json.loads(args.session_calendar.read_text(encoding="utf-8"))
        session_dates = calendar_payload.get("session_dates") if isinstance(calendar_payload, dict) else calendar_payload
    result = collect(args.sources, as_of_date=args.as_of_date, equities=equities,
                     session_dates=session_dates)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
