# Steps 40–41: Source registry, queue replay and mark-to-market risk

## Step 40 — Source registry and capture receipts
- A governed source registry binds publisher/source IDs to HTTPS hostnames, dataset kinds, authority class, review metadata and approval state.
- Capture runs accept exact bytes supplied by a separately operated connector or manual capture process, enforce approved source/host/dataset pairing, point-in-time capture cutoff and existing strict CSV intake validation.
- Each admitted capture receives a SHA-256 receipt. Duplicate payload hashes are rejected and flagged when the publisher identity differs.
- This is not a live connector, publisher authentication, proof of independent ownership, or completeness certification. Different IDs/domains do not establish independent publishers.

## Step 41 — Event-driven queue and portfolio risk
- Passive queue replay applies verified trade prints, ahead/behind cancellation attribution, new order priority and book-reset invalidation. Unknown cancellations do not reduce estimated queue ahead.
- Mark-to-market portfolio curve values open inventory at verified daily closes, deducts configurable transaction costs, tracks cash/market value/equity and reports unrealized peak-to-trough drawdown.
- Missing marks and oversells fail closed. Queue model and mark-to-market calculator are separate research primitives; integration with portfolio candidate replay and full exchange event feeds remains a follow-up.

## Research and data limitations
No network scraping or source login is performed. Queue event completeness, sequence ordering, hidden liquidity, auction rules, corporate actions and settlement release calendars require separately verified inputs. No live order routing, strategy performance claims or calibrated probabilities are enabled.
