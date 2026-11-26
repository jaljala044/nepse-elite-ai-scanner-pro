# Broker footprint engine — point-in-time, identity-gated

## Data contract

The feature consumes normalized floorsheet party observations after the
existing floorsheet pipeline has parsed the source, reconciled duplicate and
amount exceptions, resolved broker identity as of trade date, and retained
unresolved identities. Required fields are:

- `trade_date`, `symbol`, `side` (buy/sell)
- `amount`, `quantity`
- `identity_status`, `broker_entity_id`, `source_broker_code`

Only `identity_status=verified` rows with a canonical broker entity enter
ranked broker tables. Unmapped, ambiguous and rejected rows remain in gross
amount, quantity and party-observation coverage denominators. Unresolved source
codes are never merged by fuzzy name matching or treated as canonical broker
IDs. The feature pipeline also applies the existing point-in-time availability
filter before calculations.

If the normalized party schema is absent, the footprint returns
`insufficient_evidence`; it does not infer broker trades from daily OHLCV or
from the current directory mapping.

## Windows and outputs

Windows use observed distinct trading dates, not calendar-day approximations:
1D, 1W (5 sessions), 1M (21), 3M (63), 6M (126), 1Y (252) and 2Y (504).
Per-security and market-level windows report:

- Verified buyer/seller amounts, quantities and broker-level net positions.
- Top net buyers and sellers by canonical broker entity.
- Gross participation share per broker and top-three gross concentration.
- Verified identity coverage by amount, party observations and quantity.
- Counts of verified and unresolved party observations.
- A status and optional directional breadth score.
- Complete-window broker-flow persistence labels across 1W/1M/3M; partial
  histories cannot be described as multi-month accumulation/distribution.

A window score is withheld unless verified gross-amount coverage is at least
80%, at least one verified broker contributes, and the observed session count
meets the configured minimum (capped by the requested window length).

## Persistence semantics

Per-security persistence labels are calculated only from complete, identity-
adequate 1W, 1M and 3M windows. Three consistent net-buyer windows yield
`strong_accumulation`; two or more net-buyer windows yield
`moderate_accumulation`; the corresponding seller conditions yield moderate or
heavy distribution. Mixed or insufficient histories remain explicitly
labelled. These are broker-flow pattern descriptions, not evidence of intent,
beneficial ownership or manipulation.

## Score semantics

The 0–100 broker component is an uncalibrated net-buyer breadth balance:
50 + 100 × (net-buyer entity count − net-seller entity count) / verified broker
entity count, clipped to 0–100. A broker is a net buyer when its verified buy
amount exceeds its verified sell amount over the window; net seller is the
reverse. This avoids using total net amount, which is zero-sum across matched
buyer/seller party rows. The score is not a probability, evidence of beneficial
ownership, or a standalone trade signal.

## Risk and interpretation guardrails

- Broker identity mapping is effective-dated and evidence-backed; the current
  91/91 directory-code match in the dated community snapshot is not proof of
  historical legal identity.
- Broker participation is not beneficial ownership.
- Concentration is descriptive; it does not prove cornering, circular trades,
  wash trading, operator activity or manipulation.
- Persistence across windows is visible through the separate 1D–2Y summaries;
  a single window does not establish sustained accumulation/distribution.
- No production promotion or model-training authorization follows from these
  features. Source completeness, session controls and canonical data gates
  remain independent requirements.

## Integration

`build_feature_snapshot` exposes `broker_footprint` and fills the V3 broker
component candidate for a symbol only when its 1D broker window is observed.
The existing scoring engine still enforces complete 100% component coverage,
HIGH Stage-1 quality, confirmed structure, verified liquidity, tradeable market
and at least 2R reward/risk before BUY.
