import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from app.quarantine_guard import quarantine_keys, reject_quarantined_history

class LedgerGuardTests(unittest.TestCase):
    def test_pinned_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            raw = json.dumps({"schema_version":"1.0","counts":{"total_exception_records":1},"exceptions":[{"exception_id":"e1","symbol":"AAA","trade_date":"2025-07-28","disposition":"quarantined_unresolved"}]}).encode()
            path.write_bytes(raw)
            keys = quarantine_keys(path, hashlib.sha256(raw).hexdigest())
            self.assertEqual(keys, {("AAA","2025-07-28")})
            with self.assertRaisesRegex(ValueError, "quarantined"):
                reject_quarantined_history([{"date":"2025-07-28"}], "aaa", keys)
            reject_quarantined_history([{"date":"2025-07-29"}], "AAA", keys)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                quarantine_keys(path, "0"*64)

    def test_real_runtime_configuration_and_cross_engine_rejection(self):
        import os
        from unittest.mock import patch
        from app.quarantine_guard import runtime_quarantine_keys
        from app.scenario_validation import validate_binary_forecasts
        from app.walk_forward_report import build_walk_forward_report
        from app.historical_segment_eligibility import evaluate_runtime_historical_segment
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            raw = json.dumps({"schema_version":"1.0","counts":{"total_exception_records":1},"exceptions":[{"exception_id":"e1","symbol":"AAA","trade_date":"2025-07-28","disposition":"quarantined_unresolved"}]}).encode()
            path.write_bytes(raw)
            env = {"NEPSE_QUARANTINE_LEDGER":str(path),"NEPSE_QUARANTINE_LEDGER_SHA256":hashlib.sha256(raw).hexdigest()}
            row = {"symbol":"AAA","constituent_sessions":["2025-07-28"],"observation_date":"2025-07-28","actual":1,"probability":0.8}
            with patch.dict(os.environ,env,clear=True):
                self.assertEqual(runtime_quarantine_keys(required=True),frozenset({("AAA","2025-07-28")}))
                with self.assertRaisesRegex(ValueError,"quarantined forecast constituent"):
                    validate_binary_forecasts([1],[0.8],lineage=[row],require_ledger=True)
                with self.assertRaisesRegex(ValueError,"quarantined forecast constituent"):
                    build_walk_forward_report([row],1,1,require_ledger=True)
                path.write_bytes(raw+b" ")
                with self.assertRaisesRegex(ValueError,"invalid runtime quarantine ledger"):
                    runtime_quarantine_keys(required=True)
                self.assertFalse(evaluate_runtime_historical_segment()["exploratory_replay_eligible"])
            with patch.dict(os.environ,{"NEPSE_QUARANTINE_LEDGER":str(path)},clear=True):
                with self.assertRaisesRegex(ValueError,"pinned quarantine ledger required"):
                    runtime_quarantine_keys()
            with patch.dict(os.environ,{},clear=True):
                self.assertIsNone(runtime_quarantine_keys())
                with self.assertRaisesRegex(ValueError,"pinned quarantine ledger required"):
                    runtime_quarantine_keys(required=True)
