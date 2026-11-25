# NEPSE AI data-pipeline readiness report — priorities 81–90 (2026-11-25)

## Executive result

The data acquisition and reconciliation pipeline has advanced from archive discovery to a full pinned one-day floorsheet comparison, including contract-level differences and broker-code coverage. The resulting evidence is strong enough to select a **review candidate for 2026-11-24 only**, but not to declare a one-year or six-month verified dataset, and not to promote data for canonical training.

**Current state: review-only; not production-data ready.**

## Priorities 81–90

| Priority | Work | Result | Acceptance state |
|---|---|---|---|
| 81 | Acquire and pin a bounded floorsheet sample | Complete Samir 2026-11-24 CSV acquired and SHA-256 / Git blob identity calculated; SocrateAI same-date copy acquired from a pinned commit | **Complete for one-day sample** |
| 82 | Verify source and provenance | Samir scraper trace reaches MeroLagani; SocrateAI original acquisition chain is not independently established; data-use rights for both copies require confirmation | **Partially complete** |
| 83 | Map source headers | Urek 11-column publisher-declared profile and Samir 9-column physically observed profile added; source-only columns preserved | **Engineering map complete; Urek raw-header check open** |
| 84 | Reconcile contracts and daily control totals | Pipeline accepts independent daily controls for count, quantity, amount; sample comparison exactly reconciles SocrateAI to MeroLagani quantity/amount | **One-day check complete; general historical coverage open** |
| 85 | Verify broker-code coverage | 91 source codes observed in both same-day source files; all 91 match a CDSC clearing-member number; 91-row crosswalk candidate registered | **91/91 code-directory coverage; legal/effective-date identity review open** |
| 86 | Compare overlapping source dates | 2026-11-24 row-by-row contract comparison: 52,369 shared exact rows, 18 SocrateAI-only, zero Samir-only, zero shared-row conflicts | **One-day comparison complete; multi-date rerun open** |
| 87 | Identify missing trading dates | Archive date-file sets inventoried, but no complete official date-level NEPSE open/closed calendar | **Blocked on primary calendar** |
| 88 | Verify equity/fund universe | Official SEBON registry sources reviewed; no dated NEPSE crosswalk confirming 281 equities + 47 mutual funds | **Blocked on official exchange-level registry** |
| 89 | Assess one-year / six-month coverage | SocrateAI: 228 one-year / 115 six-month date files. Samir: 179 / 119. Shared dates: 157 / 107. Counts are not verified sessions or per-security coverage | **Potential coverage exists; completeness unproven** |
| 90 | Produce readiness report | This report and linked source-level audit records committed | **Report complete; readiness decision is review-only** |

## One-day sample evidence

### Pinned source files

**SamirWagle / MeroLagani-derived capture**
- Repository: \`SamirWagle/Nepse-All-Scraper\`
- Commit: \`e6160adc6bdf3d19562167388e3d9d4f645c455a\`
- File: \`data/floorsheet/floorsheet_2026-11-24.csv\`
- Git blob SHA-1: \`22eaa891b30aac2fe4cf197053efa014953351c0\`
- Size: 3,538,179 bytes
- SHA-256: \`2687b7ed6bc5ebd737fa459ca8dd620941bb3ec1da6613fbd620550495018f55\`
- 52,369 rows / 52,369 unique contract IDs
- Quantity 14,662,346; gross amount NPR 5,551,668,556.66

**SocrateAI copy**
- Repository: \`socrateai-official/nepse-open-data\`
- Commit: \`cfa92493e93211c7019a5cd0b2cbe7d400d9c4e3\`
- File: \`floorsheet/floorsheet_2026-11-24.csv\`
- Git blob SHA-1: \`e7150873219d66a21345df2dfbd78f6c5a4b1152\`
- Size: 3,058,892 bytes
- 52,387 rows / 52,387 unique contract IDs
- Quantity 14,670,177; gross amount NPR 5,553,019,249.46

### Contract-level reconciliation

Every one of the **52,369** Samir contract IDs is present in SocrateAI. All shared records match across date, symbol, buyer, seller, quantity, rate and amount. SocrateAI has **18 extra records**, with no Samir-only rows and no shared field conflicts.

Those 18 records contribute exactly **7,831 shares** and **NPR 1,350,692.80**, which closes the difference between the Samir file and the indexed MeroLagani daily totals for 2026-11-24. The SocrateAI total exactly matches MeroLagani's displayed daily quantity and gross amount. This makes SocrateAI the stronger complete-day candidate for this date only; it does not independently prove SocrateAI's original upstream collection route.

MeroLagani's indexed page also displays an average rate of 378.52. It is a site summary metric; the pipeline treats quantity and gross amount as the hard reconciliation controls and does not infer missing trades from an average-rate difference.

### Broker code coverage

- 91 unique broker codes were observed across the buyer and seller columns in both files.
- All 91 numeric codes match current CDSC clearing-member numbers.
- Each source row produces two party observations; the larger SocrateAI file therefore has 104,774 party observations.
- The crosswalk file records current directory-name candidates, but its status remains \`directory_number_match_candidate_not_effective_dated_identity_verification\`.
- Code 91's former name (CBIL Securities) changed to Citizens Share Broker; the company reports a name-change resolution on 2025-01-21 and company-registry recording on 2025-04-01.
- Code 8's current main listing is Brilliant; MeroLagani separately shows an \`8_RWS\` Ashutosh entry. It is not assumed to be the same legal entity/branch without further effective-dated records.

### Source and data-use limitations

- Samir's CSV date is written by its scraper using \`date.today()\`; it is a capture-date field. Its contract-number prefix and MeroLagani daily page support 2026-11-24 for this example, but the adapter retains date semantics as provisional.
- The pinned Samir repository README labels the material "Educational"; the pinned repository tree had no explicit LICENSE/COPYING file. No redistribution or commercial-use permission is established by this audit.
- SocrateAI's public repository licence is not proof that it has rights to any upstream NEPSE/MeroLagani source records.
- Neither archive is accepted as canonical from one-day checks alone.

## Historical file-date inventory

Pinned file-tree manifests show:

| Window | SocrateAI | SamirWagle | Shared dates | SocrateAI only | Samir only |
|---|---:|---:|---:|---:|---:|
| 2025-11-25 to 2026-11-25 | 228 | 179 | 157 | 71 | 22 |
| 2026-05-25 to 2026-11-25 | 115 | 119 | 107 | 8 | 12 |

These are date-named files, not exchange-confirmed sessions. Neither source's date manifest is a complete substitute for an official NEPSE session calendar. Per-security presence, lifecycle and expected-trade coverage must also be checked before any one-year or six-month acceptance decision.

## Unresolved acceptance gates

1. **Primary session calendar:** obtain a complete day-level NEPSE trading/open-closed date series, including extraordinary closures, holidays, suspensions and session changes. The 2022 weekly schedule notice and secondary evidence for the April 2026 change do not constitute a date-level calendar.
2. **Target security register:** obtain a dated primary NEPSE/SEBON/registrar crosswalk of security IDs, symbols, instrument types and effective listing/trading/suspension/delisting dates. The working target remains 281 equities + 47 mutual funds but is not yet verified as a date-effective exchange population.
3. **Source lineage and data rights:** establish the upstream acquisition route for each archive and the terms governing storage, processing, training and redistribution. Keep raw files immutable and review-only until resolved.
4. **Repeat daily reconciliation:** run the comparator across each candidate session, reconcile daily row and turnover controls, and retain all unmatched contract IDs and field conflicts.
5. **Historical broker identity:** construct effective-dated legal-name and code history, including broker transfers, aliases and branch-level distinctions. Do not turn present-day directory matches into verified historical links automatically.
6. **Security-level coverage:** after the official universe/calendar exist, report each expected security-session as present, no-trade, suspended, not-yet-listed, delisted, or unresolved—not as an undifferentiated missing file.
7. **OHLCV quality:** retain the earlier 1,339-row exception ledger as unresolved; its 1,331 invalid OHLC rows and eight cross-source conflicts remain quarantined. Do not promote unresolved prices to training.

## Pipeline artifacts committed

- \`backend/app/floorsheet_source_profiles.py\` — explicit Urek and Samir source profiles.
- \`backend/app/floorsheet_pipeline.py\` — independent controls integrated into the floorsheet-to-broker pipeline.
- \`backend/app/broker_aggregation.py\` — unresolved source broker codes remain separated; verified canonical entities can aggregate across source-specific codes.
- \`backend/audit_samir_merolagani_capture.py\` and tests — pinned single-file audit.
- \`backend/compare_floorsheet_source_csvs.py\` and tests — contract-level multi-source comparator.
- \`data/reference/broker_code_crosswalk_candidates_2026-11-25.csv\` — 91-code candidate crosswalk.
- \`.github/workflows/samir-merolagani-sample-audit.yml\` — pinned source audit workflow.
- \`.github/workflows/floorsheet-source-comparison.yml\` — pinned source comparator workflow.
- \`docs/MEROLAGANI_FLOORSHEET_CAPTURE_AUDIT_2026-11-24.md\`
- \`docs/FLOORSHEET_ARCHIVE_DATE_COVERAGE_ASSESSMENT_2026-11-25.md\`
- \`docs/BROKER_CODE_COVERAGE_AND_IDENTITY_REVIEW_2026-11-25.md\`

## Test and promotion status

New tests were added for source profiles, independent control totals, the cross-source comparator and the broker-code crosswalk artifact. The GitHub connector did not expose workflow status records for these latest commits during this work session, so **these new tests are not reported as passing here**. Existing earlier backend tests (464 tests) passed before this priority batch, but that result does not substitute for running the newly added test modules.

No raw floorsheet CSV was copied into the main project repository. No canonical source selection, model-training promotion or model performance claim was made.

## Final readiness decision

- One-day floorsheet evidence: substantially reconciled; SocrateAI is the best current completeness candidate for 2026-11-24 only.
- Broker code-number coverage on that day: 91/91 matched to current CDSC CM numbers; historical legal-entity identity remains candidate-only.
- One-year/six-month date-file availability: promising but not session-complete or security-complete.
- Official date-level trading calendar, verified target universe, upstream lineage and data-use rights: still open.

**NEPSE AI data readiness: REVIEW_REQUIRED. Do not start canonical model training on these floorsheets yet.**
