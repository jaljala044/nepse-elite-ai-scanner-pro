import os
import unittest
from unittest.mock import patch

from app.main import app, IDPATGateReadinessRequest, idpat_gate_readiness


class IDPATGateReadinessAPITests(unittest.TestCase):
    def test_endpoint_is_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/v1/research/idpat/gate-readiness", paths)

    def test_request_model_has_no_client_gate_attestation_field(self):
        request = IDPATGateReadinessRequest(
            decision_date="2026-11-27",
            decision_time="2026-11-27T16:00:00+05:45",
            gate_evidence={"market": {"status": "verified"}},
        )
        self.assertFalse(hasattr(request, "gate_evidence"))

    def test_unconfigured_endpoint_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            result = idpat_gate_readiness(IDPATGateReadinessRequest(
                decision_date="2026-11-27",
                decision_time="2026-11-27T16:00:00+05:45",
            ))
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["production_enabled"])
        self.assertEqual(len(result["missing_configuration"]), 3)


if __name__ == "__main__":
    unittest.main()
