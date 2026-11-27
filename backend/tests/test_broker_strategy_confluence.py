import unittest
from app.broker_strategy_confluence import unified_research

def bundle():
    return dict(symbol="TEST",as_of="2026-04-24",mode="swing",ohlcv=[],
        smc_result={"status":"research_only","as_of":"2026-04-24","score":70},
        ict_result={"status":"research_only","as_of":"2026-04-24","engine_id":"nepse_ict_research","engine_version":"0.1.0","evidence_sha256":"a"*64},
        idpat_result={"status":"research_features_ready","as_of":"2026-04-24"},
        broker_result={"status":"insufficient_evidence","as_of":"2026-04-24","signals_enabled":False})
class UnifiedResearchTests(unittest.TestCase):
    def test_components_remain_separate_and_no_score(self):
        r=unified_research(**bundle())
        self.assertEqual(r["status"],"research_only")
        self.assertIsNone(r["score"])
        self.assertEqual(r["action"],"NO TRADE")
        self.assertFalse(r["production_eligible"])
        self.assertFalse(r["signals_enabled"])
        self.assertFalse(r["idpat_specification_verified"])
    def test_unversioned_ict_claim_is_rejected(self):
        x=bundle();x["ict_result"].pop("engine_id")
        self.assertEqual(unified_research(**x)["reason"],"ict_engine_not_implemented_or_unverified")
    def test_as_of_mismatch(self):
        x=bundle();x["ict_result"]["as_of"]="2026-04-25"
        self.assertEqual(unified_research(**x)["reason"],"ict_as_of_mismatch")
    def test_broker_signal_cannot_be_enabled(self):
        x=bundle();x["broker_result"]["signals_enabled"]=True
        self.assertEqual(unified_research(**x)["reason"],"component_not_research_eligible")
    def test_component_missing(self):
        x=bundle();x["smc_result"]=None
        self.assertEqual(unified_research(**x)["reason"],"smc_result_missing")
    def test_mode_is_explicit(self):
        x=bundle();x["mode"]="intraday"
        with self.assertRaises(ValueError): unified_research(**x)
