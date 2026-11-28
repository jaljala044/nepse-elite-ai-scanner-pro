# Issue #5 — evidence-gated gap adjudication model

## Purpose

The 3,122 unique symbol/date keys identified by the cross-source gap report remain unclassified. This change adds a deterministic adjudication gate so a future evidence review cannot infer a no-trade, suspension or missing candle from absence alone.

## Accepted evidence types

- `official_security_no_trade`: explicit NEPSE date/security-specific no-trade evidence.
- `official_suspension`: explicit NEPSE/SEBON suspension evidence whose effective interval covers the date.
- `official_not_listed`: explicit NEPSE/SEBON listing-status evidence whose effective interval covers the date.
- `floorsheet_execution`: rights-cleared positive contract evidence; it creates an execution-without-bar conflict, never a synthetic candle.
- `counterpart_valid_bar`: a valid bar from the other archive; it records a source coverage difference, not authoritative truth.

Each evidence row requires source ID/URL, SHA-256, capture and availability timestamps, effective date range, and explicit rights status. Official dispositions require NEPSE/SEBON authority. All evidence must cover the target trade date.

## Output dispositions

- `verified_no_trade`
- `verified_suspended`
- `verified_not_listed`
- `execution_evidence_without_source_bar`
- `counterpart_bar_present_not_authoritative`
- `conflicting_evidence_quarantined`
- `unresolved_no_qualifying_evidence`

Contradictory official and execution evidence remains quarantined. A blank or absent floorsheet is never treated as no-trade evidence. A counterpart bar never becomes the official value.

## Point-in-time boundary

The report separately indicates whether the latest evidence was available by an explicitly supplied decision cutoff. Retrospective evidence captured after a historical decision date may help audit the archive but is not eligible for a historical backtest decision at that earlier cutoff.

## Run

```bash
python backend/adjudicate_issue5_gaps.py \
  --gaps issue5_unclassified_equity_session_gaps.csv \
  --evidence approved_gap_evidence.csv \
  --decision-cutoff 2026-11-28T16:00:00+05:45 \
  --output-dir reports/issue5-adjudication
```

The evidence CSV must include: symbol, trade_date, evidence_kind, authority, source_id, source_url, evidence_sha256, captured_at, available_at, effective_from, effective_to and rights_status.

## Current status

No evidence package was supplied or promoted by this code change. The implementation is an empty-by-default gate and test fixture only. All existing gap keys remain unresolved until real evidence is retained, reviewed and independently approved. No raw source mutation or canonical/training promotion.
