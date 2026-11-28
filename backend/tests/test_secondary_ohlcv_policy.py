import unittest

from app.secondary_ohlcv_policy import validate_secondary_ohlcv_consensus
from app.source_trust_registry import SourcePolicy


class SecondaryOhlcvPolicyTests(unittest.TestCase):
    def absence(self):
        return {
            "url": "https://www.nepalstock.com.np/",
            "query_string": "symbol=NABIL&date=2026-11-20",
            "retrieved_utc": "2026-11-21T04:00:00Z",
            "http_result": "200_no_record",
            "blocker_class": "record_not_published",
            "owner": "data-quality",
            "due_date": "2026-11-30",
            "session_date": "2026-11-20",
        }

    def observation(self, source, upstream=None, close="510"):
        return {
            "source_id": source,
            "upstream_feed": upstream or source,
            "source_url": f"https://{source}.example/data/2026-11-20",
            "payload_sha256": ("a" * 64),
            "retrieved_utc": "2026-11-21T04:00:00Z",
            "parser_version": "test-parser-v1",
            "source_revision": "fixture-r1",
            "security_id": "NEPSE-123",
            "session_date": "2026-11-20",
            "session_dates": ["2026-11-19", "2026-11-20", "2026-11-21"],
            "ohlcv": {"open": "500", "high": "515", "low": "495",
                      "close": close, "volume": "120000"},
        }

    def consensus(self, observations):
        return {"official_source_absence": self.absence(), "observations": observations}

    def test_secondary_source_policy_allows_canonical_ohlcv_only(self):
        policy = SourcePolicy(
            source_id="sharehub", publisher_name="ShareHub",
            trust_tier="secondary_publisher", allowed_record_types=("ohlcv",),
            canonical_record_types=("ohlcv",), status="active",
            effective_from="2020-01-01", effective_to=None, reviewer="reviewer-1",
            reviewed_at="2026-11-28T00:00:00Z", evidence_refs=("policy-review",),
            rights_state="research_only", redistribution_allowed=False)
        self.assertEqual(policy.canonical_record_types, ("ohlcv",))

    def test_secondary_source_policy_rejects_non_ohlcv_canonical_types(self):
        with self.assertRaisesRegex(ValueError, "canonical OHLCV only"):
            SourcePolicy(
                source_id="sharehub", publisher_name="ShareHub",
                trust_tier="secondary_publisher",
                allowed_record_types=("ohlcv", "floorsheet"),
                canonical_record_types=("floorsheet",), status="active",
                effective_from="2020-01-01", effective_to=None, reviewer="reviewer-1",
                reviewed_at="2026-11-28T00:00:00Z", evidence_refs=("policy-review",),
                rights_state="research_only", redistribution_allowed=False)

    def test_three_independent_unanimous_sources_pass(self):
        observations = [self.observation("sharehub"), self.observation("nepsealpha"),
                        self.observation("chukul")]
        self.assertEqual(validate_secondary_ohlcv_consensus(
            self.consensus(observations), session_date="2026-11-20"), [])

    def test_two_sources_are_insufficient(self):
        observations = [self.observation("sharehub"), self.observation("nepsealpha")]
        reasons = validate_secondary_ohlcv_consensus(
            self.consensus(observations), session_date="2026-11-20")
        self.assertIn("fewer_than_three_lineage_independent_sources", reasons)

    def test_same_upstream_and_overlapping_dates_collapse_to_one(self):
        observations = [self.observation("sharehub", "feed-x"),
                        self.observation("nepsealpha", "feed-x"),
                        self.observation("chukul", "feed-y")]
        reasons = validate_secondary_ohlcv_consensus(
            self.consensus(observations), session_date="2026-11-20")
        self.assertIn("fewer_than_three_lineage_independent_sources", reasons)

    def test_disagreement_is_conflict_not_majority_vote(self):
        observations = [self.observation("sharehub"),
                        self.observation("nepsealpha"),
                        self.observation("chukul", close="511")]
        reasons = validate_secondary_ohlcv_consensus(
            self.consensus(observations), session_date="2026-11-20")
        self.assertIn("secondary_ohlcv_source_conflict", reasons)

    def test_official_access_denial_does_not_prove_record_absence(self):
        evidence = self.consensus([self.observation("sharehub"),
                                   self.observation("nepsealpha"),
                                   self.observation("chukul")])
        evidence["official_source_absence"]["http_result"] = "403_forbidden"
        reasons = validate_secondary_ohlcv_consensus(
            evidence, session_date="2026-11-20")
        self.assertIn("official_source_absence_not_proven", reasons)

    def test_secondary_provider_cannot_submit_malformed_candle(self):
        item = self.observation("sharehub")
        item["ohlcv"]["high"] = "490"
        reasons = validate_secondary_ohlcv_consensus(
            self.consensus([item, self.observation("nepsealpha"),
                            self.observation("chukul")]),
            session_date="2026-11-20")
        self.assertIn("invalid_ohlc_bounds", reasons)


if __name__ == "__main__":
    unittest.main()
