import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from audit_historical_identity_readiness import audit_historical_identity_readiness


class HistoricalIdentityReadinessTests(unittest.TestCase):
    def fixture(self, root):
        snapshot = root / "snapshot.csv"
        crosswalk = root / "crosswalk.csv"
        lifecycle = root / "lifecycle.csv"
        events = root / "events.csv"
        identity = root / "identity.json"
        history = root / "history"
        (history / "symbols" / "BENH").mkdir(parents=True)

        snapshot_rows = [
            {"symbol":"ABC","security_id":"1","security_name":"Alpha","active_status":"A","snapshot_date":"2026-11-25"},
            {"symbol":"BENH","security_id":"2","security_name":"Beni Hydropower","active_status":"A","snapshot_date":"2026-11-25"},
        ]
        cross_rows = [
            {"symbol":r["symbol"],"security_id":r["security_id"],"security_name":r["security_name"],
             "snapshot_date":"2026-11-25","active_status":"A","crosswalk_status":"snapshot_id_match_active_status_A"}
            for r in snapshot_rows
        ]
        lifecycle_rows = [
            {"security_id":"1","symbol":"ABC","instrument_type":"equity","valid_from":"2020-01-01","valid_to":"",
             "target_in_scope":"true","valid_from_evidence_status":"verified_secondary_notice",
             "valid_from_evidence_uri":"https://example.test/abc","valid_from_evidence_note":"secondary fixture"},
            {"security_id":"2","symbol":"BENH","instrument_type":"equity","valid_from":"2026-10-15","valid_to":"",
             "target_in_scope":"true","valid_from_evidence_status":"verified_secondary_first_trade_archive_match",
             "valid_from_evidence_uri":"https://example.test/benh","valid_from_evidence_note":"first trade archive match"},
        ]
        for path, rows in ((snapshot,snapshot_rows),(crosswalk,cross_rows),(lifecycle,lifecycle_rows)):
            with path.open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

        event_rows=[{
            "event_id":"E1","security_id":"2","symbol":"BENH","event_type":"post_merger_shares_listed",
            "event_date":"2026-10-13","evidence_tier":"primary_nepse_notice",
            "source_url":"https://nepalstock.com.np/api/nots/security/fetchFiles?fileLocation=listing.pdf",
            "source_label":"NEPSE","review_status":"primary_notice_verified","notes":"listing date only",
        }]
        with events.open("w",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=event_rows[0].keys())
            writer.writeheader()
            writer.writerows(event_rows)

        identity.write_text(json.dumps({
            "summary":{"identity_or_event_supported":1,"probable_alias_only":0},
            "records":[{"symbol":"OLD","stable_id":None,"effective_date_verified":False}],
            "security_id_recovery":{
                "historical_predecessor_ids":{"status":"unresolved","symbols":["OLD"]},
                "promotion":{"stable_ids_assigned":False,"predecessor_ids_assigned":False,
                            "history_splicing_authorized":False,"canonical_universe_promotion_authorized":False,
                            "training_promotion_authorized":False},
                "provider_lead":{"public_retrieval_status":"not_acquired","response_body_sha256":None},
                "successor_snapshot":{"scope":"current snapshot observation only; not a historical validity interval"},
            },
        }))
        benh_rows=[
            {"businessDate":"2026-10-14","totalTrades":0,"totalTradedQuantity":0,"totalTradedValue":0},
            {"businessDate":"2026-10-15","totalTrades":9,"totalTradedQuantity":90,"totalTradedValue":26634},
        ]
        benh_path=history/"symbols"/"BENH"/"response-01.bin"
        raw=json.dumps({"content":benh_rows}).encode()
        benh_path.write_bytes(raw)
        (history/"SHA256SUMS").write_text(
            f"{hashlib.sha256(raw).hexdigest()}  symbols/BENH/response-01.bin\n"
        )
        return lifecycle,events,identity,crosswalk,snapshot,history

    def test_readiness_report_keeps_secondary_dates_and_ids_unpromoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp))
            report=audit_historical_identity_readiness(*args,expected_equity_count=2)
        self.assertEqual(report["current_equity_count"],2)
        self.assertEqual(report["lifecycle_start_evidence"]["secondary_start_evidence_count"],2)
        self.assertEqual(report["lifecycle_start_evidence"]["primary_start_evidence_count"],0)
        self.assertEqual(report["historical_identity_evidence"]["stable_id_present_count"],0)
        self.assertEqual(report["typed_security_lifecycle_events"]["primary_notice_count"],1)
        self.assertEqual(report["BENH_first_trade_reconciliation"]["2026-10-14"]["status"],"EXPLICIT_ZERO_ACTIVITY")
        self.assertEqual(report["BENH_first_trade_reconciliation"]["2026-10-15"]["shares"],"90")
        self.assertFalse(report["historical_join_admission_allowed"])
        self.assertFalse(report["corporate_action_adjustment_admission_allowed"])

    def test_current_crosswalk_id_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp))
            lifecycle=args[0]
            rows=list(csv.DictReader(lifecycle.open()))
            rows[0]["security_id"]="999"
            with lifecycle.open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError,"lifecycle/current crosswalk mismatch"):
                audit_historical_identity_readiness(*args,expected_equity_count=2)

    def test_benh_raw_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp))
            path=args[5]/"symbols"/"BENH"/"response-01.bin"
            path.write_text("tampered")
            with self.assertRaisesRegex(ValueError,"BENH raw response SHA-256"):
                audit_historical_identity_readiness(*args,expected_equity_count=2)

    def test_stable_id_without_verified_effective_date_does_not_promote(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp))
            data=json.loads(args[2].read_text())
            data["records"][0]["stable_id"]="UNVERIFIED-ID"
            data["records"][0]["effective_date_verified"]=False
            args[2].write_text(json.dumps(data))
            report=audit_historical_identity_readiness(*args,expected_equity_count=2)
        self.assertEqual(report["historical_identity_evidence"]["stable_id_present_count"],1)
        self.assertEqual(report["historical_identity_evidence"]["effective_date_verified_count"],0)
        self.assertFalse(report["historical_identity_admission_allowed"])

    def test_benh_lifecycle_status_cannot_be_silently_upgraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            args=self.fixture(Path(tmp))
            rows=list(csv.DictReader(args[0].open()))
            rows[1]["valid_from_evidence_status"]="verified_primary_notice"
            with args[0].open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError,"primary lifecycle date must link"):
                audit_historical_identity_readiness(*args,expected_equity_count=2)


if __name__ == "__main__":
    unittest.main()
