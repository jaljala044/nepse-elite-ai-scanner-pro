# P3 daily market-structure research

The daily API returns `market_structure` for histories that pass its
server-reviewed equity, trading-session, source, OHLCV, and point-in-time
checks. Ineligible histories return an empty event list and the API reports
the reasons in `eligibility`. The 281-symbol current equity reference does
not establish historical eligibility for individual candles.

| Observation | Daily rule |
| --- | --- |
| Confirmed swing | Strict high or low against `pivot_width` bars on each side. The event is dated to confirmation. |
| BOS and CHoCH | Close through an earlier confirmed swing. A break against the established directional bias is a CHoCH. |
| Liquidity sweep | The high or low crosses a swing and the close returns inside that level. |
| Fair-value gap | A three-candle wick gap between the first and third bars. |
| Order-block candidate | The range of the last opposite-bodied candle after the broken swing and before the qualifying BOS or CHoCH. |
| Retest and invalidation | A later bar intersecting the zone emits the first retest. A close beyond the far boundary invalidates the zone and takes precedence when both conditions occur on the same daily bar. |

Events carry their observation date, the source references for the bars cited,
and the latest input availability timestamp through that event. For example,
a swing can be confirmed on one date and only become knowable later when a
required candle arrives. Zone lifecycle events link to their creation event
through `zone_id`. Daily OHLCV cannot establish an intraday sequence or who
placed orders.

This increment implements the SMC/ICT daily structure portion of the Universal
research scanner. IDPAT confluence and the separate NEPSE V3.0 implementation
require their own versioned rules, inputs and validation. The previously
generated V3 CSV is a result snapshot and does not establish those rules.
The server-owned reviewed-candle manifest is currently empty, so the shipped
API will suppress research events until reviewed rows are supplied.
