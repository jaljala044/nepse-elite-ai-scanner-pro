import unittest
from app.historical_market_data_policy import (
    build_five_year_collection_plan, classify_history_coverage, resolve_record_by_two_source_match,
)
from app.source_trust_registry import SourcePolicy


def observation(source, record, upstream=None, dates=None):
    return {
        "source_id": source, "upstream_feed": upstream or source,
        "publisher_identity": {"sharehub":"ShareHub","chukul":"Chukul","sharesansar":"ShareSansar","nepsealpha":"NEPSE Alpha"}[source],
        "publisher_identity_evidence_ref": f"provider-identity:{source}",
        "source_contract_ref": f"provider-contract:{source}",
        "source_url": f"https://{source}.example/archive",
        "retrieved_utc": "2026-11-28T00:00:00Z",
        "payload_sha256": "a" * 64, "parser_version": "v1",
        "source_revision": "r1",
        "session_dates": dates or ["2026-01-01", "2026-01-02"],
        "record": record,
    }


class HistoricalMarketDataPolicyTests(unittest.TestCase):
    def chart(self, close="10"):
        return {"session_date": "2026-01-02", "symbol": "AAA",
                "open": "9", "high": "11", "low": "8",
                "close": close, "volume": "100"}

    def floor(self, amount="100"):
        return {"trade_date": "2026-01-02", "contract_id": "C1",
                "symbol": "AAA", "buyer_broker_code": "11",
                "seller_broker_code": "22", "quantity": "10",
                "rate": "10", "amount": amount}

    def test_plan_has_five_years_and_per_equity_coverage_matrix(self):
        plan = build_five_year_collection_plan(
            as_of_date="2026-11-28",
            equities=[{"symbol": "AAA", "security_id": "1"},
                      {"symbol": "BBB", "security_id": "2"}])
        self.assertEqual(plan["period_start"], "2021-11-28")
        self.assertEqual(plan["equity_count"], 2)
        self.assertEqual(len(plan["required_collections"]), 10)
        self.assertEqual(len(plan["coverage_matrix"]), 20)
        self.assertEqual(plan["session_calendar_count"], 0)
        self.assertTrue(all(x["status"] == ("BLOCKED_DEPENDENCY" if x["data_type"] == "floorsheet" else "BLOCKED_ACCESS") for x in plan["coverage_matrix"]))

    def test_plan_exposes_five_year_target_and_three_year_minimum(self):
        plan = build_five_year_collection_plan(
            as_of_date="2026-11-28",
            equities=[{"symbol": "AAA", "security_id": "1"}])
        self.assertEqual(plan["preferred_years"], 5)
        self.assertEqual(plan["minimum_years"], 3)
        self.assertEqual(plan["minimum_period_start"], "2023-11-28")
        self.assertTrue(all(x["minimum_years"] == 3 for x in plan["coverage_matrix"]))

    def test_five_year_history_is_preferred(self):
        result = classify_history_coverage(
            coverage_start="2021-11-28", as_of_date="2026-11-28")
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")
        self.assertEqual(result["coverage_tier"], "preferred_5_year")

    def test_three_year_history_is_accepted_as_minimum_fallback(self):
        result = classify_history_coverage(
            coverage_start="2023-11-28", as_of_date="2026-11-28")
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")
        self.assertEqual(result["coverage_tier"], "minimum_3_year_fallback")

    def test_less_than_three_year_history_remains_partial(self):
        result = classify_history_coverage(
            coverage_start="2024-01-01", as_of_date="2026-11-28")
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")
        self.assertEqual(result["coverage_tier"], "below_3_year_minimum")

    def test_plan_handles_leap_day(self):
        self.assertEqual(
            build_five_year_collection_plan(as_of_date="2024-02-29",
                equities=[{"symbol": "AAA", "security_id": "1"}])["period_start"],
            "2019-02-28")

    def test_plan_rejects_missing_or_duplicate_security_identity(self):
        with self.assertRaisesRegex(ValueError, "complete equity universe"):
            build_five_year_collection_plan(as_of_date="2026-11-28", equities=[])
        with self.assertRaisesRegex(ValueError, "unique symbol/security_id"):
            build_five_year_collection_plan(
                as_of_date="2026-11-28",
                equities=[{"symbol": "AAA", "security_id": "1"},
                          {"symbol": "AAA", "security_id": "1"}])

    def test_two_independent_sources_matching_chart_complete(self):
        result = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=[observation("sharehub", self.chart()),
                          observation("chukul", self.chart())])
        self.assertEqual(result["status"], "COMPLETE_EVIDENCED")
        self.assertTrue(result["canonical_candidate"])

    def test_two_same_lineage_sources_do_not_count_as_two(self):
        dates = ["2021-01-01", "2022-01-01", "2023-01-01"]
        result = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=[observation("sharehub", self.chart(), "feed-x", dates),
                          observation("chukul", self.chart(), "feed-x", dates)])
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")
        self.assertFalse(result["canonical_candidate"])

    def test_two_matching_sources_resolve_floor_contract(self):
        result = resolve_record_by_two_source_match(
            record_type="floorsheet", record_key="2026-01-02|C1",
            observations=[observation("sharehub", self.floor()),
                          observation("sharesansar", self.floor())])
        self.assertEqual(result["status"], "COMPLETE_EVIDENCED")
        self.assertEqual(result["selected_record"]["contract_id"], "C1")

    def test_third_source_mismatch_requires_reason_and_evidence_reference(self):
        observations = [observation("sharehub", self.chart()),
                        observation("chukul", self.chart()),
                        observation("sharesansar", self.chart(close="10.5"))]
        unresolved = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=observations)
        self.assertEqual(unresolved["status"], "PARTIAL_EVIDENCED")
        resolved = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=observations,
            mismatch_investigation={"reason": "different adjustment basis",
                                    "evidence_refs": ["corporate-action-record-1"]})
        self.assertEqual(resolved["status"], "COMPLETE_EVIDENCED")
        self.assertEqual(len(resolved["conflicts"]), 1)
        self.assertIn("price_basis_corporate_action_or_parser",
                      resolved["conflicts"][0]["possible_causes"])

    def test_one_source_or_two_matching_from_same_lineage_does_not_approve(self):
        result = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=[observation("sharehub", self.chart())])
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")

    def test_secondary_provider_can_supply_canonical_chart_and_floorsheet_only(self):
        policy = SourcePolicy(
            source_id="sharehub", publisher_name="ShareHub",
            trust_tier="secondary_publisher",
            allowed_record_types=("ohlcv", "floorsheet"),
            canonical_record_types=("ohlcv", "floorsheet"),
            status="active", effective_from="2021-01-01", effective_to=None,
            reviewer="reviewer-1", reviewed_at="2026-11-28T00:00:00Z",
            evidence_refs=("two-source-policy",), rights_state="research_only",
            redistribution_allowed=False)
        self.assertEqual(set(policy.canonical_record_types), {"ohlcv", "floorsheet"})

    def test_secondary_provider_cannot_supply_canonical_sector_or_broker_records(self):
        with self.assertRaisesRegex(ValueError, "canonical OHLCV and floorsheet records only"):
            SourcePolicy(
                source_id="sharehub", publisher_name="ShareHub",
                trust_tier="secondary_publisher",
                allowed_record_types=("ohlcv", "sector_membership"),
                canonical_record_types=("sector_membership",),
                status="active", effective_from="2021-01-01", effective_to=None,
                reviewer="reviewer-1", reviewed_at="2026-11-28T00:00:00Z",
                evidence_refs=("two-source-policy",))

    def test_invalid_chart_is_rejected(self):
        bad = self.chart()
        bad["high"] = "7"
        result = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=[observation("sharehub", bad),
                          observation("chukul", bad)])
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")


    def test_same_publisher_with_different_upstream_labels_is_not_independent(self):
        first = observation("sharehub", self.chart(), "claimed-feed-a")
        second = observation("chukul", self.chart(), "claimed-feed-b")
        second["publisher_identity"] = first["publisher_identity"]
        result = resolve_record_by_two_source_match(
            record_type="chart", record_key="AAA|2026-01-02",
            observations=[first, second])
        self.assertEqual(result["status"], "PARTIAL_EVIDENCED")
        self.assertFalse(result["canonical_candidate"])

    def test_collection_plan_rejects_noncanonical_as_of_date(self):
        with self.assertRaisesRegex(ValueError, "canonical YYYY-MM-DD"):
            build_five_year_collection_plan(
                as_of_date="2026-1-2",
                equities=[{"symbol": "AAA", "security_id": "1"}])

    def test_collection_plan_rejects_session_outside_three_year_minimum_window(self):
        with self.assertRaisesRegex(ValueError, "minimum collection window"):
            build_five_year_collection_plan(
                as_of_date="2026-11-28",
                equities=[{"symbol": "AAA", "security_id": "1"}],
                session_dates=["2023-11-27"])

    def test_collection_plan_sorts_session_grid_deterministically(self):
        result = build_five_year_collection_plan(
            as_of_date="2026-11-28",
            equities=[{"symbol": "AAA", "security_id": "1"}],
            session_dates=["2026-11-27", "2026-11-26"])
        self.assertEqual(result["session_calendar_count"], 2)


if __name__ == "__main__":
    unittest.main()
