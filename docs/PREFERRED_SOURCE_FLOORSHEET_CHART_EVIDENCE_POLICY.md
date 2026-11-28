# Preferred-source floorsheet and chart evidence policy

**Status:** Proposed project policy on branch `policy/preferred-source-floorsheet-chart-evidence`.
**Scope:** P1 repeated OHLCV resolution, P2 invalid OHLC/conflicts, P3 historical continuity, P4 source collection, and P5 canonical integration.

This policy records the project owner's updated source-selection instruction. It supersedes the older **4-of-6 providers plus two independent lineages** requirement as a prerequisite for *project-level preliminary collection and preferred-source approval*. It does not turn a secondary provider into an exchange authority, waive field validation, or authorize unsupported canonical promotion.

## 1. Eligible collection sources

The collector may use any one available source from this preferred group to begin collection:

1. ShareHub
2. Chukul
3. NepseAlpha
4. ShareSansar

Do not block collection or preliminary analysis merely because the other providers are unavailable. Try ShareHub and Chukul first when accessible; use NepseAlpha and ShareSansar as additional or fallback sources. Record every attempted source and its actual access result.

A configured URL, provider name, public landing page, or synthetic fixture is not proof that a live historical integration works. Use only public documented interfaces, provider-authorized APIs/exports, or user-supplied captures. Do not guess private endpoints, bypass authentication, or disregard provider licence terms.

## 2. Required evidence modalities

Search and preserve both chart and floorsheet evidence wherever available.

### Chart evidence
Capture the provider, symbol/security identity, Nepal trading date, literal field labels, Open, High, Low, Close, adjustment basis, retrieval/publication time, URL or export reference, and raw payload/export hash.

Keep LTP, official close, adjusted close, previous close, VWAP, and weighted-average close as distinct fields unless documented evidence establishes equivalence.

### Floorsheet evidence
Capture the provider, symbol/security identity, trading date, contract/transaction rows, timestamps, rate, quantity, amount/turnover, trade count where available, retrieval time, URL/export reference, and raw payload/export hash.

Where raw contracts are available, independently aggregate transaction quantity and turnover and reconstruct the applicable traded-price evidence. Document excluded trade types, corrections, partial coverage, and aggregation rules. A daily floorsheet aggregate is not automatically interchangeable with chart OHLC.

### Field-to-evidence mapping
- Open/High/Low/Close: compare chart OHLC with transaction-level floorsheet evidence where the relevant field can be reconstructed. Explain any field that cannot be reconstructed from contracts.
- Volume/quantity: compare chart/provider quantity with the sum of eligible floorsheet contract quantities.
- Turnover: compare chart/provider turnover with the sum of eligible contract amounts, documenting units and exclusions.
- Trade count: compare only when both sources define and expose comparable counts.
- VWAP: calculate from eligible transaction amount divided by eligible quantity; do not relabel it as Close.

A chart and floorsheet from the same provider are two evidence modalities, not two independent provider lineages. Record that distinction.

## 3. Project-level decision rules

Use field-specific decisions. One field can be approved while another remains provisional or quarantined.

- `APPROVED_PREFERRED_SOURCE`: ShareHub or Chukul value accepted for the specific field after the available chart and floorsheet evidence has been examined and the value is supported within documented semantics, coverage, and tolerances. Record why that provider value was selected.
- `APPROVED_CROSS_CHECKED`: field is supported by comparable records from multiple sources with lineage and semantics recorded.
- `APPROVED_PROVISIONAL`: sufficient internally consistent evidence exists for preliminary analysis, but a required independent check or evidence modality is unavailable.
- `QUARANTINED`: material conflict, unclear field semantics, inadequate coverage, or insufficient evidence remains.
- `REJECTED`: record fails identity, schema, arithmetic, integrity, or other mandatory validation.

One accessible provider is sufficient to collect and begin preliminary analysis. It is not automatically sufficient to mark every field approved.

When NepseAlpha or ShareSansar disagrees with ShareHub or Chukul, do not automatically reject the ShareHub/Chukul value. Investigate the exact field, date, adjustment basis, source timestamp, coverage, and floorsheet/chart evidence. ShareHub or Chukul may be selected as the project-preferred value when that evidence supports it.

When ShareHub and Chukul disagree, compare both against the relevant chart and floorsheet evidence. Do not use a blind source hierarchy or majority vote. If the discrepancy cannot be resolved, quarantine only the affected field and retain all original values.

If chart and floorsheet evidence disagree, first investigate field semantics, session date/timezone, trade-type filters, corporate actions, partial captures, corrections, and rounding. Do not silently choose a value.

## 4. Provenance and immutable evidence

For every capture, preserve:
- source name and canonical URL/endpoint or supplied-file identity;
- retrieval timestamp and source publication/update timestamp when available;
- symbol and stable security identity;
- market date and timezone/session convention;
- original literal field names and values;
- raw bytes/export and SHA-256;
- parser/schema/version and normalization details;
- coverage, pagination, missing fields, and access/licence limitations;
- chart/floorsheet comparison results, tolerances, and reviewer decision;
- every conflicting original value and a discrepancy history.

Never overwrite raw evidence. Corrections must be append-only decisions linked to the evidence that supports them.

## 5. Validation safeguards that remain mandatory

This policy does not permit:
- fabricated prices, volume, turnover, dates, sessions, or source captures;
- treating a missing row as zero, no-trade, or market closure;
- forward-filling OHLCV;
- silently rounding away material differences;
- mixing adjusted and unadjusted prices;
- treating LTP, Close, and VWAP as equivalent without evidence;
- assuming two websites are independent when they share an upstream feed;
- treating a provider's lack of data as agreement or disagreement;
- promoting unresolved fields to canonical data.

Security identity, lifecycle, session status, corporate-action basis, point-in-time availability, and data-quality checks remain required. Preliminary research may use clearly labelled provisional data, but BUY/trade eligibility and risk gates must not be bypassed.

## 6. Evidence tiers and official verification

`APPROVED_PREFERRED_SOURCE` is a project-level acceptance label, not NEPSE certification.

Only qualifying NEPSE first-party attestation can establish `verified_open_tier1`. Secondary-source agreement, including ShareHub/Chukul agreement or chart/floorsheet consistency, cannot create T1 status. Existing T1/T2/T3 definitions and restrictions remain in force. T3 concordance cannot authorize T1 status or an otherwise restricted OHLCV correction.

## 7. Application to P1–P5

| Workstream | Evidence application |
|---|---|
| P1 — Repeated OHLCV | Use available historical chart records and floorsheet evidence to classify each repeated candidate. Preserve unknown dates and unresolved cases; never forward-fill. |
| P2 — Invalid OHLC/conflicts | Compare each disputed OHLC field with chart and transaction evidence. ShareHub/Chukul may be accepted when supported; quarantine unresolved fields. |
| P3 — Historical continuity | Use historical charts, daily records, floorsheet activity, and lifecycle evidence. Distinguish no-trade from missing data and market closure. |
| P4 — Collection | Collect from any accessible preferred source. Record actual access, coverage, permissions, and raw evidence. Add other providers when available; do not require all four. |
| P5 — Canonical integration | Promote only fields that satisfy canonical identity, lifecycle, session, corporate-action, provenance, and approval gates. Project-preferred approval alone does not waive these gates. |

## 8. Implementation and audit requirements

This document defines policy; it does not claim that provider adapters, historical captures, or runtime eligibility changes have already been implemented. Implementation work must:
1. map these decision labels to explicit schema fields without conflating them with T1/T2/T3;
2. add field-specific reconciliation and reviewer evidence requirements;
3. add tests for one-source collection, preferred-source acceptance, provider disagreement, chart/floorsheet disagreement, missing modalities, and unresolved quarantine;
4. verify that provisional and project-preferred records cannot bypass mandatory scanner eligibility;
5. report actual provider captures separately from synthetic test fixtures.

Do not report a provider integration or a historical record as verified until a real authorized capture and reproducible validation evidence exist.
