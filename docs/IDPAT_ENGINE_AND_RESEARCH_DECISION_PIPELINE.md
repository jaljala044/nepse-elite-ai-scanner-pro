# IDPAT Research Engine and Conservative Decision Pipeline

## Step 14 — IDPAT price-volume and hidden-level engine
The new `idpat_price_volume_features` calculates descriptive candidates from point-in-time OHLCV: spring/upthrust candidates, SOS/SOW candidates, high-volume demand/supply effort candidates, and repeated swing-high/low clusters. It validates OHLCV and duplicate dates. Hidden levels are explicitly labelled inferred chart levels, not order-book liquidity.

The module does not claim confirmed LPS/LPSY, Backup to Creek, Jump Across Creek, calibrated scores, probabilities, operator activity, broker ownership or manipulation. Those require additional context and independent evidence.

## Step 15 — Evidence-backed research decision composition
`build_research_decision` connects the existing trade-plan builder, signal qualifier, risk sizing and execution checks. It requires verified price levels, all existing evidence gates, a current execution snapshot and risk sizing inputs before returning a research BUY for human review. Missing execution data, levels, gates or sizing fails closed to NO_TRADE.

The plan uses the conservative high end of the entry range for qualification and the existing net T1 reward/risk rule. Risk sizing applies the shared risk, cash, allocation, ADV and gap-stress caps. Execution snapshots are not fill guarantees and must be refreshed. The pipeline does not place orders.

## Limitations
- IDPAT heuristics are descriptive and uncalibrated; their scores remain null and are not fed into weighted scoring.
- The IDPAT module is currently callable independently; production feature-pipeline integration and trusted provenance for each derived event remain a follow-on.
- Dedicated broker persistence, fundamentals and full Smart Money Hidden Levels remain incomplete.
- All output is research-only; production remains disabled.
