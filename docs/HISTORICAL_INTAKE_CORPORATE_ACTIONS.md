# Historical File Intake and Corporate-Action Reconciliation — Steps 8 and 9

## Step 8 — Controlled historical file intake
\`app.nepse_historical_intake.ingest_captured_csv\` accepts exact provider-supplied CSV bytes, calculates SHA-256 from those bytes, parses required dataset columns and passes the resulting rows and provenance envelope through the existing strict NEPSE adapter. Capture time must be timezone-aware and no later than the decision cutoff.

This is an import/verification boundary, not a web scraper or live feed. Publisher identity, source rights, finality and registry approval remain externally governed assertions. A byte hash detects later payload changes but does not authenticate the publisher or prove data accuracy.

## Step 9 — Corporate-action reconciliation
\`app.nepse_corporate_action_reconciliation.reconcile_corporate_actions\` requires two distinct source IDs and publisher names to agree on security, action type, announcement/effective dates, status and explicit price/volume adjustment factors. Disagreements, missing sources, unapproved rights, invalid hashes and future evidence are withheld.

\`apply_reconciled_adjustments\` applies agreed factors only to bars strictly before the effective date. It preserves recorded turnover and does not infer theoretical ex-rights prices or factors. Only events available by the requested decision cutoff may be applied.

## Current readiness
- No live provider downloads or credentials were added.
- No historical NEPSE dataset was acquired in this change.
- Independent publisher identity and source rights still need governance review.
- Adjustment factors must be provided and reconciled; unsupported events remain excluded.
- Research only; no strategy performance claim and no production enablement.
