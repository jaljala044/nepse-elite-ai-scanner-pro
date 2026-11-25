# SamirWagle / MeroLagani-derived floorsheet source profile

## Pinned sample identity

- Repository: \`SamirWagle/Nepse-All-Scraper\`
- Pinned commit: \`e6160adc6bdf3d19562167388e3d9d4f645c455a\`
- File: \`data/floorsheet/floorsheet_2026-11-24.csv\`
- Observed exact headers: \`date,sn,contract_no,stock_symbol,buyer,seller,quantity,rate,amount\`
- Full source-specific audit: [MEROLAGANI_FLOORSHEET_CAPTURE_AUDIT_2026-11-24.md](MEROLAGANI_FLOORSHEET_CAPTURE_AUDIT_2026-11-24.md)

## Explicit canonical mapping

| Canonical field | Source header | Use |
|---|---|---|
| trade_date | \`date\` | Provisional only. The scraper writes Python \`date.today()\`; this is a capture-date field, not an exchange-supplied trade date |
| contract_id | \`contract_no\` | Preserve as string |
| symbol | \`stock_symbol\` | Preserve raw value; normalize only in canonical adapter |
| buyer_broker_code | \`buyer\` | Source broker code only; no identity inferred |
| seller_broker_code | \`seller\` | Source broker code only; no identity inferred |
| quantity | \`quantity\` | Parse as decimal/integer and reconcile |
| rate | \`rate\` | Parse as decimal and reconcile |
| amount | \`amount\` | Parse as decimal and reconcile |
| source-only | \`sn\` | Preserve in immutable raw payload; not part of the canonical contract |

The mapping is implemented in \`backend/app/floorsheet_source_profiles.py\` as \`samir_merolagani_capture_mapping()\`. The header review is \`review_samir_merolagani_headers()\`. The profile's evidence status is \`raw_header_observed_capture_date_semantics_unverified\`.

A successful parser fixture is not a source-identity or completeness pass. The 2026-11-24 file passed row syntax and row arithmetic checks, but its totals differ from MeroLagani's displayed daily totals. Keep \`source_specific_mapping_verified=false\` until source-specific date and control-total evidence is reconciled.

## Use guardrails

- Do not treat \`date\` alone as the exchange trade date.
- Do not infer a broker's legal entity or beneficial owner from a numeric code.
- Do not treat a daily CSV as complete solely because it has a date filename, unique contract numbers or valid arithmetic.
- Do not redistribute or use commercially until the source terms are clarified: the pinned README uses an “Educational” license badge and the pinned repository has no explicit LICENSE/COPYING file.
- Keep the file review-only; do not promote it to canonical or model-training data.
