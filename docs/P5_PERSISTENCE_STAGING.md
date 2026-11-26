# P5 private staging persistence

The research API uses a versioned SQLite database for uploaded OHLCV and its
import history. The process creates schema version 1 at startup. Rows held in
memory by an older process have no database to migrate. Re-import the original
CSV files to seed this database with their source labels.

For staging, mount a writable persistent volume and set `NEPSE_DB_PATH` to a
database file on that volume. The default for local runs is
`backend/instance/nepse.sqlite3`. Use one API replica with a local database
volume for this first deployment increment.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Process liveness and research-only mode |
| `GET /ready` | Confirms the database schema is current and readable |
| `POST /v1/ingest/csv` | Atomically stores candles and records the source, uploaded file hash and UTC import time |
| `GET /v1/imports` | Returns the most recent 100 accepted import records |

A byte-identical retry under the same source label returns the existing import
record. Identical candles from separate files share one symbol-date record.
When an import disagrees with a stored candle, the API returns HTTP 409 and
rolls back the batch. Resolve the discrepancy against dated evidence before
retrying. Use the file hash to identify the original upload.

Keep this staging API on private access. Authentication, backups and restore
drills, monitoring, and provider deployment acceptance remain P5 work before
public exposure or scan scheduling. The provider-confirmed current equity
reference is the [281-symbol manifest](../data/reference/nepse_active_equity_manifest_2026-11-26.csv).
Market-data acceptance and scanner validation continue under their respective
priorities.
