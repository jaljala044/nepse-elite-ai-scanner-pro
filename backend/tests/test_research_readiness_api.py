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
