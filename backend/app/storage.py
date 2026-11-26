import csv
import hashlib
import io
import json
import math
import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {"symbol", "date", "open", "high", "low", "close", "volume"}
SCHEMA_VERSION = 1

CREATE_CANDLES = """
CREATE TABLE candles (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    PRIMARY KEY (symbol, date)
)
"""

CREATE_IMPORTS = """
CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    rows_accepted INTEGER NOT NULL,
    symbols TEXT NOT NULL,
    latest_session TEXT NOT NULL,
    UNIQUE (source, sha256)
)
"""


class CandleConflict(ValueError):
    """An import offers a different value for an existing symbol and date."""


def parse_candles(raw: bytes) -> dict[tuple[str, str], tuple[float, float, float, float, int]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header")
    fields = [name.strip().lower() for name in reader.fieldnames]
    missing = REQUIRED - set(fields)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    if len(fields) != len(set(fields)):
        raise ValueError("CSV has duplicate column names")
    reader.fieldnames = fields
    parsed = {}
    for row in reader:
        line = reader.line_num
        try:
            if None in row or any(row[column] is None for column in REQUIRED):
                raise ValueError("row does not match the CSV header")
            symbol = row["symbol"].strip().upper()
            if not symbol or len(symbol) > 20:
                raise ValueError("invalid symbol")
            day = date.fromisoformat(row["date"].strip()).isoformat()
            o, h, lo, c = (float(row[column]) for column in ("open", "high", "low", "close"))
            volume = Decimal(row["volume"])
            if (
                not all(math.isfinite(price) and price > 0 for price in (o, h, lo, c))
                or not lo <= min(o, c) <= max(o, c) <= h
                or not volume.is_finite()
                or not 0 <= volume <= 2**63 - 1
                or volume != volume.to_integral_value()
            ):
                raise ValueError("invalid OHLCV values")
            values = (o, h, lo, c, int(volume))
        except (ValueError, InvalidOperation, OverflowError) as exc:
            raise ValueError(f"Invalid row {line}: {exc}") from exc
        key = (symbol, day)
        if key in parsed and parsed[key] != values:
            raise CandleConflict(f"Conflicting duplicate row for {symbol} on {day}")
        parsed[key] = values
    return parsed


def import_record(row: sqlite3.Row) -> dict:
    record = dict(row)
    record.pop("id")
    record["symbols"] = json.loads(record["symbols"])
    return record


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path.resolve()

    def _connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            connection = sqlite3.connect(f"{self.path.as_uri()}?mode=ro", uri=True, timeout=10)
        else:
            connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                connection.execute(CREATE_CANDLES)
                connection.execute(CREATE_IMPORTS)
                connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            elif version != SCHEMA_VERSION:
                raise RuntimeError(f"Unsupported database schema version: {version}")

    def is_ready(self) -> bool:
        try:
            with closing(self._connect(readonly=True)) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version != SCHEMA_VERSION:
                    return False
                connection.execute("SELECT symbol, date, open, high, low, close, volume FROM candles LIMIT 0")
                connection.execute(
                    "SELECT source, sha256, imported_at, rows_accepted, symbols, latest_session FROM imports LIMIT 0"
                )
                return True
        except sqlite3.Error:
            return False

    def store_rows(self, raw: bytes, source: str) -> dict:
        parsed = parse_candles(raw)
        digest = hashlib.sha256(raw).hexdigest()
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT * FROM imports WHERE source = ? AND sha256 = ?", (source, digest)
            ).fetchone()
            if previous is not None:
                return import_record(previous)

            for (symbol, day), values in parsed.items():
                inserted = connection.execute(
                    """
                    INSERT INTO candles (symbol, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (symbol, date) DO NOTHING
                    """,
                    (symbol, day, *values),
                )
                if not inserted.rowcount:
                    existing = connection.execute(
                        "SELECT open, high, low, close, volume FROM candles WHERE symbol = ? AND date = ?",
                        (symbol, day),
                    ).fetchone()
                    if tuple(existing) != values:
                        raise CandleConflict(f"Stored candle differs for {symbol} on {day}")

            cursor = connection.execute(
                """
                INSERT INTO imports (source, sha256, imported_at, rows_accepted, symbols, latest_session)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    digest,
                    datetime.now(timezone.utc).isoformat(),
                    len(parsed),
                    json.dumps(sorted({symbol for symbol, _ in parsed})),
                    max((day for _, day in parsed), default=""),
                ),
            )
            saved = connection.execute("SELECT * FROM imports WHERE id = ?", (cursor.lastrowid,)).fetchone()
            return import_record(saved)

    def recent_imports(self) -> list[dict]:
        with closing(self._connect(readonly=True)) as connection:
            rows = connection.execute("SELECT * FROM imports ORDER BY id DESC LIMIT 100").fetchall()
            return [import_record(row) for row in reversed(rows)]

    @staticmethod
    def _symbols(connection: sqlite3.Connection) -> list[str]:
        rows = connection.execute("SELECT DISTINCT symbol FROM candles ORDER BY symbol")
        return [row["symbol"] for row in rows]

    def symbols(self) -> list[str]:
        with closing(self._connect(readonly=True)) as connection:
            return self._symbols(connection)

    @staticmethod
    def _history(connection: sqlite3.Connection, symbol: str, as_of: date | None = None) -> list[dict]:
        statement = "SELECT date, open, high, low, close, volume FROM candles WHERE symbol = ?"
        params = (symbol,)
        if as_of is not None:
            statement += " AND date <= ?"
            params += (as_of.isoformat(),)
        rows = connection.execute(statement + " ORDER BY date", params)
        return [{**row, "date": date.fromisoformat(row["date"])} for row in rows]

    def history(self, symbol: str) -> list[dict]:
        with closing(self._connect(readonly=True)) as connection:
            return self._history(connection, symbol)

    def histories(self, symbols: list[str] | None, as_of: date | None) -> list[tuple[str, list[dict]]]:
        with closing(self._connect(readonly=True)) as connection:
            connection.execute("BEGIN")
            selected = [symbol.upper() for symbol in symbols] if symbols else self._symbols(connection)
            return [(symbol, self._history(connection, symbol, as_of)) for symbol in selected]
