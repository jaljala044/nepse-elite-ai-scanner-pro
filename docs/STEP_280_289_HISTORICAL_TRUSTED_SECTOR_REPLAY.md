# Steps 280–289: historical trusted sector replay

1. Connect append-only persisted sector timeline events to publisher trust assessment.
2. Apply the registry snapshot visible at the historical decision cutoff.
3. Apply the explicit freshness policy visible at that cutoff; reject future-dated snapshots.
4. Require source URLs so publisher hostnames can be checked against the reviewed registry.
5. Exclude unknown publishers, unapproved hosts, stale observations and missing host provenance.
6. Map accepted publisher brands to reviewed ownership groups before timeline corroboration.
7. Report publisher registry/policy fingerprints and cutoff-specific eligibility for audit.
8. Report publisher ownership-group changes between supplied decision cutoffs as review-required.
9. Add per-sector symbol coverage and missing capture-session diagnostics.
10. Expose historical replay readiness and add regression tests for trusted persistent replay.

## Important limitations
- The implementation supports explicit server-side maps from exact decision-time cutoffs to archived signed registry and freshness-policy paths. It does not automatically discover archive files; a snapshot generated after a historical cutoff is rejected rather than backfilled. Publisher ownership-group changes across explicitly selected snapshots are flagged for review.
- Historical events without a source URL are excluded because host trust cannot be checked.
- Expected symbols and capture sessions are operator-supplied expectations, not authoritative exchange calendars or official sector membership.
- No real publisher registry, freshness SLA, or timeline database is provisioned by this change.
- All outputs remain provisional/research-only. Production admission and recommendations remain disabled.
