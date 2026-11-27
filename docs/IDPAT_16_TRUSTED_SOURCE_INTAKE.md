# IDPAT-16 — Trusted NEPSE source intake

- Adds a trusted-registry intake adapter over immutable raw capture and canonical CSV admission.
- Requires an approved registry record, independently reviewed publisher signature status, rights, source validation, finality, exact source identity/URI/publisher match and optional pinned SHA-256.
- On success, delegates content-addressed capture and point-in-time OHLCV admission to the existing validators.
- No HTTP, scraping, credentials or external source retrieval is implemented.
- Publisher authentication and registry governance remain responsibilities of the trusted operator; hash integrity alone does not authenticate a publisher.
- All outputs remain research-only; production promotion is always false.
- Synthetic tests cover fail-closed registry and digest mismatches only. No real NEPSE data is claimed.
