# Secondary historical evidence policy (superseded)

This earlier OHLCV-only, three-independent-source policy is superseded by
[Five-year all-equity historical evidence policy](FIVE_YEAR_HISTORICAL_EVIDENCE_POLICY.md).

The current policy collects five years of floorsheet and chart data for every
equity from ShareHub, NEPSE Alpha, Chukul and ShareSansar, checks available
NEPSE reference records, and permits a record to be marked COMPLETE_EVIDENCED
when two lineage-independent sources match exactly. Mero Lagani may be used to
investigate discrepancies. Pairwise Jaccard date-set overlap greater than 0.98
combined with the same upstream_feed collapses providers into one lineage.

Do not use this superseded document's former three-source threshold or its
OHLCV-only restriction. The new policy does not authorize production signals,
deployment, or automatic trading.
