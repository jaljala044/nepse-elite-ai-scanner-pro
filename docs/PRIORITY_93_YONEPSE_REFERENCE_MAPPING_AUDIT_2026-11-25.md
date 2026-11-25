# Priority 93 — Yonepse security and broker reference mapping audit (2026-11-25)

## Scope

This is a bounded reference-mapping audit for the pinned Yonepse 2026-11-24 floorsheet payload. It is not an official NEPSE universe verification and does not establish effective-dated broker legal identity.

Pinned Yonepse commit:
- Floorsheet file commit: `1bfa798e84c7170f826e473e7e1ec3957c81966c`
- Tree: `33e7fc54f0b225e92d148f0ef362fbb67045abcd`
- Floorsheet blob: `2a758194c470048e3b22aefc8954365397d9c48d`
- File: `data/floor_sheet/daily/2026-11-24.json`

Reference files were read from the same commit:
- `data/other/securities.json`
- `data/other/brokers.json`

## Security ID mapping

- Securities registry rows: 652.
- Distinct stock IDs in floorsheet: 350.
- Mapped stock IDs: 346.
- Unmapped stock IDs: `8111`, `469`, `700`, `661`.
- Among the 346 mapped traded IDs, the reference snapshot labels:
  - 279 as `Equity`, status `A`.
  - 43 as `Mutual Funds`, status `A`.
  - 24 as `Non-Convertible Debentures`, status `A`.

The 24 debenture IDs are source records and must not enter the project's target equity/fund universe. They should remain in raw audit history with instrument type retained and be excluded from target scanner outputs. Four unmapped IDs remain unresolved and must not be guessed or force-mapped.

These counts describe distinct securities traded on this one date, not the full 281-equity + 47-fund target population. They do not prove registry completeness or point-in-time listing/suspension/delisting status. The reference snapshot is a community-maintained Yonepse file, not a dated official NEPSE registry.

## Broker member-code mapping

- Distinct buyer/seller broker codes observed: 91.
- Matched to Yonepse `brokers.json.memberCode`: 91/91.
- All 91 matched entries have `activeStatus=A` in this reference snapshot.
- The mapping provides a current directory-name candidate only. It does not establish historical legal entity identity, effective dates, branch/alias continuity, or official CDSC/SEBON identity.

## Data handling decision

1. Preserve the original numeric `stockId` and broker member codes as source identifiers.
2. Attach the mapped symbol/name and broker name only as reference enrichment with source commit/path/hash lineage.
3. Keep the four unmapped stock IDs unresolved.
4. Retain the 24 NCD rows in raw source evidence, but exclude them from the active target universe and scanner candidates.
5. Do not infer that a missing symbol or broker was inactive, suspended, delisted or nonexistent.
6. Require an official dated registry and effective-dated broker crosswalk before canonical identity promotion.

## Acceptance status

- Security mapping: **partial** — 346/350 traded stock IDs mapped to a same-commit community reference; four unresolved.
- Broker mapping: **directory candidate complete for this date** — 91/91 member codes mapped; historical identity remains unverified.
- Target universe validation: **not complete**.
- Canonical data promotion: **not authorized**.

No raw floorsheet rows or reference files were copied into the project repository by this audit. No model training or predictive claim is supported by this one-day mapping exercise.
