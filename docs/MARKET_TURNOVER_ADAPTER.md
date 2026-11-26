# Verified NEPSE market turnover adapter

## Purpose
Provides the 20% market-turnover participation input to the market-health
classifier. It measures activity and its recent persistence; it is not a
directional signal. Rising turnover can accompany either accumulation or
distribution and must be cross-checked against verified index trend, breadth,
sector participation and broker evidence.

## Admission contract
- Requires 21 exact NEPSE exchange sessions from an independently validated
  ordered calendar.
- Admits only \`record_type=market_summary\`, \`market_code=NEPSE\`, verified,
  final records with positive finite \`total_turnover\`, source ID, SHA-256
  payload digest and timezone-aware \`available_at\` no later than decision time.
- Duplicate session records fail. Missing, provisional, future or
  provenance-incomplete records withhold the score.
- A single source identifier must cover the full 21-session window.
- No forward-fill, interpolation, session substitution or source splicing.

## Scoring
- Activity score (65%): latest turnover relative to the median of the prior
  20 sessions, with fixed bounded interpolation anchors at ratios 0.0, 0.5,
  0.8, 1.0, 1.5 and 2.0.
- Persistence score (35%): recent five-session average relative to the
  preceding five-session average, mapped to a bounded 0-100 scale around 1.0.
- The combined score is descriptive participation context, not a probability
  and not an assessment of whether buyers or sellers dominated.

## Warnings and limitations
Flags sharp turnover expansion, contraction and a latest-session ratio at
least twice the trailing median. Large single-session turnover can be a
climax, event or distribution day; the component intentionally cannot decide
that alone. Synthetic tests validate calculations only. The adapter is
standalone and is not yet wired to production market-summary feeds, the API
or market-health classifier. No live turnover score is claimed.
