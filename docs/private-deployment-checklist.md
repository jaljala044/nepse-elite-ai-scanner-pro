# Private research deployment gate

Do not publish the service directly on the internet. Build from repository root with Dockerfile.research. Bind the container only to a private proxy network, or publish to loopback for local testing. Configure a trusted OIDC authentication proxy that strips client-supplied X-NEPSE-Subject and X-NEPSE-Proxy-Secret headers and injects the verified subject and a server-side random secret of at least 32 characters. Never expose that secret to browser JavaScript. Use TLS, secure cookies, CSRF controls, rate limiting, and explicit admin subjects. Mount persistent private storage at /srv/private. Back up and test restore before service launch. Do not promote shared uploaded OHLCV to canonical data. All AI recommendations remain disabled.

Release blockers: successful backend CI, browser regression, independently audited proxy/authentication configuration, account isolation and migration, licensed data and complete evidence manifests, restore drill, security testing. No production deployment is claimed by this container definition.

## Required quarantine ledger
Mount the independently reviewed OHLCV exception ledger read-only at `/run/nepse/quarantine/ledger.json` (or override `NEPSE_QUARANTINE_LEDGER`). Supply all three runtime pins:
- `NEPSE_QUARANTINE_LEDGER_SHA256`: SHA-256 of the exact mounted ledger bytes.
- `NEPSE_QUARANTINE_SOURCE_COMMITS`: JSON object mapping the two source repository full names to the exact 40-character commits used by the deployed OHLCV archives, for example `{"jaljala044/nepse-smc-data":"<40-hex>","jaljala044/nepse-history-starter":"<40-hex>"}`.
- `NEPSE_QUARANTINE_LEDGER`: mounted read-only ledger path.

The image sets `NEPSE_REQUIRE_QUARANTINE_LEDGER=1`; startup fails before serving requests if any pin is missing, malformed, unreadable, mismatched, or stale against the deployed source commit pins. Runtime readers recheck the digest and source commits so replacement or mutation is rejected. A valid empty ledger is distinct from a missing ledger. The repository does not provide a production ledger mount or deploy-time source-commit pins; operators must provision and independently review them. A generated artifact alone does not establish authoritative coverage. Do not enable production backtesting or recommendations.
