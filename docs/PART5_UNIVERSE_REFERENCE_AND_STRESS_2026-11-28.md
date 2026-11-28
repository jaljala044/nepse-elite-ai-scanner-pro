# Part 5 comparative archive experiment — 2026-11-28

Classification: retrospective research only; production_eligible=false; independent_holdout=false.

Inputs downloaded and SHA-256 verified against unified-archive-research workflow:
- Price artifact 15133662109: 61449bd6449fbde66f20951192a66ab62e4da7b2fb02a1a29c3c1c33616f4985.
- Broker artifact 15150674205: 01af48fd9cbf4e310ff16bc61c235081080314073d1fcb597e682a391fe120cc (downloaded, not used in this experiment).
- Project session calendar blob c5fe82bea1796fd14a004878c1c7178a75c0bf31; 659 accepted sessions 2024-01-01 through 2026-11-20.
- 281 symbols, 154467 candidate records, 79143 pre-quarantined records not used, no structurally invalid symbol groups. Zero additional repeated adjacent accepted-session signatures in candidate file.

Reference experiment: chronological contiguous prefixes, next-session open to holding-session close, per-symbol nonoverlap, 1 percentage-point cost. Six rules (unconditional, 20-session momentum, 20-session breakout, four provisional price-volume checks, seven Minervini checks, Wyckoff SOS/spring proxy). Local Python mirrors selected conditions, not full repository-engine execution. No certified settlement, actual fills, independent holdout, portfolio or adjustment evidence.

| Rule | 2025 5-session n / mean % | 2026 5-session n / mean % | 2025 20-session n / mean % | 2026 20-session n / mean % | 2025 60-session n / mean % | 2026 60-session n / mean % |
|---|---|---|---|---|---|---|
| Unconditional | 8869 / -0.908 | 6807 / -1.002 | 2372 / -1.036 | 1594 / -1.795 | 699 / -4.029 | 311 / -9.596 |
| Momentum | 4740 / -1.332 | 3328 / -1.256 | 1620 / -1.781 | 1031 / -2.456 | 628 / -4.296 | 237 / -10.328 |
| Breakout | 1062 / -1.748 | 526 / -1.808 | 711 / -2.876 | 336 / -3.223 | 433 / -9.335 | 67 / -13.281 |
| Provisional | 990 / -1.822 | 486 / -1.922 | 684 / -3.011 | 320 / -3.330 | 430 / -9.622 | 61 / -13.043 |
| Minervini | 284 / -1.839 | 31 / -0.529 | 109 / -3.682 | 5 / +2.028 | 65 / -5.618 | unavailable |
| Wyckoff proxy | 1105 / -1.844 | 710 / -1.264 | 816 / -2.651 | 422 / -2.626 | 425 / -7.096 | 88 / -9.260 |

Separate hypothetical 2025 execution stress: NPR 1m starting cash, 5% initial capital per position, maximum ten simultaneous positions, 0.1% daily-volume participation, 20bp each-side adverse slippage, 0.36% brokerage with NPR10 minimum, 0.015% regulatory, NPR25 DP, 7.5% tax on positive simplified gain; all assumptions not independently certified. 10% prior-close band with NPR0.11 tolerance, accepted trading days as settlement proxy, exit after second post-entry session. Stop-first, pending stop on pre-settlement breach, fixed 5-session deadline. Alphabetical entry priority. Unusable paths or exits permanently lock a position in this deliberately severe stress, not a realistic retry model. No same-day exit cash reuse. Not a statement of actual NEPSE fee law.

| Rule | Opened | Closed | Unresolved | Realized net PnL NPR (closed only) |
|---|---:|---:|---:|---:|
| Unconditional |24|14|10|1381.37|
| Momentum |26|16|10|10112.97|
| Breakout |21|11|10|12385.47|
| Provisional |22|12|10|8496.46|
| Minervini |64|54|10|-13987.70|
| Wyckoff proxy |27|17|10|555.15|
| Breakout 3% stop/6% target |19|9|10|4969.75|
| Breakout 8% stop/16% target |21|11|10|10887.01|

All configurations have unresolved positions; total portfolio return and drawdown withheld. Closed-only positive outcomes are selection-biased and cannot justify promotion. The results do not validate strategy accuracy. Local scripts and JSON results were generated separately; repository integration and parity remain pending. Next: exact repository-engine replay, retry model for uncertain exits, historical universe/adjustments, actual settlement and price-band controls, independent holdout.
