import unittest
from app.broker_identity import (
    BrokerIdentityLink, aggregate_broker_side, resolve_broker_identity,
    validate_identity_link,
)


class BrokerIdentityTests(unittest.TestCase):
    def test_verified_mapping_requires_evidence(self):
        with self.assertRaises(ValueError):
            validate_identity_link(BrokerIdentityLink("src", "42", "B42", "verified", None))

    def test_unmapped_code_never_gets_entity(self):
        link = BrokerIdentityLink("src", "42", None, "unmapped", "registry-snapshot")
        self.assertEqual(resolve_broker_identity("src", "42", [link])["status"], "unmapped")

    def test_only_explicit_verified_link_resolves(self):
        link = BrokerIdentityLink("src", "42", "B42", "verified", "official-record")
        result = resolve_broker_identity("src", "42", [link])
        self.assertEqual(result["broker_entity_id"], "B42")
        self.assertEqual(result["status"], "verified")

    def test_ambiguous_link_stays_unresolved(self):
        link = BrokerIdentityLink("src", "42", None, "ambiguous", "review-1")
        self.assertIsNone(resolve_broker_identity("src", "42", [link])["broker_entity_id"])

    def test_conflicting_verified_links_stay_ambiguous(self):
        links = [
            BrokerIdentityLink("src", "42", "B42", "verified", "e1"),
            BrokerIdentityLink("src", "42", "B99", "verified", "e2"),
        ]
        self.assertEqual(resolve_broker_identity("src", "42", links)["status"], "ambiguous")

    def test_aggregation_keeps_unmapped_bucket_separate(self):
        rows = [
            {"session_date":"2026-11-24","security_id":"SEC1","broker_entity_id":"B42",
             "identity_status":"verified","side":"buy","quantity":10,"amount":1000},
            {"session_date":"2026-11-24","security_id":"SEC1","broker_entity_id":None,
             "identity_status":"unmapped","side":"buy","quantity":5,"amount":500},
        ]
        result = aggregate_broker_side(rows)
        self.assertEqual(len(result), 2)
        self.assertEqual(sum(x["quantity"] for x in result), 15)

    def test_negative_values_rejected(self):
        row = {"session_date":"2026-11-24","security_id":"SEC1","side":"buy",
               "quantity":-1,"amount":100}
        with self.assertRaises(ValueError):
            aggregate_broker_side([row])


if __name__ == "__main__":
    unittest.main()
