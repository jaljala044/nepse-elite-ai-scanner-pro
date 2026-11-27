# P443 partial-field historical recovery policy

- Preserve every raw OHLCV row and its source hash unchanged.
- Never write a reconstructed partial candle into canonical daily_prices.
- A field is eligible for research-only replacement only when its source is authenticated, symbol/date matched, independently corroborated, and derivation documented.
- Keep unresolved fields null in research views; never forward-fill from adjacent sessions.
- Volume and turnover are separate measures. Require transaction-level quantity and amount reconciliation before accepting either.
- If open is unreliable, retain verified high/low/close/volume only as separately sourced fields; mark the candle incomplete and exclude it from indicators, backtests, and signals requiring a complete OHLCV bar.
- Check corporate actions, splits, symbol lifecycle and trading calendar before joining dates.
- Release requires independent reviewer approval, regression tests, and an immutable correction ledger with before/after values and evidence hashes.
- This policy does not authorize any of the 1,329 quarantined records for canonical admission.
