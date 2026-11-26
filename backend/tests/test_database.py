import os
import tempfile
import unittest
from pathlib import Path

from app.database import load_state, persist_import


class PersistentStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["NEPSE_API_DATABASE"] = str(Path(self.tmp.name) / "test.duckdb")

    def tearDown(self):
        os.environ.pop("NEPSE_API_DATABASE", None)
        self.tmp.cleanup()

    def test_round_trip_and_idempotent_same_bar(self):
        from datetime import date
        rows = {"NABIL": [{
            "date": date(2025, 1, 2), "open": 100.0, "high": 105.0,
            "low": 99.0, "close": 103.0, "volume": 1000
        }]}
        first = persist_import("fixture", rows)
        second = persist_import("fixture", rows)
        data, imports = load_state()
        self.assertEqual(data["NABIL"][0]["close"], 103.0)
        self.assertEqual(len(imports), 2)
        self.assertNotEqual(first["batch_id"], second["batch_id"])

    def test_conflicting_bar_is_rejected(self):
        from datetime import date
        base = {"date": date(2025, 1, 2), "open": 100.0, "high": 105.0,
                "low": 99.0, "close": 103.0, "volume": 1000}
        persist_import("fixture", {"NABIL": [base]})
        changed = {**base, "close": 104.0}
        with self.assertRaises(ValueError):
            persist_import("fixture", {"NABIL": [changed]})


if __name__ == "__main__":
    unittest.main()
