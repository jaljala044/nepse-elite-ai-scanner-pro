# Issue #20 — same-day session finality

The lifecycle evaluator now requires explicit, point-in-time session evidence. When an expected session is on the Kathmandu-local decision date, a separate primary-source finality record must:

- pass the retained-payload/base64/SHA-256 and rights checks;
- bind the exact session date, classification and `complete` finality status;
- provide a `finalized_at` timestamp no later than the decision cutoff and on the same Kathmandu-local date.

Absent, mismatched, late or cross-date finality keeps the session unknown and blocks exploratory eligibility. The archive quarantine guard remains intact. Tests use synthetic fixtures only; this does not certify live NEPSE sessions or enable production promotion.
