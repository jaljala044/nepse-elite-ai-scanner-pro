from __future__ import annotations

import unittest

from backend.validation.hrl_conflict_record import HRLConflictRecord


HISTORY_SHA = "2aaac3df4b8bf236d1d1864fc5af96e6548eac95dc20c23f97cec82d0c972db3"
SMC_SHA = "2d4c103cc07d54bd8b197784763c9a5f8c4a6fe014452ae0c91f28d03ccbc83b"


def make_record(**kw):
    base = dict(
        symbol_id="HRL",
        trade_date="2026-11-19",
        raw_low=480.00,
        project_designated_low=483.90,
        open=483.00,
        high=488.00,
        close=486.00,
        raw_archive_sha256=HISTORY_SHA,
        source_archive_sha256={
            "nepse-history-starter": HISTORY_SHA,
            "nepse-smc-data": SMC_SHA,
        },
        source_rows={
            "nepse-history-starter": {
                "open": "483", "high": "488", "low": "480",
                "close": "483.9", "volume": "49184", "source_csv_line": 935,
            },
            "nepse-smc-data": {
                "open": "483", "high": "488", "low": "480",
                "close": "486", "volume": "18817", "source_csv_line": 654,
            },
        },
    )
    base.update(kw)
    return HRLConflictRecord(**base)


class HRLConflictRecordTests(unittest.TestCase):
    def test_both_values_and_both_raw_source_rows_preserved(self):
        record = make_record()
        self.assertEqual(record.raw_low, 480.00)
        self.assertEqual(record.project_designated_low, 483.90)
        self.assertEqual(record.source_rows["nepse-history-starter"]["low"], "480")
        self.assertEqual(record.source_rows["nepse-smc-data"]["low"], "480")
        self.assertEqual(record.source_rows["nepse-history-starter"]["close"], "483.9")
        self.assertEqual(record.source_rows["nepse-smc-data"]["close"], "486")

    def test_raw_geometry_valid(self):
        self.assertTrue(make_record().geometry_valid_for_raw())

    def test_project_geometry_invalid(self):
        self.assertFalse(make_record().geometry_valid_for_project())

    def test_default_quarantined_no_promotion(self):
        record = make_record()
        self.assertEqual(record.status, "QUARANTINED")
        self.assertFalse(record.canonical_promotion_allowed)

    def test_option_a_resolution_keeps_both_values_and_promotion_disabled(self):
        record = make_record(
            status="RESOLVED", chosen_option="A", decided_by="owner",
            decision_date="2026-11-28",
            justification="Adopt raw low; retain project value in provenance.",
        )
        self.assertEqual(record.status, "RESOLVED")
        self.assertEqual(record.raw_low, 480.00)
        self.assertEqual(record.project_designated_low, 483.90)
        self.assertFalse(record.canonical_promotion_allowed)

    def test_option_c_stays_quarantined(self):
        record = make_record(
            chosen_option="C", decided_by="owner", decision_date="2026-11-28",
            justification="Retain the source conflict without canonical promotion.",
        )
        self.assertEqual(record.status, "QUARANTINED")
        self.assertEqual(record.chosen_option, "C")
        self.assertEqual(record.decided_by, "owner")

    def test_no_silent_replacement_in_serialized_record(self):
        data = make_record().to_dict()
        self.assertNotEqual(data["raw_low"], data["project_designated_low"])
        self.assertIn("raw_low", data)
        self.assertIn("project_designated_low", data)
        self.assertEqual(set(data["source_rows"]), {"nepse-history-starter", "nepse-smc-data"})

    def test_incomplete_or_unsafe_decisions_fail_closed(self):
        invalid = [
            {"status": "RESOLVED", "chosen_option": "A"},
            {"status": "RESOLVED", "chosen_option": "C", "decided_by": "owner",
             "decision_date": "2026-11-28", "justification": "Keep conflict."},
            {"canonical_promotion_allowed": True},
            {"chosen_option": "B"},
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                make_record(**kwargs)

    def test_invalid_archive_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            make_record(raw_archive_sha256="<sha>")

    def test_only_hrl_identity_accepted(self):
        with self.assertRaisesRegex(ValueError, "symbol_id"):
            make_record(symbol_id="API")


if __name__ == "__main__":
    unittest.main()
