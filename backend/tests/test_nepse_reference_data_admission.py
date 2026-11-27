import hashlib, tempfile, unittest
from pathlib import Path
from app.nepse_reference_data_admission import admit_reference_data_bundle

class ReferenceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.cutoff="2026-11-27T16:00:00Z"
        self.capture=[]
        for sid,group,body in [("CAL-A","publisher-a",b"official calendar notice a"),
                               ("CAL-B","publisher-b",b"official calendar notice b"),
                               ("UNI","publisher-c",b"official universe snapshot")]:
            name=sid.lower()+".bin"; (self.root/name).write_bytes(body)
            self.capture.append({"source_id":sid,"url":"https://www.nepalstock.com.np/evidence/"+sid,
                "raw_evidence_path":name,"raw_evidence_sha256":hashlib.sha256(body).hexdigest(),
                "retrieved_at_utc":"2026-11-26T10:00:00Z","rights_status":"approved",
                "source_validation_status":"verified","finality_status":"final",
                "independence_group":group,"independence_review_status":"approved"})
        self.universe={"source_id":"UNI","source_url":"https://www.nepalstock.com.np/evidence/UNI",
            "retrieved_at_utc":"2026-11-26T10:00:00Z","raw_payload_sha256":self.capture[2]["raw_evidence_sha256"],
            "snapshot_as_of":"2026-11-26","records":[
                {"security_id":"E1","symbol":"AAA","instrument_type":"equity","status":"active","target_in_scope":True,"valid_from":"2020-01-01"},
                {"security_id":"E2","symbol":"BBB","instrument_type":"equity","status":"active","target_in_scope":True,"valid_from":"2020-01-01"},
                {"security_id":"M1","symbol":"FUND1","instrument_type":"mutual_fund","status":"active","target_in_scope":True,"valid_from":"2020-01-01"}]}
        self.calendar=[{"date":"2026-11-26","status":"verified_open","scope":"all_securities","source_ids":["CAL-A","CAL-B"]}]
    def tearDown(self): self.tmp.cleanup()
    def run_bundle(self, **kwargs):
        args={"calendar_rows":self.calendar,"captures":self.capture,"universe_snapshot":self.universe,
            "evidence_root":self.root,"expected_calendar_dates":["2026-11-26"],"decision_cutoff":self.cutoff,
            "expected_equities":2,"expected_mutual_funds":1}
        args.update(kwargs)
        return admit_reference_data_bundle(**args)
    def test_valid_bundle_allows_research_review_only(self):
        r=self.run_bundle()
        self.assertTrue(r["research_review_allowed"])
        self.assertFalse(r["production_promotion_allowed"])
    def test_raw_byte_tampering_blocks_capture(self):
        (self.root/"cal-a.bin").write_bytes(b"altered")
        r=self.run_bundle()
        self.assertFalse(r["research_review_allowed"])
        self.assertTrue(any("raw_evidence_hash_mismatch" in str(x) for x in r["errors"]))
    def test_rights_or_independence_missing_blocks(self):
        self.capture[1]["rights_status"]="unknown"
        r=self.run_bundle()
        self.assertFalse(r["research_review_allowed"])
    def test_one_independent_calendar_source_is_not_enough(self):
        self.calendar[0]["source_ids"]=["CAL-A"]
        r=self.run_bundle()
        self.assertFalse(r["research_review_allowed"])
        self.assertTrue(any("lacks_independent_sources" in x for x in r["errors"]))
    def test_calendar_gap_is_not_filled(self):
        r=self.run_bundle(expected_calendar_dates=["2026-11-26","2026-11-27"])
        self.assertFalse(r["research_review_allowed"])
        self.assertTrue(any("missing_or_ambiguous" in x for x in r["errors"]))
    def test_universe_capture_hash_mismatch_blocks(self):
        self.universe["raw_payload_sha256"]="0"*64
        r=self.run_bundle()
        self.assertFalse(r["research_review_allowed"])
    def test_late_capture_blocks(self):
        self.capture[0]["retrieved_at_utc"]="2026-11-27T17:00:00Z"
        r=self.run_bundle()
        self.assertFalse(r["research_review_allowed"])
    def test_path_traversal_blocks(self):
        self.capture[0]["raw_evidence_path"]="../escape.bin"
        r=self.run_bundle()
        self.assertFalse(r["research_review_allowed"])

if __name__=="__main__": unittest.main()
