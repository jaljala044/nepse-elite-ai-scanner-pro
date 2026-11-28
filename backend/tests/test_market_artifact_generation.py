import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.market_artifact_generation import generate_market_candidates

class CandidateTests(unittest.TestCase):
    def test_idempotent_and_never_promotes(self):
        bundle = dict(decision_time="2026-11-27T16:00:00+05:45",
            calendar={"sessions":["2026-11-27"]}, universe={"symbols":["A"]},
            daily_rows=[], benchmark_rows=[], index_rows=[], expected_indices=["NEPSE"],
            stock_rows=[], expected_sector_members={}, sector_membership={})
        with tempfile.TemporaryDirectory() as root, patch("app.market_artifact_generation.daily_market_participation", return_value={"status":"research_only","as_of_session":"2026-11-27"}), patch("app.market_artifact_generation.build_verified_rotation_dashboard", return_value={"status":"research_only","as_of":"2026-11-27"}), patch("app.market_artifact_generation.build_verified_sector_rotation", return_value={"status":"observed","as_of_session":"2026-11-27"}):
            first = generate_market_candidates(bundle, root)
            second = generate_market_candidates(bundle, root)
            self.assertEqual(first, second)
            self.assertEqual(len(list(Path(root).iterdir())), 4)
            self.assertFalse(first["promotion_allowed"])
            self.assertFalse(first["signals_enabled"])

    def test_incomplete_does_not_write(self):
        bundle = dict(decision_time="2026-11-27T16:00:00+05:45",
            calendar={"sessions":[]}, universe={"symbols":["A"]}, daily_rows=[], benchmark_rows=[])
        with tempfile.TemporaryDirectory() as root, patch("app.market_artifact_generation.daily_market_participation", return_value={"status":"insufficient_evidence"}):
            with self.assertRaisesRegex(ValueError,"daily_evidence_incomplete"):
                generate_market_candidates(bundle, root)
            self.assertEqual(list(Path(root).iterdir()), [])
