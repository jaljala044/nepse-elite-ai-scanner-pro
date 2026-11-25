"""Warehouse-backed daily OHLCV coverage audit for the V3 universe.

The audit reads directly from DuckDB. It never fabricates the 309-symbol
master or trading calendar: both must be supplied as authoritative warehouse
tables by the operator.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import duckdb


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _qualified(name: str) -> str:
    parts = name.split(".")
    if not parts or any(not _IDENTIFIER.fullmatch(part) for part in parts):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return ".".join(f'"{part}"' for part in parts)


def _table_exists(con: duckdb.DuckDBPyConnection, table: str) -> bool:
    parts = table.split(".")
    if len(parts) == 1:
        query = "SELECT 1 FROM information_schema.tables WHERE table_name = ? LIMIT 1"
        return con.execute(query, [parts[0]]).fetchone() is not None
    if len(parts) == 2:
        query = """SELECT 1 FROM information_schema.tables
                   WHERE table_schema = ? AND table_name = ? LIMIT 1"""
        return con.execute(query, parts).fetchone() is not None
    raise ValueError("Table name must be table or schema.table")


def audit_coverage(
    database: str,
    ohlcv_table: str,
    symbol_master_table: str,
    calendar_table: str,
    *,
    symbol_col: str = "symbol",
    date_col: str = "date",
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    master_symbol_col: str = "symbol",
    calendar_date_col: str = "session_date",
) -> dict[str, Any]:
    """Audit every master symbol against the verified session calendar."""
    # Validate every identifier before opening the database connection.
    ohlcv = _qualified(ohlcv_table)
    master = _qualified(symbol_master_table)
    calendar = _qualified(calendar_table)
    sc, dc = map(_qualified, (symbol_col, date_col))
    oc, hc, lc, cc, vc = map(_qualified, (open_col, high_col, low_col, close_col, volume_col))
    mc, kc = map(_qualified, (master_symbol_col, calendar_date_col))
    con = duckdb.connect(database, read_only=True)
    try:
        for table in (ohlcv_table, symbol_master_table, calendar_table):
            if not _table_exists(con, table):
                raise ValueError(f"Required warehouse table not found: {table}")

        symbols = [r[0] for r in con.execute(
            f"SELECT DISTINCT upper(trim(CAST({mc} AS VARCHAR))) FROM {master} "
            f"WHERE {mc} IS NOT NULL AND trim(CAST({mc} AS VARCHAR)) <> '' ORDER BY 1"
        ).fetchall()]
        sessions = [r[0] for r in con.execute(
            f"SELECT DISTINCT CAST({kc} AS DATE) FROM {calendar} "
            f"WHERE {kc} IS NOT NULL ORDER BY 1"
        ).fetchall()]
        if not symbols:
            raise ValueError("Authoritative symbol master is empty")
        if not sessions:
            raise ValueError("Verified session calendar is empty")

        bounds = con.execute(
            f"SELECT min(CAST({dc} AS DATE)), max(CAST({dc} AS DATE)) FROM {ohlcv}"
        ).fetchone()
        if not bounds or bounds[0] is None:
            raise ValueError("OHLCV warehouse table is empty")
        first_date, last_date = bounds
        expected_sessions = [d for d in sessions if first_date <= d <= last_date]
        if not expected_sessions:
            raise ValueError("No verified calendar sessions overlap the OHLCV date range")

        rows = con.execute(f"""
            SELECT upper(trim(CAST({sc} AS VARCHAR))) AS symbol,
                   CAST({dc} AS DATE) AS session_date,
                   count(*) AS row_count,
                   bool_and(
                     {oc} IS NOT NULL AND {hc} IS NOT NULL AND {lc} IS NOT NULL
                     AND {cc} IS NOT NULL AND {vc} IS NOT NULL
                     AND try_cast({oc} AS DOUBLE) > 0
                     AND try_cast({hc} AS DOUBLE) > 0
                     AND try_cast({lc} AS DOUBLE) > 0
                     AND try_cast({cc} AS DOUBLE) > 0
                     AND try_cast({vc} AS DOUBLE) >= 0
                     AND try_cast({hc} AS DOUBLE) >= greatest(
                       try_cast({oc} AS DOUBLE), try_cast({cc} AS DOUBLE),
                       try_cast({lc} AS DOUBLE))
                     AND try_cast({lc} AS DOUBLE) <= least(
                       try_cast({oc} AS DOUBLE), try_cast({cc} AS DOUBLE),
                       try_cast({hc} AS DOUBLE))
                   ) AS valid_ohlcv
            FROM {ohlcv}
            WHERE {sc} IS NOT NULL AND {dc} IS NOT NULL
            GROUP BY 1, 2
        """).fetchall()

        observed: dict[str, dict[Any, tuple[int, bool]]] = {}
        for symbol, session, count, valid in rows:
            observed.setdefault(symbol, {})[session] = (int(count), bool(valid))

        report = []
        for symbol in symbols:
            by_date = observed.get(symbol, {})
            present = [d for d in expected_sessions if d in by_date]
            missing = [d.isoformat() for d in expected_sessions if d not in by_date]
            duplicate = [d.isoformat() for d, (count, _) in by_date.items() if count > 1]
            invalid = [d.isoformat() for d, (_, valid) in by_date.items() if not valid]
            coverage = len(present) / len(expected_sessions) * 100.0
            report.append({
                "symbol": symbol,
                "expected_sessions": len(expected_sessions),
                "observed_sessions": len(present),
                "coverage_pct": round(coverage, 2),
                "missing_sessions": missing,
                "duplicate_sessions": sorted(duplicate),
                "invalid_ohlcv_sessions": sorted(invalid),
                "status": "pass" if not missing and not duplicate and not invalid else "review",
            })

        total_expected = len(symbols) * len(expected_sessions)
        total_observed = sum(item["observed_sessions"] for item in report)
        return {
            "audit": "nepse_ohlcv_coverage_v1",
            "database": str(Path(database)),
            "tables": {
                "ohlcv": ohlcv_table,
                "symbol_master": symbol_master_table,
                "session_calendar": calendar_table,
            },
            "date_range": {"from": first_date.isoformat(), "to": last_date.isoformat()},
            "universe_symbols": len(symbols),
            "calendar_sessions": len(expected_sessions),
            "expected_symbol_sessions": total_expected,
            "observed_symbol_sessions": total_observed,
            "overall_coverage_pct": round(total_observed / total_expected * 100.0, 2),
            "symbols_passed": sum(x["status"] == "pass" for x in report),
            "symbols_requiring_review": sum(x["status"] != "pass" for x in report),
            "results": report,
            "limitations": [
                "Coverage is measured only against the supplied authoritative symbol master and verified session calendar.",
                "The audit does not certify corporate-action adjustment, source authenticity, or economic correctness.",
                "Symbols absent from the master are excluded; master/calendar provenance must be independently verified.",
            ],
        }
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Existing DuckDB file")
    parser.add_argument("--ohlcv-table", required=True, help="OHLCV table, optionally schema.table")
    parser.add_argument("--symbol-master-table", required=True)
    parser.add_argument("--calendar-table", required=True)
    parser.add_argument("--output", default="artifacts/v3_coverage_report.json")
    parser.add_argument("--symbol-col", default="symbol")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--open-col", default="open")
    parser.add_argument("--high-col", default="high")
    parser.add_argument("--low-col", default="low")
    parser.add_argument("--close-col", default="close")
    parser.add_argument("--volume-col", default="volume")
    parser.add_argument("--master-symbol-col", default="symbol")
    parser.add_argument("--calendar-date-col", default="session_date")
    args = parser.parse_args()
    report = audit_coverage(
        args.database, args.ohlcv_table, args.symbol_master_table, args.calendar_table,
        symbol_col=args.symbol_col, date_col=args.date_col,
        open_col=args.open_col, high_col=args.high_col, low_col=args.low_col,
        close_col=args.close_col, volume_col=args.volume_col,
        master_symbol_col=args.master_symbol_col, calendar_date_col=args.calendar_date_col,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
