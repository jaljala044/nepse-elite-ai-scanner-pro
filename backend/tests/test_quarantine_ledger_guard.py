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
