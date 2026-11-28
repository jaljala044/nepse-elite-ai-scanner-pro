# Verified market sector participation adapter

## Purpose

Provides the 15% sector-participation input to market health using the share
of sectors with positive median constituent returns over four horizons:
1W, 1M, 3M and 6M. It complements sector relative-strength ranking; it does
not infer official sector-index returns or broker rotation.

## Admission contract

- Requires verified sector-universe and price-evidence manifests with matching
  decision session, source IDs and SHA-256 payload digests.
- Requires the existing sector-strength engine output, method
  `median_constituent_return_cross_sector_percentile`, status=observed and
  matching as-of session.
- Requires exact expected sector count and at least 80% observed sector
  returns independently for every 1W, 1M, 3M and 6M window.
- Missing/stale/unverified sector returns withhold the score; no imputation.

## Scoring

- 20%: percentage of observed sectors with positive 1W median constituent return.
- 30%: percentage of observed sectors with positive 1M median constituent return.
- 30%: percentage of observed sectors with positive 3M median constituent return.
- 20%: percentage of observed sectors with positive 6M median constituent return.
- A sector with zero return is not counted as positive.
- Short-term deterioration/recovery warnings compare 1W participation with
  the 6M participation baseline.
- The result is a rules-based participation descriptor, not a probability or
  stock-level signal.

## Limitations

The existing sector engine uses median constituent returns, not official
sector indices. Membership and underlying price manifests must be validated
upstream. Synthetic tests validate logic only. The market-health pipeline
accepts this component through explicit caller-supplied evidence; no live
sector participation score is claimed without verified source artifacts.
