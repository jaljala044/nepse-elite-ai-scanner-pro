# Five-year all-equity historical evidence policy

Effective policy change: user-directed 2026-11-28. This policy supersedes the
previous three-source OHLCV fallback threshold for historical floorsheet and
chart evidence. It also supersedes the earlier secondary-source prohibition for
canonical historical OHLCV and floorsheet row selection only within the narrowly
defined evidence process below. It does not enable production trading signals.

## Collection scope

For every security in the supplied, effective-dated NEPSE equity universe,
collect five years of:
- Daily floorsheet transaction records; and
- Daily chart / OHLCV records.

The four collection providers are ShareHub, NEPSE Alpha, Chukul and ShareSansar.
Use every source that is actually accessible and rights-permitted. Mero Lagani is
an additional diagnostic comparison source when discrepancies remain; it is not
silently substituted for a missing primary collection.

The collection window is the five-year period ending on an explicit as-of date.
Do not assume the equity universe, security IDs, source endpoints, session
calendar, or data coverage. Generate a coverage manifest by equity, source,
record type and session. A plan is not proof of acquisition.

## Source order and capture

1. Query NEPSE's available historical data first and retain it as a reference.
2. Acquire available five-year floorsheet and chart archives from each configured
   provider using provider-documented public endpoints, authorized access, or
   user-provided exports. Never invent endpoints or bypass access controls.
3. Preserve raw bytes immutably and record source URL, exact query, retrieval UTC,
   HTTP result, SHA-256, source revision, parser version, symbol/security ID,
   session date and source lineage.
4. Record unavailable providers and coverage gaps with URL, query, retrieval UTC,
   HTTP result, blocker class, owner and due date. Access denial is not evidence
   that the underlying market record does not exist.

## Two-source record verification

For chart rows, compare exact security ID, session date, open, high, low, close
and volume. For floorsheet rows, compare trade date, contract ID, symbol, buyer
and seller broker codes, quantity, rate and amount.

A record can be marked COMPLETE_EVIDENCED when at least two sources provide the
same complete record and are lineage-independent. Compute pairwise Jaccard
similarity over source session-date sets. If overlap is greater than 0.98 and
the upstream_feed is the same, collapse those providers into one lineage source.
Two websites backed by the same upstream feed are not two independent sources.

Where NEPSE data exists, compare against it. Where it does not, use the secondary
sources. Two independent secondary sources matching exactly can establish the
selected historical record under this policy; preserve the T3/secondary source
labels and never misrepresent it as NEPSE first-party attestation.

## Mismatch investigation

When any source differs:
- Keep every raw observation and do not overwrite it.
- Compare the record against all available ShareHub, NEPSE Alpha, Chukul,
  ShareSansar and, where useful, Mero Lagani observations.
- Diagnose field-level causes, including missing/duplicate rows, symbol or
  security-ID mapping, date/session alignment, timezone, corporate-action or
  adjusted/unadjusted price basis, volume units, rounding, parser/schema changes,
  stale snapshots and upstream-feed duplication.
- Record the reason, supporting evidence references, source values and hashes.
- If a matching independent pair exists, it may establish the selected value
  after the mismatch reason is documented. If no unique independent pair exists,
  retain PARTIAL_EVIDENCED and quarantine the row.

No majority vote: the rule is a matching independent pair, not the largest
cluster. Multiple competing pairs remain PARTIAL_EVIDENCED.

## Floorsheet-specific controls

Compare transactions by stable trade date + contract ID where available.
Check duplicate contracts, missing contracts, symbol, buyer/seller broker IDs,
quantity, rate, amount, daily row counts, total quantity and gross turnover.
Do not infer complete daily floorsheet coverage from a partial sample. Broker
identity and beneficial ownership are separate evidence domains.

## Chart-specific controls

Validate positive prices, OHLC high/low bounds, non-negative whole-share volume,
duplicate symbol/date keys, security lifecycle, trading-session coverage,
point-in-time availability and corporate-action basis. Do not forward-fill or
silently repair missing candles.

## Rights and use

Record provider terms and rights evidence separately from data correctness.
Use only access methods permitted by the provider. Do not redistribute raw
provider payloads unless redistribution rights are evidenced.

## Approval boundary

This policy permits a validated, two-source historical record to be marked
COMPLETE_EVIDENCED and selected as the canonical historical data candidate.
It does not itself authorize production signals, deployment, or automatic
trading; those remain separately gated.
