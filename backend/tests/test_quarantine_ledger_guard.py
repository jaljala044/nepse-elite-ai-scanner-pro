import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from app.quarantine_guard import quarantine_keys, reject_quarantined_history

class LedgerGuardTests(unittest.TestCase):
    def _ledger(self, day):
        return json.dumps({
            "schema_version": "1.0",
            "source_audit": {
                "generated_at_utc": "2026-11-27T00:00:00Z",
                "source_audit_report_sha256": "c" * 64,
                "repositories": {
                    "jaljala044/nepse-smc-data": {"commit_sha": "a" * 40},
                    "jaljala044/nepse-history-starter": {"commit_sha": "b" * 40},
                },
            },
            "counts": {"total_exception_records": 1},
            "exceptions": [{
                "exception_id": "e1", "symbol": "AAA",
                "trade_date": day, "disposition": "quarantined_unresolved"
            }]
        }).encode()

    def test_pinned_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            raw = self._ledger("2025-07-28")
            path.write_bytes(raw)
            keys = quarantine_keys(path, hashlib.sha256(raw).hexdigest())
            self.assertEqual(keys, {("AAA", "2025-07-28")})
            with self.assertRaisesRegex(ValueError, "quarantined"):
                reject_quarantined_history([{"date": "2025-07-28"}], "aaa", keys)
            reject_quarantined_history([{"date": "2025-07-29"}], "AAA", keys)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                quarantine_keys(path, "0" * 64)

    def test_ledger_rejects_non_object_document_and_malformed_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            for raw in (b"[]", b"null", b"42"):
                path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, "invalid quarantine ledger schema"):
                    quarantine_keys(path, hashlib.sha256(raw).hexdigest())
            raw = self._ledger("2025-07-28")
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "invalid quarantine ledger digest"):
                quarantine_keys(path, "bad")
            self.assertEqual(quarantine_keys(path, hashlib.sha256(raw).hexdigest().upper()),
                             {("AAA", "2025-07-28")})

    def test_ledger_requires_exact_source_repository_set_and_integer_count(self):
        for mutate in ("repository", "boolean_count"):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.json"
                ledger = json.loads(self._ledger("2025-07-28"))
                if mutate == "repository":
                    ledger["source_audit"]["repositories"] = {
                        "attacker.example/other": {"commit_sha": "a" * 40},
                        "jaljala044/nepse-history-starter": {"commit_sha": "b" * 40},
                    }
                else:
                    ledger["counts"]["total_exception_records"] = True
                raw = json.dumps(ledger).encode()
                path.write_bytes(raw)
                expected = "source audit" if mutate == "repository" else "count mismatch"
                with self.assertRaisesRegex(ValueError, expected):
                    quarantine_keys(path, hashlib.sha256(raw).hexdigest())

    def test_noncanonical_ledger_dates_are_rejected(self):
        for day in ("20250728", "2025-7-28", "2025-07-28T00:00:00"):
            with self.subTest(day=day), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.json"
                raw = self._ledger(day)
                path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, "invalid runtime quarantine ledger record"):
                    quarantine_keys(path, hashlib.sha256(raw).hexdigest())

    def test_ledger_rejects_non_object_rows_and_blank_identity(self):
        for row in (None, [], {"exception_id": "e1", "symbol": " ", "trade_date": "2025-07-28", "disposition": "quarantined"}):
            with self.subTest(row=row), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.json"
                raw = json.dumps({"schema_version": "1.0",
                    "source_audit":{"generated_at_utc":"2026-11-27T00:00:00Z","source_audit_report_sha256":"c"*64,
                        "repositories":{"jaljala044/nepse-smc-data":{"commit_sha":"a"*40},
                                        "jaljala044/nepse-history-starter":{"commit_sha":"b"*40}}},
                    "counts": {"total_exception_records": 1}, "exceptions": [row]}).encode()
                path.write_bytes(raw)
                with self.assertRaisesRegex(ValueError, "invalid runtime quarantine ledger record"):
                    quarantine_keys(path, hashlib.sha256(raw).hexdigest())

    def test_real_runtime_configuration_and_cross_engine_rejection(self):
        import os
        from unittest.mock import patch
        from app.quarantine_guard import runtime_quarantine_keys
        from app.scenario_validation import validate_binary_forecasts
        from app.walk_forward_report import build_walk_forward_report
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            raw = self._ledger("2025-07-28")
            path.write_bytes(raw)
            env = {"NEPSE_QUARANTINE_LEDGER": str(path), "NEPSE_QUARANTINE_LEDGER_SHA256": hashlib.sha256(raw).hexdigest(), "NEPSE_QUARANTINE_SOURCE_COMMITS": json.dumps({"jaljala044/nepse-smc-data":"a"*40,"jaljala044/nepse-history-starter":"b"*40})}
            row = {"symbol": "AAA", "constituent_sessions": ["2025-07-28"], "observation_date": "2025-07-28", "actual": 1, "probability": 0.8}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(runtime_quarantine_keys(required=True), frozenset({("AAA", "2025-07-28")}))
                with self.assertRaisesRegex(ValueError, "quarantined forecast constituent"):
                    validate_binary_forecasts([1], [0.8], lineage=[row], require_ledger=True)
                with self.assertRaisesRegex(ValueError, "quarantined forecast constituent"):
                    build_walk_forward_report([row], 1, 1, require_ledger=True)
                path.write_bytes(raw + b" ")
                with self.assertRaisesRegex(ValueError, "invalid runtime quarantine ledger"):
                    runtime_quarantine_keys(required=True)
            with patch.dict(os.environ, {"NEPSE_QUARANTINE_LEDGER": str(path)}, clear=True):
                with self.assertRaisesRegex(ValueError, "pinned quarantine ledger required"):
                    runtime_quarantine_keys()
            with patch.dict(os.environ, {}, clear=True):
                self.assertIsNone(runtime_quarantine_keys())
                with self.assertRaisesRegex(ValueError, "pinned quarantine ledger required"):
                    runtime_quarantine_keys(required=True)

    def test_deployment_flag_requires_ledger_for_all_runtime_consumers(self):
        import os
        from unittest.mock import patch
        from app.quarantine_guard import runtime_quarantine_keys
        from app.database import load_state, persist_import
        from app.feature_pipeline import build_feature_snapshot
        from app.scenario_validation import validate_binary_forecasts
        from app.walk_forward_report import build_walk_forward_report
        with patch.dict(os.environ, {"NEPSE_REQUIRE_QUARANTINE_LEDGER": "1"}, clear=True):
            for consumer in (
                lambda: runtime_quarantine_keys(),
                lambda: load_state(),
                lambda: persist_import("fixture", {}),
                lambda: build_feature_snapshot([], "2026-11-27T12:00:00Z"),
                lambda: validate_binary_forecasts([], []),
                lambda: build_walk_forward_report([], 1, 1),
            ):
                with self.subTest(consumer=consumer):
                    with self.assertRaisesRegex(ValueError, "pinned quarantine ledger required"):
                        consumer()
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "ledger.json"
                raw = self._ledger("2025-07-28")
                path.write_bytes(raw)
                with patch.dict(os.environ, {"NEPSE_QUARANTINE_LEDGER": str(path), "NEPSE_QUARANTINE_LEDGER_SHA256": hashlib.sha256(raw).hexdigest(), "NEPSE_QUARANTINE_SOURCE_COMMITS": json.dumps({"jaljala044/nepse-smc-data":"a"*40,"jaljala044/nepse-history-starter":"b"*40})}):
                    self.assertEqual(runtime_quarantine_keys(), frozenset({("AAA", "2025-07-28")}))
                    path.write_bytes(raw + b" ")
                    with self.assertRaisesRegex(ValueError, "invalid runtime quarantine ledger"):
                        runtime_quarantine_keys()


    def test_valid_empty_ledger_is_distinct_from_missing_ledger(self):
        import os
        from unittest.mock import patch
        from app.quarantine_guard import runtime_quarantine_keys
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.json"
            empty = {
                "schema_version":"1.0",
                "source_audit":{"generated_at_utc":"2026-11-27T00:00:00Z",
                    "source_audit_report_sha256":"c"*64,
                    "repositories":{"jaljala044/nepse-smc-data":{"commit_sha":"a"*40},
                                    "jaljala044/nepse-history-starter":{"commit_sha":"b"*40}}},
                "counts":{"total_exception_records":0},"exceptions":[],
            }
            raw = json.dumps(empty).encode()
            path.write_bytes(raw)
            env = {"NEPSE_REQUIRE_QUARANTINE_LEDGER":"1","NEPSE_QUARANTINE_LEDGER":str(path),
                "NEPSE_QUARANTINE_LEDGER_SHA256":hashlib.sha256(raw).hexdigest(),
                "NEPSE_QUARANTINE_SOURCE_COMMITS":json.dumps({"jaljala044/nepse-smc-data":"a"*40,
                    "jaljala044/nepse-history-starter":"b"*40})}
            with patch.dict(os.environ,env,clear=True):
                self.assertEqual(runtime_quarantine_keys(),frozenset())
                path.write_bytes(raw+b" ")
                with self.assertRaisesRegex(ValueError,"invalid runtime quarantine ledger"):
                    runtime_quarantine_keys()

    def test_required_runtime_rejects_missing_partial_and_stale_source_pins(self):
        import os
        from unittest.mock import patch
        from app.quarantine_guard import runtime_quarantine_keys
        with patch.dict(os.environ,{"NEPSE_REQUIRE_QUARANTINE_LEDGER":"1"},clear=True):
            with self.assertRaisesRegex(ValueError,"pinned quarantine ledger required"):
                runtime_quarantine_keys()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"ledger.json"
            raw=self._ledger("2025-07-28")
            path.write_bytes(raw)
            base={"NEPSE_REQUIRE_QUARANTINE_LEDGER":"1","NEPSE_QUARANTINE_LEDGER":str(path),
                "NEPSE_QUARANTINE_LEDGER_SHA256":hashlib.sha256(raw).hexdigest()}
            with patch.dict(os.environ,base,clear=True):
                with self.assertRaisesRegex(ValueError,"pinned quarantine source commits required"):
                    runtime_quarantine_keys()
            with patch.dict(os.environ,{**base,"NEPSE_QUARANTINE_SOURCE_COMMITS":json.dumps({"jaljala044/nepse-smc-data":"a"*40,"jaljala044/nepse-history-starter":"b"*40})},clear=True):
                path.write_bytes(b"")
                with self.assertRaisesRegex(ValueError,"invalid runtime quarantine ledger"):
                    runtime_quarantine_keys()
                path.write_bytes(raw)
            stale={"NEPSE_QUARANTINE_SOURCE_COMMITS":json.dumps({"jaljala044/nepse-smc-data":"d"*40,
                "jaljala044/nepse-history-starter":"b"*40})}
            with patch.dict(os.environ,{**base,**stale},clear=True):
                with self.assertRaisesRegex(ValueError,"invalid runtime quarantine ledger"):
                    runtime_quarantine_keys()

    def test_startup_validation_blocks_missing_ledger(self):
        import os
        from unittest.mock import patch
        from app.main import validate_quarantine_configuration
        with patch.dict(os.environ,{"NEPSE_REQUIRE_QUARANTINE_LEDGER":"1"},clear=True):
            with self.assertRaisesRegex(ValueError,"pinned quarantine ledger required"):
                validate_quarantine_configuration()

    def test_missing_blocked_candle_inside_window(self):
        from app.quarantine_guard import filter_quarantined_feature_rows
        keys = frozenset({("AAA", "2025-07-28")})
        rows = [{"symbol":"AAA","date":day,"record_type":"ohlcv"}
                for day in ("2025-07-27","2025-07-29")]
        with self.assertRaisesRegex(ValueError,"quarantined"):
            reject_quarantined_history(rows,"AAA",keys)
        self.assertEqual(filter_quarantined_feature_rows(rows,keys),[])
        unaffected = {"symbol":"BBB","date":"2025-07-29","record_type":"ohlcv"}
        self.assertEqual(filter_quarantined_feature_rows(rows+[unaffected],keys),[unaffected])
        reject_quarantined_history(rows[1:],"AAA",keys)
        self.assertEqual(filter_quarantined_feature_rows(rows[1:],keys),rows[1:])

    def test_database_withholds_missing_blocked_candle_without_deletion(self):
        import os
        from unittest.mock import patch
        from app.database import persist_import, load_state, connect
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"ledger.json"
            raw = self._ledger("2025-07-28")
            path.write_bytes(raw)
            env = {"NEPSE_API_DATABASE":str(Path(tmp)/"test.duckdb"),
                   "NEPSE_QUARANTINE_LEDGER":str(path),
                   "NEPSE_QUARANTINE_LEDGER_SHA256":hashlib.sha256(raw).hexdigest()}
            def bar(day):
                return {"date":day,"open":10,"high":11,"low":9,"close":10,"volume":100}
            with patch.dict(os.environ,env,clear=True):
                persist_import("fixture",{"AAA":[bar("2025-07-27"),bar("2025-07-29")],
                                          "BBB":[bar("2025-07-29")]})
                data, _ = load_state()
                self.assertNotIn("AAA",data)
                self.assertIn("BBB",data)
                con = connect()
                try:
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM daily_ohlcv").fetchone()[0],3)
                finally:
                    con.close()


    def test_forecast_engines_reject_omitted_blocked_session(self):
        from unittest.mock import patch
        from app.scenario_validation import validate_binary_forecasts
        from app.walk_forward_report import build_walk_forward_report
        keys = frozenset({("AAA", "2025-07-28")})
        row = {"symbol":"AAA","constituent_sessions":["2025-07-27","2025-07-29"],
               "observation_date":"2025-07-29","actual":1,"probability":0.8}
        with patch("app.scenario_validation.runtime_quarantine_keys",return_value=keys), patch("app.walk_forward_report.runtime_quarantine_keys",return_value=keys):
            with self.assertRaisesRegex(ValueError,"quarantined forecast constituent"):
                validate_binary_forecasts([1],[0.8],lineage=[row])
            with self.assertRaisesRegex(ValueError,"quarantined forecast constituent"):
                build_walk_forward_report([row],1,1)
            clean = dict(row,symbol="BBB")
            self.assertEqual(validate_binary_forecasts([1],[0.8],lineage=[clean])["sample_count"],1)
            self.assertEqual(build_walk_forward_report([clean],1,1)["status"],"insufficient_sample")


if __name__ == "__main__":
    unittest.main()
