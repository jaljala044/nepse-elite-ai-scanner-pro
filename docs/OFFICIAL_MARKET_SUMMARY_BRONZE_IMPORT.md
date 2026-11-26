# Official NEPSE market-summary bronze import

## Purpose

The importer takes the exact raw response archived by the official market-summary capture workflow and writes it into the append-only evidence store.

## Controls

- Rechecks source ID, HTTPS host, endpoint path, HTTP 200 status, exact byte length and SHA-256.
- Parses original response bytes, not a rewritten CSV.
- Preserves each source row and row number, fetch ID and raw-payload lineage.
- Uses the capture report retrieval timestamp as the conservative availability bound. The current report lacks request-start time; the importer does not invent it.
- Exact replays are idempotent; conflicting fetch content is rejected.
- Every row is forcibly review_required and provisional. Dates are claims, not verified exchange sessions.

## Run

From repository root:

    python backend/import_official_market_summary_to_bronze.py --capture-dir data/evidence/raw/nepse/market-summary-history/YYYY-MM-DD --storage-root /var/lib/nepse-evidence/raw --database /var/lib/nepse-evidence/evidence.duckdb

Run tests from backend:

    python -m unittest discover -s tests -p 'test_official_market_summary_bronze_import.py' -v

## Non-goals

This does not activate source policy, prove licensing, verify sessions, create OHLCV/index prices, or enable market-health/BUY signals. Source registry and reviewer promotion remain authoritative.
