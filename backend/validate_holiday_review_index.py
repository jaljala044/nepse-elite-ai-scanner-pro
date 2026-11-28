"""Fail-closed validator for the holiday review index; never authorizes promotion.

Review-index locators are not independently verified evidence. This validator
checks structural consistency only and deliberately exposes no admission path.
"""
import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

FIELDS = ("date", "official_observations", "secondary_observations",
          "official_locators", "secondary_locators", "existing_calendar_status",
          "review_disposition", "new_promotion_allowed")
DISPOSITIONS = {
    "project_accepted_open": "hold_open_conflict",
    "verified_closed": "existing_reviewed_closure_no_change",
    "verified_exceptional_closed": "existing_reviewed_closure_no_change",
    "unlisted": "hold_scope_or_evidence_review",
}

def validate(index, calendar, as_of):
    """Validate unique dates, source locators, and pinned-calendar dispositions."""
    seen, locators, counts = set(), set(), Counter()
    official = secondary = future = 0
    for row in index:
        if set(row) != set(FIELDS) or any(v is None for v in row.values()):
            raise ValueError("invalid review row schema")
        day = date.fromisoformat(row["date"])
        if day.isoformat() != row["date"] or day in seen:
            raise ValueError("duplicate or noncanonical date")
        seen.add(day)
        for kind in ("official", "secondary"):
            n = int(row[kind + "_observations"])
            ids = row[kind + "_locators"].split(";") if row[kind + "_locators"] else []
            if n < 0 or n != len(ids) or any(not x.strip() for x in ids):
                raise ValueError("observation count mismatch")
            for locator in ids:
                key = (kind, locator)
                if key in locators:
                    raise ValueError("duplicate source locator")
                locators.add(key)
            if kind == "official":
                official += n
            else:
                secondary += n
        if int(row["official_observations"]) + int(row["secondary_observations"]) == 0:
            raise ValueError("missing evidence locators")
        status = calendar.get(row["date"], "unlisted")
        if status not in DISPOSITIONS or row["existing_calendar_status"] != status:
            raise ValueError("calendar mismatch or unknown status")
        expected = DISPOSITIONS[status]
        if row["review_disposition"] != expected or row["new_promotion_allowed"] != "false":
            raise ValueError("unsafe holiday admission")
        counts[expected] += 1
        future += day > as_of
    if not seen:
        raise ValueError("empty index")
    return {"unique_dates": len(seen), "official_observations": official,
            "secondary_observations": secondary, "future_dates": future,
            "dispositions": dict(counts), "new_promotions": 0,
            "scope": "structural_review_only_not_source_certification"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--calendar", type=Path, required=True)
    p.add_argument("--as-of", type=date.fromisoformat, required=True)
    a = p.parse_args()
    with a.calendar.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    calendar = {}
    for row in rows[1:]:
        if len(row) < 2 or row[0] in calendar:
            raise ValueError("invalid or duplicate calendar row")
        if date.fromisoformat(row[0]).isoformat() != row[0]:
            raise ValueError("noncanonical calendar date")
        calendar[row[0]] = row[1]
    with a.index.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("unexpected index header")
        print(json.dumps(validate(reader, calendar, a.as_of), sort_keys=True))

if __name__ == "__main__":
    main()
