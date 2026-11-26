"""Classify source-only floorsheet contracts against a dated security snapshot.

This is a dated instrument-scope review, not a source-completeness audit.
Unmatched and unclassified instruments remain UNKNOWN; no coverage is promoted.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or ())
        missing = sorted(required - headers)
        if missing:
            raise ValueError(f"{path} missing required columns: {missing}")
        return [{key: (value or "").strip() for key, value in row.items()}
                for row in reader]


def unique_index(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
    result = {}
    for row in rows:
        symbol = row.get("symbol", "").strip().upper()
        if not symbol or symbol in result:
            raise ValueError(f"{label} has blank or duplicate symbol: {symbol!r}")
        result[symbol] = row
    return result


def classify_one_sided_contracts(
    audit: dict,
    equity_crosswalk_path: str | Path,
    target_candidates_path: str | Path,
    security_snapshot_path: str | Path,
    expected_snapshot_date: str,
) -> dict:
    import datetime
    try:
        expected_snapshot_date = datetime.date.fromisoformat(expected_snapshot_date).isoformat()
    except ValueError as exc:
        raise ValueError("expected snapshot date must be ISO YYYY-MM-DD") from exc

    crosswalk_rows = read_csv(Path(equity_crosswalk_path), {
        "symbol", "security_id", "security_name", "snapshot_date",
        "active_status", "crosswalk_status",
    })
    candidate_rows = read_csv(Path(target_candidates_path), {
        "symbol", "instrument_class_from_rendered_list", "official_snapshot_id",
        "official_snapshot_status",
    })
    snapshot_rows = read_csv(Path(security_snapshot_path), {
        "symbol", "security_id", "security_name", "active_status", "snapshot_date",
    })
    crosswalk = unique_index(crosswalk_rows, "equity crosswalk")
    candidates = unique_index(candidate_rows, "target candidates")
    snapshot = unique_index(snapshot_rows, "security snapshot")

    for symbol, row in crosswalk.items():
        security = snapshot.get(symbol)
        if (row["snapshot_date"] != expected_snapshot_date
                or row["active_status"] != "A"
                or row["crosswalk_status"] != "snapshot_id_match_active_status_A"):
            raise ValueError(f"crosswalk row for {symbol} is not verified active on {expected_snapshot_date}")
        if security is None or any((
            row["security_id"] != security["security_id"],
            row["security_name"] != security["security_name"],
            row["active_status"] != security["active_status"],
            row["snapshot_date"] != security["snapshot_date"],
        )):
            raise ValueError(f"crosswalk/security snapshot conflict for {symbol}")

    date_reports = audit.get("date_reports")
    if not isinstance(date_reports, dict) or not date_reports:
        raise ValueError("audit must contain non-empty date_reports")
    contract_rows = []
    for day, date_report in sorted(date_reports.items()):
        comparison = ((date_report.get("audit") or {}).get("comparison") or {})
        if comparison.get("comparison_status") != "compared_review_only":
            raise ValueError(f"{day}: source comparison not complete")
        if comparison.get("conflicting_shared_contract_count") != 0:
            raise ValueError(f"{day}: shared-field conflicts prevent one-sided classification")
        if comparison.get("samir_only_contract_keys"):
            raise ValueError(f"{day}: Samir-only contracts require separate adjudication")
        for row in comparison.get("right_only_contracts", []):
            if row.get("trade_date") != day:
                raise ValueError(f"{day}: one-sided contract has inconsistent trade date")
            if not row.get("contract_id") or not row.get("symbol"):
                raise ValueError(f"{day}: one-sided contract missing contract ID or symbol")
            contract_rows.append({**row, "audit_date": day, "one_sided_source": "socrateai_only"})

    classified = []
    class_counts: Counter[str] = Counter()
    by_date_symbol: dict[tuple[str, str, str], dict] = {}
    for row in contract_rows:
        symbol = row["symbol"].strip().upper()
        security = snapshot.get(symbol)
        cross = crosswalk.get(symbol)
        candidate = candidates.get(symbol)
        candidate_class = (candidate or {}).get("instrument_class_from_rendered_list", "")
        name = (security or {}).get("security_name", "").casefold()

        if cross:
            scope = "IN_SCOPE_EQUITY_CANDIDATE"
            security_id = cross["security_id"]
            evidence = "dated_equity_crosswalk_and_security_snapshot_identity_match"
        elif candidate_class.casefold() == "mutual fund":
            scope = "OUT_OF_SCOPE_MUTUAL_FUND"
            security_id = (candidate or {}).get("official_snapshot_id") or (security or {}).get("security_id")
            evidence = "dated_target_candidate_instrument_class"
        elif security and "promoter" in name:
            scope = "OUT_OF_SCOPE_PROMOTER_SHARE"
            security_id = security["security_id"]
            evidence = "dated_security_snapshot_name_identifies_promoter_share"
        elif security and "debenture" in name:
            scope = "OUT_OF_SCOPE_DEBENTURE"
            security_id = security["security_id"]
            evidence = "dated_security_snapshot_name_identifies_debenture"
        elif security and re.search(r"\\bbond\\b", name):
            scope = "OUT_OF_SCOPE_BOND"
            security_id = security["security_id"]
            evidence = "dated_security_snapshot_name_identifies_bond"
        elif candidate_class.casefold() == "equity":
            scope = "EQUITY_CANDIDATE_NOT_IN_CROSSWALK"
            security_id = (candidate or {}).get("official_snapshot_id") or (security or {}).get("security_id")
            evidence = "dated_target_equity_candidate_not_in_equity_crosswalk"
        elif security:
            scope = "UNCLASSIFIED_SECURITY_SNAPSHOT_ONLY"
            security_id = security["security_id"]
            evidence = "dated_security_snapshot_without_approved_instrument_class"
        else:
            scope = "UNKNOWN_NO_SECURITY_SNAPSHOT_MATCH"
            security_id = None
            evidence = "no_dated_security_snapshot_match"
        class_counts[scope] += 1
        classified_row = {
            "trade_date": row["trade_date"],
            "contract_id": row["contract_id"],
            "symbol": symbol,
            "quantity": str(row["quantity"]),
            "rate": str(row["rate"]),
            "amount": str(row["amount"]),
            "scope_class": scope,
            "security_id": security_id,
            "security_name": (security or {}).get("security_name"),
            "evidence": evidence,
            "buyer_broker_code": row.get("buyer_broker_code"),
            "seller_broker_code": row.get("seller_broker_code"),
        }
        classified.append(classified_row)
        key = (row["trade_date"], symbol, scope)
        agg = by_date_symbol.setdefault(key, {
            "trade_date": row["trade_date"], "symbol": symbol,
            "scope_class": scope, "security_id": security_id,
            "contract_count": 0, "quantity": Decimal("0"),
            "gross_amount": Decimal("0"),
        })
        try:
            quantity = Decimal(str(row["quantity"]))
            amount = Decimal(str(row["amount"]))
        except InvalidOperation as exc:
            raise ValueError(f"invalid quantity/amount for {row['contract_id']}") from exc
        if not quantity.is_finite() or quantity <= 0 or not amount.is_finite() or amount <= 0:
            raise ValueError(f"nonpositive or nonfinite one-sided contract {row['contract_id']}")
        agg["contract_count"] += 1
        agg["quantity"] += quantity
        agg["gross_amount"] += amount

    aggregates = []
    for row in sorted(by_date_symbol.values(), key=lambda item: (item["trade_date"], item["symbol"])):
        aggregates.append({
            **row,
            "quantity": str(row["quantity"]),
            "gross_amount": str(row["gross_amount"]),
        })
    date_counts = {}
    for day in sorted(date_reports):
        rows = [row for row in classified if row["trade_date"] == day]
        counts = Counter(row["scope_class"] for row in rows)
        date_counts[day] = {
            "one_sided_contract_count": len(rows),
            "scope_class_counts": dict(sorted(counts.items())),
            "symbols": sorted({row["symbol"] for row in rows}),
            "quantity": str(sum((Decimal(row["quantity"]) for row in rows), Decimal("0"))),
            "gross_amount": str(sum((Decimal(row["amount"]) for row in rows), Decimal("0"))),
        }

    return {
        "schema_version": "1.0",
        "audit_status": "review_only_dated_scope_classification",
        "security_snapshot_date": expected_snapshot_date,
        "crosswalk_rows": len(crosswalk_rows),
        "target_candidate_rows": len(candidate_rows),
        "security_snapshot_rows": len(snapshot_rows),
        "one_sided_contract_count": len(classified),
        "scope_class_counts": dict(sorted(class_counts.items())),
        "date_summaries": date_counts,
        "date_symbol_aggregates": aggregates,
        "one_sided_contracts": classified,
        "source_independence_verified": False,
        "daily_capture_completeness_verified": False,
        "official_session_status_verified": False,
        "source_rights_verified": False,
        "coverage_admission_allowed": False,
        "canonical_promotion_allowed": False,
        "policy": "dated_instrument_scope_only_unknown_preserved_no_source_completeness_or_no_trade_inference",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--equity-crosswalk", type=Path, required=True)
    parser.add_argument("--target-candidates", type=Path, required=True)
    parser.add_argument("--security-snapshot", type=Path, required=True)
    parser.add_argument("--expected-snapshot-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    report = classify_one_sided_contracts(
        audit, args.equity_crosswalk, args.target_candidates,
        args.security_snapshot, args.expected_snapshot_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "audit_status": report["audit_status"],
        "one_sided_contract_count": report["one_sided_contract_count"],
        "scope_class_counts": report["scope_class_counts"],
        "coverage_admission_allowed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
