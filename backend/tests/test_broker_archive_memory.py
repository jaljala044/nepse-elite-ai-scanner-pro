import hashlib
import tempfile
import unittest
from pathlib import Path
from app.broker_archive_memory import connect, ingest, profile, rotation

class BrokerArchiveMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=connect(Path(self.tmp.name)/"test.sqlite")
    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
    def fixture(self,day,flip=False):
        a,b=("2","1") if flip else ("1","2")
        raw=("symbol,date,broker,buy_qty,sell_qty,buy_value,sell_value\n"
             f"AAA,{day},{a},10,0,1000.00,0.00\n"
             f"AAA,{day},{b},0,10,0.00,1000.00\n").encode()
        c=dict(date=day,blob_sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),shares="10",turnover="1000",instruments="1")
        return raw,c
    def test_idempotent(self):
        r,c=self.fixture("2026-11-01")
        self.assertEqual(ingest(self.db,r,c)["status"],"recorded")
        self.assertEqual(ingest(self.db,r,c)["status"],"already_recorded")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM archive_broker").fetchone()[0],2)
    def test_control_mismatch(self):
        r,c=self.fixture("2026-11-01")
        c["shares"]="11"
        with self.assertRaises(ValueError):ingest(self.db,r,c)
    def test_hash(self):
        r,c=self.fixture("2026-11-01")
        with self.assertRaises(ValueError):ingest(self.db,r+b"\n",c)
    def test_missing_session(self):
        r,c=self.fixture("2026-11-01")
        ingest(self.db,r,c)
        self.assertEqual(profile(self.db,"AAA",["2026-11-01","2026-11-02"])["status"],"unavailable")
    def test_rotation(self):
        for day,flip in [("2026-11-01",False),("2026-11-02",True)]:
            r,c=self.fixture(day,flip)
            ingest(self.db,r,c)
        a=profile(self.db,"AAA",["2026-11-01"])
        b=profile(self.db,"AAA",["2026-11-02"])
        self.assertEqual(a["brokers"][0]["classification"],"persistent_net_buy")
        self.assertFalse(a["production_eligible"])
        self.assertEqual(len(rotation(a,b)["direction_changes"]),2)
