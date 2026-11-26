# UNL low-frequency execution and scan disposition — 2026-11-26

## Decision

UNL remains in the equity scan universe, but its scan result must be **UNKNOWN / LOW CONFIDENCE**, with no generated BUY/SELL/HOLD signal, no numeric score, and no assumed no-trade classification until session-level execution evidence is reconciled.

## Evidence reviewed

### 2026-11-25

- NepView's UNL page reports two executed trades, 310 shares, turnover NPR 1.48 crore, with rates from NPR 47,500.10 to NPR 47,800. It identifies 300 shares through brokers 34/38 and a further 10 shares through broker 20.
- NEPSE Quant's daily floorsheet page displays a UNL contract of 300 shares at NPR 47,800, buyer broker 34 / seller broker 38.
- NEPSE Quant's UNL broker page independently summarizes 310 shares and NPR 1.48 crore for the session.
- Interpretation: positive execution is established by the displayed contract evidence; the 300-vs-310 page-level presentation is a reconciliation item, not a basis to claim zero trades.

Sources:
- https://nepview.com/explore/UNL
- https://nepsequant.com/floorsheet
- https://nepsequant.com/stocks/UNL/brokers
- https://nepsedemotrading.com/stocks/UNL

### 2026-11-24 to 2026-11-03 low-frequency observations

NEPSE Quant's UNL broker page reports the following recent session aggregates through 2026-11-25: 24 Nov 72 shares; 23 Nov 332; 20 Nov 50; 19 Nov 80; 18 Nov 43; 17 Nov 30; 13 Nov 40; 6 Nov 340; 5 Nov 100. NepView's history shows additional sparse-volume bars, including 3 Nov 20 shares, 2 Nov 90, 30 Oct 10 and 28 Oct 65. These records support low trading frequency/volume, but do not establish missing sessions or explain repeated OHLCV rows across the full historical archive.

### 2026-11-26

- A current-session floorsheet page exists and reports 49,806 trades across 355 symbols, but the accessible page excerpt does not provide a complete UNL-filtered contract list or a machine-verifiable zero-result response.
- UNL is not in the displayed most-traded-stock summary; absence from a top-stock list is not proof that it did not trade.
- Therefore 26 Nov UNL trade/no-trade state remains UNKNOWN in this review. Do not infer no trade from omission in a ranking or from a chart with no visible movement.

## Chart vs execution interpretation

A daily OHLCV chart is an aggregate view, not a complete contract ledger. For a thinly traded stock:
- A flat close can coexist with one or more executions at unchanged prices.
- Sparse executions can produce low volume and few chart updates.
- A repeated OHLCV row may be a provider carry-forward, a no-trade placeholder, or a true unchanged daily bar. It cannot be classified without dated session and complete floorsheet evidence.
- A missing chart bar does not prove the exchange was closed, and an unchanged chart bar does not prove a trade occurred.

## Required three-state session model

1. `TRADED`: at least one valid UNL contract exists for that date in a complete, session-matched floorsheet.
2. `NO_TRADE`: exchange session is independently confirmed open, floorsheet completeness is validated for that date, and zero UNL contracts are returned.
3. `UNKNOWN`: session status, floorsheet completeness, session-date provenance, or symbol-filter coverage is missing/ambiguous.

No-trade must never be inferred from absent OHLCV, a stale chart, zero volume alone, a missing symbol in a top-N table, or an incomplete floorsheet page.

## Scanner change

The scanner now emits UNL as:
- `status=unknown_result`
- `data_status=UNKNOWN`
- `data_quality=LOW_CONFIDENCE`
- `eligibility.eligible=false`
- no signals and no metrics/scores
- explicit reasons: historical OHLCV quarantined, session-level trade/no-trade unresolved, complete primary floorsheet coverage unverified, and historical source lineage/integrity unresolved.

This preserves visibility of UNL without letting it contaminate rankings or being silently dropped from scan coverage.

## Remaining evidence required to clear UNL

- Acquire a complete, date-scoped floorsheet response for each candidate session, including explicit pagination/total-row or source completeness evidence.
- Reconcile per-session UNL contract count, quantity and turnover against daily statistics and chart OHLCV.
- Validate the actual exchange session date from source metadata, not client request date.
- Determine whether historical repeated rows correspond to exchange-open/no-trade dates, provider carry-forward, or source defects.
- Resolve archive source lineage, OHLCV invariant failures, and point-in-time availability before indicators/backtests/training.
- Keep all original raw files immutable; no shifting, interpolation, synthetic bars, or cross-source price splicing.

## Data quality and action

**LOW CONFIDENCE / UNKNOWN. NO TRADE for all horizons until evidence gates clear.** This is a data eligibility decision, not a bearish technical view or a statement that UNL did not trade.
