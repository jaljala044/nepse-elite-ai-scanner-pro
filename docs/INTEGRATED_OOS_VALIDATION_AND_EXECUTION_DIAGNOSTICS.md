# Integrated OOS validation and execution diagnostics

## Step 36 — Integrated research validation
The integrated report composes independent strategy/horizon portfolio replay, signal outcome ledger, trade-level audit and the existing fold-stability selector. The final assessment accepts only explicitly labelled out-of-sample signals, replay runs and fold records. It will reject mixed train/validation/OOS input rather than silently filter it. Missing strategy/horizon pairs remain missing and cannot become winners.

## Step 37 — Execution-quality diagnostics
The report groups closed, settlement-pending, replay-rejected and unmatched signals by strategy and horizon. It includes settlement-lock stop counts and average observed maximum favorable/adverse excursion (MFE/MAE) when the replay provides those fields. Missing excursion observations remain unavailable. MFE/MAE are path diagnostics, not executable profit or stop-fill estimates.

## Promotion boundary
Strategy eligibility still requires portfolio-level OOS sample, positive expectancy, profit factor, drawdown and stable chronological walk-forward folds. The report is research-only, not a live signal or production promotion. No live NEPSE dataset or performance claim is included.
