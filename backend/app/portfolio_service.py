"""Private portfolio ledger with deterministic weighted-average accounting.

Market prices and corporate-action adjustments are intentionally not sourced here.
All monetary values are stored as decimal strings; no binary floats are used.
"""
from __future__ import annotations

import os
import re
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

_SYMBOL = re.compile(r"[A-Z0-9]{1,20}")
_NAME_LIMIT = 100


def _decimal(value, field: str, *, allow_zero: bool = False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite decimal") from exc
    if not result.is_finite() or result < 0 or (not allow_zero and result == 0):
        raise ValueError(f"{field} must be {'non-negative' if allow_zero else 'positive'} and finite")
    return result


def _connect():
    path = Path(os.getenv("NEPSE_PORTFOLIO_DB", "private/portfolios.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Portfolio rows contain private financial information. Create the database
    # with restrictive permissions before SQLite opens it, and tighten existing
    # paths on every connection. O_NOFOLLOW prevents silently opening a symlink.
    os.chmod(path.parent, 0o700)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_portfolios_owner ON portfolios(owner);
        CREATE TABLE IF NOT EXISTS portfolio_transactions (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY','SELL')),
            quantity TEXT NOT NULL,
            price TEXT NOT NULL,
            fees TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            idempotency_key TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(owner, idempotency_key)
        );
        CREATE INDEX IF NOT EXISTS idx_portfolio_tx_order
            ON portfolio_transactions(owner, portfolio_id, symbol, trade_date, created_at, id);
        CREATE TABLE IF NOT EXISTS portfolio_holding_preferences (
            owner TEXT NOT NULL,
            portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            symbol TEXT NOT NULL,
            investment_horizon TEXT NOT NULL CHECK(investment_horizon IN
                ('short_term','one_to_three_months','three_to_six_months','long_term')),
            risk_preference TEXT NOT NULL CHECK(risk_preference IN
                ('capital_protection','balanced','aggressive_growth')),
            updated_at TEXT NOT NULL,
            PRIMARY KEY(owner, portfolio_id, symbol)
        );
    """)
    return con


def _portfolio(row):
    return {"id": row["id"], "name": row["name"],
            "created_at": row["created_at"], "updated_at": row["updated_at"]}


def create_portfolio(owner: str, name: str) -> dict:
    name = str(name).strip()
    if not name or len(name) > _NAME_LIMIT:
        raise ValueError("name must contain 1 to 100 characters")
    now = datetime.now(timezone.utc).isoformat()
    item_id = str(uuid4())
    with _connect() as con:
        con.execute("INSERT INTO portfolios VALUES (?,?,?,?,?)",
                    (item_id, owner, name, now, now))
        row = con.execute("SELECT * FROM portfolios WHERE id=? AND owner=?",
                          (item_id, owner)).fetchone()
    return _portfolio(row)


def list_portfolios(owner: str) -> list[dict]:
    with _connect() as con:
        rows = con.execute("SELECT * FROM portfolios WHERE owner=? ORDER BY created_at,id",
                           (owner,)).fetchall()
    return [_portfolio(row) for row in rows]


def get_portfolio(owner: str, portfolio_id: str) -> dict | None:
    with _connect() as con:
        row = con.execute("SELECT * FROM portfolios WHERE id=? AND owner=?",
                          (portfolio_id, owner)).fetchone()
    return _portfolio(row) if row else None


def update_portfolio(owner: str, portfolio_id: str, name: str) -> dict | None:
    name = str(name).strip()
    if not name or len(name) > _NAME_LIMIT:
        raise ValueError("name must contain 1 to 100 characters")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        changed = con.execute(
            "UPDATE portfolios SET name=?,updated_at=? WHERE id=? AND owner=?",
            (name, now, portfolio_id, owner)).rowcount
        row = con.execute("SELECT * FROM portfolios WHERE id=? AND owner=?",
                          (portfolio_id, owner)).fetchone() if changed else None
    return _portfolio(row) if row else None


def delete_portfolio(owner: str, portfolio_id: str) -> bool:
    with _connect() as con:
        changed = con.execute("DELETE FROM portfolios WHERE id=? AND owner=?",
                              (portfolio_id, owner)).rowcount
    return bool(changed)


def add_transaction(owner: str, portfolio_id: str, *, symbol: str, side: str,
                    quantity, price, fees=0, trade_date: str,
                    idempotency_key: str | None = None) -> dict:
    symbol = str(symbol).strip().upper()
    side = str(side).strip().upper()
    if not _SYMBOL.fullmatch(symbol):
        raise ValueError("symbol must be 1 to 20 uppercase letters or digits")
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    qty = _decimal(quantity, "quantity")
    unit_price = _decimal(price, "price")
    fee = _decimal(fees, "fees", allow_zero=True)
    date_text = str(trade_date)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_text):
        raise ValueError("trade_date must be YYYY-MM-DD")
    try:
        normalized_date = date.fromisoformat(date_text).isoformat()
    except ValueError as exc:
        raise ValueError("trade_date must be YYYY-MM-DD") from exc
    if idempotency_key is not None:
        idempotency_key = str(idempotency_key).strip()
        if not idempotency_key or len(idempotency_key) > 200:
            raise ValueError("idempotency_key must contain 1 to 200 characters")
    transaction_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        # Serialize the idempotency lookup + insert so concurrent replays cannot
        # race past the pre-insert check. SQLite grants the write reservation
        # before either request reads the idempotency key.
        con.execute("BEGIN IMMEDIATE")
        portfolio = con.execute("SELECT id FROM portfolios WHERE id=? AND owner=?",
                                (portfolio_id, owner)).fetchone()
        if portfolio is None:
            raise LookupError("portfolio not found")
        if idempotency_key:
            prior = con.execute(
                "SELECT * FROM portfolio_transactions WHERE owner=? AND idempotency_key=?",
                (owner, idempotency_key)).fetchone()
            if prior:
                if (prior["portfolio_id"], prior["symbol"], prior["side"], prior["quantity"],
                    prior["price"], prior["fees"], prior["trade_date"]) != (
                    portfolio_id, symbol, side, str(qty), str(unit_price), str(fee), normalized_date):
                    raise ValueError("idempotency_key already used for a different transaction")
                return _transaction(prior)
        if side == "SELL":
            position = _calculate_positions(con, owner, portfolio_id).get(symbol)
            available = Decimal(position["quantity"]) if position else Decimal(0)
            if qty > available:
                raise ValueError("sell quantity exceeds available shares")
        con.execute("""INSERT INTO portfolio_transactions
            (id,owner,portfolio_id,symbol,side,quantity,price,fees,trade_date,idempotency_key,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (transaction_id, owner, portfolio_id, symbol, side, str(qty), str(unit_price),
             str(fee), normalized_date, idempotency_key, now))
        # Recompute the complete chronological ledger before committing. This
        # rejects backdated sells that would make an earlier position negative.
        _calculate_positions(con, owner, portfolio_id)
        row = con.execute("SELECT * FROM portfolio_transactions WHERE id=?",
                          (transaction_id,)).fetchone()
    return _transaction(row)


def _transaction(row):
    return {key: row[key] for key in
            ("id", "portfolio_id", "symbol", "side", "quantity", "price", "fees",
             "trade_date", "created_at")}


def _calculate_positions(con, owner: str, portfolio_id: str) -> dict[str, dict]:
    rows = con.execute("""SELECT * FROM portfolio_transactions
        WHERE owner=? AND portfolio_id=?
        ORDER BY trade_date,created_at,id""", (owner, portfolio_id)).fetchall()
    state: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        symbol = row["symbol"]
        position = state.setdefault(symbol, {
            "quantity": Decimal(0), "cost_basis": Decimal(0), "realized_pnl": Decimal(0)
        })
        qty, price, fees = Decimal(row["quantity"]), Decimal(row["price"]), Decimal(row["fees"])
        if row["side"] == "BUY":
            position["quantity"] += qty
            position["cost_basis"] += qty * price + fees
        else:
            if qty > position["quantity"]:
                raise ValueError(f"historical sells exceed buys for {symbol}")
            average_cost = position["cost_basis"] / position["quantity"]
            position["realized_pnl"] += qty * price - fees - average_cost * qty
            position["quantity"] -= qty
            position["cost_basis"] = average_cost * position["quantity"]
    result = {}
    for symbol, p in state.items():
        avg = p["cost_basis"] / p["quantity"] if p["quantity"] else Decimal(0)
        result[symbol] = {
            "symbol": symbol,
            "quantity": str(p["quantity"]),
            "cost_basis": str(p["cost_basis"]),
            "average_cost": str(avg),
            "realized_pnl": str(p["realized_pnl"]),
            "market_value": None,
            "unrealized_pnl": None,
            "valuation_status": "price_not_supplied",
            "corporate_action_status": "not_adjusted_unless_verified_event_is_applied",
        }
    return result


def portfolio_positions(owner: str, portfolio_id: str) -> list[dict] | None:
    with _connect() as con:
        exists = con.execute("SELECT 1 FROM portfolios WHERE id=? AND owner=?",
                             (portfolio_id, owner)).fetchone()
        if not exists:
            return None
        return list(_calculate_positions(con, owner, portfolio_id).values())


def portfolio_transactions(owner: str, portfolio_id: str) -> list[dict] | None:
    with _connect() as con:
        exists = con.execute("SELECT 1 FROM portfolios WHERE id=? AND owner=?",
                             (portfolio_id, owner)).fetchone()
        if not exists:
            return None
        rows = con.execute("""SELECT * FROM portfolio_transactions
            WHERE owner=? AND portfolio_id=? ORDER BY trade_date,created_at,id""",
            (owner, portfolio_id)).fetchall()
    return [_transaction(row) for row in rows]


_HORIZONS = {
    "short_term", "one_to_three_months", "three_to_six_months", "long_term"
}
_RISK_PREFERENCES = {"capital_protection", "balanced", "aggressive_growth"}


def set_holding_preferences(owner: str, portfolio_id: str, symbol: str, *,
                            investment_horizon: str, risk_preference: str) -> dict | None:
    """Set user-owned planning preferences for an existing positive holding.

    Preferences are user intent, not a market signal or recommendation. They
    are deliberately separate from the transaction ledger and valuation.
    """
    symbol = str(symbol).strip().upper()
    horizon = str(investment_horizon).strip()
    risk = str(risk_preference).strip()
    if not _SYMBOL.fullmatch(symbol):
        raise ValueError("symbol must be 1 to 20 uppercase letters or digits")
    if horizon not in _HORIZONS:
        raise ValueError("investment_horizon is not supported")
    if risk not in _RISK_PREFERENCES:
        raise ValueError("risk_preference is not supported")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as con:
        con.execute("BEGIN IMMEDIATE")
        portfolio = con.execute(
            "SELECT 1 FROM portfolios WHERE id=? AND owner=?",
            (portfolio_id, owner),
        ).fetchone()
        if portfolio is None:
            return None
        position = _calculate_positions(con, owner, portfolio_id).get(symbol)
        if position is None or Decimal(position["quantity"]) <= 0:
            raise LookupError("positive holding not found")
        con.execute("""
            INSERT INTO portfolio_holding_preferences
                (owner, portfolio_id, symbol, investment_horizon, risk_preference, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(owner, portfolio_id, symbol) DO UPDATE SET
                investment_horizon=excluded.investment_horizon,
                risk_preference=excluded.risk_preference,
                updated_at=excluded.updated_at
        """, (owner, portfolio_id, symbol, horizon, risk, now))
        row = con.execute("""
            SELECT symbol, investment_horizon, risk_preference, updated_at
            FROM portfolio_holding_preferences
            WHERE owner=? AND portfolio_id=? AND symbol=?
        """, (owner, portfolio_id, symbol)).fetchone()
    return dict(row)


def list_holding_preferences(owner: str, portfolio_id: str) -> list[dict] | None:
    with _connect() as con:
        exists = con.execute(
            "SELECT 1 FROM portfolios WHERE id=? AND owner=?",
            (portfolio_id, owner),
        ).fetchone()
        if exists is None:
            return None
        rows = con.execute("""
            SELECT symbol, investment_horizon, risk_preference, updated_at
            FROM portfolio_holding_preferences
            WHERE owner=? AND portfolio_id=? ORDER BY symbol
        """, (owner, portfolio_id)).fetchall()
    return [dict(row) for row in rows]
