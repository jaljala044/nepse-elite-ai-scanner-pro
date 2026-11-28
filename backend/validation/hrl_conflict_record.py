"""Issue #4 — HRL 2026-11-19 source-conflict record.

Both source lows and the separate project-designated low are preserved.  This
record is descriptive evidence, not a source-selection or promotion mechanism.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import re
from typing import Any, Optional


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_STATUSES = {"QUARANTINED", "RESOLVED"}
_ALLOWED_OPTIONS = {"A", "B", "C"}


@dataclass
class HRLConflictRecord:
    symbol_id: str
    trade_date: str
    raw_low: float
    project_designated_low: float
    open: float
    high: float
    close: float
    raw_archive_sha256: str
    status: str = "QUARANTINED"
    chosen_option: Optional[str] = None
    decided_by: Optional[str] = None
    decision_date: Optional[str] = None
    justification: Optional[str] = None
    canonical_promotion_allowed: bool = False
    # Both immutable source rows are retained because close and volume conflict.
    source_archive_sha256: dict[str, str] = field(default_factory=dict)
    source_rows: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.symbol_id != "HRL":
            raise ValueError("HRLConflictRecord only accepts symbol_id='HRL'")
        try:
            date.fromisoformat(self.trade_date)
        except (TypeError, ValueError) as exc:
            raise ValueError("trade_date must be an ISO YYYY-MM-DD date") from exc
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError(f"status must be one of {sorted(_ALLOWED_STATUSES)}")
        if self.chosen_option not in (None, *_ALLOWED_OPTIONS):
            raise ValueError("chosen_option must be A, B, C or None")
        if self.canonical_promotion_allowed:
            raise ValueError("canonical promotion is a separate approval gate and must remain false")
        for name, digest in {"raw_archive_sha256": self.raw_archive_sha256, **self.source_archive_sha256}.items():
            if not _SHA256_RE.fullmatch(digest):
                raise ValueError(f"{name} must be a 64-character lowercase SHA-256 hex digest")
        if self.status == "QUARANTINED":
            if self.chosen_option not in (None, "C"):
                raise ValueError("a quarantined record may only have no decision or Option C")
            decision_values = (self.decided_by, self.decision_date, self.justification)
            if self.chosen_option is None and any(value is not None for value in decision_values):
                raise ValueError("an undecided quarantined record cannot carry decision metadata")
            if self.chosen_option == "C" and any(value is not None for value in decision_values):
                if not all(isinstance(value, str) and value.strip() for value in decision_values):
                    raise ValueError("an explicit Option C decision requires owner, date and justification")
                try:
                    date.fromisoformat(self.decision_date)
                except ValueError as exc:
                    raise ValueError("decision_date must be an ISO YYYY-MM-DD date") from exc
        else:
            if self.chosen_option not in {"A", "B"}:
                raise ValueError("RESOLVED requires an explicit Option A or B")
            if not all(isinstance(value, str) and value.strip() for value in (
                self.decided_by, self.decision_date, self.justification
            )):
                raise ValueError("RESOLVED requires decided_by, decision_date and justification")
            try:
                date.fromisoformat(self.decision_date)
            except ValueError as exc:
                raise ValueError("decision_date must be an ISO YYYY-MM-DD date") from exc
        if self.source_archive_sha256 and set(self.source_archive_sha256) != {
            "nepse-history-starter", "nepse-smc-data"
        }:
            raise ValueError("source_archive_sha256 must identify both pinned source archives")
        if self.source_rows and set(self.source_rows) != {
            "nepse-history-starter", "nepse-smc-data"
        }:
            raise ValueError("source_rows must preserve both pinned source rows")

    def geometry_valid_for_raw(self) -> bool:
        o, h, l, c = self.open, self.high, self.raw_low, self.close
        return min(o, h, l, c) > 0 and h >= max(o, c, l) and l <= min(o, c, h) and l <= h

    def geometry_valid_for_project(self) -> bool:
        o, h, l, c = self.open, self.high, self.project_designated_low, self.close
        return min(o, h, l, c) > 0 and h >= max(o, c, l) and l <= min(o, c, h) and l <= h

    def to_dict(self) -> dict[str, Any]:
        """Return a detached, JSON-serializable representation."""
        return asdict(self)
