# Steps 52–53 — official capture validation and pilot evidence bundle

## Step 52: captured official-source artifact validation

Added `backend/app/historical_pilot_capture.py`. It validates an operator-supplied capture manifest against an approved source registry, HTTPS host allowlist, publisher ID, timezone-aware capture/availability/window timestamps, exact SHA-256 of supplied raw bytes, page numbering, expected page count, HTTP status, final-page marker, content type and explicit complete-capture declaration.

No network retrieval or source endpoint discovery is performed. A hash proves byte integrity relative to the supplied bytes, not that the publisher is authentic or that the endpoint returned every exchange record. No actual NEPSE/CDSC payload was acquired for this change.

## Step 53: joined pilot evidence admission

Added `backend/app/historical_pilot_admission.py`. It joins required capture reports, the official first-trade verification report and the point-in-time panel readiness report. Any missing/blocked capture, unresolved first-trade boundary or blocked panel keeps the pilot BLOCKED.

A fully validated bundle only permits bounded research review. Canonical promotion, backtest admission and production remain false by design.

## Validation boundary

Synthetic tests exercise tamper detection, pagination gaps, host allowlisting and fail-closed admission. They are not official market evidence. SAIL remains unresolved until a real complete official first-day capture is supplied. No strategy accuracy, profitability, calibrated probabilities or live BUY/SELL claims are made.
