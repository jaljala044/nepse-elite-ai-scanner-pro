import unittest
from fastapi.testclient import TestClient
from app.main import app

class ResearchReadinessAPITests(unittest.TestCase):
    def test_readiness_cannot_authorize_recommendations(self):
        with TestClient(app) as client:
            response=client.get("/v1/research/readiness")
            self.assertEqual(response.status_code,200)
            data=response.json()
            self.assertEqual(data["mode"],"research_only")
            self.assertFalse(data["production_recommendations_enabled"])
            self.assertFalse(data["ai_recommendations_enabled"])
            self.assertFalse(data["ranking_enabled"])
            self.assertEqual(data["missing_evidence_policy"],"UNKNOWN")
            self.assertEqual(data["publisher_trust"]["status"], "not_configured_or_invalid")
            self.assertFalse(data["publisher_trust"]["production_admission_allowed"])
            self.assertEqual(data["historical_sector_replay"]["status"], "not_configured_or_invalid")
            self.assertFalse(data["historical_sector_replay"]["production_admission_allowed"])
            self.assertEqual(data["source_reliability"]["status"], "not_configured")
            self.assertFalse(data["source_reliability"]["production_admission_allowed"])
            self.assertFalse(data["source_reliability"]["recommendation_override"])
            self.assertEqual(data["source_data_quality"]["status"], "not_configured")
            self.assertFalse(data["source_data_quality"]["production_admission_allowed"])
            self.assertFalse(data["source_data_quality"]["recommendation_override"])
            self.assertEqual(data["source_data_quality"]["review_registry_status"], "not_configured")
