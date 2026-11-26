# Canonical evidence to scanner feature bridge

The build_canonical_feature_snapshot function is the only supported bridge from bronze evidence into the descriptive feature pipeline.

- Revalidates the pinned source registry, hash-chained promotion ledger, reviewer HMAC attestation, source policy, row identity, raw payload digest and point-in-time availability.
- Only accepted promotions reach build_feature_snapshot; bronze/provisional rows and secondary-source fallback are never supplied.
- Accepted, signed revocations supersede earlier promotions. Rejected or unsigned revocations do not change canonical state.
- OHLCV, index, market-summary and floorsheet promotions additionally require an exchange_finality=passed attestation before canonical finality is emitted.
- The session calendar is loaded from a server-side evidence CSV. Only explicitly verified-open dates whose retrieval and verification timestamps are no later than decision time are passed downstream.
- Missing canonical rows or calendar evidence returns UNKNOWN / PRESERVE_CAPITAL. The bridge never authorizes BUY and always marks production source claims false.

This is an integration seam, not proof that any live NEPSE source is activated. The runtime source registry remains empty until independently reviewed source policies and reviewer keys are provisioned.
