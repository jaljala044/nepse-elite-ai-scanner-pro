"""Small persistent DuckDB store for validated API OHLCV imports.

The research warehouse remains source-separated. This database only backs the
interactive API's validated CSV upload/history endpoints; it is not canonical
market data and does not certify source rights or trading-session completeness.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import duckdb
from app.quarantine_guard import is_quarantined, runtime_quarantine_keys, ledger_blocked

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "nepse-api.duckdb"


def database_path() -> Path:
    return Path(os.getenv("NEPSE_API_DATABASE", str(DEFAULT_DB))).expanduser()


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_batches (
            batch_id VARCHAR PRIMARY KEY,
            source_label VARCHAR NOT NULL,
            captured_at TIMESTAMPTZ NOT NULL,
            rows_accepted BIGINT NOT NULL,
            symbols VARCHAR NOT NULL,
            latest_session DATE
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            symbol VARCHAR NOT NULL,
            trading_date DATE NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume BIGINT NOT NULL,
            first_batch_id VARCHAR NOT NULL,
            PRIMARY KEY (symbol, trading_date)
        )
    """)
    return con


def load_state() -> tuple[dict[str, list[dict]], list[dict]]:
    keys = runtime_quarantine_keys()
    con = connect()
    try:
        bars = con.execute("""
            SELECT symbol, trading_date, open, high, low, close, volume
            FROM daily_ohlcv ORDER BY symbol, trading_date
        """).fetchall()
        imports = con.execute("""
            SELECT source_label, rows_accepted, symbols, latest_session, captured_at
            FROM ingestion_batches ORDER BY captured_at
        """).fetchall()
    finally:
        con.close()
    data: dict[str, list[dict]] = {}
    # Withhold the complete affected symbol history; dropping a single bar
    # would silently bridge an unresolved session in downstream indicators.
    blocked_symbols = {symbol for symbol, d, *_ in bars
                       if ledger_blocked({"date": d}, keys, symbol)}
    for symbol, d, o, h, l, c, v in bars:
        if symbol in blocked_symbols:
            continue
        data.setdefault(symbol, []).append({
            "date": d, "open": o, "high": h, "low": l, "close": c, "volume": v
        })
    history = [{
        "source": source, "rows_accepted": count,
        "symbols": symbols.split(",") if symbols else [],
        "latest_session": str(latest or ""),
        "captured_at": captured.isoformat()
    } for source, count, symbols, latest, captured in imports]
    return data, history


def persist_import(source: str, parsed: dict[str, list[dict]]) -> dict:
    keys = runtime_quarantine_keys()
    if any(ledger_blocked(row, keys, symbol) for symbol, values in parsed.items() for row in values):
        raise ValueError("Quarantined OHLCV input")
    rows = [(symbol, row["date"], row["open"], row["high"], row["low"],
             row["close"], row["volume"])
            for symbol, values in parsed.items() for row in values]
    batch_id = str(uuid4())
    captured = datetime.now(timezone.utc)
    symbols = sorted(parsed)
    latest = max((row["date"] for _, values in parsed.items() for row in values), default=None)
    con = connect()
    try:
        con.execute("BEGIN TRANSACTION")
        for symbol, d, o, h, l, c, volume in rows:
            existing = con.execute("""
                SELECT open, high, low, close, volume FROM daily_ohlcv
                WHERE symbol = ? AND trading_date = ?
            """, [symbol, d]).fetchone()
            values = (o, h, l, c, volume)
            if existing is not None and tuple(existing) != values:
                raise ValueError(f"Conflicting persisted row for {symbol} on {d}")
        con.execute("""
            INSERT INTO ingestion_batches
            VALUES (?, ?, ?, ?, ?, ?)
        """, [batch_id, source, captured, len(rows), ",".join(symbols), latest])
        for symbol, d, o, h, l, c, volume in rows:
            con.execute("""
                INSERT INTO daily_ohlcv
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (symbol, trading_date) DO NOTHING
            """, [symbol, d, o, h, l, c, volume, batch_id])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return {"batch_id": batch_id, "rows_accepted": len(rows),
            "symbols": symbols, "latest_session": str(latest or "")}
