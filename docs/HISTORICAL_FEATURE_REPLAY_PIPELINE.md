# Historical feature replay pipeline — Steps 30–31

## Step 30: universe timeline integrity
Permanent security IDs remain canonical. Explicit effective intervals are checked for overlaps and unexplained gaps. A symbol may be reused over time, but two securities may not own the same symbol on one session. Unknown intervals are errors, not inferred active membership.

## Step 31: point-in-time feature snapshots
The feature builder consumes admitted panel rows and an explicit timezone-aware decision cutoff for each session. It computes 5/20/50/150/200-session simple moving averages, RSI(14), 20-session volume ratio and 5/20/60/120-session returns. Each snapshot has a deterministic SHA-256 fingerprint binding the decision cutoff, all OHLCV observations used in its rolling history, their source/evidence references and availability timestamps, the emitted feature values, and aligned benchmark lineage when used. Warm-up-incomplete snapshots are explicitly labeled and are not signals.

Benchmark-relative calculations are emitted only when matching benchmark history is supplied and available by the same cutoff. This implementation does not generate Wyckoff/SMC/broker/fundamental claims or BUY/SELL recommendations. It is research-only; empirical performance requires verified NEPSE history and downstream replay.
