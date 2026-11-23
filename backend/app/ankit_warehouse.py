"""Load AnkitSanjyal's Parquet tables into separate DuckDB source tables with QA.

This intentionally keeps eod_price and eod_history_ext separate. It also performs
an overlap comparison where dates/symbols match. It does not create trading signals.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

SOURCE_REPO = "AnkitSanjyal/nepse-market-data"
SOURCE_REVISION = "main"

TABLES = {
    "floorsheet": {
        "required": [
            "contract_id", "business_date", "trade_time", "stock_symbol",
            "buyer_member_id", "seller_member_id", "contract_quantity",
            "contract_rate", "contract_amount",
        ],
        "key": ["business_date", "contract_id"],
    },
    "eod_price": {
        "required": [
            "business_date", "symbol", "open_price", "high_price",
            "low_price", "close_price", "total_traded_quantity",
            "total_traded_value",
        ],
        "key": ["business_date", "symbol"],
    },
    "eod_history_ext": {
        "required": [
            "source", "symbol", "business_date", "open_price", "high_price",
            "low_price", "close_price", "traded_quantity", "traded_amount",
        ],
        "key": ["business_date", "symbol"],
    },
    "broker_flow_daily": {
        "required": [
            "business_date", "symbol", "broker_id", "buy_qty",
            "sell_qty", "net_qty", "buy_value", "sell_value", "net_value",
        ],
        "key": ["business_date", "symbol", "broker_id"],
    },
    "bars_1m": {
        "required": [
            "business_date", "symbol", "bar_ts", "open", "high",
            "low", "close", "volume", "turnover", "trades", "vwap",
        ],
        "key": ["business_date", "symbol", "bar_ts"],
    },
    "daily_stats": {
        "required": [
            "business_date", "symbol", "vwap", "volume",
            "turnover", "trades", "first_trade", "last_trade",
        ],
        "key": ["business_date", "symbol"],
    },
}

def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _table_schema(con: duckdb.DuckDBPyConnection, table: str) -> list[dict[str, str]]:
    rows = con.execute(f"DESCRIBE SELECT * FROM {table}").fetchall()
    return [{"name": row[0], "type": row[1]} for row in rows]

def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int | float | str | None:
    value = con.execute(sql).fetchone()[0]
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "as_tuple"):
        return str(value)
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)

def _ohlc_quality(
    con: duckdb.DuckDBPyConnection, table: str, *,
    date_col: str, symbol_col: str,
    open_col: str, high_col: str, low_col: str, close_col: str,
    flag_col: str | None = None,
) -> dict[str, Any]:
    cols = [quote for quote in (date_col, symbol_col, open_col, high_col, low_col, close_col)]
    date_q, symbol_q, open_q, high_q, low_q, close_q = [f'"{name}"' for name in cols]
    nonpositive = (
        f"{open_q} <= 0 OR {high_q} <= 0 OR {low_q} <= 0 OR {close_q} <= 0"
    )
    high_below_low = f"{high_q} < {low_q}"
    open_outside = f"({open_q} < {low_q} OR {open_q} > {high_q})"
    close_outside = f"({close_q} < {low_q} OR {close_q} > {high_q})"
    outlier = f"({nonpositive}) OR ({high_below_low}) OR {open_outside} OR {close_outside}"

    result: dict[str, Any] = {
        "nonpositive_price_rows": int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE {nonpositive}"
        ) or 0),
        "high_below_low_rows": int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE {high_below_low}"
        ) or 0),
        "open_outside_range_rows": int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE {open_outside}"
        ) or 0),
        "close_outside_range_rows": int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE {close_outside}"
        ) or 0),
        "ohlc_outlier_rows": int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE {outlier}"
        ) or 0),
        "first_session": _scalar(con, f"SELECT MIN({date_q}) FROM {table}"),
        "last_session": _scalar(con, f"SELECT MAX({date_q}) FROM {table}"),
    }
    if flag_col:
        flag_q = f'"{flag_col}"'
        result["flagged_close_outside_range_rows"] = int(_scalar(
            con,
            f"""SELECT COUNT(*) FROM {table}
                WHERE ({outlier}) AND {flag_q} ILIKE '%close_outside_range%'"""
        ) or 0)
        result["unflagged_ohlc_outlier_rows"] = int(_scalar(
            con,
            f"""SELECT COUNT(*) FROM {table}
                WHERE ({outlier})
                  AND ({flag_q} IS NULL OR {flag_q} NOT ILIKE '%close_outside_range%')"""
        ) or 0)
    else:
        result["unflagged_ohlc_outlier_rows"] = result["ohlc_outlier_rows"]

    top = con.execute(
        f"""SELECT {symbol_q}, COUNT(*) AS n
            FROM {table} WHERE ({outlier})
            GROUP BY {symbol_q} ORDER BY n DESC, {symbol_q} LIMIT 20"""
    ).fetchall()
    result["top_symbols_with_ohlc_outliers"] = [
        {"symbol": row[0], "rows": int(row[1])} for row in top
    ]
    sample_rows = con.execute(
        f"""SELECT {date_q}, {symbol_q}, {open_q}, {high_q}, {low_q}, {close_q}
            {f', "{flag_col}"' if flag_col else ''}
            FROM {table} WHERE ({outlier})
            ORDER BY {date_q}, {symbol_q} LIMIT 20"""
    ).fetchall()
    sample_columns = ["business_date", "symbol", "open", "high", "low", "close"]
    if flag_col:
        sample_columns.append(flag_col)
    result["sample_ohlc_outliers"] = [
        {name: (value.isoformat() if hasattr(value, "isoformat") else str(value) if value is not None else None)
         for name, value in zip(sample_columns, row)}
        for row in sample_rows
    ]
    result["status"] = "review_required" if result["ohlc_outlier_rows"] else "pass"
    return result


def _table_qc(con: duckdb.DuckDBPyConnection, table: str) -> dict[str, Any]:
    schema = _table_schema(con, table)
    columns = {item["name"] for item in schema}
    config = TABLES[table.split(".", 1)[-1]]
    missing = sorted(set(config["required"]) - columns)
    if missing:
        raise ValueError(f"{table} missing required columns: {', '.join(missing)}")

    total = int(_scalar(con, f"SELECT COUNT(*) FROM {table}") or 0)
    key_expr = ", ".join(f'"{column}"' for column in config["key"])
    duplicate_groups = int(_scalar(
        con,
        f"SELECT COUNT(*) FROM (SELECT {key_expr} FROM {table} "
        f"GROUP BY {key_expr} HAVING COUNT(*) > 1)"
    ) or 0)
    quality: dict[str, Any] = {
        "rows": total,
        "duplicate_key_groups": duplicate_groups,
    }

    if table.endswith(".floorsheet"):
        quality["bad_trade_values"] = int(_scalar(
            con,
            f"""SELECT COUNT(*) FROM {table}
                WHERE contract_quantity IS NULL OR contract_quantity <= 0
                   OR contract_rate IS NULL OR contract_rate <= 0
                   OR contract_amount IS NULL OR contract_amount <= 0"""
        ) or 0)
        quality["amount_arithmetic_errors_over_npr_1"] = int(_scalar(
            con,
            f"""SELECT COUNT(*) FROM {table}
                WHERE ABS(CAST(contract_quantity AS DECIMAL(24,4)) *
                          contract_rate - contract_amount) > 1.00"""
        ) or 0)
        quality["first_session"] = _scalar(con, f"SELECT MIN(business_date) FROM {table}")
        quality["last_session"] = _scalar(con, f"SELECT MAX(business_date) FROM {table}")
        quality["symbols"] = int(_scalar(con, f"SELECT COUNT(DISTINCT stock_symbol) FROM {table}") or 0)

    elif table.endswith(".eod_price"):
        quality.update(_ohlc_quality(
            con, table,
            date_col="business_date", symbol_col="symbol",
            open_col="open_price", high_col="high_price",
            low_col="low_price", close_col="close_price",
            flag_col="quality_flags" if "quality_flags" in columns else None,
        ))
        quality["symbols_per_session_min"] = _scalar(
            con, f"SELECT MIN(n) FROM (SELECT COUNT(DISTINCT symbol) n FROM {table} GROUP BY business_date)"
        )

    elif table.endswith(".eod_history_ext"):
        quality.update(_ohlc_quality(
            con, table,
            date_col="business_date", symbol_col="symbol",
            open_col="open_price", high_col="high_price",
            low_col="low_price", close_col="close_price",
        ))
        quality["symbols"] = int(_scalar(con, f"SELECT COUNT(DISTINCT symbol) FROM {table}") or 0)

    elif table.endswith(".broker_flow_daily"):
        quality["net_quantity_mismatch_rows"] = int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE net_qty != buy_qty - sell_qty"
        ) or 0)
        quality["net_value_mismatch_rows_over_npr_1"] = int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE ABS(net_value - (buy_value - sell_value)) > 1.00"
        ) or 0)
        quality["first_session"] = _scalar(con, f"SELECT MIN(business_date) FROM {table}")
        quality["last_session"] = _scalar(con, f"SELECT MAX(business_date) FROM {table}")

    elif table.endswith(".bars_1m"):
        quality.update(_ohlc_quality(
            con, table,
            date_col="business_date", symbol_col="symbol",
            open_col="open", high_col="high", low_col="low", close_col="close",
        ))
        quality["first_bar"] = _scalar(con, f"SELECT MIN(bar_ts) FROM {table}")
        quality["last_bar"] = _scalar(con, f"SELECT MAX(bar_ts) FROM {table}")

    elif table.endswith(".daily_stats"):
        quality["negative_volume_or_turnover_rows"] = int(_scalar(
            con, f"SELECT COUNT(*) FROM {table} WHERE volume < 0 OR turnover < 0 OR trades < 0"
        ) or 0)
        quality["first_session"] = _scalar(con, f"SELECT MIN(business_date) FROM {table}")
        quality["last_session"] = _scalar(con, f"SELECT MAX(business_date) FROM {table}")

    return {"schema": schema, "quality": quality}

def _overlap_reconciliation(con: duckdb.DuckDBPyConnection) -> dict[str, Any] | None:
    left, right = "ankit.eod_history_ext", "ankit.eod_price"
    exists = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema='ankit' AND table_name IN ('eod_history_ext','eod_price')"
    ).fetchone()[0]
    if exists != 2:
        return None
    row = con.execute(f"""
        SELECT
            COUNT(*) AS matched_symbol_dates,
            COUNT(*) FILTER (WHERE h.traded_quantity = p.total_traded_quantity) AS exact_volume_matches,
            COUNT(*) FILTER (WHERE h.close_price = p.close_price) AS exact_close_matches,
            COUNT(*) FILTER (WHERE ABS(h.close_price - p.close_price) <= 0.01) AS close_matches_within_0_01,
            MAX(ABS(h.close_price - p.close_price)) AS max_abs_close_difference,
            MIN(h.business_date) AS overlap_start,
            MAX(h.business_date) AS overlap_end
        FROM {left} h
        INNER JOIN {right} p
          ON h.business_date = p.business_date AND h.symbol = p.symbol
    """).fetchone()
    return {
        "matched_symbol_dates": int(row[0]),
        "exact_volume_matches": int(row[1]),
        "exact_close_matches": int(row[2]),
        "close_matches_within_0_01": int(row[3]),
        "max_abs_close_difference": str(row[4]) if row[4] is not None else None,
        "overlap_start": row[5].isoformat() if row[5] else None,
        "overlap_end": row[6].isoformat() if row[6] else None,
        "note": "This is an independent comparison of two publisher-provided tables; do not collapse the two source tables after comparison.",
    }

def load_ankit_warehouse(
    input_root: str | Path,
    database_path: str | Path,
    report_path: str | Path,
) -> dict[str, Any]:
    root = Path(input_root).resolve()
    db = Path(database_path).resolve()
    report = Path(report_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Parquet input directory does not exist: {root}")
    db.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db))
    result: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_repo": SOURCE_REPO,
        "source_revision": SOURCE_REVISION,
        "database_path": str(db),
        "tables": {},
        "source_files": [],
        "overlap_reconciliation": None,
        "limitations": [
            "Each source table is loaded under a separate schema/table; no tables are merged.",
            "eod_history_ext is a secondary ShareSansar-derived source; eod_price is a separate NEPSE EOD source according to the publisher.",
            "Broker-flow records are aggregated by broker code and do not identify beneficial owners.",
            "Quality checks do not prove completeness against NEPSE totals; corporate-action adjustment is not performed.",
        ],
    }
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS ankit")
        for table, config in TABLES.items():
            folder = root / table
            files = sorted(folder.rglob("*.parquet")) if folder.is_dir() else []
            if not files:
                result["tables"][table] = {"status": "no_files", "rows": 0}
                continue
            if not all(path.is_file() for path in files):
                raise ValueError(f"Missing files detected in {folder}")
            for path in files:
                result["source_files"].append({
                    "table": table,
                    "path": str(path.relative_to(root)),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_file(path),
                })
            file_list = "[" + ", ".join(_sql_literal(str(path)) for path in files) + "]"
            target = f"ankit.{table}"
            con.execute(
                f"CREATE OR REPLACE TABLE {target} AS "
                f"SELECT *, {_sql_literal(SOURCE_REPO)}::VARCHAR AS _source_repo, "
                f"{_sql_literal(SOURCE_REVISION)}::VARCHAR AS _source_revision, "
                f"CURRENT_TIMESTAMP AS _loaded_at_utc "
                f"FROM read_parquet({file_list}, union_by_name = false)"
            )
            result["tables"][table] = {
                "status": "loaded",
                "files": len(files),
                **_table_qc(con, target),
            }
        result["overlap_reconciliation"] = _overlap_reconciliation(con)
        result["warehouse_bytes"] = db.stat().st_size if db.exists() else 0
    finally:
        con.close()

    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
