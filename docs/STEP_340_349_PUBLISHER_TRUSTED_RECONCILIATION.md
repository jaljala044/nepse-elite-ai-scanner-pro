# Steps 340–349 — Publisher-trusted cross-source quality reconciliation

## Ten implementation items

1. Load the existing server-owned HMAC publisher/domain/ownership-group registry.
2. Load the explicit server-owned evidence freshness policy.
3. Require both configurations before observations can contribute to corroboration.
4. Require each market observation to identify a publisher ID, source URL, source class and capture timestamp.
5. Match the observation hostname against the reviewed publisher's approved hosts.
6. Reject unknown publishers, unapproved hosts, missing freshness limits, stale captures and future captures.
7. Map accepted publisher brands to reviewed ownership-group IDs before cross-source reconciliation.
8. Count each ownership group once; two brands in one group cannot satisfy independent corroboration.
9. Preserve a separate untrusted source comparison for audit while only trusted ownership-group observations influence the quality score.
10. Expose publisher registry/freshness readiness and test independent groups, shared groups, conflicts and missing trust.

## Runtime configuration

Reuses the existing server-side configuration:
- `NEPSE_PUBLISHER_TRUST_REGISTRY_PATH`
- `NEPSE_EVIDENCE_FRESHNESS_POLICY_PATH`
- `NEPSE_PUBLISHER_TRUST_HMAC_KEY`

## Evidence and safety boundaries

The source record must carry `publisher_id`, `source_url`, `source_class` and `captured_at`; missing fields are not inferred from a source label. The registry's reviewed ownership groups are an internal research classification, not legal proof of beneficial ownership. HMAC is an integrity control, not proof of official NEPSE status. Conflicts remain visible and no majority value is promoted. All observations remain provisional; canonical OHLCV/floorsheet admission and recommendations remain disabled.
