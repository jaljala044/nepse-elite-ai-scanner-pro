# Trusted market dashboard deployment

Research only. No production recommendations.

## Deployment configuration
Set NEPSE_MARKET_ARTIFACT_ROOT to a read-only artifact directory and NEPSE_MARKET_ARTIFACT_REGISTRY to a deployment-owned JSON registry file. Do not allow browser users or uploaded files to write either. Keep registry and artifact permissions restricted to the reviewed ingestion service. Do not publish an example registry as real evidence.

Each module entry requires source_id, evidence_ids, payload_path, payload_sha256, as_of_date, available_at, status, coverage_ratio, source_validation_status, finality_status and session_calendar_id. Additional module-specific requirements are enforced by TrustedArtifactStore. Daily participation requires verified equity universe, expected_symbols and full coverage; index rotation requires expected_indices and complete aligned six-point trails. Sector rotation requires verified effective-dated membership and version. Price modules require corporate-action clearance.

## Acceptance
1. Acquire and independently validate authoritative source records and calendar; preserve immutable raw bytes and hashes.
2. Generate descriptive artifacts from verified records; independently check calculations against source.
3. Pin exact artifact hashes in the server registry; do not promote synthetic fixtures.
4. Confirm GET /v1/research/market-dashboard with no registry returns unavailable modules and disabled signals.
5. Verify actual deployment with reviewed artifacts, including stale, missing, tampered and mismatched-calendar cases.
6. Run frontend syntax/build checks and browser tests for ranking selector, chart point focus, hover, click, mobile overflow, API errors and empty evidence.
7. Require exact-head CI, merge compatibility and independent review of PR #294.
8. Keep historical data and circuit-breaker evidence gates open until authoritative records are obtained.

No deployment credentials, reviewed real artifact registry or authoritative index/sector evidence were obtained in this execution. Do not claim provisioning or production acceptance.

## Offline candidate generation
Run from the repository root:

```sh
python backend/generate_market_candidates.py --bundle /secure/reviewed-input.json --output-dir /secure/candidates
```

The normalized input bundle requires decision_time, calendar, universe, daily_rows, benchmark_rows, index_rows, expected_indices, stock_rows, expected_sector_members and sector_membership. The generator invokes the existing evidence-aware calculators and writes hash-addressed files plus a review-required manifest. It does not certify source authenticity, write a trusted registry, or grant admission. Keep candidate storage separate from deployed trusted artifacts. Review the raw-source evidence and exact session coverage before constructing any deployment registry.
