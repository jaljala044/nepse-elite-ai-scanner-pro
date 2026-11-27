# Private research deployment gate

Do not publish the service directly on the internet. Build from repository root with Dockerfile.research. Bind the container only to a private proxy network, or publish to loopback for local testing. Configure a trusted OIDC authentication proxy that strips client-supplied X-NEPSE-Subject and X-NEPSE-Proxy-Secret headers and injects the verified subject and a server-side random secret of at least 32 characters. Never expose that secret to browser JavaScript. Use TLS, secure cookies, CSRF controls, rate limiting, and explicit admin subjects. Mount persistent private storage at /srv/private. Back up and test restore before service launch. Do not promote shared uploaded OHLCV to canonical data. All AI recommendations remain disabled.

Release blockers: successful backend CI, browser regression, independently audited proxy/authentication configuration, account isolation and migration, licensed data and complete evidence manifests, restore drill, security testing. No production deployment is claimed by this container definition.

## Trusted Part 2 / broker dashboard artifacts

For `POST /v1/research/broker-dashboard/trusted`, provision the following
server-only environment settings in the private deployment:

- `NEPSE_TRUSTED_ARTIFACT_ROOT=/srv/private/trusted-artifacts`
- `NEPSE_TRUSTED_ARTIFACT_REGISTRY_PATH=/srv/private/trusted-artifacts/registry.json`
- `NEPSE_TRUSTED_ARTIFACT_MAX_AGE_DAYS=7`

The registry and immutable payload files must be mounted read-only to the API
container, writable only by the separately controlled ingestion/approval
process, and included in encrypted backup/restore drills. Do not place the
registry, payloads, or credentials in the repository, browser bundle, public
volume, request body, or logs. The registry path is deployment configuration;
the API caller cannot choose or replace it.

The trusted broker dashboard requires hash-pinned artifacts for market health,
index intelligence, effective-dated sector rotation, broker profiles and
broker-sector rotation. All five must pass source/finality, evidence, freshness,
point-in-time, coverage, corporate-action, sector-membership, broker-mapping,
same-session and same-calendar checks. Missing artifacts keep the dashboard
withheld. No live feed, registry or production readiness is implied until these
deployment operations are completed and independently reviewed.
