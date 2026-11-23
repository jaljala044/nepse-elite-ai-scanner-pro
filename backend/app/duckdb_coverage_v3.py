"""Read-only V3 OHLCV coverage audit against the source-separated DuckDB warehouse."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterator

import duckdb

from .data_coverage_v3 import audit_ohlcv

SOURCE_TABLE = "ankit.eod_price"
REQUIRED_COLUMNS = {
    "business_date", "symbol", "open_price", "high_price",
    "low_price", "close_price", "total_traded_quantity",
}


def audit_duckdb_ohlcv(
    database_path: str | Path,
    *,
    as_of: date | str | None = None,
    target_universe_size: int = 309,
    expected_symbols: list[str] | None = None,
    expected_sessions: list[date | str] | None = None,
) -> dict[str, Any]:
    """Audit eod_price without modifying the warehouse or inventing reference data."""
    db_path = Path(database_path).expanduser().resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB warehouse not found: {db_path}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        exists = con.execute(
            """SELECT COUNT(*) FROM information_schema.tables
               WHERE table_schema = 'ankit' AND table_name = 'eod_price'"""
        ).fetchone()[0]
        if not exists:
            raise ValueError(f"Required source table {SOURCE_TABLE} is not present")
        columns = {
            row[0] for row in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'ankit' AND table_name = 'eod_price'"
            ).fetchall()
        }
        missing = sorted(REQUIRED_COLUMNS - columns)
        if missing:
            raise ValueError(f"{SOURCE_TABLE} missing columns: {', '.join(missing)}")

        sql = (
            "SELECT symbol, business_date AS date, open_price AS open, "
            "high_price AS high, low_price AS low, close_price AS close, "
            "total_traded_quantity AS volume "
            f"FROM {SOURCE_TABLE} "
        )
        params: list[Any] = []
        if as_of is not None:
            cutoff = date.fromisoformat(str(as_of)[:10]) if not isinstance(as_of, date) else as_of
            sql += "WHERE business_date <= ? "
            params.append(cutoff)
        sql += "ORDER BY symbol, business_date"

        cursor = con.execute(sql, params)

        def observations() -> Iterator[dict[str, Any]]:
            while True:
                batch = cursor.fetchmany(5000)
                if not batch:
                    break
                for values in batch:
                    yield dict(zip(
                        ("symbol", "date", "open", "high", "low", "close", "volume"),
                        values,
                    ))

        report = audit_ohlcv(
            observations(),
            expected_symbols=expected_symbols,
            expected_sessions=expected_sessions,
            target_universe_size=target_universe_size,
            as_of=as_of,
        )
        report["warehouse"] = {
            "source_table": SOURCE_TABLE,
            "read_only": True,
            "database_file": db_path.name,
        }
        report["limitations"].extend([
            "The warehouse currently does not supply an authoritative 309-symbol master to this audit; target count is not proof of universe identity.",
            "The warehouse currently does not supply a verified NEPSE exchange-session calendar to this audit; missing sessions are not inferred.",
            "This audit checks stored OHLCV shape and coverage, not source authenticity or corporate-action adjustment.",
        ])
        return report
    finally:
        con.close()
