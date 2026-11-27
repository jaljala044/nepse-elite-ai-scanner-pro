IDPAT-2 CI dependency

This branch inherits `research/issue-20-historical-segment-eligibility` through its IDPAT-1 parent branch. The dependency restores `backend/app/historical_segment_eligibility.py`, required by the repository-wide backend suite. The earlier full-suite error was a missing module in the prior base snapshot, not an IDPAT-2 detector assertion. This documentation-only update requests fresh validation after the IDPAT-1 dependency repair. No detector behavior or source evidence has changed.
