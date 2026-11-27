# Six-Strategy Selection and Feature Ablation

## Step 22 — Selection integration
`select_six_strategies` combines the independent strategy/horizon portfolio replay with the walk-forward fold diagnostics. It uses only an `out_of_sample` portfolio comparison. Each candidate must pass portfolio closed-trade sample size, positive net average trade return, profit factor >= 1, and drawdown limit, as well as the fold module's minimum trade/fold and all-fold stability gates. A winner is selected independently for each horizon using median fold expectancy after both gates pass. Missing strategy/horizon pairs are counted and never scored as neutral.

The portfolio adapter computes average net trade return from closed-position records. Open positions are not treated as closed outcomes. An infinite profit factor is retained when there are gains and no losses.

## Step 23 — Feature ablation
`compare_feature_ablations` compares a full-feature baseline against a single feature group removed, per strategy/horizon and OOS fold. Each pair must share the same universe fingerprint, panel fingerprint, cost model and execution model. It reports trade counts, mean fold expectancy delta, number of folds improved by removal, and direction. Defaults require at least three folds and 30 closed trades in each variant before interpretation.

Ablation may change which trades are selected. The report therefore measures the portfolio-level effect of the variant, not isolated causal importance. Run one feature group at a time, preserve all original signals, and use a later untouched holdout for final confirmation.

## Data and deployment limits
These modules consume supplied OOS outcomes; they do not fetch NEPSE data, generate features, or create trade signals. No live NEPSE historical dataset is presently verified, so no real winner or feature improvement is claimed. Research only; production disabled.
