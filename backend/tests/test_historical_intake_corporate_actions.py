import hashlib, unittest
from app.nepse_historical_intake import ingest_captured_csv
from app.nepse_corporate_action_reconciliation import reconcile_corporate_actions, apply_reconciled_adjustments

CUTOFF="2025-01-10T12:00:00+05:45"
def action(source,publisher,fp="0.5",fv="2"):
    return {"security_id":"SEC1","action_type":"bonus","announcement_date":"2024-12-01",
        "effective_date":"2025-01-05","status":"completed","price_adjustment_factor":fp,
        "volume_adjustment_factor":fv,"source_id":source,"publisher":publisher,
        "evidence_id":"EV-"+source,"available_at":"2025-01-06T10:00:00+05:45",
        "raw_sha256":hashlib.sha256(source.encode()).hexdigest(),
        "rights_status":"approved","source_validation_status":"verified","finality_status":"final"}

class HistoricalIntakeTests(unittest.TestCase):
    def test_csv_hash_is_computed_from_exact_bytes(self):
        raw=b"security_id,session_date,open,high,low,close,volume,turnover\nSEC1,2025-01-02,100,110,95,105,1000,105000\n"
        out=ingest_captured_csv(raw_bytes=raw,dataset_kind="ohlcv",source_id="S1",publisher="P1",
            source_uri="https://source.invalid/file.csv",evidence_id="E1",captured_at="2025-01-03T10:00:00+05:45",
            decision_cutoff="2025-01-04T10:00:00+05:45",rights_status="approved",registry_review_id="R1")
        self.assertEqual(out["raw_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertEqual(out["status"],"validated_for_research")
    def test_future_capture_blocked(self):
        with self.assertRaisesRegex(ValueError,"capture_after"):
            ingest_captured_csv(raw_bytes=b"x",dataset_kind="ohlcv",source_id="S",publisher="P",source_uri="u",
                evidence_id="E",captured_at="2025-01-05T10:00:00+05:45",decision_cutoff="2025-01-04T10:00:00+05:45",
                rights_status="approved",registry_review_id="R")
    def test_missing_columns_rejected(self):
        with self.assertRaisesRegex(ValueError,"missing_required_columns"):
            ingest_captured_csv(raw_bytes=b"symbol,close\nAAA,10\n",dataset_kind="ohlcv",source_id="S",publisher="P",
                source_uri="u",evidence_id="E",captured_at="2025-01-03T10:00:00+05:45",
                decision_cutoff="2025-01-04T10:00:00+05:45",rights_status="approved",registry_review_id="R")

class CorporateActionTests(unittest.TestCase):
    def test_two_publishers_reconcile_and_adjust_pre_event_bars(self):
        out=reconcile_corporate_actions(action_records=[action("A","Publisher A"),action("B","Publisher B")],decision_cutoff=CUTOFF)
        self.assertEqual(len(out["reconciled_events"]),1)
        bars=[{"security_id":"SEC1","session_date":"2025-01-04","open":"100","high":"110","low":"90","close":"105","volume":"1000","turnover":"105000"},
              {"security_id":"SEC1","session_date":"2025-01-05","open":"50","high":"55","low":"45","close":"52","volume":"2000","turnover":"104000"}]
        adjusted=apply_reconciled_adjustments(bars=bars,reconciled_events=out["reconciled_events"],decision_cutoff=CUTOFF)
        self.assertEqual(adjusted["bars"][0]["close"],"52.5")
        self.assertEqual(adjusted["bars"][0]["volume"],"2000")
        self.assertEqual(adjusted["bars"][0]["turnover"],"105000")
        self.assertEqual(adjusted["bars"][1]["close"],"52")
    def test_single_publisher_withheld(self):
        out=reconcile_corporate_actions(action_records=[action("A","Publisher A")],decision_cutoff=CUTOFF)
        self.assertEqual(out["withheld_events"][0]["reason"],"two_independent_publishers_required")
    def test_disagreeing_factors_withheld(self):
        out=reconcile_corporate_actions(action_records=[action("A","Publisher A"),action("B","Publisher B",fp="0.6")],decision_cutoff=CUTOFF)
        self.assertEqual(out["withheld_events"][0]["reason"],"source_terms_or_adjustment_factors_disagree")
    def test_future_evidence_rejected(self):
        row=action("A","Publisher A"); row["available_at"]="2025-01-11T10:00:00+05:45"
        out=reconcile_corporate_actions(action_records=[row],decision_cutoff=CUTOFF)
        self.assertEqual(out["rejected_records"][0]["reason"],"evidence_unavailable_at_cutoff")
    def test_unreconciled_action_cannot_adjust(self):
        with self.assertRaisesRegex(ValueError,"unreconciled"):
            apply_reconciled_adjustments(bars=[],reconciled_events=[action("A","Publisher A")],decision_cutoff=CUTOFF)

if __name__=="__main__": unittest.main()
