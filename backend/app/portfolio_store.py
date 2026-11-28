"""Private, owner-scoped portfolio persistence.

This module deliberately has no HTTP/authentication layer. Callers must pass the
authenticated principal's stable owner_id (never a client-supplied owner field).
Every read/write is scoped by owner_id and related resource IDs. Market marks,
corporate actions, taxes and recommendations are intentionally out of scope.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import os
from uuid import uuid4

import duckdb

DEFAULT_PORTFOLIO_DB = Path(__file__).resolve().parents[1] / "data" / "nepse-portfolio.duckdb"
HORIZONS = {"short_term", "one_to_three_months", "three_to_six_months", "long_term"}
RISK_PREFERENCES = {"capital_protection", "balanced", "aggressive_growth"}
TRANSACTION_TYPES = {"buy", "sell"}


def _owner(owner_id: str) -> str:
    if not isinstance(owner_id, str) or not owner_id.strip() or len(owner_id) > 200:
        raise ValueError("authenticated owner_id is required")
    return owner_id.strip()


def _name(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
        raise ValueError("name must contain 1 to 100 characters")
    return value.strip()


def _symbol(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("symbol must be text")
    result = value.strip().upper()
    if not result or len(result) > 20 or not result.replace("-", "").isalnum():
        raise ValueError("symbol must be a valid 1 to 20 character ticker")
    return result


def _date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("trade_date must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("trade_date must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError("trade_date must be canonical YYYY-MM-DD")
    return value


def _decimal(value, field: str, *, positive: bool = False) -> str:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal") from exc
    if not parsed.is_finite() or (positive and parsed <= 0) or (not positive and parsed < 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{field} must be a finite {qualifier} decimal")
    return format(parsed, "f")


def database_path() -> Path:
    return Path(os.getenv("NEPSE_PORTFOLIO_DATABASE", str(DEFAULT_PORTFOLIO_DB))).expanduser()


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            portfolio_id VARCHAR PRIMARY KEY,
            owner_id VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_holdings (
            holding_id VARCHAR PRIMARY KEY,
            portfolio_id VARCHAR NOT NULL,
            owner_id VARCHAR NOT NULL,
            symbol VARCHAR NOT NULL,
            horizon VARCHAR NOT NULL,
            risk_preference VARCHAR NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            transaction_id VARCHAR PRIMARY KEY,
            portfolio_id VARCHAR NOT NULL,
            holding_id VARCHAR NOT NULL,
            owner_id VARCHAR NOT NULL,
            transaction_type VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            quantity BIGINT NOT NULL,
            unit_price DECIMAL(24, 8) NOT NULL,
            fees DECIMAL(24, 8) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_portfolios_owner ON portfolios(owner_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_holdings_owner ON portfolio_holdings(owner_id, portfolio_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_transactions_owner ON portfolio_transactions(owner_id, holding_id)")
    return con


def create_portfolio(owner_id: str, name: str) -> dict:
    owner, title = _owner(owner_id), _name(name)
    portfolio_id, now = str(uuid4()), datetime.now(timezone.utc)
    con = connect()
    try:
        con.execute("INSERT INTO portfolios VALUES (?, ?, ?, ?, ?)",
                    [portfolio_id, owner, title, now, now])
    finally:
        con.close()
    return {"portfolio_id": portfolio_id, "owner_id": owner, "name": title,
            "created_at": now.isoformat(), "updated_at": now.isoformat()}


def list_portfolios(owner_id: str) -> list[dict]:
    owner = _owner(owner_id)
    con = connect()
    try:
        rows = con.execute("""
            SELECT portfolio_id, name, created_at, updated_at
            FROM portfolios WHERE owner_id = ? ORDER BY created_at, portfolio_id
        """, [owner]).fetchall()
    finally:
        con.close()
    return [{"portfolio_id": r[0], "name": r[1], "created_at": r[2].isoformat(),
             "updated_at": r[3].isoformat()} for r in rows]


def rename_portfolio(owner_id: str, portfolio_id: str, name: str) -> bool:
    owner, title = _owner(owner_id), _name(name)
    con = connect()
    try:
        changed = con.execute("""
            UPDATE portfolios SET name = ?, updated_at = ?
            WHERE owner_id = ? AND portfolio_id = ?
            RETURNING portfolio_id
        """, [title, datetime.now(timezone.utc), owner, portfolio_id]).fetchone()
    finally:
        con.close()
    return changed is not None


def delete_portfolio(owner_id: str, portfolio_id: str) -> bool:
    owner = _owner(owner_id)
    con = connect()
    try:
        con.execute("BEGIN TRANSACTION")
        exists = con.execute("""
            SELECT 1 FROM portfolios WHERE owner_id = ? AND portfolio_id = ?
        """, [owner, portfolio_id]).fetchone()
        if not exists:
            con.execute("ROLLBACK")
            return False
        con.execute("DELETE FROM portfolio_transactions WHERE owner_id = ? AND portfolio_id = ?",
                    [owner, portfolio_id])
        con.execute("DELETE FROM portfolio_holdings WHERE owner_id = ? AND portfolio_id = ?",
                    [owner, portfolio_id])
        con.execute("DELETE FROM portfolios WHERE owner_id = ? AND portfolio_id = ?",
                    [owner, portfolio_id])
        con.execute("COMMIT")
        return True
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def add_holding(owner_id: str, portfolio_id: str, symbol: str, *,
                horizon: str = "long_term", risk_preference: str = "balanced") -> dict:
    owner, ticker = _owner(owner_id), _symbol(symbol)
    if horizon not in HORIZONS:
        raise ValueError("unsupported investment horizon")
    if risk_preference not in RISK_PREFERENCES:
        raise ValueError("unsupported risk preference")
    holding_id, now = str(uuid4()), datetime.now(timezone.utc)
    con = connect()
    try:
        exists = con.execute("""
            SELECT 1 FROM portfolios WHERE owner_id = ? AND portfolio_id = ?
        """, [owner, portfolio_id]).fetchone()
        if not exists:
            raise LookupError("portfolio not found")
        con.execute("INSERT INTO portfolio_holdings VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [holding_id, portfolio_id, owner, ticker, horizon, risk_preference, now, now])
    finally:
        con.close()
    return {"holding_id": holding_id, "portfolio_id": portfolio_id, "symbol": ticker,
            "horizon": horizon, "risk_preference": risk_preference,
            "created_at": now.isoformat()}


def list_holdings(owner_id: str, portfolio_id: str) -> list[dict]:
    owner = _owner(owner_id)
    con = connect()
    try:
        rows = con.execute("""
            SELECT holding_id, symbol, horizon, risk_preference, created_at
            FROM portfolio_holdings
            WHERE owner_id = ? AND portfolio_id = ?
            ORDER BY created_at, holding_id
        """, [owner, portfolio_id]).fetchall()
    finally:
        con.close()
    return [{"holding_id": r[0], "symbol": r[1], "horizon": r[2],
             "risk_preference": r[3], "created_at": r[4].isoformat()} for r in rows]


def add_transaction(owner_id: str, portfolio_id: str, holding_id: str, *,
                    transaction_type: str, trade_date: str, quantity: int,
                    unit_price, fees=0, transaction_id: str | None = None) -> dict:
    owner = _owner(owner_id)
    day = _date(trade_date)
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("transaction_type must be buy or sell")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError("quantity must be a positive whole share count")
    price = _decimal(unit_price, "unit_price", positive=True)
    fee = _decimal(fees, "fees")
    tx_id = transaction_id or str(uuid4())
    if not isinstance(tx_id, str) or not tx_id.strip() or len(tx_id) > 100:
        raise ValueError("transaction_id must be non-empty text up to 100 characters")
    now = datetime.now(timezone.utc)
    con = connect()
    try:
        con.execute("BEGIN TRANSACTION")
        parent = con.execute("""
            SELECT 1 FROM portfolio_holdings
            WHERE owner_id = ? AND portfolio_id = ? AND holding_id = ?
        """, [owner, portfolio_id, holding_id]).fetchone()
        if not parent:
            raise LookupError("holding not found")
        duplicate = con.execute("""
            SELECT 1 FROM portfolio_transactions
            WHERE owner_id = ? AND transaction_id = ?
        """, [owner, tx_id]).fetchone()
        if duplicate:
            raise ValueError("duplicate transaction_id")
        existing = con.execute("""
            SELECT transaction_id, transaction_type, CAST(trade_date AS VARCHAR),
                   quantity, CAST(unit_price AS VARCHAR), CAST(fees AS VARCHAR)
            FROM portfolio_transactions
            WHERE owner_id = ? AND portfolio_id = ? AND holding_id = ?
            ORDER BY trade_date, created_at, transaction_id
        """, [owner, portfolio_id, holding_id]).fetchall()
        from .portfolio_accounting import calculate_position
        candidate = [{"id": r[0], "type": r[1], "trade_date": r[2],
                      "quantity": r[3], "unit_price": r[4], "fees": r[5]}
                     for r in existing]
        candidate.append({"id": tx_id, "type": transaction_type, "trade_date": day,
                          "quantity": quantity, "unit_price": price, "fees": fee})
        candidate.sort(key=lambda item: (item["trade_date"], item["id"]))
        calculate_position(candidate)
        con.execute("""
            INSERT INTO portfolio_transactions
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [tx_id, portfolio_id, holding_id, owner, transaction_type, date.fromisoformat(day),
              quantity, price, fee, now])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return {"transaction_id": tx_id, "portfolio_id": portfolio_id,
            "holding_id": holding_id, "transaction_type": transaction_type,
            "trade_date": day, "quantity": quantity, "unit_price": price,
            "fees": fee, "created_at": now.isoformat()}


def list_transactions(owner_id: str, portfolio_id: str, holding_id: str) -> list[dict]:
    owner = _owner(owner_id)
    con = connect()
    try:
        rows = con.execute("""
            SELECT transaction_id, transaction_type, CAST(trade_date AS VARCHAR),
                   quantity, CAST(unit_price AS VARCHAR), CAST(fees AS VARCHAR), created_at
            FROM portfolio_transactions
            WHERE owner_id = ? AND portfolio_id = ? AND holding_id = ?
            ORDER BY trade_date, created_at, transaction_id
        """, [owner, portfolio_id, holding_id]).fetchall()
    finally:
        con.close()
    return [{"transaction_id": r[0], "transaction_type": r[1], "trade_date": r[2],
             "quantity": r[3], "unit_price": r[4], "fees": r[5],
             "created_at": r[6].isoformat()} for r in rows]
