# Steps 96–97 — primary document and corporate-action batch intake

## Step 96: primary listing/lifecycle document bytes
- Validate operator-supplied PDF bytes, PDF signature, approved NEPSE/CDSC HTTPS host, HTTP status/content type metadata, safe archive path, retrieval/availability timestamps, decision cutoff and SHA-256.
- Preserve publisher and event references with exact byte count and digest.
- The verifier does not fetch URLs or prove publisher authenticity. A PDF signature only establishes file format, not document legitimacy.

## Step 97: corporate-action batch coverage
- Aggregate individually validated Step 95 CSV intake outputs by action ID.
- Require at least two distinct publishers including NEPSE/CDSC primary evidence.
- Compare action facts across publishers and block any disagreement for manual resolution.
- Report missing event evidence and invalid source files.

## Strict boundaries
No source URLs are fetched. No real PDF/CSV source records are included. Synthetic fixtures test validation only. Review readiness is not corporate-action admission, factor approval, historical dataset admission, OHLCV adjustment or scanner activation.
