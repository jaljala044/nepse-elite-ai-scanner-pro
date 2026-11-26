# Source trust candidate inventory — 2026-11-26

## Decision

The runtime source registry is intentionally empty. The current repository
evidence supports a small set of **candidate** source identities, but none is
ready to be activated for canonical market-data promotion. This inventory is
review guidance, not a trust registry and is never loaded by the runtime.

## Candidates found in the pinned source-object manifest

| Source ID | Publisher class | Existing evidence | Current decision |
|---|---|---|---|
| `NEPSE_OFFICIAL_HOLIDAY_API_2026` | Primary official NEPSE holiday API | Raw response retained at `data/evidence/raw/nepse/holiday-api-authenticated/2026-11-25/response-body.bin`; SHA-256 `dd1777e3c61623048e00dc170d860659b14b8821ffabff8338002ccafdb2ea8f`; retrieved 2026-11-25 13:13:17.600880 UTC; 41 unique holiday-date records | Strong official-source candidate for an explicit exchange-holiday evidence type, but the current registry record-type schema does not yet include a dedicated holiday type. Reuse terms remain unreviewed; not canonical-promoted. |
| `CDSC_CURRENT_CLEARING_MEMBER_DIRECTORY` | Official CDSC current directory | Raw CSV at `data/evidence/raw/cdsc/2026-11-25/clearing-members.csv`; SHA-256 `feb4597d66ad37dbc6f0ed2a9fd54c4fc7c04e67ce0b91c066bb9574c1c49de3`; 92 current clearing-member numbers | Official current directory only. It is not an effective-dated historical NEPSE broker-number/name register. Redistribution terms remain unreviewed; not canonical for historical broker observations. |
| `rajeevpaudel/nepse-history` | Community-maintained historical archive; README attributes upstream history to Merolagani | Pinned repository revision `927a15986012b31dba6c29c2266fb17f966a087b`; immutable Git blob and SHA-256 manifests; one staged 2026-11-19 floorsheet raw file and derived EOD OHLCV | Secondary corroboration only. Publisher reports 112 failed historical fetch attempts/retries and known per-date row shortfalls; no intraday timestamps. The 2026-11-18 file is 41,594 rows vs 41,627 expected; 2015-01-04 has an amount arithmetic exception and no staged raw copy. Derived OHLCV is not independent of the same floorsheet pipeline. Rights not independently verified. |

## Evidence gaps and actions

### NEPSE official holiday API
- Keep the exact raw response and digest immutable.
- `exchange_holiday` is now implemented on the feature branch with mandatory checks for payload integrity, source identity, schema mapping, date validity, duplicate detection, instrument scope, point-in-time availability and official notice evidence. It is not yet merged or active in the runtime registry.
- Validate holiday-date parsing, scope, instrument applicability, duplicate dates and the 2026-09-21 emergency-close description.
- Treat explicit holiday rows as closures only; absence from the list is not proof that a session was open.
- Review reuse terms separately from authenticity.

### CDSC clearing-member directory
- Obtain historical/effective-dated broker and clearing-member mappings for each relevant period.
- Reconcile CM numbers against NEPSE floorsheet buyer/seller codes and the applicable historical exchange register.
- Keep current member names separate from historical identity claims.
- Review reuse rights independently.

### Community historical archive
- Keep it secondary and preserve pinned revision, blob IDs, raw SHA-256 and date-level shortfall metadata.
- Do not promote publisher-derived OHLCV as independent confirmation of its own floorsheet rows.
- Reconcile date-level contract counts, quantity, turnover and arithmetic against a primary exchange record or genuinely independent source.
- Obtain explicit rights evidence for intended storage and analytics use.
- Quarantine dates with unresolved completeness or arithmetic issues.

## Holiday-source rights and admission decision

The NEPSE holiday API capture establishes a candidate official-source identity and an integrity-checked raw response. It does **not** establish permission to redistribute, publish, train on, or otherwise reuse the content. Rights remain `review_required`; redistribution remains disabled. No legal or terms-of-use conclusion is inferred from the fact that the endpoint is publicly reachable.

The feature-branch registry change adds the dedicated `exchange_holiday` type and its evidence requirements. The candidate remains non-active, has no canonical record-type approval, and must stay quarantined until a named human reviewer records source-scope and rights evidence. Explicit returned closure dates may be reviewed as closure claims only; absence of a date is not evidence that the exchange was open.

## Runtime registry state

`data/reference/source-trust-registry.v1.json` is deliberately empty and has
pinned SHA-256:

`8f6a17cf87aa05150ade5c6cc510b72e5d2a5098130021f6a2d2be53762e91fc`

There are zero active sources and zero canonical record-type approvals. Do not
populate this file until a named reviewer has checked source identity, scope,
effective dates, exact evidence references and intended-use rights. Registry
updates must change the pinned digest in deployment configuration.

## Related reviews

- `docs/FLOORSHEET_SOURCE_PROVENANCE_REVIEW_2026-11-25.md`
- `docs/PRIORITY_91_THIRD_SOURCE_FLOORSHEET_CANDIDATE_REVIEW_2026-11-25.md`
- `docs/P1_EVIDENCE_MANIFEST_CONTRACTS_2026-11-25.md`

A source candidate is not an approved source. No live prices, floorsheets,
broker flows, sector memberships or trade signals are promoted by this inventory.
