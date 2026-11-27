# Steps 26–27 — Historical Dataset Readiness and Corporate-Action Reconciliation

## Step 26 — Readiness and coverage gate
`assess_historical_dataset_readiness` inventories required OHLCV, open-session calendar, historical instrument universe and corporate-action reports, plus optional floorsheet, broker, sector and fundamental datasets. It checks timezone-aware availability against the decision cutoff, duplicate open sessions, duplicate security/session bars, OHLCV numeric sanity, sample-start universe membership and per-security session coverage.

Status semantics:
- `READY`: all configured required datasets exist, no critical errors, and measured sample-start universe OHLCV coverage meets the configured threshold.
- `PARTIAL`: required inputs pass but optional datasets are absent.
- `BLOCKED`: missing required inputs, point-in-time violations, duplicates, invalid bars, incomplete security histories or other critical gaps.

The default OHLCV session coverage threshold is 100%. Optional floorsheet, broker, sector and fundamental data are never silently imputed. A caller may promote any optional dataset to required via `require_optional`.

## Step 27 — Cross-source corporate-action reconciliation
`reconcile_corporate_actions` requires two distinct source IDs and publisher names, verified/final/rights-approved source envelopes, exact agreement on event terms, and explicit positive price and volume adjustment factors. Conflicts and uncorroborated events are withheld. `apply_reconciled_adjustments` adjusts only bars strictly before the effective date, preserves recorded turnover and rejects unreconciled or non-point-in-time events.

## Guardrails and known limitations
- Modules consume captured reports; they do not download NEPSE data.
- Distinct publisher names are not proof of true independence; external governance must validate source independence.
- Sample-start universe coverage does not prove delisted-security completeness or eliminate survivorship bias. Effective-to universe history is still needed.
- The readiness module measures OHLCV coverage; it does not prove every optional dataset is complete or reconciled.
- Corporate-action factors are required inputs, not derived by this code. Adjustment is not a guarantee of correct issuer terms.
- `READY` means eligible to attempt research-panel assembly, not production or live-trading readiness.
- No real historical dataset, backtest metrics, future probabilities or BUY/SELL signals are claimed.
