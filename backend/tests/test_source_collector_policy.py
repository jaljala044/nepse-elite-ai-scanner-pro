import os
import unittest
from unittest.mock import patch

from app.source_collector import collect_configured_provider, _provider_access_approval


class NoNetworkClient:
    def get(self, *args, **kwargs):
        raise AssertionError("network must not be called in configuration-gate tests")


class SourceCollectorPolicyTests(unittest.TestCase):
    def test_missing_provider_endpoint_is_blocked_access(self):
        with patch.dict(os.environ, {}, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "sharehub", "chart",
                equities=[{"symbol": "AAA", "security_id": "1"}])
        self.assertEqual(result[0]["status"], "BLOCKED_ACCESS")

    def test_daily_floorsheet_template_requires_verified_session_calendar(self):
        with patch.dict(os.environ, {
            "SHAREHUB_FLOORSHEET_URL_TEMPLATE":
                "https://provider.example/floorsheet/{date}"
        }, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "sharehub", "floorsheet",
                equities=[{"symbol": "AAA", "security_id": "1"}],
                session_dates=None)
        self.assertEqual(result[0]["status"], "BLOCKED_DEPENDENCY")
        self.assertIn("session_calendar", result[0]["error"])

    def test_per_equity_chart_template_requires_complete_equity_universe(self):
        with patch.dict(os.environ, {
            "CHUKUL_CHART_URL_TEMPLATE":
                "https://provider.example/chart/{symbol}?from={from}&to={to}"
        }, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "chukul", "chart", equities=None)
        self.assertEqual(result[0]["status"], "BLOCKED_DEPENDENCY")
        self.assertIn("equity_universe", result[0]["error"])

    def test_unsupported_template_placeholder_fails_closed(self):
        with patch.dict(os.environ, {
            "NEPSEALPHA_CHART_URL_TEMPLATE":
                "https://provider.example/chart/{symbol}?token={unknown}"
        }, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "nepsealpha", "chart",
                equities=[{"symbol": "AAA", "security_id": "1"}])
        self.assertEqual(result[0]["status"], "BLOCKED_ACCESS")
        self.assertIn("unsupported_url_template_placeholder", result[0]["error"])


    def test_configured_endpoint_is_blocked_without_reviewed_rights_manifest(self):
        with patch.dict(os.environ, {
            "SHAREHUB_CHART_URL_TEMPLATE":
                "https://sharehubnepal.com/data/api/v1/nepse-data/price-history/{symbol}?time=5Y"
        }, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "sharehub", "chart",
                equities=[{"symbol": "AAA", "security_id": "1"}],
                period_start="2021-11-28", period_end="2026-11-28")
        self.assertEqual(result[0]["status"], "BLOCKED_ACCESS")
        self.assertEqual(result[0]["error"], "provider_access_manifest_missing")


    def test_reviewed_manifest_approves_exact_host_and_path(self):
        manifest = {
            "providers": {"sharehub": {
                "status": "approved", "allowed_data_types": ["chart"],
                "rights_status": "research_only", "reviewer": "reviewer",
                "evidence_ref": "evidence:sharehub", "contract_ref": "contract:sharehub",
                "valid_until": "2099-12-31", "allowed_hosts": ["sharehubnepal.com"],
                "allowed_path_prefixes": ["/data/api/v1/nepse-data/price-history/"],
            }}
        }
        with patch.dict(os.environ, {"NEPSE_PROVIDER_ACCESS_MANIFEST": __import__("json").dumps(manifest)}, clear=True):
            self.assertEqual(_provider_access_approval(
                "sharehub", "chart",
                "https://sharehubnepal.com/data/api/v1/nepse-data/price-history/AAA?time=5Y"),
                (True, "approved"))

    def test_manifest_with_string_host_list_is_rejected(self):
        manifest = {
            "providers": {"sharehub": {
                "status": "approved", "allowed_data_types": ["chart"],
                "rights_status": "research_only", "reviewer": "reviewer",
                "evidence_ref": "evidence:sharehub", "contract_ref": "contract:sharehub",
                "valid_until": "2099-12-31", "allowed_hosts": "sharehubnepal.com",
                "allowed_path_prefixes": ["/data/"],
            }}
        }
        with patch.dict(os.environ, {"NEPSE_PROVIDER_ACCESS_MANIFEST": __import__("json").dumps(manifest)}, clear=True):
            self.assertEqual(_provider_access_approval(
                "sharehub", "chart", "https://sharehubnepal.com/data/x"),
                (False, "provider_access_manifest_invalid"))

    def test_manifest_cannot_authorize_another_host_or_path(self):
        manifest = {
            "providers": {"sharehub": {
                "status": "approved", "allowed_data_types": ["chart"],
                "rights_status": "research_only", "reviewer": "reviewer",
                "evidence_ref": "evidence:sharehub", "contract_ref": "contract:sharehub",
                "valid_until": "2099-12-31", "allowed_hosts": ["sharehubnepal.com"],
                "allowed_path_prefixes": ["/data/api/v1/nepse-data/price-history/"],
            }}
        }
        with patch.dict(os.environ, {"NEPSE_PROVIDER_ACCESS_MANIFEST": __import__("json").dumps(manifest)}, clear=True):
            self.assertEqual(_provider_access_approval(
                "sharehub", "chart", "https://evil.example/data/api/v1/nepse-data/price-history/AAA"),
                (False, "provider_endpoint_host_not_approved"))
            self.assertEqual(_provider_access_approval(
                "sharehub", "chart", "https://sharehubnepal.com/admin/export"),
                (False, "provider_endpoint_path_not_approved"))


    def test_untrusted_symbol_cannot_inject_path_into_provider_template(self):
        with patch.dict(os.environ, {
            "SHAREHUB_CHART_URL_TEMPLATE": "https://provider.example/chart/{symbol}"
        }, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "sharehub", "chart",
                equities=[{"symbol": "AAA/../../admin", "security_id": "1"}])
        self.assertEqual(result[0]["status"], "BLOCKED_ACCESS")
        self.assertEqual(result[0]["error"], "invalid_equity_template_value")

    def test_noncanonical_session_date_is_blocked_before_request(self):
        with patch.dict(os.environ, {
            "SHAREHUB_FLOORSHEET_URL_TEMPLATE": "https://provider.example/floorsheet/{date}"
        }, clear=True):
            result = collect_configured_provider(
                NoNetworkClient(), "sharehub", "floorsheet",
                session_dates=["2026-1-2"])
        self.assertEqual(result[0]["status"], "BLOCKED_ACCESS")
        self.assertEqual(result[0]["error"], "invalid_session_date_template_value")

if __name__ == "__main__":
    unittest.main()
