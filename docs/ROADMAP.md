# Roadmap

## Phase 0 — repository foundation
- [x] Private repository and project documentation
- [x] FastAPI health, CSV ingestion, history and scan endpoints
- [x] Basic OHLCV validation and audit metadata
- [ ] Persistent database and migrations
- [x] Automated tests and CI (20 backend tests passed on 2026-11-23)

## Phase 1 — verified data
- [x] Public Hugging Face dataset inventory with measured file/date/size coverage
- [x] Bounded, resumable downloads with size and published SHA-256 verification
- [x] Daily floorsheet and sector-index CSV/CSV.GZ normalizers with quarantine and independent audit reports
- [x] One-session real-data smoke test (2024-01-02); this is parser validation, not full-history validation
- [x] Bounded Parquet schema/row inspection for all 306 inventoried files
- [ ] Download, normalize and audit the complete 603-file floorsheet and 6,429-file index archive
- [ ] Stage and validate the Kaggle legacy archive using owner-configured credentials
- [ ] Normalize Parquet EOD/floorsheet/broker-flow tables into canonical silver datasets
- [ ] Confirm legal/technical access to each NEPSE data source
- [ ] Reconcile daily OHLCV against an authoritative source
- [ ] Detect stale, missing and conflicting records using a verified trading calendar
- [ ] Corporate-action ledger and adjusted/unadjusted price separation

## Phase 2 — research engine
- [ ] Formalize and test SMC/Wyckoff/VSA/IPDA definitions
- [ ] Add broker/floorsheet data only after provenance and coverage validation
- [ ] Add explainable scoring and confidence calibration
- [ ] Historical walk-forward evaluation; avoid look-ahead bias
- [ ] Integrate and validate the complete 309-stock universe

## Phase 3 — product
- [ ] Persistent database and migrations
- [ ] Web dashboard and charting
- [ ] Android client
- [ ] Authentication, authorization and secret management
- [ ] Private deployment, backups, monitoring and audit logs
- [ ] Scheduled scans only after data quality gates pass

Automated trading is out of scope for this project foundation.

See [PIPELINE_STATUS_2026-11-23.md](PIPELINE_STATUS_2026-11-23.md) for measured evidence, known limitations and the next acceptance sequence.
