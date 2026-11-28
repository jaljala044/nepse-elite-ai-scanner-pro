# Steps 270–279: trusted reconciliation integration

1. Load the reviewed publisher registry at the decision timestamp.
2. Load the separately reviewed per-source-class freshness policy.
3. Validate every observation against publisher identity and approved host.
4. Exclude unknown, unapproved, stale, future and unconfigured evidence.
5. Map reviewed publisher IDs to reviewed ownership-group IDs before reconciliation.
6. Count related publisher brands once, preventing false independent corroboration.
7. Preserve conflicting sector claims as withheld outcomes.
8. Add a readiness adapter reporting missing registry/policy without leaking secrets.
9. Keep the integration research-only and recommendation-neutral.
10. Add end-to-end tests for grouping, host mismatch, freshness, conflicts and fail-closed behavior.

## Runtime boundary
This is an integration adapter plus read-only readiness diagnostics. It does not populate registry/policy files, prove legal ownership, or establish official NEPSE membership. The API runtime must explicitly configure server-owned registry and freshness-policy paths and a protected HMAC key before research assessment can be enabled. No client request can provide or override these trust settings. Production recommendations remain disabled.
