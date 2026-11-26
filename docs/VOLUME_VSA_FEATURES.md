# Volume / VSA feature contract

The VSA feature engine consumes point-in-time OHLCV rows only. It computes prior-20-session average volume and spread, relative volume/spread, close-location value, current return, prior range and close breakouts/breakdowns.

Rules are explicit: volume expansion >=1.5x; dry-up <=0.7x; wide spread >=1.5x; narrow spread <=0.7x; close near high >=0.70 CLV; close near low <=0.30 CLV. It reports demand-response, supply-response, low-activity/dry-up or mixed interpretations. These are observations, not evidence of operator intent and not standalone entries.

At least 21 valid sessions are required for a 20-session baseline. Missing OHLCV fields return an unavailable/null score. Duplicate dates, invalid prices, inconsistent OHLC and non-finite values are rejected. No synthetic sessions, calendar interpolation or historical price splicing are performed.
