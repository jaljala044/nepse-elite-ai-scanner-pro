# Five-year all-equity historical evidence policy

Effective policy change: user-directed 2026-11-28. This policy supersedes the
previous three-source OHLCV fallback threshold for historical chart evidence.
It also extends two-source historical evidence resolution to floorsheet rows.
It does not enable production trading signals.

## Collection scope

For every security in the supplied, effective-dated NEPSE equity universe,
collect five years of:
- Daily floorsheet transaction records; and
- Daily chart / OHLCV records.

The four collection providers are ShareHub, NEPSE Alpha, Chukul and ShareSansar.
NEPSE's available historical records are retained as the reference source.
Mero Lagani is an additional diagnostic comparison source when discrepancies
remain. Use every source that is actually accessible and rights-permitted.

### Provider access evidence checked 2026-11-28

- ShareHub documents a daily all-time OHLCV endpoint at `/price-history/{symbol}` with `time=5Y` or `ALL`; access requires a Data API account, enabled licence, bearer/API key and allow-listed server IP. Its documented raw floorsheet endpoint is for today's floorsheet; documented broker-analysis periods are capped at one year. Public documentation does not establish a five-year raw transaction-floorsheet endpoint. See https://sharehubnepal.com/data/nepse-data-documentation/.
- NEPSE Alpha describes adjusted historical price data for listed companies and real-time floorsheet features, but no public historical export/API contract was verified in this check. See https://nepsealpha.com/about-nepsealpha.
- Chukul describes adjusted stock history and longer-history Pro broker tools, but no public five-year raw floorsheet API contract was verified in this check. See https://chukul.com/broker-desk/details and https://chukul.com/technical-desk/details.
- The public ShareSansar-derived archive documents a free per-symbol `api/history/{SYMBOL}.json` history endpoint. The collector captures this as a ShareSansar-derived chart archive, not as an official ShareSansar or NEPSE attestation. Its published API description does not list a floorsheet archive endpoint. See https://omitnomis.github.io/ShareSansarScraper/about.html.
- Mero Lagani exposes a datewise floorsheet page, but a stable documented five-year API/export contract was not verified here. It remains a diagnostic comparison source unless a permitted endpoint or export is supplied. See https://merolagani.com/Floorsheet.aspx.

Consequently, the code can capture ShareSansar-derived chart history now and can capture other provider data through exact configured URL templates or bulk archive URLs. Five-year floorsheet coverage remains blocked where a provider has not documented or supplied an authorized historical archive. Do not treat a missing endpoint as proof that the data does not exist.

The collection window is the five-year period ending on an explicit as-of date.
Do not assume the equity universe, security IDs, source endpoints, session
calendar, or data coverage. Generate a coverage manifest by equity, source,
record type and session. A plan is not proof of acquisition.

## Source order and capture

1. Query NEPSE historical data where available and retain it as a reference.
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
selected historical record under this policy; preserve T3/secondary labels and
never misrepresent them as NEPSE first-party attestation.

## Mismatch investigation

When any source differs:
- Keep every raw observation and do not overwrite it.
- Compare the record against all available ShareHub, NEPSE Alpha, Chukul,
  ShareSansar and, where useful, Mero Lagani observations.
- Diagnose missing/duplicate rows, symbol or security-ID mapping, date/session
  alignment, timezone, corporate-action or adjusted/unadjusted price basis,
  volume units, rounding, parser/schema changes, stale snapshots and shared
  upstream-feed duplication.
- Record field-level differences, the reason, supporting evidence references,
  source values and hashes.
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

A validated two-source historical record may be marked COMPLETE_EVIDENCED and
selected as a canonical historical data candidate. This does not authorize
production signals, deployment, or automatic trading; those remain separate.
