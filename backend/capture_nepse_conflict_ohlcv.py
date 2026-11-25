#!/usr/bin/env python3
"""Capture official NEPSE price/volume history for quarantined OHLCV conflicts."""
from __future__ import annotations
import argparse, csv, hashlib, json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

DATE_FIELDS = ("businessDate", "business_date", "date", "businessdate")
OHLCV_FIELDS = {
    "open": ("openPrice", "open", "openingPrice", "open_price"),
    "high": ("highPrice", "high", "maxPrice", "high_price"),
    "low": ("lowPrice", "low", "minPrice", "low_price"),
    "close": ("closePrice", "close", "closingPrice", "close_price"),
    "volume": ("totalTradedQuantity", "totalTradeQuantity", "totalTradedVolume", "volume", "quantity"),
}
HISTORY_PATH_PREFIX = "/api/nots/market/history/security/"
SECURITY_PATH = "/api/nots/security"


def _as_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _decimal(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _find_records(payload):
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)], {"container": "root_list"}
    if not isinstance(payload, dict):
        return [], {"container": type(payload).__name__}
    for key in ("content", "data", "records", "result", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)], {
                "container": key,
                "total_pages": payload.get("totalPages"),
                "total_elements": payload.get("totalElements"),
            }
        if isinstance(value, dict):
            rows, meta = _find_records(value)
            if meta.get("container") != "unrecognized_dict_shape":
                return rows, {
                    **{name: value for name, value in meta.items() if name != "container"},
                    "container": key + "." + meta["container"],
                }
    return [], {"container": "unrecognized_dict_shape", "top_level_keys": sorted(payload.keys())}


def _first_field(row, aliases):
    return next((name for name in aliases if name in row and row[name] is not None), None)


def _query_window(conflicts, padding_days=30):
    dates = [date.fromisoformat(item["date"]) for item in conflicts]
    return min(dates) - timedelta(days=padding_days), max(dates) + timedelta(days=padding_days)


def analyze_history_payload(payload, conflicts):
    rows, pagination = _find_records(payload)
    date_field = next(
        (field for field in DATE_FIELDS if any(_as_date(row.get(field)) for row in rows)),
        None,
    )
    if date_field is None:
        # An explicitly recognized empty collection is valid evidence of an empty
        # response, not an unknown schema. Record every requested date as missing.
        if not rows and pagination.get("container") != "unrecognized_dict_shape":
            comparisons = [
                {"symbol": conflict["symbol"], "date": conflict["date"],
                 "status": "no_primary_row", "primary_rows_found": 0}
                for conflict in conflicts
            ]
            return {
                "status": "empty_valid_response", "record_count": 0,
                "pagination": pagination, "date_field": None,
                "field_names": [], "conflict_comparisons": comparisons,
                "decision_requires_review": True, "canonical_promotion_allowed": False,
            }
        return {
            "status": "unmapped_schema", "record_count": len(rows),
            "pagination": pagination, "date_field": None,
            "field_names": sorted({key for row in rows for key in row}),
            "conflict_comparisons": [
                {"symbol": conflict["symbol"], "date": conflict["date"],
                 "status": "unmapped_date_schema", "primary_rows_found": None}
                for conflict in conflicts
            ],
            "decision_requires_review": True,
            "canonical_promotion_allowed": False,
        }

    comparisons = []
    for conflict in conflicts:
        target_date = conflict["date"]
        matching_rows = [row for row in rows if _as_date(row.get(date_field)) == target_date]
        if not matching_rows:
            comparisons.append({"symbol": conflict["symbol"], "date": target_date, "status": "no_primary_row", "primary_rows_found": 0})
            continue
        if len(matching_rows) != 1:
            comparisons.append({"symbol": conflict["symbol"], "date": target_date, "status": "multiple_primary_rows", "primary_rows_found": len(matching_rows), "primary_rows": matching_rows})
            continue

        row = matching_rows[0]
        field_map = {field: _first_field(row, aliases) for field, aliases in OHLCV_FIELDS.items()}
        values = {field: _decimal(row.get(source_field)) if source_field else None for field, source_field in field_map.items()}
        if any(value is None for value in values.values()):
            comparisons.append({
                "symbol": conflict["symbol"], "date": target_date,
                "status": "partial_primary_fields",
                "field_map": field_map,
                "missing_fields": [field for field, value in values.items() if value is None],
                "available_primary_fields": {field: str(value) for field, value in values.items() if value is not None},
                "primary_row": row,
            })
            continue

        official_tuple = tuple(values[key] for key in ("open", "high", "low", "close", "volume"))
        source_a = tuple(_decimal(value) for value in conflict["source_a"]["ohlcv"])
        source_b = tuple(_decimal(value) for value in conflict["source_b"]["ohlcv"])
        if official_tuple == source_a and official_tuple == source_b:
            status = "matches_both"
        elif official_tuple == source_a:
            status = "matches_source_a"
        elif official_tuple == source_b:
            status = "matches_source_b"
        else:
            status = "matches_neither"
        comparisons.append({
            "symbol": conflict["symbol"], "date": target_date, "status": status,
            "field_map": field_map,
            "official_ohlcv": [str(value) for value in official_tuple],
            "source_a_ohlcv": [str(value) for value in source_a],
            "source_b_ohlcv": [str(value) for value in source_b],
            "primary_row": row,
        })

    all_matched = len(comparisons) == len(conflicts) and all(
        item["status"] in {"matches_source_a", "matches_source_b", "matches_both"}
        for item in comparisons
    )
    return {
        "status": "all_conflicts_have_primary_match" if all_matched else "review_required",
        "record_count": len(rows),
        "unique_primary_dates": len({_as_date(row.get(date_field)) for row in rows if _as_date(row.get(date_field))}),
        "pagination": pagination, "date_field": date_field,
        "field_names": sorted({key for row in rows for key in row}),
        "conflict_comparisons": comparisons,
        "all_conflicts_have_primary_match": all_matched,
        "decision_requires_review": True, "canonical_promotion_allowed": False,
    }



def _row_symbol(row, security_id_to_symbol=None):
    for field in ("symbol", "securitySymbol", "stockSymbol", "ticker"):
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    for parent in ("security", "securityData", "securityInfo", "scrip"):
        nested = row.get(parent)
        if isinstance(nested, dict):
            value = _row_symbol(nested, security_id_to_symbol)
            if value:
                return value
    for field in ("securityId", "security_id", "id"):
        value = row.get(field)
        if value is not None and security_id_to_symbol:
            mapped = security_id_to_symbol.get(str(value))
            if mapped:
                return mapped
    return None


def analyze_date_price_volume_payload(payload, conflicts, security_id_to_symbol=None):
    """Match a date-specific NEPSE board response to each disputed symbol."""
    rows, pagination = _find_records(payload)
    if not rows:
        status = "no_primary_row" if pagination.get("container") != "unrecognized_dict_shape" else "unmapped_schema"
        return [
            {"symbol": item["symbol"], "date": item["date"], "status": status,
             "primary_rows_found": 0 if status == "no_primary_row" else None,
             "pagination": pagination}
            for item in conflicts
        ]

    row_symbols = [_row_symbol(row, security_id_to_symbol) for row in rows]
    if not any(row_symbols):
        return [
            {"symbol": item["symbol"], "date": item["date"],
             "status": "unmapped_symbol_schema", "primary_rows_found": None,
             "field_names": sorted({field for row in rows for field in row})}
            for item in conflicts
        ]

    comparisons = []
    for conflict in conflicts:
        matches = [row for row, symbol in zip(rows, row_symbols) if symbol == conflict["symbol"].upper()]
        if not matches:
            comparisons.append({
                "symbol": conflict["symbol"], "date": conflict["date"],
                "status": "no_primary_row", "primary_rows_found": 0,
            })
            continue
        if len(matches) != 1:
            comparisons.append({
                "symbol": conflict["symbol"], "date": conflict["date"],
                "status": "multiple_primary_rows", "primary_rows_found": len(matches),
                "primary_rows": matches,
            })
            continue

        row = matches[0]
        field_map = {field: _first_field(row, aliases) for field, aliases in OHLCV_FIELDS.items()}
        values = {field: _decimal(row.get(source)) if source else None for field, source in field_map.items()}
        if any(value is None for value in values.values()):
            comparisons.append({
                "symbol": conflict["symbol"], "date": conflict["date"],
                "status": "partial_primary_fields", "field_map": field_map,
                "missing_fields": [field for field, value in values.items() if value is None],
                "available_primary_fields": {field: str(value) for field, value in values.items() if value is not None},
                "primary_row": row,
            })
            continue

        official = tuple(values[key] for key in ("open", "high", "low", "close", "volume"))
        source_a = tuple(_decimal(value) for value in conflict["source_a"]["ohlcv"])
        source_b = tuple(_decimal(value) for value in conflict["source_b"]["ohlcv"])
        if official == source_a and official == source_b:
            status = "matches_both"
        elif official == source_a:
            status = "matches_source_a"
        elif official == source_b:
            status = "matches_source_b"
        else:
            status = "matches_neither"
        comparisons.append({
            "symbol": conflict["symbol"], "date": conflict["date"], "status": status,
            "field_map": field_map, "official_ohlcv": [str(value) for value in official],
            "source_a_ohlcv": [str(value) for value in source_a],
            "source_b_ohlcv": [str(value) for value in source_b], "primary_row": row,
        })
    return comparisons


def select_primary_comparison(date_specific_result, per_security_result):
    """Select a complete primary result without hiding endpoint disagreements."""
    accepted = {"matches_source_a", "matches_source_b", "matches_both"}
    date_ok = bool(date_specific_result and date_specific_result.get("status") in accepted)
    history_ok = bool(per_security_result and per_security_result.get("status") in accepted)
    if date_ok and history_ok:
        if date_specific_result.get("official_ohlcv") != per_security_result.get("official_ohlcv"):
            return {
                "symbol": date_specific_result["symbol"], "date": date_specific_result["date"],
                "status": "primary_endpoint_disagreement",
                "date_specific_ohlcv": date_specific_result.get("official_ohlcv"),
                "per_security_ohlcv": per_security_result.get("official_ohlcv"),
            }
        return date_specific_result
    if date_ok:
        return date_specific_result
    if history_ok:
        return per_security_result
    return date_specific_result or per_security_result


def capture(ledger_path, output_dir):
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    conflicts = ledger["conflicts"]
    by_symbol = {}
    for conflict in conflicts:
        by_symbol.setdefault(conflict["symbol"], []).append(conflict)

    output_dir.mkdir(parents=True, exist_ok=True)
    responses_dir = output_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    captured = {}
    active_symbol = None
    active_business_date = None

    from nepse_client import NepseClient
    client = NepseClient(timeout=90.0)
    graph_path_prefix = client.api_end_points.get("company_daily_graph", "")
    market_price_volume_path = client.api_end_points.get("todays_price", "")

    def preserve_response(response):
        path = urlparse(str(response.url)).path
        is_security_list = path == SECURITY_PATH
        is_history = path.startswith(HISTORY_PATH_PREFIX)
        is_daily_graph = bool(graph_path_prefix) and path.startswith(graph_path_prefix)
        is_market_price_volume = bool(market_price_volume_path) and path.startswith(market_price_volume_path)
        if not (is_security_list or is_history or is_daily_graph or is_market_price_volume):
            return
        response.read()
        if is_security_list:
            key = "security-list"
        elif is_history:
            key = active_symbol or "unknown-symbol"
        elif is_daily_graph:
            key = (active_symbol or "unknown-symbol") + ".daily-graph"
        else:
            key = "market-price-volume." + (active_business_date or "unknown-date")
        captured[key] = {
            "body": response.content, "status": response.status_code,
            "url": str(response.url),
            "headers": {name: response.headers.get(name) for name in ("date", "content-type", "content-length", "server") if response.headers.get(name) is not None},
        }

    client.client.event_hooks["response"].append(preserve_response)
    request_errors = {}
    try:
        # Capture NEPSE's date-specific market price-volume endpoint once per
        # disputed session. Preserve raw responses for independent field review.
        for business_date in sorted({item["date"] for item in conflicts}):
            active_business_date = business_date
            try:
                client.getPriceVolumeHistory(business_date=business_date)
            except Exception as exc:
                request_errors.setdefault("market-price-volume", {})[business_date] = {
                    "type": type(exc).__name__, "message": str(exc)[:300]
                }
        for symbol, symbol_conflicts in sorted(by_symbol.items()):
            active_symbol = symbol
            # Query a surrounding window, not only the exact disputed date.
            # This verifies that the symbol ID and history endpoint return records
            # in the relevant period and makes an isolated missing session visible.
            query_start, query_end = _query_window(symbol_conflicts)
            try:
                client.getCompanyPriceVolumeHistory(
                    symbol, start_date=query_start, end_date=query_end
                )
            except Exception as exc:
                request_errors[symbol] = {"history": {"type": type(exc).__name__, "message": str(exc)[:300]}}
            # Capture the separate official daily-scrip graph endpoint as an
            # independent response. Its schema is inspected from raw evidence;
            # do not assume it contains opening prices or a complete OHLCV row.
            try:
                client.getDailyScripPriceGraph(symbol)
            except Exception as exc:
                request_errors.setdefault(symbol, {})["daily_graph"] = {
                    "type": type(exc).__name__, "message": str(exc)[:300]
                }
    finally:
        client.close()

    reports = {}
    for symbol, item in captured.items():
        body = item["body"]
        filename = f"{symbol}.response-body.bin"
        (responses_dir / filename).write_bytes(body)
        try:
            parsed = json.loads(body)
            (responses_dir / f"{symbol}.parsed-response.json").write_text(json.dumps(parsed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except Exception:
            parsed = None
        reports[symbol] = {
            "http_status": item["status"], "source_url": item["url"],
            "response_headers": item["headers"], "response_bytes": len(body),
            "response_sha256": hashlib.sha256(body).hexdigest(), "parsed": parsed,
        }

    security_id_to_symbol = {}
    security_list_report = reports.get("security-list")
    if security_list_report and isinstance(security_list_report["parsed"], list):
        for security in security_list_report["parsed"]:
            if isinstance(security, dict) and security.get("id") is not None and security.get("symbol"):
                security_id_to_symbol[str(security["id"])] = str(security["symbol"]).upper()

    market_price_volume_reports = {}
    date_specific_comparisons = []
    for business_date in sorted({item["date"] for item in conflicts}):
        date_conflicts = [item for item in conflicts if item["date"] == business_date]
        key = "market-price-volume." + business_date
        item = reports.get(key)
        if item is None:
            market_price_volume_reports[business_date] = {"status": "not_captured"}
            date_specific_comparisons.extend({
                "symbol": c["symbol"], "date": c["date"], "status": "primary_response_unavailable"
            } for c in date_conflicts)
            continue
        parsed = item["parsed"]
        rows, pagination = _find_records(parsed) if parsed is not None else ([], {"container": "unparseable"})
        date_comparisons = analyze_date_price_volume_payload(parsed, date_conflicts, security_id_to_symbol) if parsed is not None else [
            {"symbol": c["symbol"], "date": c["date"], "status": "primary_response_unparseable"}
            for c in date_conflicts
        ]
        date_specific_comparisons.extend(date_comparisons)
        market_price_volume_reports[business_date] = {
            "status": "captured" if item["http_status"] == 200 and parsed is not None else "unavailable_or_unparseable",
            "http_status": item["http_status"], "source_url": item["source_url"],
            "response_sha256": item["response_sha256"],
            "response_bytes": item["response_bytes"],
            "record_count": len(rows), "pagination": pagination,
            "field_names": sorted({field for row in rows for field in row}),
            "records": rows,
        }

    graph_reports = {}
    for symbol in sorted(by_symbol):
        graph = reports.get(symbol + ".daily-graph")
        if graph is None:
            graph_reports[symbol] = {"status": "not_captured"}
            continue
        parsed_graph = graph["parsed"]
        graph_reports[symbol] = {
            "status": "captured" if graph["http_status"] == 200 and parsed_graph is not None else "unavailable_or_unparseable",
            "http_status": graph["http_status"],
            "source_url": graph["source_url"],
            "response_sha256": graph["response_sha256"],
            "response_bytes": graph["response_bytes"],
            "parsed_type": type(parsed_graph).__name__,
            "top_level_keys": sorted(parsed_graph.keys()) if isinstance(parsed_graph, dict) else [],
        }

    symbol_reports = {}
    comparison_results = []
    for symbol, symbol_conflicts in sorted(by_symbol.items()):
        response = reports.get(symbol)
        if response is None or response["http_status"] != 200 or response["parsed"] is None:
            symbol_reports[symbol] = {"status": "response_missing_or_non_200", "request_error": request_errors.get(symbol)}
            comparison_results.extend({"symbol": item["symbol"], "date": item["date"], "status": "primary_response_unavailable"} for item in symbol_conflicts)
            continue
        analysis = analyze_history_payload(response["parsed"], symbol_conflicts)
        symbol_reports[symbol] = {
            "status": analysis["status"], "source_url": response["source_url"],
            "response_sha256": response["response_sha256"],
            "record_count": analysis["record_count"], "pagination": analysis["pagination"],
            "date_field": analysis["date_field"],
            "query_start_date": _query_window(symbol_conflicts)[0].isoformat(),
            "query_end_date": _query_window(symbol_conflicts)[1].isoformat(),
        }
        comparison_results.extend(analysis["conflict_comparisons"])

    # Prefer the independent date-specific NEPSE board comparison; fall back
    # to the per-security history only when it supplies a complete OHLCV match.
    history_by_key = {(item["symbol"], item["date"]): item for item in comparison_results}
    date_by_key = {(item["symbol"], item["date"]): item for item in date_specific_comparisons}
    resolved_comparisons = []
    for conflict in conflicts:
        key = (conflict["symbol"], conflict["date"])
        date_result = date_by_key.get(key)
        history_result = history_by_key.get(key)
        chosen = select_primary_comparison(date_result, history_result)
        if chosen is not None:
            resolved_comparisons.append(chosen)
    all_matched = len(resolved_comparisons) == len(conflicts) and all(
        item["status"] in {"matches_source_a", "matches_source_b", "matches_both"}
        for item in resolved_comparisons
    )
    report = {
        "schema_version": 1, "source_id": "NEPSE_OFFICIAL_PRICE_VOLUME_HISTORY",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "endpoint_path": "/api/nots/market/history/security/{securityId}",
        "client_version": "nepse-client==0.1.4",
        "conflict_count": len(conflicts), "symbol_count": len(by_symbol),
        "captured_response_count": len(reports),
        "security_list_captured": "security-list" in reports,
        "symbol_reports": symbol_reports, "daily_graph_reports": graph_reports,
        "date_specific_market_price_volume": market_price_volume_reports,\n        "date_specific_conflict_comparisons": date_specific_comparisons,\n        "resolved_conflict_comparisons": resolved_comparisons,
        "request_errors": request_errors,
        "conflict_comparisons": comparison_results,
        "all_conflicts_have_primary_match": all_matched,
        "decision_requires_review": True, "canonical_promotion_allowed": False,
        "training_allowed": False,
    }
    (output_dir / "capture-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{meta['response_sha256']}  responses/{symbol}.response-body.bin\n" for symbol, meta in sorted(reports.items())),
        encoding="utf-8",
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = capture(args.ledger, args.output_dir)
    print(json.dumps({
        "conflict_count": report["conflict_count"], "symbol_count": report["symbol_count"],
        "captured_response_count": report["captured_response_count"],
        "all_conflicts_have_primary_match": report["all_conflicts_have_primary_match"],
        "request_errors": report["request_errors"], "canonical_promotion_allowed": False,
    }, indent=2))
    return 0 if report["all_conflicts_have_primary_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
