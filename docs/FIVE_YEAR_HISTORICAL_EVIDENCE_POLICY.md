# 3–5-year all-equity historical evidence policy

Effective policy change: user-directed 2026-11-28. This policy supersedes the
previous three-source OHLCV fallback threshold for historical chart evidence.
It also extends two-source historical evidence resolution to floorsheet rows.
It does not enable production trading signals.

## Collection scope

For every security in the supplied, effective-dated NEPSE equity universe,
collect 3–5 years of:
- Daily floorsheet transaction records; and
- Daily chart / OHLCV records.

Five years is the preferred target. If a provider cannot supply five years,
collect at least three complete years for that equity and data type. Three years
is the minimum fallback, not the preferred target. If fewer than three years are
available, retain the partial coverage and missing-period report; do not mark it
complete or silently substitute a shorter window.

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

Consequently, the code can capture ShareSansar-derived chart history now and can capture other provider data through exact configured URL templates or bulk archive URLs. A five-year result is preferred; a three-year result is the minimum acceptable fallback. Floorsheet coverage remains blocked where a provider has not documented or supplied an authorized historical archive. Do not treat a missing endpoint as proof that the data does not exist.

The collection window targets five years ending on an explicit as-of date, with a three-year minimum fallback evaluated separately for every equity, provider and data type.
Do not assume the equity universe, security IDs, source endpoints, session
calendar, or data coverage. Generate a coverage manifest by equity, source,
record type and session. A plan is not proof of acquisition.

## Source order and capture

1. Query NEPSE historical data where available and retain it as a reference.
2. Acquire available 3–5-year floorsheet and chart archives from each configured
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
same complete record and are lineage-independent. Repeated observations from a
single provider or providers declaring the same upstream feed are grouped into
one lineage regardless of their session-date overlap. Distinct feed labels alone
do not prove real-world independence; review upstream provenance separately.
Require the record key and session date to match the source observation. Require
positive whole-share floorsheet quantity, positive price and exact quantity-times-rate
amount; discrepancies remain unresolved pending documented rounding evidence.

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


## Collector configuration

The collector supports provider-documented URL templates. Configure them as
server-side environment variables; never commit API credentials.

- `SHAREHUB_CHART_URL_TEMPLATE=https://sharehubnepal.com/data/api/v1/nepse-data/price-history/{symbol}?time=5Y`
- `SHAREHUB_API_TOKEN` for Bearer auth, or `SHAREHUB_API_KEY` for the documented `X-Api-Key` header. ShareHub also requires a licensed service and allow-listed server IP.
- `SHAREHUB_FLOORSHEET_URL_TEMPLATE` only if ShareHub supplies an authorized historical archive endpoint. Its public docs currently describe today's raw floorsheet, not a five-year raw archive.
- `NEPSEALPHA_CHART_URL_TEMPLATE`, `NEPSEALPHA_FLOORSHEET_URL_TEMPLATE`, `CHUKUL_CHART_URL_TEMPLATE`, `CHUKUL_FLOORSHEET_URL_TEMPLATE`, `SHARESANSAR_CHART_URL_TEMPLATE`, and `SHARESANSAR_FLOORSHEET_URL_TEMPLATE` must be exact endpoints/templates supplied by the respective provider or an authorized export process.
- URL templates may use only `{symbol}`, `{security_id}`, `{date}`, `{from}`, and `{to}`. Chart templates should be per-symbol. Daily floorsheet templates should use `{date}` and require the complete exchange-verified session calendar. A bulk archive URL can be supplied with `<PROVIDER>_<TYPE>_DATA_URL`.
- `MEROLAGANI_CHART_URL_TEMPLATE` and `MEROLAGANI_FLOORSHEET_URL_TEMPLATE` are diagnostic-only inputs.

Example command (replace the input paths with the verified project artifacts):

```bash
python backend/collect_sources.py \
  --as-of-date 2026-11-28 \
  --equity-universe data/reference/nepse_active_equity_manifest_2026-11-26.csv \
  --session-calendar path/to/verified_session_dates.json \
  --source sharehub --source nepsealpha --source chukul --source sharesansar
```

The equity universe may be a JSON array of `{"symbol":"...","security_id":"..."}`
objects or a CSV with `symbol`, `security_id`, `instrument_type`, and `status`
columns. The repository currently has a 281-row active-equity candidate snapshot
at `data/reference/nepse_active_equity_manifest_2026-11-26.csv`, sourced from
NEPSE Alpha; it is a collection starting point, not an official NEPSE universe
attestation. Cross-check it against other available provider and NEPSE security
records before treating its coverage as complete. The session-calendar JSON is
an array of ISO trading dates or an object with a `session_dates` array. The
existing `data/reference/nepse_session_calendar.csv` is ShareSansar-derived and
explicitly not exchange-certified, so it must not be supplied as an
exchange-verified calendar for full daily floorsheet coverage. Collector results
remain PARTIAL_EVIDENCED until parsed row counts, five-year coverage, security
lifecycle, source lineage and two-source reconciliation have been verified.
