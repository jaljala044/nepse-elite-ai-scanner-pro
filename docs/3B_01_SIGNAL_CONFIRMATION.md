# 3B.01 — Signal confirmation engine

## Rule set

A bullish confirmation requires all of:
1. Latest close above the prior 20-session high (latest candle excluded).
2. Latest close above SMA20 and SMA50.
3. SMA20 above SMA50.
4. Latest volume at least 1.5 times the prior 20-session average.
5. Latest close in the upper 25% of its candle range.

A bearish warning is the symmetric downside pattern: close below the prior
20-session low and both moving averages, SMA20 below SMA50, volume expansion,
and a close in the lower 25% of the candle. It is not a short-sale instruction.

## Fail-closed behavior

The caller must pass `eligible=True` only after the server-owned review gate
has certified row identity, lifecycle, session, provenance, corporate-action
and point-in-time availability. The default is false. Invalid or insufficient
input returns UNKNOWN.

## Output classes

- `bullish_confirmation`: all bullish rules passed.
- `bearish_warning`: all bearish rules passed.
- `no_confirmation`: eligible data, neither full rule set passed.
- `UNKNOWN`: eligibility or structural validation unavailable.
- `insufficient_data`: fewer than 55 observations.

## Limitations

Daily OHLCV only. No intraday confirmation, order book, verified broker flow,
sector/market regime, liquidity, slippage, transaction costs or out-of-sample
backtest. Thresholds are research defaults, not calibrated probabilities.
No BUY/SELL/HOLD/NO TRADE, entry, stop, target, sizing, alert or order is emitted.

## Tests

From `backend/`: `python -m unittest tests.test_signal_confirmation`

## Real-data acceptance status (2026-11-27)

The feature is implemented and its automated tests cover deterministic synthetic
patterns. That is software verification, not market-history validation.

The repository's official per-security history review window
(`2026-10-05` through `2026-11-26`) contains 29 reported session dates and
281 current-equity candidate crosswalk matches. Its audit explicitly sets
`canonical_promotion_allowed=false`,
`coverage_admission_allowed=false`, and
`historical_security_identity_verified=false`. The per-security history
payloads provide date, trades, volume, turnover, high, low and close; they do
not provide the complete open/high/low/close/volume row required by this
engine. The captured window is also shorter than the engine's 55-observation
default.

The server-owned canonical reviewed-row manifest
(`data/reference/scanner_canonical_reviewed_rows.json`) currently contains
zero records. The ShareSansar archive already in this project is secondary
evidence and its own manifest prohibits promotion/training. Neither source may
be used to bypass the server eligibility gate.

### Additional source investigation (2026-11-27)

A public NEPSE data-pipeline project reports that NEPSE's per-security EOD
history API returns complete daily OHLCV but is server-limited to a rolling
365-day window. Its published research dataset keeps this official-source
table separate from a longer ShareSansar-derived history; the project reports
a 226-day overlap with 75,671 matched rows and exact volume agreement, but
explicitly says the pre-2025 history is not independently verified. The same
pipeline documents a WASM-derived token/access-control mechanism and describes
the legality of working around it as uncertain. We will not copy that
authentication workaround, scrape around access controls, or import its
third-party data as canonical reviewed evidence:
https://huggingface.co/datasets/AnkitSanjyal/nepse-market-data

A second public archive claims 3,600 sessions from 2011 onward and publishes
complete daily OHLCV CSVs. Its README is unusually transparent: it says the
archive is scraped from ShareSansar (not NEPSE directly), describes public
publication as a redistribution decision rather than a settled right, and
states the data is not covered by its MIT code licence. It also documents
unresolved source days and says no adjustment for bonus shares, rights issues
or splits is applied. This is useful provenance/coverage research, but it is
not independent exchange evidence, does not establish our right to ingest or
redistribute the data, and does not satisfy the corporate-action and source
rights review required by our canonical gate:
https://github.com/srijankarki07/nepse-data

A third candidate is `socrateai-official/nepse-open-data`. Its public
GitHub tree contains 8,442 stock-OHLC CSV paths across adjusted and unadjusted
daily folders, with dated files as early as 2007 and through 2026-11-26. A sampled
unadjusted file has date, close, open, high, low, volume and symbol; it is
structurally close to what the engine needs. The repository publishes an MIT
licence that expressly purports to cover the dataset. However, its short README
does not identify the upstream source, collection method, adjustment
methodology, corporate-action factors, symbol lifecycle process, or
completeness/exception policy. A permissive downstream licence alone cannot
establish that the publisher had rights to sublicense the underlying exchange
data. We have not imported it or treated it as canonical. It is the best
community-data candidate for a provenance request and controlled sample
reconciliation, not an accepted source yet:
https://github.com/socrateai-official/nepse-open-data

A separate commercial API vendor, Share Hub, documents an all-time per-stock
daily OHLCV history service. Access requires a vendor-issued Data API account,
a server IP allow-list, and the relevant licensed package. Its docs describe
bearer-token authentication, per-licence rate limits, and a test mode that the
vendor must enable:
https://sharehubnepal.com/data/nepse-data-documentation/
This is the strongest currently documented procurement/integration route, but
it is not presently available to this repository: no account, test-mode
enablement, licence, credentials, or rights grant is present. We will not
attempt unauthenticated calls, guess credentials, or treat documentation as
proof of entitlement.

### Source decision and next acceptance path

- Do not ingest either ShareSansar-derived archive into the canonical reviewed
  manifest. Their common upstream is not independent confirmation; publication
  does not grant this project data rights.
- Do not reverse-engineer or bypass NEPSE's token/access controls.
- The direct official-source route remains the preferred route if NEPSE
  provides an authorized capture method and adequate history. A rolling
  365-day window could support a 55-session test, but the source must first be
  accessed lawfully and the capture independently reviewed.
- The practical alternative is a licensed Share Hub account with price-history
  service enabled and this project's server IP allow-listed. Only after access
  and permitted-use terms are established should an adapter capture data into
  quarantine for row-level reconciliation, identity/lifecycle review,
  corporate-action checks, and canonical admission.
- No external data has been imported or promoted by this investigation.

### Acceptance decision

- Implementation and synthetic unit/API tests: complete.
- Latest verified code CI (commit `28fed929`): 2/2 workflows passed.
- Documentation-only follow-up commit: CI result pending/none reported yet.
- Production-reviewed historical rows: unavailable.
- Real-market backtest and out-of-sample calibration: not performed.
- Production signal eligibility: not granted.
- PR remains open and unmerged pending the project's normal review.

Do not mark this feature fully validated, production-ready, or performance-
tested until a sufficiently long, complete, independently reviewed OHLCV
history is admitted through the canonical evidence process.


### Follow-up provenance check (2026-11-27)

A second independent public project, YONEPSE, credits
`socrateai-official/nepse-open-data` specifically as an upstream for its
NEPSE sub-index and headline index history (2003–2025). This corroborates that
SocrateAI is used as a source by another project, but it does not identify the
upstream origin or licensing authority for SocrateAI's **individual stock
OHLCV** files. It is not independent validation of those stock rows:
https://shubhamnpk.github.io/yonepse/pages/sources.html

The SocrateAI commit history also records late additions to already-published
sessions: its 2026-11-19 commit says BENH was backfilled into 12 prior sessions
after the exchange supplied its history, and its 2026-10-02 commit says a
GBIMEP row was added for 2026-09-18 after it arrived late. This is useful
evidence that late-arriving records can occur, but it is not a complete
correction/revision policy or a guarantee that all such changes are logged:
https://github.com/socrateai-official/nepse-open-data/commits/main/

The repository's public issue tracker contains an unanswered request asking
the publisher to clarify the data licence scope, upstream rights, private
retention, update/correction policy, and whether the stock OHLCV values are
genuine end-of-day source values. As checked on 2026-11-27, that issue remains
open with no public comments. This is not permission and cannot substitute
for a publisher response:
https://github.com/socrateai-official/nepse-open-data/issues/2

The current-day adjusted and unadjusted stock files sampled for 2026-11-26
have the same rows and values in the returned sample. That is expected for
same-day prices but does not validate the historical adjustment factors or
corporate-action treatment. No files were downloaded into this project,
reconciled as an acceptance dataset, or promoted to the canonical manifest.


### Controlled overlap sample — BGWT (2026-11-27)

A read-only comparison was performed between the project's captured official
NEPSE per-security history response for BGWT (2026-10-05 through 2026-11-26)
and the corresponding 29 daily rows in SocrateAI's unadjusted stock CSVs.
This is a bounded one-security sample, not a market-wide acceptance audit.

- High, low and close: **29/29 exact matches**.
- Volume: **14/29 exact matches**.
- The other 15 volume values in the SocrateAI files were lower than the
  official NEPSE quantity by 1–17 shares.
- Open: not independently comparable because the official per-security
  response captured in this project does not expose an open field.

The result is mixed: it supports the sampled high/low/close values, but it
demonstrates a repeatable volume discrepancy and cannot validate the open,
other securities, historical dates, corporate actions, or the publisher's
rights. The source remains quarantined and is **not eligible** for canonical
promotion or signal testing. The 29 rows must not be generalized to the
archive as a whole.

### Additional one-session structural audit — SocrateAI (2026-11-27)

A read-only structural check was run on the publisher's unadjusted daily file
for 2026-11-26
(`ohlc_unadjusted_stock/unadj_2026-11-26.csv`). It contains 349 rows with
the columns date, close, open, high, low, volume and symbol.

- 349/349 date-symbol keys are unique in this one-file sample.
- No duplicate keys were found.
- No negative volumes or basic OHLC-bound violations were found
  (high below open/close/low or low above open/close/high).
- 13/349 rows have zero volume. The file mixes instrument types, so this
  requires instrument-universe classification before treating all rows as
  tradable common-equity observations.
- This is a single-date structural check only. It does not establish complete
  market coverage, historical continuity, source accuracy, identity/lifecycle,
  or corporate-action correctness.

There is also a licensing metadata ambiguity: the repository's root
`LICENSE` file contains MIT-style text that expressly says it applies to
the dataset, but GitHub's repository API currently reports the repository
licence as `Other` with SPDX `NOASSERTION`. That API classification does
not invalidate the text file, but it means automated licence detection does
not independently confirm an SPDX licence. More importantly, neither the
text nor metadata proves that the publisher owns or is authorized to
sublicense upstream exchange/provider data.

The repository's commits inspected for the recent daily updates are unsigned
according to GitHub's commit-verification metadata. This is not evidence that
the data is false; it means those commits do not provide a verified
cryptographic publisher signature. The existing open provenance question
(issue #2) has no comments as of this check. No publisher clarification or
permission has therefore been obtained.

This additional sample does not change the source decision: keep the archive
quarantined and do not promote it into the canonical reviewed-row manifest.

### New upstream/provider leads — 2026-11-27

SocrateAI's public organization profile says its work is built in collaboration
with Nepalytix for real NEPSE data and lists `support@socrateai.com` as its
contact. This makes Nepalytix a specific provenance lead for the SocrateAI
archive, but it does not prove that Nepalytix supplied the individual-stock
CSV files or that SocrateAI has sublicensing rights:
https://github.com/socrateai-official
https://github.com/socrateai-official/nepse-open-data

Nepalytix publicly describes open JSON REST endpoints and five-year price
history. Its terms say market data comes from public NEPSE records and
third-party providers, prohibit scraping/copying/redistribution without
written permission, and state that its REST API is for personal/research use
while commercial API use requires a separate written agreement with Cognify
System Pvt. Ltd. The terms do not clearly settle permanent local retention,
derived datasets, or redistribution of outputs. Therefore, do not harvest
the open endpoints or ingest Nepalytix data into this project until written
scope and retention permission are clarified:
https://nepalytix.com/
https://nepalytix.com/terms

A stronger documented authorized-provider route has also been identified:
Source Code Pvt. Ltd. markets its Market Data Provider (MDP) as a NEPSE-
licensed data platform, describing live and 5–10 years of historical market
data, API packages, and corporate-action coverage. Its public contact is
`info@sourcecode.com.np` / `+977 980-2071475`. This is a vendor claim, not
independent proof of a specific licence grant to this project. A written
quote and contract must specify historical daily OHLCV fields, security
universe and lifecycle, corporate-action adjustments, correction/version
history, permitted local retention, backtesting, derived analytics, internal
use, and any public display or redistribution rights before integration:
https://sourcecode.com.np/product/mdp
https://mdp.sourcecode.com.np/

The provider's public material makes this a better route to pursue than
unauthorized scraping or republishing community archives. No account,
contract, credentials, or licence has been obtained; no API calls or data
imports were made. The signal engine remains fail-closed until a properly
authorized dataset is captured, reconciled and admitted.

### Additional authorized-provider comparison — 2026-11-27

A second commercial API route was checked: Share Hub's published NEPSE Data
API documentation specifies a `price-history/{symbol}` endpoint returning
daily `time`, `symbol`, `open`, `close`, `high`, `low`, and `volume`.
The documented `ALL` period is described as history from listing. Access
requires a Data API account, bearer-token authentication, server IP
allow-listing, and the relevant licensed service/package. Test mode must be
enabled by Share Hub. Public documentation does not state a definitive
retention/backtesting/derived-analytics grant, so these must be negotiated
in writing before ingestion:
https://sharehubnepal.com/data/nepse-data-documentation/

Provider route comparison:
- **Source Code MDP:** markets itself as a NEPSE-authorized/API data provider;
  its published MDP material describes NEPSE data, corporate actions and
  API integration. Obtain written confirmation of the exact daily OHLCV
  history endpoint, historical depth, corporate-action methodology and
  retention/backtesting rights.
  https://sourcecode.com.np/
  https://mdp.sourcecode.com.np/
- **Share Hub Data API:** most explicit public endpoint contract for the
  exact daily OHLCV fields needed by this engine, including ALL history.
  Obtain a quote and written confirmation of local retention, backtesting,
  derived signals and user-facing analytics rights.
  https://sharehubnepal.com/data/nepse-data-documentation/
- **Nepalytix/SocrateAI public datasets:** useful provenance lead and
  research material, but upstream rights and permanent local use remain
  unresolved; keep quarantined.

No commercial API credentials or licences are available in the project.
No paid endpoint was called and no vendor data was imported. This comparison
narrows the procurement path but does not satisfy the real-data acceptance
gate.

### Freely downloadable public dataset candidate — 2026-11-27

The public repository `binayabaral/nepal-market-data` is a practical
no-cost candidate for a quarantined research copy:
https://github.com/binayabaral/nepal-market-data
https://binayabaral.github.io/nepal-market-data/

Its publisher states that the dataset is MIT-licensed and exposes per-symbol
CSV files without authentication. The documented schema includes
`published_date, open, high, low, close, per_change, traded_quantity,
traded_amount, status`. The repository tree contains 472 NEPSE CSV files
including the index and a symbol reference table. Its reference master
distinguishes ordinary shares from debentures, promoter shares, funds and
merged instruments; scanner ingestion must not treat every CSV as an
ordinary equity.

The publisher explicitly attributes NEPSE stock prices to ShareSansar and
historical backfill to `Aabishkar2/nepse-data`. The latter README describes
the same nine-column schema and says it is MIT licensed, but no LICENSE file
was present at the inspected repository root. The downstream MIT declaration
is therefore recorded as the publisher's licence statement, not independent
proof of rights in upstream ShareSansar material. The archive is unofficial,
best-effort and explicitly disclaims accuracy/completeness guarantees.
Its prices are unadjusted for bonus issues, rights issues and splits.

A bounded structural sample was inspected directly from
`data/nepse/ADBL.csv`:
- 3,684 rows, 2010-09-16 through 2026-11-26.
- 0 duplicate dates and 0 non-finite numeric rows.
- 405 rows (11.0%) violate basic OHLC bounds (high below open/close/low,
  or low above open/close/high, or non-positive low).
- 112 rows have zero turnover.
- The reference master classifies ADBL as an ordinary, listed commercial bank.

This single-symbol check is not a full-archive audit. However, the observed
OHLC violations are sufficient to reject this sample as signal-engine input
until row-level correction/reconciliation is completed. Do not import it into
the canonical reviewed-row manifest or represent it as verified exchange
data. It may be retained as a public, secondary research candidate for
quarantine and cross-source diagnostics only.

Decision: use freely accessible public files for source discovery and
quarantined diagnostics; do not bypass the existing eligibility gate. A
candidate dataset becomes eligible only after full-universe schema and
duplicate checks, OHLCV validation, instrument/lifecycle filtering,
corporate-action handling, overlap reconciliation against independent
evidence, and a documented decision on upstream data-use rights.

#### Expanded ten-symbol structural spot check

To avoid drawing a conclusion from ADBL alone, the same basic checks were
run on ten ordinary-equity CSVs in the public candidate archive. Each file
had zero duplicate dates. Basic OHLC-bound violations were:

| Symbol | Rows | Invalid OHLC rows | Invalid % |
| --- | ---: | ---: | ---: |
| ADBL | 3,684 | 405 | 10.99% |
| NABIL | 3,538 | 556 | 15.72% |
| NTC | 3,558 | 481 | 13.52% |
| HRL | 658 | 1 | 0.15% |
| NICA | 3,039 | 257 | 8.46% |
| API | 2,496 | 113 | 4.53% |
| AHPC | 3,785 | 587 | 15.51% |
| MEHL | 717 | 0 | 0.00% |
| RHGCL | 962 | 0 | 0.00% |
| ULHC | 717 | 0 | 0.00% |

These are spot-check results, not a full-archive score. They show that
quality is heterogeneous: three newer symbols passed this narrow OHLC
bound check, while six of the other seven had material violations. A clean
sample does not establish accuracy, source independence, corporate-action
correctness, or licensing. The dataset remains quarantined as a whole; any
future symbol-level research subset must preserve source lineage and undergo
independent reconciliation before it can be admitted.

#### Research-only engine-rule smoke check on clean public samples

For a narrow smoke check, the engine's published 20-session breakout,
SMA20/SMA50, 1.5x relative-volume and candle-close rules were independently
recomputed against the three sample files that passed the preceding OHLC
spot check. This was not a server API call and did not set
`eligible=True`.

| Symbol | Observations | As of | Relative volume | Rule result |
| --- | ---: | --- | ---: | --- |
| MEHL | 717 | 2026-11-26 | 1.79x | no_confirmation |
| RHGCL | 962 | 2026-11-26 | 3.75x | no_confirmation |
| ULHC | 717 | 2026-11-26 | 0.87x | no_confirmation |

All three had zero structural OHLCV errors under the scanner's current
basic rules in this sample. None met the full bullish or bearish conjunction
on the last available session. These are descriptive outputs from an
unverified, unadjusted secondary dataset—not validated signals, investment
advice, or evidence of predictive performance. The server-reviewed manifest
remains empty, so the production/API engine must continue to return UNKNOWN
for these records.

### Full public-archive audit automation added — 2026-11-27

A reproducible, read-only full-universe audit has now been added:
- `backend/audit_public_nepal_market_data.py`
- `backend/tests/test_audit_public_nepal_market_data.py`
- `.github/workflows/public-nepse-data-audit.yml`

The workflow pins the public archive to the commit SHA resolved at audit start,
reads the publisher's instrument reference master, selects every row marked
`instrument_type=ordinary` and `status=listed`, and audits the matching
per-symbol CSV files. It checks header/schema, missing symbol files, malformed
rows, ISO dates, duplicate dates, chronological order, finite numeric fields,
OHLC bounds, negative/fractional volume, negative/zero turnover, and
percentage-change formatting. It writes a per-symbol JSON report as a
30-day GitHub Actions artifact.

This automation is intentionally read-only: it does not copy any source rows
into project datasets, modify the public archive, promote canonical records,
or enable signal eligibility. Its structural gate is separate from source
rights, exchange accuracy, session-calendar verification, historical
security identity and corporate-action adjustment. A clean structural report
would still be only a necessary, not sufficient, condition for research use.

The full-universe run is pending the GitHub Actions execution on this PR. Until
that report is available and independently reconciled, the previous ten-symbol
spot-check findings remain the only completed local structural sample.

#### Full-universe public archive audit result — 2026-11-27

The new GitHub Actions audit completed successfully as an audit process on
public archive commit
`944bc95872e46b299625091f6c9f32f57010e71a`. The parser tests passed and all
285 ordinary-listed symbol files in the publisher's reference master were
downloaded and audited; there were no missing files or download errors.

| Measure | Full-universe result |
| --- | ---: |
| Ordinary listed equity files expected / audited | 285 / 285 |
| Rows inspected | 439,116 |
| Structurally valid rows under the audit's strict checks | 402,234 |
| Invalid OHLC-bound rows | 35,228 (8.02%) |
| Positive-volume rows with zero turnover | 3,682 |
| Invalid percentage-change values | 2 |
| Duplicate dates | 0 |
| Invalid dates | 0 |
| Out-of-order transitions | 0 |
| Malformed rows | 0 |
| Blank/non-finite numeric fields | 0 |
| Negative/fractional volume | 0 |
| Negative turnover | 0 |
| Symbols with at least one quality issue | 181 / 285 (63.51%) |
| Observed coverage envelope | 1995-07-20 to 2026-11-26 |

The archive audit workflow completed with a successful execution status, but
the **data quality gate is FAIL**. These are separate statuses: successful
automation means the audit completed and produced its report, not that the
data passed. The per-symbol report is retained as the
`public-nepse-secondary-archive-audit` GitHub Actions artifact for run
45894621663:
https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45893777462

The report's structural counts do not certify exchange correctness or
completeness. The publisher attributes its daily NEPSE prices to ShareSansar
and historical backfill to Aabishkar2/nepse-data; the archive's MIT notice
does not independently establish upstream data sublicensing rights. Prices
are unadjusted for bonus issues, rights issues and splits. Accordingly:
- Keep the complete archive quarantined from canonical reviewed rows.
- Do not use its raw returns for backtesting or production signal ranking.
- Do not repair the 35,228 OHLC exceptions by guessing which field is wrong.
- Resolve zero-turnover and percentage-change anomalies with source evidence.
- Reconcile any candidate records with independent official or otherwise
  authorized evidence, including historical security identity and corporate
  actions, before considering a narrow symbol/date subset for admission.

The audit implementation also corrects the meaning of `valid_rows`: a row is
counted valid only if all strict structural checks pass, including OHLC,
volume, turnover and percentage-change rules. The repeat run after this fix
reports 402,234 valid rows, not merely rows with parseable numeric fields.

#### Official NEPSE overlap reconciliation — 2026-11-27

The full public archive was additionally compared with the project's pinned
official NEPSE per-security history captures for the same recent window.
The audit verified SHA-256 for each official raw response against the
committed `SHA256SUMS` manifest before comparing rows.

| Measure | Result |
| --- | ---: |
| Official symbols with captured response | 281 |
| Official symbol-date rows | 8,142 |
| Public rows found on official dates | 8,079 |
| Official explicit zero-activity rows absent from public CSVs | 63 |
| Public missing active rows | 0 |
| Public symbol files missing for captured official symbols | 0 |
| Compared fields per matched row | 5 (high, low, close, volume, turnover) |
| Total field comparisons | 40,395 |
| Fully matching rows after documented turnover-rounding tolerance | 8,078 / 8,079 (99.9876%) |
| Material field mismatches | 1 |

The publisher intentionally omits dates when a security did not trade; all
63 unmatched official rows were explicit zero-activity rows, so those absences
are consistent with the public archive's stated missing-rather-than-forward-
fill policy. There were no missing public rows for official positive-activity
dates.

The one material mismatch is **CFCL on 2026-11-18**:
- Public archive: close **636**.
- Official NEPSE history: close **589.9**.
- High (640), low (589.9), volume (307,576) and turnover (NPR 184,031,033.4)
  agree between the two sources.
- The public row is therefore not safe to use as-is even though it passes
  basic OHLC bounds; the official close contradicts it.

Three smaller turnover differences in the initial strict comparison were
NPR 0.02–0.03, caused by the public CSV's one-decimal turnover formatting
versus the official response's two-decimal precision. The audit now allows a
0.05 NPR rounding tolerance for turnover. This leaves the single CFCL close
mismatch unresolved. High, low, close, volume and turnover were compared;
**open, percentage change and status were not independently cross-checked**.

The comparison demonstrates strong agreement in this bounded recent window,
but does not validate the full 1995–2026 archive, open prices, corporate
actions, historical security identity, data-use rights or predictive value.
The archive remains quarantined. Do not silently overwrite CFCL's public
value or promote any other rows from this comparison into the canonical
reviewed manifest.

#### Concrete unreviewed row examples and diagnostic samples — 2026-11-27

The pinned public archive snapshot contains these inspectable examples:

**ADBL — 2010-09-23** (`data/nepse/ADBL.csv`, data line 5):
- Open 116, high 120, low 117, close 120.
- Volume 8,417; turnover 0.
- OHLC violation: the reported open (116) is below the reported low (117).
- Turnover violation: positive volume with zero reported value.
- This row must be quarantined, not repaired by inference.

ADBL has 405 OHLC-bound violations and 112 positive-volume/zero-turnover rows in its 3,684-row public file in the pinned audit snapshot. The per-symbol audit counts are exact for that snapshot.

**CFCL — 2026-11-18**:
- Public archive: open 598.5, high 640, low 589.9, close 636, volume 307,576, turnover NPR 184,031,033.4.
- Pinned official NEPSE capture: high 640, low 589.9, close 589.9, volume 307,576, turnover NPR 184,031,033.4.
- The public close differs by NPR 46.1. The public row passes OHLC bounds but fails independent source reconciliation. Official history does not supply open, so open remains unverified.

The audit now retains row-level diagnostic samples by defect type (including the date and relevant OHLC/volume/turnover values) in the full per-symbol artifact, capped at five samples per defect type per symbol. Aggregate counters still count every detected row. The updated artifact is run 45894621663: https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45894621663. This allows a reviewer to inspect examples without inflating the artifact with every defective row.

**Why these records remain unreviewed:** (1) the public publisher describes the archive as unofficial and sourced from third parties; (2) the full archive has widespread structural defects; (3) official overlap reveals at least one material close discrepancy; (4) official history does not independently verify open; (5) historical security lifecycle and corporate-action adjustment are not established for the complete archive; and (6) the repository's publication licence does not independently prove rights to sublicense underlying market data. No automatic correction, canonical promotion or trading use is allowed.

#### Second free archive spot-check — SocrateAI NEPSE Open Data

The public `socrateai-official/nepse-open-data` repository contains 4,817
unadjusted daily stock CSVs dated from 2007 through 2026-11-26 and publishes
an MIT-style licence that expressly claims to cover the dataset. Its README
does not identify the upstream source or document the collection, correction,
corporate-action adjustment or historical security-lifecycle methodology.
The advertised `meta/symbols.csv` is not present in the current repository
tree (the `meta/` directory contains only `.gitkeep`). Daily files mix
ordinary equities with other instruments, so the rows require an independently
verified instrument crosswalk.

Two spot checks demonstrate why this candidate also needs reconciliation:

- **ADBL, 2010-09-23:** SocrateAI reports open 117, high 120, low 117, close
  120, volume 8,417. The other public archive reports open 116 with the same
  high, low, close and volume, making its open impossible because it is below
  the day's low. There is no pinned official per-security history for 2010 in
  this project, so the SocrateAI value is a conflicting secondary observation,
  not a verified correction.
- **CFCL, 2026-11-18:** SocrateAI reports close 589.9, agreeing with the
  official NEPSE close and contradicting the other public archive's 636.
  However, SocrateAI reports volume 307,567 versus 307,576 in the official
  capture. Its close is corroborated, but its volume is not exact.

The audit now fetches the SocrateAI daily CSV for each date in the pinned
official review window and compares high, low, close and volume against the
hash-verified official captures. Open and turnover are unavailable from the
official historical endpoint and therefore cannot be compared. The automated
full-window result is retained in the same public archive audit artifact.
This is a bounded reconciliation exercise only; it does not establish
upstream data rights or authorize canonical promotion.

#### Full-window SocrateAI reconciliation result — 2026-11-27

The audit downloaded all 29 SocrateAI unadjusted daily CSVs for the pinned
official review dates and compared the 281 captured equity candidates. The
SocrateAI source snapshot was pinned to commit
`70324524df83eaa7c2964441ad4026d6ab00cc7e`; its full per-row exceptions are
retained in audit artifact run 45894916469:
https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45894916469

| Measure | Result |
| --- | ---: |
| Official rows in window | 8,142 |
| SocrateAI date files expected / found | 29 / 29 |
| SocrateAI rows across those files (mixed instruments) | 10,025 |
| Official rows with matching public date+symbol row | 8,079 |
| Missing public rows for official active dates | 0 |
| Missing public rows for official zero-activity dates | 63 |
| Fully matching official rows (high, low, close, volume) | 3,669 / 8,079 (45.42%) |
| Field comparisons | 32,316 |
| Field mismatches | 4,642 |
| High / low / close / volume mismatches | 217 / 130 / 12 / 4,283 |
| Duplicate symbol rows / malformed rows / invalid OHLC rows | 0 / 0 / 0 |

The data is structurally cleaner in this 29-date sample than the other public
archive, but it does **not** reconcile accurately enough with official NEPSE:
volume differs on 4,283 comparisons, with additional high/low/close
differences. No official active rows are missing, but that does not make
differing values interchangeable. The candidate fails the cross-source gate.

CFCL on 2026-11-18 illustrates the mixed result: SocrateAI's close (589.9)
matches official NEPSE and the other public archive's close (636) is wrong,
but SocrateAI volume (307,567) differs from official volume (307,576). On
ADBL 2010-09-23, SocrateAI's open is 117 while the other archive says 116;
the official capture window does not reach 2010, so neither historical open
is independently established.

The comparison covers high, low, close and volume only. Official history does
not supply open or turnover in this captured endpoint. No source data is
promoted. Despite the MIT-style dataset licence, upstream provenance and
sublicensing authority remain unverified, and the repository does not provide
the advertised symbol-master CSV or documented adjustment methodology.
