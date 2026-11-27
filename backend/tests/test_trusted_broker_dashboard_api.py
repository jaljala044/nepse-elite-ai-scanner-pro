import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from app import main


class TrustedBrokerDashboardApiTests(unittest.TestCase):
    def test_request_accepts_only_decision_cutoff(self):
        self.assertEqual(
            set(main.TrustedBrokerDashboardRequest.model_fields),
            {"as_of_date", "as_of_timestamp"},
        )

    def test_endpoint_fails_closed_when_deployment_registry_is_not_configured(self):
        request = main.TrustedBrokerDashboardRequest(
            as_of_date="2026-11-26",
            as_of_timestamp="2026-11-26T16:00:00+05:45",
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as raised:
                main.trusted_broker_dashboard(request)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(
            raised.exception.detail,
            "trusted_broker_artifact_store_not_configured",
        )

    def test_trusted_endpoint_is_registered(self):
        paths = {
            route.path for route in main.app.routes
            if getattr(route, "methods", None)
        }
        self.assertIn("/v1/research/broker-dashboard/trusted", paths)


if __name__ == "__main__":
    unittest.main()
