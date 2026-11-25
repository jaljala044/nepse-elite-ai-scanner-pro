import unittest
from datetime import date
from app.broker_identity import (
    BrokerIdentityLink, aggregate_broker_side, resolve_broker_identity,
    validate_identity_link, BrokerNameObservation, BrokerEntityName,
    reconcile_broker_source_name, broker_name_history,
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


    def test_effective_dated_mapping_resolves_historical_identity(self):
        links = [
            BrokerIdentityLink("src", "42", "B42", "verified", "e1",
                               valid_from=date(2020,1,1), valid_to=date(2023,12,31)),
            BrokerIdentityLink("src", "42", "B99", "verified", "e2",
                               valid_from=date(2024,1,1)),
        ]
        self.assertEqual(resolve_broker_identity("src", "42", links, "2022-06-01")["broker_entity_id"], "B42")
        self.assertEqual(resolve_broker_identity("src", "42", links, "2025-01-01")["broker_entity_id"], "B99")

    def test_dated_mapping_is_not_assumed_current_without_as_of(self):
        link = BrokerIdentityLink("src", "42", "B42", "verified", "e1",
                                  valid_from=date(2020,1,1))
        self.assertEqual(resolve_broker_identity("src", "42", [link])["status"], "unmapped")

    def test_overlapping_effective_mappings_are_ambiguous(self):
        links = [
            BrokerIdentityLink("src", "42", "B42", "verified", "e1",
                               valid_from=date(2020,1,1)),
            BrokerIdentityLink("src", "42", "B99", "verified", "e2",
                               valid_from=date(2022,1,1)),
        ]
        self.assertEqual(resolve_broker_identity("src", "42", links, date(2023,1,1))["status"], "ambiguous")

    def test_invalid_effective_date_range_rejected(self):
        link = BrokerIdentityLink("src", "42", "B42", "verified", "e1",
                                   valid_from=date(2024,1,2), valid_to=date(2024,1,1))
        with self.assertRaises(ValueError):
            validate_identity_link(link)

    def test_exact_name_match_is_only_a_review_candidate(self):
        names = [BrokerEntityName("B42", "ABC Securities Ltd", date(2020,1,1), None, "registry-1")]
        result = reconcile_broker_source_name("ABC Securities Ltd", date(2024,1,1), names)
        self.assertEqual(result["status"], "candidate_requires_evidence")
        self.assertFalse(result["auto_verified"])

    def test_same_name_on_multiple_entities_is_ambiguous(self):
        names = [
            BrokerEntityName("B42", "ABC Securities", date(2020,1,1), None, "e1"),
            BrokerEntityName("B99", "ABC Securities", date(2020,1,1), None, "e2"),
        ]
        self.assertEqual(reconcile_broker_source_name("ABC Securities", date(2024,1,1), names)["status"], "ambiguous")

    def test_historical_name_is_not_used_outside_validity(self):
        names = [BrokerEntityName("B42", "Old Broker Name", date(2020,1,1), date(2022,12,31), "e1")]
        self.assertEqual(reconcile_broker_source_name("Old Broker Name", date(2024,1,1), names)["status"], "unmapped")

    def test_source_name_history_is_preserved_in_date_order(self):
        observations = [
            BrokerNameObservation("src", "42", "New Name", date(2024,1,1), "e2"),
            BrokerNameObservation("src", "42", "Old Name", date(2020,1,1), "e1"),
        ]
        history = broker_name_history(observations)
        self.assertEqual([x["observed_name"] for x in history], ["Old Name", "New Name"])


if __name__ == "__main__":
    unittest.main()
