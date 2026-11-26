# Market health and regime engine

## Purpose
Converts validated market-level component scores into a coverage-aware
0-100 descriptor, rules-based regime and conservative trading posture. It
does not forecast returns or authorize trades.

## Inputs and provenance
Each component requires a 0-100 score, status=verified, the same as-of
session as the decision session, a nonblank source ID and a 64-character
SHA-256 source-payload digest.

| Component | Weight | Evidence requirement |
|---|---:|---|
| Index trend | 25% | Verified NEPSE index trend calculation |
| Market breadth | 25% | Complete point-in-time equity universe |
| Turnover | 20% | Verified daily market turnover/session history |
| Sector participation | 15% | Verified point-in-time sector membership and returns |
| Volatility | 15% | Verified index OHLCV/realized-volatility calculation |

Missing, stale, provisional or provenance-incomplete inputs remain null and
reduce coverage. Scores are normalized only over observed component weights;
coverage is reported separately. Regime classification is withheld unless
coverage is at least 80% and trend, breadth and turnover are verified.

## Regime rules
- Bull: trend >=65, breadth >=60, turnover >=55, health >=65.
- Markup: trend >=60, breadth >=50 and turnover >=55.
- Distribution: trend >=50 with breadth <50, or health <45 after other rules.
- Accumulation: trend >=45, breadth >=40 and health >=50.
- Correction: trend <45 and breadth <45.
- Markdown: trend <35 and breadth <35.
- Sideways: remaining adequately covered cases.
- Unknown: regime prerequisites or coverage are missing.

The implementation evaluates markdown and correction before bullish rules.
This is a descriptive rules-based classification, not a probability,
recommendation or substitute for stock-level confirmation.

## Integration boundary
The engine is standalone until canonical market turnover, index volatility
and complete-universe breadth adapters are wired to validated point-in-time
source records. Do not pass estimated, synthetic or stale scores as verified.
