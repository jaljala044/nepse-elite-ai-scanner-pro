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

    def test_end_to_end_calculators_without_mocks(self):
        from datetime import date, timedelta
        from hashlib import sha256
        import json
        cutoff = "2026-11-27T16:00:00+05:45"
        days = [(date(2026, 1, 1)+timedelta(days=i)).isoformat() for i in range(127)]
        provenance = dict(source_id="synthetic-test", source_payload_sha256="a"*64, available_at=cutoff)
        meta = dict(status="verified", **provenance)
        prices = dict(source_validation_status="verified", finality_status="final", **provenance)
        members = {"BANK":["A"], "HYDRO":["B"]}
        benchmark = [dict(record_type="index_ohlcv", index_code="NEPSE", session_date=d,
                          close=100+i, **prices) for i,d in enumerate(days)]
        index_rows = benchmark + [dict(record_type="index_ohlcv", index_code="BANK",
            session_date=d, close=100+2*i, **prices) for i,d in enumerate(days)]
        stock_rows = [dict(symbol=s, session_date=d, close=100+m*i,
            price_basis_status="verified_unadjusted_no_actions", corporate_action_status="clear",
            **prices) for s,m in [("A",2),("B",0.5)] for i,d in enumerate(days)]
        daily_rows = [dict(symbol=s, session_date=days[-1], prior_session=days[-2],
            prior_close_verified=True, corporate_action_status="verified_clear",
            close=100+m*126, prior_close=100+m*125, volume=100, turnover=10000,
            **prices) for s,m in [("A",2),("B",0.5)]]
        bundle = dict(decision_time=cutoff, calendar=dict(meta,sessions=days),
            universe=dict(meta,symbols=["A","B"],as_of_session=days[-1]),
            daily_rows=daily_rows, benchmark_rows=benchmark, index_rows=index_rows,
            expected_indices=["NEPSE","BANK"], stock_rows=stock_rows,
            expected_sector_members=members, sector_membership={
                s:dict(meta,sector_code=k,effective_from=days[0],effective_to=None)
                for k,ss in members.items() for s in ss})
        with tempfile.TemporaryDirectory() as root:
            result = generate_market_candidates(bundle,root)
            self.assertEqual(len(result["artifacts"]),3)
            self.assertFalse(result["promotion_allowed"])
            for entry in result["artifacts"].values():
                raw = (Path(root)/entry["payload_path"]).read_bytes()
                self.assertEqual(sha256(raw).hexdigest(),entry["payload_sha256"])
                self.assertFalse(json.loads(raw)["signals_enabled"])
            self.assertEqual(generate_market_candidates(bundle,root),result)
            bundle["daily_rows"].pop()
            with self.assertRaisesRegex(ValueError,"daily_evidence_incomplete"):
                generate_market_candidates(bundle,root)
            self.assertEqual(len(list(Path(root).iterdir())),4)
