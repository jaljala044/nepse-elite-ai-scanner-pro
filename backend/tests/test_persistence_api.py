import hashlib
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main
from app.storage import SQLiteStore

HEADER = b"symbol,date,open,high,low,close,volume\n"
FIRST = b"RHGCL,2026-11-19,252.10,259.50,252.10,258.00,9054\n"
NEXT = b"RHGCL,2026-11-20,258.00,264.70,254.00,254.20,18724\n"
CHANGED = b"RHGCL,2026-11-19,252.10,259.50,252.10,256.00,4216\n"


class PersistenceAPITest(unittest.TestCase):
    def setUp(self):
        temp = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(temp) / "instance" / "prices.sqlite3"
        self.enterContext(patch.object(main, "store", SQLiteStore(self.database)))

    @staticmethod
    def ingest(client, rows, source="staging_sample"):
        return client.post(
            "/v1/ingest/csv",
            files={"file": ("prices.csv", HEADER + rows)},
            headers={"X-Source-Label": source},
        )

    def test_ingest_persists_across_startup_and_replay_is_idempotent(self):
        with TestClient(main.app) as client:
            self.assertEqual(client.get("/ready").json(), {"status": "ready"})
            first = self.ingest(client, FIRST + NEXT)
            self.assertEqual(first.status_code, 200)
            audit = first.json()
            self.assertEqual(audit["sha256"], hashlib.sha256(HEADER + FIRST + NEXT).hexdigest())
            self.assertEqual(audit["rows_accepted"], 2)
            self.assertEqual(audit["latest_session"], "2026-11-20")

        with patch.object(main, "store", SQLiteStore(self.database)), TestClient(main.app) as client:
            self.assertEqual(self.ingest(client, FIRST + NEXT).json(), audit)
            self.assertEqual(client.get("/v1/imports").json(), {"imports": [audit]})
            self.assertEqual(client.get("/v1/symbols").json(), {"symbols": ["RHGCL"], "count": 1})
            candles = client.get("/v1/data/rhgcl").json()["rows"]
            self.assertEqual([r["date"] for r in candles], ["2026-11-19", "2026-11-20"])
            scan = client.post(
                "/v1/scan", json={"symbols": ["rhgcl"], "as_of": "2026-11-19"}
            ).json()
            self.assertEqual(scan["mode"], "research_only")
            self.assertEqual(scan["results"][0]["observations"], 1)
            self.assertEqual(scan["results"][0]["as_of"], "2026-11-19")
            self.assertEqual(client.get("/v1/data/unknown").status_code, 404)

    def test_conflict_rolls_back_new_rows_and_import_history(self):
        with TestClient(main.app) as client:
            self.assertEqual(self.ingest(client, FIRST).status_code, 200)
            conflict = self.ingest(client, NEXT + CHANGED, "other_source")
            self.assertEqual(conflict.status_code, 409)
            self.assertIn("RHGCL on 2026-11-19", conflict.json()["detail"])
            candles = client.get("/v1/data/RHGCL").json()["rows"]
            self.assertEqual(len(candles), 1)
            self.assertEqual(candles[0]["close"], 258)
            self.assertEqual(len(client.get("/v1/imports").json()["imports"]), 1)

    def test_invalid_rows_and_upload_limit_leave_store_empty(self):
        with TestClient(main.app) as client:
            for row in (
                FIRST.replace(b"9054", b"4.5"),
                FIRST.replace(b"9054", b"9223372036854775808"),
                FIRST.replace(b"252.10", b"NaN", 1),
                FIRST.replace(b"258.00", b"300.00"),
            ):
                with self.subTest(row=row):
                    self.assertEqual(self.ingest(client, row).status_code, 422)
            with patch.object(main, "MAX_CSV_BYTES", len(HEADER) + len(FIRST) - 1):
                self.assertEqual(self.ingest(client, FIRST).status_code, 413)
            self.assertEqual(client.get("/v1/symbols").json()["count"], 0)
            self.assertEqual(client.get("/v1/imports").json()["imports"], [])

    def test_identical_rows_in_a_file_count_once(self):
        with TestClient(main.app) as client:
            response = self.ingest(client, FIRST + FIRST)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["rows_accepted"], 1)
            self.assertEqual(len(client.get("/v1/data/RHGCL").json()["rows"]), 1)

    def test_readiness_reports_missing_schema(self):
        with TestClient(main.app) as client:
            with patch.object(main, "store", SQLiteStore(self.database.with_name("missing.sqlite3"))):
                self.assertEqual(client.get("/health").status_code, 200)
                self.assertEqual(client.get("/ready").status_code, 503)

    def test_future_schema_is_rejected_without_reset(self):
        with TestClient(main.app):
            pass
        with sqlite3.connect(self.database) as conn:
            conn.execute("PRAGMA user_version=99")
        self.assertFalse(main.store.is_ready())
        with self.assertRaisesRegex(RuntimeError, "Unsupported database schema version: 99"):
            main.store.initialize()
        with sqlite3.connect(self.database) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 99)

    def test_concurrent_startup_and_retries_share_one_import(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            def worker(_):
                store = SQLiteStore(self.database)
                store.initialize()
                return store.store_rows(HEADER + FIRST, "staging_sample")

            results = list(pool.map(worker, range(8)))

        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(len(main.store.recent_imports()), 1)
        self.assertEqual(len(main.store.history("RHGCL")), 1)
