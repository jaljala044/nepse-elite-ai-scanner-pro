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
            persist_import("test", {"AAA":[{"row_status":"quarantined"}]})

    def test_broker_rejects_marked_row(self):
        report = IngestionReport("test", "complete", "1", accepted=[{"status":"descriptive_only","quarantined":True}])
        with self.assertRaisesRegex(PromotionRejected, "quarantined"):
            promote_validated_batch(report, None, as_of_date="2026-11-27")

    def test_broker_rejects_conflicts(self):
        report = IngestionReport("test", "complete", "1", accepted=[{}], conflicts=1)
        with self.assertRaisesRegex(PromotionRejected, "conflicts"):
            promote_validated_batch(report, None, as_of_date="2026-11-27")
