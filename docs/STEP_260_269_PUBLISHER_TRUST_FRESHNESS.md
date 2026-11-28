# Steps 260–269: publisher trust and evidence freshness

1. Add a server-owned publisher registry with reviewed entries.
2. Bind publisher IDs to approved hostnames; observation URLs must match.
3. Record reviewed ownership-group IDs so related brands count as one source.
4. Require HMAC-protected reviewer attestations and registry signatures.
5. Reject duplicate IDs, invalid hosts, future registry versions and bad signatures.
6. Add a separate reviewed freshness policy with per-source-class maximum ages.
7. Do not invent refresh SLAs: missing policy means freshness is unconfigured.
8. Exclude unapproved hosts, unknown publishers, stale and future-dated captures.
9. Count independent ownership groups, not raw publisher ID strings.
10. Add synthetic tests and keep all outputs research-only.

## Trust boundaries
The HMAC proves integrity relative to the configured internal key; it does not prove legal ownership, beneficial ownership, publisher authenticity, or official NEPSE status. Ownership-group assignments require independent human review. A reviewed registry and policy are not populated by this change. Until configured, corroboration and freshness remain unavailable. No scanner recommendation or production admission is enabled.
