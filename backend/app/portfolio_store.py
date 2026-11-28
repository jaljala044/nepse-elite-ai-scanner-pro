"""Owner-scoped portfolio persistence primitives.

This module is deliberately not wired to HTTP routes until a trusted authentication
principal is available. Callers MUST pass the authenticated subject as owner_id;
never accept owner_id from request payloads. Local DuckDB persistence is not a
claim of production multi-writer durability.
"""
from __future__ import annotations

import os
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

import duckdb


def database_path() -> Path:
    default = Path(__file__).resolve().parents[1] / "data" / "portfolio.duckdb"
    return Path(os.getenv("NEPSE_PORTFOLIO_DATABASE", str(default))).expanduser()


def _owner(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("authenticated owner_id is required")
    return value.strip()


def _decimal(value, field: str, *, positive: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError(f"{field} must be a finite positive decimal" if positive else f"{field} must be a finite decimal")
    return result


def _decimal_text(value: Decimal) -> str:
    """Return a stable decimal string without fixed-scale storage padding."""
    return format(value.normalize(), "f")


def _date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("trade_date must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("trade_date must be canonical YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError("trade_date must be canonical YYYY-MM-DD")
    return value


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            portfolio_id VARCHAR PRIMARY KEY,
            owner_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            holding_id VARCHAR PRIMARY KEY,
            portfolio_id VARCHAR NOT NULL,
            owner_id VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            horizon VARCHAR NOT NULL DEFAULT 'unknown',
            risk_preference VARCHAR NOT NULL DEFAULT 'balanced',
            created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
            UNIQUE(portfolio_id, symbol)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            transaction_id VARCHAR NOT NULL,
            holding_id VARCHAR NOT NULL,
            portfolio_id VARCHAR NOT NULL,
            owner_id VARCHAR NOT NULL,
            transaction_type VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            quantity BIGINT NOT NULL,
            unit_price DECIMAL(24, 8) NOT NULL,
            fees DECIMAL(24, 8) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY(owner_id, transaction_id)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_portfolios_owner ON portfolios(owner_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_holdings_owner_portfolio ON portfolio_holdings(owner_id, portfolio_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_transactions_owner_holding ON portfolio_transactions(owner_id, holding_id)")
    return con


def create_portfolio(owner_id: str, name: str) -> dict:
    owner = _owner(owner_id)
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("name must contain 1 to 100 characters")
    item_id = str(uuid4())
    con = connect()
    try:
        con.execute("INSERT INTO portfolios(portfolio_id, owner_id, name) VALUES (?, ?, ?)",
                    [item_id, owner, name.strip()])
        row = con.execute("SELECT portfolio_id, name, created_at FROM portfolios WHERE portfolio_id=? AND owner_id=?",
                          [item_id, owner]).fetchone()
        return {"portfolio_id": row[0], "name": row[1], "created_at": row[2].isoformat()}
    finally:
        con.close()


def list_portfolios(owner_id: str) -> list[dict]:
    owner = _owner(owner_id)
    con = connect()
    try:
        rows = con.execute("""SELECT portfolio_id, name, created_at, updated_at
                              FROM portfolios WHERE owner_id=? ORDER BY created_at, portfolio_id""", [owner]).fetchall()
        return [{"portfolio_id": r[0], "name": r[1], "created_at": r[2].isoformat(),
                 "updated_at": r[3].isoformat()} for r in rows]
    finally:
        con.close()


def _owned_portfolio(con, owner: str, portfolio_id: str) -> bool:
    return con.execute("SELECT 1 FROM portfolios WHERE portfolio_id=? AND owner_id=?",
                       [portfolio_id, owner]).fetchone() is not None


def rename_portfolio(owner_id: str, portfolio_id: str, name: str) -> bool:
    owner = _owner(owner_id)
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        raise ValueError("name must contain 1 to 100 characters")
    con = connect()
    try:
        result = con.execute("""UPDATE portfolios SET name=?, updated_at=current_timestamp
                                WHERE portfolio_id=? AND owner_id=? RETURNING portfolio_id""",
                             [name.strip(), portfolio_id, owner]).fetchone()
        return result is not None
    finally:
        con.close()


def delete_portfolio(owner_id: str, portfolio_id: str) -> bool:
    owner = _owner(owner_id)
    con = connect()
    try:
        con.execute("BEGIN TRANSACTION")
        if not _owned_portfolio(con, owner, portfolio_id):
            con.execute("ROLLBACK")
            return False
        con.execute("DELETE FROM portfolio_transactions WHERE owner_id=? AND portfolio_id=?", [owner, portfolio_id])
        con.execute("DELETE FROM portfolio_holdings WHERE owner_id=? AND portfolio_id=?", [owner, portfolio_id])
        con.execute("DELETE FROM portfolios WHERE owner_id=? AND portfolio_id=?", [owner, portfolio_id])
        con.execute("COMMIT")
        return True
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def create_holding(owner_id: str, portfolio_id: str, symbol: str, *,
                   horizon: str = "unknown", risk_preference: str = "balanced") -> dict | None:
    owner = _owner(owner_id)
    if not isinstance(symbol, str) or not symbol.strip() or len(symbol.strip()) > 20:
        raise ValueError("symbol must contain 1 to 20 characters")
    symbol = symbol.strip().upper()
    if horizon not in {"unknown", "short_term", "one_to_three_months", "three_to_six_months", "long_term"}:
        raise ValueError("unsupported investment horizon")
    if risk_preference not in {"capital_protection", "balanced", "aggressive_growth"}:
        raise ValueError("unsupported risk preference")
    con = connect()
    try:
        if not _owned_portfolio(con, owner, portfolio_id):
            return None
        holding_id = str(uuid4())
        con.execute("""INSERT INTO portfolio_holdings
                       (holding_id, portfolio_id, owner_id, symbol, horizon, risk_preference)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    [holding_id, portfolio_id, owner, symbol, horizon, risk_preference])
        return {"holding_id": holding_id, "portfolio_id": portfolio_id, "symbol": symbol,
                "horizon": horizon, "risk_preference": risk_preference}
    finally:
        con.close()


def list_holdings(owner_id: str, portfolio_id: str) -> list[dict] | None:
    owner = _owner(owner_id)
    con = connect()
    try:
        if not _owned_portfolio(con, owner, portfolio_id):
            return None
        rows = con.execute("""SELECT holding_id, symbol, horizon, risk_preference
                              FROM portfolio_holdings WHERE owner_id=? AND portfolio_id=?
                              ORDER BY symbol""", [owner, portfolio_id]).fetchall()
        return [{"holding_id": r[0], "symbol": r[1], "horizon": r[2], "risk_preference": r[3]} for r in rows]
    finally:
        con.close()


def add_transaction(owner_id: str, portfolio_id: str, holding_id: str, *,
                    transaction_id: str, transaction_type: str, trade_date: str,
                    quantity: int, unit_price, fees=0) -> dict | None:
    owner = _owner(owner_id)
    if not isinstance(transaction_id, str) or not transaction_id.strip():
        raise ValueError("transaction_id is required")
    if transaction_type not in {"buy", "sell"}:
        raise ValueError("transaction_type must be buy or sell")
    day = _date(trade_date)
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive whole share count")
    price = _decimal(unit_price, "unit_price", positive=True)
    fee = _decimal(fees, "fees")
    if fee < 0:
        raise ValueError("fees must be non-negative")
    con = connect()
    try:
        owned = con.execute("""SELECT 1 FROM portfolio_holdings h
                               JOIN portfolios p ON p.portfolio_id=h.portfolio_id AND p.owner_id=h.owner_id
                               WHERE h.holding_id=? AND h.portfolio_id=? AND h.owner_id=?""",
                            [holding_id, portfolio_id, owner]).fetchone()
        if owned is None:
            return None
        latest = con.execute("""SELECT max(trade_date) FROM portfolio_transactions
                                WHERE holding_id=? AND owner_id=?""", [holding_id, owner]).fetchone()[0]
        if latest is not None and date.fromisoformat(day) < latest:
            raise ValueError("transactions must be chronological")
        con.execute("""INSERT INTO portfolio_transactions
                       (transaction_id, holding_id, portfolio_id, owner_id, transaction_type,
                        trade_date, quantity, unit_price, fees)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [transaction_id.strip(), holding_id, portfolio_id, owner, transaction_type,
                     day, quantity, price, fee])
        return {"transaction_id": transaction_id.strip(), "holding_id": holding_id,
                "transaction_type": transaction_type, "trade_date": day,
                "quantity": quantity, "unit_price": str(price), "fees": str(fee)}
    finally:
        con.close()


def list_transactions(owner_id: str, portfolio_id: str, holding_id: str) -> list[dict] | None:
    owner = _owner(owner_id)
    con = connect()
    try:
        owned = con.execute("""SELECT 1 FROM portfolio_holdings
                               WHERE holding_id=? AND portfolio_id=? AND owner_id=?""",
                            [holding_id, portfolio_id, owner]).fetchone()
        if owned is None:
            return None
        rows = con.execute("""SELECT transaction_id, transaction_type, trade_date, quantity, unit_price, fees
                              FROM portfolio_transactions WHERE owner_id=? AND portfolio_id=? AND holding_id=?
                              ORDER BY trade_date, created_at, transaction_id""",
                           [owner, portfolio_id, holding_id]).fetchall()
        return [{"id": r[0], "type": r[1], "trade_date": r[2].isoformat(),
                 "quantity": r[3], "unit_price": _decimal_text(r[4]), "fees": _decimal_text(r[5])} for r in rows]
    finally:
        con.close()
