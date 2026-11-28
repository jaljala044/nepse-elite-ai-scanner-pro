import unittest,json,tempfile,os
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
import duckdb
from app.broker_ledger_profiles import ledger_profiles,quarantine_category,ROOT
from app.broker_daily_history import BrokerDailyHistoryStore
from test_broker_daily_history import source_row,report,manifest

class LedgerProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"ledger.duckdb"
        self.store=BrokerDailyHistoryStore(self.path)
        self.days=[(date(2026,11,25)-timedelta(days=i)).isoformat() for i in range(4,-1,-1)]
        self.cal={date.fromisoformat(d):{"scope":"market_wide","status":"verified_open","verified_at_utc":"2026-11-26T00:00:00Z"} for d in self.days}
        for d in self.days:
            m=manifest(d);m["identity_coverage_min"]="1"
            self.store.append_validated_daily_batch(report([source_row(d),source_row(d,evidence="E2",side="SELL")],batch_id="B-"+d),coverage_manifest=m)
    def run_profile(self):
        with patch.dict(os.environ,{"NEPSE_BROKER_LEDGER_PATH":str(self.path)}),patch("app.broker_ledger_profiles.load_calendar",return_value=self.cal):
            return ledger_profiles(as_of_date=self.days[-1],decision_time="2026-11-26T12:00:00+05:45",window="weekly")
    def test_read_only_coverage_and_no_security_publication(self):
        r=self.run_profile()
        self.assertEqual(r["status"],"descriptive_only")
        self.assertEqual(r["observation_count"],10)
        self.assertEqual(r["profiles"],[])
        self.assertFalse(r["signals_enabled"])
        self.assertFalse(r["production_eligible"])
    def test_modified_observation_amount(self):
        with duckdb.connect(str(self.path)) as con:
            con.execute("UPDATE broker_daily_observations SET amount=999")
        self.assertEqual(self.run_profile()["reason"],"observation_payload_mismatch")
    def test_modified_manifest_hash(self):
        with duckdb.connect(str(self.path)) as con:
            con.execute("UPDATE broker_daily_session_manifests SET manifest_sha256='bad'")
        self.assertEqual(self.run_profile()["reason"],"manifest_hash_mismatch")
    def test_missing_session(self):
        self.cal.pop(date.fromisoformat(self.days[1]))
        self.assertEqual(self.run_profile()["reason"],"trusted_calendar_incomplete")

class ExhaustiveQuarantineTests(unittest.TestCase):
    def test_all_registry_keys_at_both_window_boundaries(self):
        registry=json.loads((ROOT/"data/reference/p443_equity_quarantine.json").read_text())
        q={(r["symbol"],r["date"]) for r in registry["records"]}
        self.assertEqual(len(q),1329)
        for symbol,day in sorted(q):
            with self.subTest(symbol=symbol,day=day):
                self.assertEqual(quarantine_category("id",{"id":{symbol}},q,day,day),"quarantine_blocked")
                d=date.fromisoformat(day)
                self.assertEqual(quarantine_category("id",{"id":{symbol}},q,(d-timedelta(days=4)).isoformat(),day),"quarantine_blocked")
                self.assertEqual(quarantine_category("id",{"id":{symbol}},q,day,(d+timedelta(days=4)).isoformat()),"quarantine_blocked")
    def test_ambiguous_and_missing_identity(self):
        self.assertEqual(quarantine_category("id",{},set(),"2026-01-01","2026-01-05"),"identity_unmapped")
        self.assertEqual(quarantine_category("id",{"id":{"A","B"}},set(),"2026-01-01","2026-01-05"),"identity_unmapped")
