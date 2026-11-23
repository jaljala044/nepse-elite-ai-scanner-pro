"""Read-only schema and data-quality inventory for downloaded NEPSE Parquet files."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

DATE_LIKE = {
    "date", "business_date", "calculation_date", "trade_date",
    "timestamp", "bar_ts", "created_at", "updated_at",
}

def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def sql_path(path: Path) -> str:
    return "'" + str(path.resolve()).replace("\\", "/").replace("'", "''") + "'"

def inspect_one(con: duckdb.DuckDBPyConnection, path: Path, root: Path) -> dict[str, Any]:
    source = sql_path(path)
    description = con.execute(f"DESCRIBE SELECT * FROM read_parquet({source})").fetchall()
    columns = [{"name": row[0], "type": row[1]} for row in description]
    row_count = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({source})").fetchone()[0])

    present_date_cols = [
        item["name"] for item in columns
        if item["name"].lower() in DATE_LIKE
        or item["name"].lower().endswith(("_date", "_timestamp", "_ts"))
    ]
    date_ranges: dict[str, Any] = {}
    for column in present_date_cols:
        ident = quote_ident(column)
        try:
            bounds = con.execute(
                f"SELECT CAST(MIN({ident}) AS VARCHAR), CAST(MAX({ident}) AS VARCHAR) "
                f"FROM read_parquet({source})"
            ).fetchone()
            date_ranges[column] = {"min": bounds[0], "max": bounds[1]}
        except Exception as exc:
            date_ranges[column] = {"error": f"{type(exc).__name__}: {exc}"}

    null_counts: dict[str, int] = {}
    if row_count:
        # Count nulls for all fields; parquet files in this data repo are relatively small.
        expressions = [
            f"SUM(CASE WHEN {quote_ident(col['name'])} IS NULL THEN 1 ELSE 0 END)"
            for col in columns
        ]
        if expressions:
            values = con.execute(
                f"SELECT {', '.join(expressions)} FROM read_parquet({source})"
            ).fetchone()
            null_counts = {col["name"]: int(values[i] or 0) for i, col in enumerate(columns)}

    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "row_count": row_count,
        "columns": columns,
        "date_ranges": date_ranges,
        "null_counts": null_counts,
    }

def inspect_directory(input_dir: Path, max_files: int | None = None) -> dict[str, Any]:
    root = input_dir.resolve()
    files = sorted(root.rglob("*.parquet"))
    if max_files is not None:
        files = files[:max_files]
    con = duckdb.connect(database=":memory:")
    results = []
    failures = []
    try:
        for path in files:
            try:
                results.append(inspect_one(con, path, root))
            except Exception as exc:
                failures.append({
                    "path": str(path.relative_to(root)),
                    "error": f"{type(exc).__name__}: {exc}",
                })
    finally:
        con.close()

    by_table: dict[str, dict[str, Any]] = {}
    for record in results:
        table = record["path"].split("/", 1)[0]
        aggregate = by_table.setdefault(table, {
            "files": 0, "bytes": 0, "rows": 0, "schemas": {},
            "date_ranges": {},
        })
        aggregate["files"] += 1
        aggregate["bytes"] += record["bytes"]
        aggregate["rows"] += record["row_count"]
        signature = tuple((col["name"], col["type"]) for col in record["columns"])
        schema_key = json.dumps(signature)
        aggregate["schemas"][schema_key] = aggregate["schemas"].get(schema_key, 0) + 1
        for column, bounds in record["date_ranges"].items():
            if "min" not in bounds or "max" not in bounds:
                continue
            current = aggregate["date_ranges"].setdefault(column, {"min": bounds["min"], "max": bounds["max"]})
            if bounds["min"] is not None and (current["min"] is None or bounds["min"] < current["min"]):
                current["min"] = bounds["min"]
            if bounds["max"] is not None and (current["max"] is None or bounds["max"] > current["max"]):
                current["max"] = bounds["max"]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_root": str(root),
        "files_found": len(files),
        "files_inspected": len(results),
        "files_failed": len(failures),
        "tables": by_table,
        "files": results,
        "failures": failures,
        "limitations": [
            "This is a schema, row-count, null-count and date-range inventory, not proof that source rows are exchange-complete.",
            "The dataset publisher's source labels and validation claims remain provenance statements.",
            "The two EOD source tables must remain distinct until row-level overlap reconciliation is independently performed.",
            "Broker-flow outputs are derived summaries, not evidence of beneficial-owner identity or intent.",
            "Corporate-action normalization is not performed by this inspector.",
        ],
    }

def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect downloaded NEPSE Parquet schemas and row counts")
    parser.add_argument("input", nargs="?", default="../data/raw/huggingface/AnkitSanjyal__nepse-market-data/main")
    parser.add_argument("--max-files", type=int)
    parser.add_argument("--output", type=Path, default=Path("../data/reports/ankit-parquet-inspection.json"))
    args = parser.parse_args()
    result = inspect_directory(Path(args.input), args.max_files)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "files_found": result["files_found"],
        "files_inspected": result["files_inspected"],
        "files_failed": result["files_failed"],
        "tables": {
            name: {
                "files": value["files"],
                "rows": value["rows"],
                "bytes": value["bytes"],
                "schema_variants": len(value["schemas"]),
                "date_ranges": value["date_ranges"],
            }
            for name, value in result["tables"].items()
        },
        "output": str(args.output),
    }, indent=2))
    if result["files_failed"]:
        raise SystemExit(1)
    if result["files_inspected"] == 0:
        raise SystemExit("No Parquet files inspected")

if __name__ == "__main__":
    main()
