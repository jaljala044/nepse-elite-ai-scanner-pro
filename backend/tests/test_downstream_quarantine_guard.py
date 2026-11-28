import unittest
from app.quarantine_guard import is_quarantined
from app.database import persist_import
from app.broker_ingestion import IngestionReport
from app.broker_memory_promotion import promote_validated_batch, PromotionRejected

class DownstreamQuarantineTests(unittest.TestCase):
    def test_markers(self):
        for row in ({"row_status":"quarantined"}, {"disposition":"quarantined_unresolved"}, {"quarantine_reasons":["conflict"]}, {"quarantined":True}, {"status":"QUARANTINED"}):
            with self.subTest(row=row):
                self.assertTrue(is_quarantined(row))
        self.assertFalse(is_quarantined({"status":"descriptive_only"}))

    def test_database_rejects_before_opening(self):
        with self.assertRaisesRegex(ValueError, "Quarantined"):
            persist_import("test", {"AAA":[{
                "date": "2026-11-27", "open": 10, "high": 12, "low": 9,
                "close": 11, "volume": 100, "row_status": "quarantined"
            }]})

    def test_database_rejects_each_quarantine_marker_before_opening(self):
        markers = [
            {"row_status": "quarantined"},
            {"disposition": "quarantined_unresolved"},
            {"quarantine_status": "quarantined"},
            {"quarantined": True},
            {"quarantine_reasons": ["source_conflict"]},
        ]
        for marker in markers:
            with self.subTest(marker=marker):
                with self.assertRaisesRegex(ValueError, "Quarantined"):
                    persist_import("test", {"AAA": [{
                        "date": "2026-11-27", "open": 10, "high": 12, "low": 9,
                        "close": 11, "volume": 100, **marker,
                    }]})

    def test_broker_rejects_marked_row(self):
        report = IngestionReport("test", "complete", "1", accepted=[{"status":"descriptive_only","quarantined":True}])
        with self.assertRaisesRegex(PromotionRejected, "quarantined"):
            promote_validated_batch(report, None, as_of_date="2026-11-27")

    def test_broker_rejects_conflicts(self):
        report = IngestionReport("test", "complete", "1", accepted=[{}], conflicts=1)
        with self.assertRaisesRegex(PromotionRejected, "conflicts"):
            promote_validated_batch(report, None, as_of_date="2026-11-27")


    def test_database_withholds_whole_affected_history(self):
        import tempfile
        from pathlib import Path
        from datetime import date
        from unittest.mock import patch
        from app.database import load_state
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app.database.database_path", return_value=Path(tmp)/"test.duckdb"):
                def bar(day):
                    return {"date":date.fromisoformat(day),"open":10,"high":12,"low":9,"close":11,"volume":100}
                with patch("app.database.runtime_quarantine_keys",return_value=None):
                    persist_import("fixture",{"AAA":[bar("2025-07-27"),bar("2025-07-28"),bar("2025-07-29")],"BBB":[bar("2025-07-29")]})
                with patch("app.database.runtime_quarantine_keys",return_value=frozenset({("AAA","2025-07-28")})):
                    data,_ = load_state()
                    self.assertEqual(set(data),{"BBB"})
                with patch("app.database.runtime_quarantine_keys",return_value=None):
                    self.assertEqual(len(load_state()[0]["AAA"]),3)
