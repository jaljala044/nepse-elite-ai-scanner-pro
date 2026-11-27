# Official NEPSE market activity archive review

Reviewed main archive `data/evidence/raw/nepse/market-summary-history/2026-11-27/` on 2026-11-27.

The capture report records HTTP 200, 31,150 bytes and SHA-256 `7165788ee78b0bfcb5cbcbc5f204120c258e67a5081fa61c9b4d78058c14a546`. The checksum manifest agrees; raw bytes were not independently rehashed in this review.

The payload analysis reports 229 unique activity-confirmed dates from 2025-11-27 through 2026-11-27, zero duplicate dates and zero invalid dates. Weekday counts (UTC date labels, Sunday=0): {"0":16,"1":46,"2":47,"3":47,"4":45,"5":28}.

## Calendar decision

Treat these as review candidates for observed market activity, not a complete calendar or per-security execution proof. Missing dates cannot be classified as closures. No evidence for the 12 unresolved 2016–2020 candles is supplied by this archive. Do not release quarantine or classify repeated candles automatically. Reconcile per-security floorsheets and exchange notices; independently verify raw bytes before promotion. No production or AI recommendation authorization.
