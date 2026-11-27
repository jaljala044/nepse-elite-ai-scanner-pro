import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_ohlcv_exception_ledger import validate


def record(kind, number):
    common = {
        "exception_id": f"{kind}:{number}",
        "exception_type": kind,
        "symbol": f"S{number}",
        "trade_date": "2026-01-01",
        "source_repository": "jaljala044/nepse-smc-data",
        "disposition": "quarantined_unresolved",
        "reviewer_rationale": "Fixture only; retain unresolved.",
    }
    if kind == "invalid_ohlc":
        common.update({
            "source_commit_sha": "a" * 40,
            "source_path": f"data/S{number}.csv",
            "source_file_sha256": "b" * 64,
            "source_csv_line": 2,
            "raw_source_row": {"open": "10", "high": "9", "low": "8", "close": "9"},
        })
    else:
        common["source_evidence"] = {
            "jaljala044/nepse-smc-data": {
                "commit_sha": "a" * 40, "path": "data/example.csv",
                "file_sha256": "b" * 64, "row": {"close": "10"},
            },
            "jaljala044/nepse-history-starter": {
                "commit_sha": "c" * 40, "path": "data/example.csv",
                "file_sha256": "d" * 64, "row": {"close": "11"},
            },
        }
    return common


class LedgerValidationTests(unittest.TestCase):
    def test_expected_ledger_passes(self):
        records = ([record("invalid_ohlc", i) for i in range(1331)] +
                   [record("cross_source_ohlcv_conflict", i) for i in range(8)])
        for row in records[1331:1338]:
            row["disposition"] = "resolved_with_user_authoritative_evidence"
            row["resolution_evidence"] = {
                "authority": "explicit_user_designation_as_final_and_authoritative",
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jp, cp = root / "ledger.json", root / "ledger.csv"
            jp.write_text(json.dumps({
                "counts": {"total_exception_records": 1339,
                           "invalid_ohlc_rows": 1331,
                           "cross_source_conflict_keys": 8},
                "exceptions": records,
            }), encoding="utf-8")
            fields = sorted({key for row in records for key in row})
            with cp.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for row in records:
                    writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v
                                     for k, v in row.items()})
            self.assertEqual(validate(jp, cp), [])

    def test_unresolved_disposition_is_required(self):
        records = ([record("invalid_ohlc", i) for i in range(1331)] +
                   [record("cross_source_ohlcv_conflict", i) for i in range(8)])
        for row in records[1331:1336]:
            row["disposition"] = "resolved_with_user_authoritative_evidence"
            row["resolution_evidence"] = {
                "authority": "explicit_user_designation_as_final_and_authoritative",
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        records[0]["disposition"] = "accepted"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jp, cp = root / "ledger.json", root / "ledger.csv"
            jp.write_text(json.dumps({
                "counts": {"total_exception_records": 1339,
                           "invalid_ohlc_rows": 1331,
                           "cross_source_conflict_keys": 8},
                "exceptions": records,
            }), encoding="utf-8")
            fields = sorted({key for row in records for key in row})
            with cp.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for row in records:
                    writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v
                                     for k, v in row.items()})
            self.assertTrue(any("must remain quarantined_unresolved" in e for e in validate(jp, cp)))


    def test_csv_disposition_cannot_be_swapped_while_preserving_counts(self):
        records = ([record("invalid_ohlc", i) for i in range(1331)] +
                   [record("cross_source_ohlcv_conflict", i) for i in range(8)])
        for row in records[1331:1336]:
            row["disposition"] = "resolved_with_user_authoritative_evidence"
            row["resolution_evidence"] = {
                "authority": "explicit_user_designation_as_final_and_authoritative",
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jp, cp = root / "ledger.json", root / "ledger.csv"
            jp.write_text(json.dumps({
                "counts": {"total_exception_records": 1339,
                           "invalid_ohlc_rows": 1331,
                           "cross_source_conflict_keys": 8},
                "exceptions": records,
            }), encoding="utf-8")
            fields = sorted({key for row in records for key in row})
            with cp.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for row in records:
                    writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v
                                     for k, v in row.items()})
            with cp.open(encoding="utf-8", newline="") as stream:
                csv_rows = list(csv.DictReader(stream))
                fieldnames = csv_rows[0].keys()
            csv_rows[0]["disposition"] = "resolved_with_user_authoritative_evidence"
            csv_rows[1331]["disposition"] = "quarantined_unresolved"
            with cp.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
            errors = validate(jp, cp)
            self.assertTrue(any("JSON/CSV disposition mismatch" in error
                                for error in errors))


    def test_csv_identity_fields_cannot_be_changed_under_same_exception_id(self):
        records = ([record("invalid_ohlc", i) for i in range(1331)] +
                   [record("cross_source_ohlcv_conflict", i) for i in range(8)])
        for row in records[1331:1338]:
            row["disposition"] = "resolved_with_user_authoritative_evidence"
            row["resolution_evidence"] = {
                "authority": "explicit_user_designation_as_final_and_authoritative",
                "canonical_promotion_allowed": False,
                "raw_source_rows_modified": False,
            }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            jp, cp = root / "ledger.json", root / "ledger.csv"
            jp.write_text(json.dumps({
                "counts": {"total_exception_records": 1339,
                           "invalid_ohlc_rows": 1331,
                           "cross_source_conflict_keys": 8},
                "exceptions": records,
            }), encoding="utf-8")
            fields = sorted({key for row in records for key in row})
            csv_rows = []
            for row in records:
                csv_rows.append({
                    key: json.dumps(value) if isinstance(value, (dict, list)) else value
                    for key, value in row.items()
                })
            for field, replacement in (
                ("exception_type", "cross_source_ohlcv_conflict"),
                ("symbol", "OTHER"),
                ("trade_date", "2026-01-02"),
                ("source_repository", "attacker/other-repository"),
            ):
                with self.subTest(field=field):
                    changed = [dict(row) for row in csv_rows]
                    changed[0][field] = replacement
                    with cp.open("w", encoding="utf-8", newline="") as stream:
                        writer = csv.DictWriter(stream, fieldnames=fields)
                        writer.writeheader()
                        writer.writerows(changed)
                    errors = validate(jp, cp)
                    self.assertTrue(
                        any(f"JSON/CSV {field} mismatch" in error for error in errors),
                        errors,
                    )


if __name__ == "__main__":
    unittest.main()
