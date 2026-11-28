# Steps 100–109 — historical source cohort pipeline

1. Normalize OHLCV fields and dates into a canonical schema; reject malformed rows.
2. Attach provider lineage to every normalized observation.
3. Detect duplicate symbol/session records without silently deduplicating.
4. Compare matching sessions across providers and expose field-level conflicts.
5. Measure missing sessions against an explicit expected trading-session calendar.
6. Validate effective-dated symbol/security mappings with evidence references.
7. Produce per-symbol coverage and quality reports.
8. Block cohort qualification on duplicates, low coverage or source conflicts.
9. Preserve a research/review qualification state distinct from production admission.
10. Emit machine-readable cohort output and explicit fail-closed production flags.

## Source policy
ShareHub, Chukul, ShareSansar, Punji and the other project-listed platforms are accepted collection channels under the project owner's NEPSE-derived distribution assumption. Record-level provenance, schema, dates, identity, anomalies and cross-checks still apply. Pending evidence can be retained for research with confidence labels; conflicts are surfaced for review.

## BENH correction
A chart/floorsheet earliest-date mismatch cannot be called corroborated, even if archive bounds exist. Floorsheet completeness must be explicitly verified. An incomplete or mismatched history remains partial evidence.

## Boundaries
This is a deterministic intake and cohort-quality layer. No real provider records are embedded or downloaded by these tests. Cohort review qualification is not production admission, backtest validation or scanner activation.
