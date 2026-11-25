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
            fields = list(records[0])
            with cp.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for row in records:
                    writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v
                                     for k, v in row.items()})
            self.assertTrue(any("not quarantined_unresolved" in e for e in validate(jp, cp)))


if __name__ == "__main__":
    unittest.main()
