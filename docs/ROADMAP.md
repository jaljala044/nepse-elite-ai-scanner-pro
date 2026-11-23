# Roadmap

## Phase 0 — repository foundation
- [x] Private repository and project documentation
- [x] FastAPI health, CSV ingestion, history and scan endpoints
- [x] Basic OHLCV validation and audit metadata
- [ ] Persistent database and migrations
- [ ] Automated tests and CI

## Phase 1 — verified data
- [ ] Confirm legal/technical access to each NEPSE data source
- [ ] Build source adapters with timestamps, session calendar and retry logic
- [ ] Reconcile daily OHLCV against an authoritative source
- [ ] Detect stale, missing and conflicting records

## Phase 2 — research engine
- [ ] Formalize and test SMC/Wyckoff/VSA definitions
- [ ] Add broker/floorsheet data only after provenance validation
- [ ] Add explainable scoring and confidence calibration
- [ ] Historical walk-forward evaluation; avoid look-ahead bias

## Phase 3 — product
- [ ] Web dashboard and charting
- [ ] Android client
- [ ] Authentication, authorization and secret management
- [ ] Private deployment, backups, monitoring and audit logs
- [ ] Scheduled scans only after data quality gates pass

Automated trading is out of scope for this project foundation.
