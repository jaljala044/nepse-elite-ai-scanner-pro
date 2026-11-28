import unittest
import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.quarantine_guard import (
    is_quarantined, quarantine_keys, quarantine_gap_symbols,
    runtime_quarantine_keys, reject_quarantined_history,
)
from app.database import persist_import
from app.broker_ingestion import IngestionReport
from app.broker_memory_promotion import promote_validated_batch, PromotionRejected

class DownstreamQuarantineTests(unittest.TestCase):

    def _ledger_file(self, root, exceptions=None):
        ledger = {
            "schema_version": "1.0",
            "counts": {"total_exception_records": len(exceptions or [])},
            "source_audit": {
                "source_audit_report_sha256": "a" * 64,
                "repositories": {
                    "jaljala044/nepse-smc-data": {"commit_sha": "1" * 40},
                    "jaljala044/nepse-history-starter": {"commit_sha": "2" * 40},
                },
            },
            "exceptions": exceptions or [],
        }
        path = Path(root) / "quarantine.json"
        raw = json.dumps(ledger, sort_keys=True).encode()
        path.write_bytes(raw)
        return path, hashlib.sha256(raw).hexdigest()

    def test_pinned_ledger_requires_exact_source_commit_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self._ledger_file(tmp, [{
                "exception_id": "ex-1", "symbol": "AAA",
                "trade_date": "2026-11-27", "disposition": "unresolved",
            }])
            expected = {
                "jaljala044/nepse-smc-data": "1" * 40,
                "jaljala044/nepse-history-starter": "2" * 40,
            }
            self.assertEqual(quarantine_keys(path, digest, expected_source_commits=expected),
                             frozenset({("AAA", "2026-11-27")}))
            expected["jaljala044/nepse-smc-data"] = "3" * 40
            with self.assertRaisesRegex(ValueError, "source commits stale"):
                quarantine_keys(path, digest, expected_source_commits=expected)

    def test_pinned_ledger_rejects_duplicate_exception_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = {"exception_id": "dup", "symbol": "AAA",
                   "trade_date": "2026-11-27", "disposition": "unresolved"}
            path, digest = self._ledger_file(tmp, [row, row])
            with self.assertRaisesRegex(ValueError, "invalid runtime quarantine"):
                quarantine_keys(path, digest)

    def test_pinned_ledger_rejects_noncanonical_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self._ledger_file(tmp, [{
                "exception_id": "ex-1", "symbol": "AAA",
                "trade_date": "2026-11-7", "disposition": "unresolved",
            }])
            with self.assertRaisesRegex(ValueError, "invalid runtime quarantine"):
                quarantine_keys(path, digest)

    def test_required_runtime_ledger_fails_closed_when_missing(self):
        with patch.dict(os.environ, {"NEPSE_REQUIRE_QUARANTINE_LEDGER": "1"}, clear=True):
            with self.assertRaisesRegex(ValueError, "pinned quarantine ledger required"):
                runtime_quarantine_keys()

    def test_ledger_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, digest = self._ledger_file(tmp)
            with self.assertRaisesRegex(ValueError, "ledger hash mismatch"):
                quarantine_keys(path, "0" * 64)

    def test_gap_inside_history_span_blocks_full_symbol(self):
        keys = frozenset({("AAA", "2026-11-27")})
        self.assertEqual(
            quarantine_gap_symbols([("AAA", "2026-11-26"), ("AAA", "2026-11-28")], keys),
            {"AAA"},
        )
        self.assertEqual(
            quarantine_gap_symbols([("BBB", "2026-11-26"), ("BBB", "2026-11-28")], keys),
            set(),
        )

    def test_history_rejects_quarantined_constituent_session(self):
        with self.assertRaisesRegex(ValueError, "quarantined"):
            reject_quarantined_history(
                [{"date": "2026-11-26"}, {"date": "2026-11-28"}],
                "AAA", frozenset({("AAA", "2026-11-27")}),
            )

    def test_markers(self):
        for row in ({"row_status":"quarantined"}, {"disposition":"quarantined_unresolved"}, {"quarantine_reasons":["conflict"]}, {"quarantined":True}, {"status":"QUARANTINED"}):
            with self.subTest(row=row):
                self.assertTrue(is_quarantined(row))
        self.assertFalse(is_quarantined({"status":"descriptive_only"}))

    def test_database_rejects_before_opening(self):
        with self.assertRaisesRegex(ValueError, "Quarantined"):
            persist_import("test", {"AAA":[{
                "date": "2026-11-27", "open": 10, "high": 12, "low": 9,
                "close": 11, "volume": 100, "row_status": "quarantined"
            }]})

    def test_database_rejects_quarantined_row_without_date_before_opening(self):
        with self.assertRaisesRegex(ValueError, "Quarantined or incomplete"):
            persist_import("test", {"AAA": [{"row_status": "quarantined"}]})

    def test_database_rejects_each_quarantine_marker_before_opening(self):
        markers = [
            {"row_status": "quarantined"},
            {"disposition": "quarantined_unresolved"},
            {"quarantine_status": "quarantined"},
            {"quarantined": True},
            {"quarantine_reasons": ["source_conflict"]},
        ]
        for marker in markers:
            with self.subTest(marker=marker):
                with self.assertRaisesRegex(ValueError, "Quarantined"):
                    persist_import("test", {"AAA": [{
                        "date": "2026-11-27", "open": 10, "high": 12, "low": 9,
                        "close": 11, "volume": 100, **marker,
                    }]})

    def test_broker_rejects_marked_row(self):
        report = IngestionReport("test", "complete", "1", accepted=[{"status":"descriptive_only","quarantined":True}])
        with self.assertRaisesRegex(PromotionRejected, "quarantined"):
            promote_validated_batch(report, None, as_of_date="2026-11-27")

    def test_broker_rejects_conflicts(self):
        report = IngestionReport("test", "complete", "1", accepted=[{}], conflicts=1)
        with self.assertRaisesRegex(PromotionRejected, "conflicts"):
            promote_validated_batch(report, None, as_of_date="2026-11-27")


    def test_database_withholds_whole_affected_history(self):
        import tempfile
        from pathlib import Path
        from datetime import date
        from unittest.mock import patch
        from app.database import load_state
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.database.database_path", return_value=Path(tmp)/"test.duckdb"):
                def bar(day):
                    return {"date":date.fromisoformat(day),"open":10,"high":12,"low":9,"close":11,"volume":100}
                with patch("app.database.runtime_quarantine_keys",return_value=None):
                    persist_import("fixture",{"AAA":[bar("2025-07-27"),bar("2025-07-28"),bar("2025-07-29")],"BBB":[bar("2025-07-29")]})
                with patch("app.database.runtime_quarantine_keys",return_value=frozenset({("AAA","2025-07-28")})):
                    data,_ = load_state()
                    self.assertEqual(set(data),{"BBB"})
                with patch("app.database.runtime_quarantine_keys",return_value=None):
                    self.assertEqual(len(load_state()[0]["AAA"]),3)
