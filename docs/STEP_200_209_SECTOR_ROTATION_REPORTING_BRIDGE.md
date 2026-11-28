# Steps 200–209: sector rotation reporting bridge

1. Reuse the point-in-time verified sector rotation output rather than rebuilding sector returns in the reporting layer.
2. Reject stale decision sessions and non-observed rotation snapshots.
3. Validate sector counts and overall sector coverage before rendering a report.
4. Adapt observed 1W/1M/3M/6M median constituent returns to the existing market-health participation contract.
5. Preserve per-window missing evidence as insufficient; never fill or infer returns.
6. Publish a ranked sector report with Leading, Improving, Neutral, Weakening and Lagging labels only when the upstream score is observed.
7. Include weighted NEPSE-relative excess return, percentile rank and per-horizon coverage.
8. Explicitly mark the report descriptive-only; it is not an official sector index, broker-flow report or stock trade signal.
9. Integrate the optional verified rotation snapshot into market-health pipeline output.
10. Add regression tests for ordering, stale snapshots, insufficient evidence, withheld labels and coverage validation.

## Data and safety contract

The upstream rotation engine remains responsible for point-in-time membership, 127 exact verified sessions, corporate-action-aware prices, NEPSE benchmark rows and source provenance. This bridge does not upgrade provenance or promote research data. Market-health participation still validates separate sector-universe and price-evidence manifests.

No live NEPSE sector ranking, broker accumulation, volume expansion, turnover growth, or production recommendation is claimed by these synthetic tests.
