Portfolio Slice A CI dependency

This pull request is based on `fix/main-historical-segment-ci-dependency`, which restores the historical-segment eligibility module imported by the repository-wide backend test suite. The original full-suite failure was a missing module in the base snapshot, not a Portfolio Slice A test assertion. Portfolio-specific tests and inventory checks passed on the prior head; this documentation-only update requests fresh validation against the corrected base. No accounting behavior or portfolio data has been changed.
