import unittest
from datetime import date, timedelta
from app.historical_segment_eligibility import evaluate_historical_segment


class HistoricalSegmentEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.sessions = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(120)]
        self.segment = {
            "symbol": "NABIL", "security_id": "123", "identity_verified": True,
            "effective_from": self.sessions[0], "effective_to": None,
            "boundary_reviewed": True, "suspension_overlap": False,
            "merger_or_successor_boundary": False, "adjustment_basis": "raw",
            "minimum_warmup_sessions": 20,
            "identity_evidence": self.source_evidence(
                "identity:NABIL:123", claims={"symbol": "NABIL", "security_id": "123"}
            ),
            "lifecycle_evidence": self.source_evidence(
                "lifecycle:NABIL:123",
                claims={
                    "symbol": "NABIL", "security_id": "123",
                    "effective_from": date(2025, 1, 1).isoformat(),
                    "effective_to": None, "boundary_reviewed": True,
                    "suspension_overlap": False,
                    "merger_or_successor_boundary": False,
                },
            ),
        }
        self.statuses = {day: "traded" for day in self.sessions}
        self.session_evidence = {
            day: {
                "status": "traded", "source_id": "fixture-calendar-v1",
                "source_record_ref": f"fixture:{day}",
                "source_url": "https://www.nepalstock.com/calendar/2025",
                "evidence_sha256": "e094fe908c56611d9de193318a6c9919e23d883b962adf83786b9d174fc85194",
                "payload_sha256": "e094fe908c56611d9de193318a6c9919e23d883b962adf83786b9d174fc85194",
                "payload_base64": "Zml4dHVyZS1jYWxlbmRhci1wYXlsb2Fk", "rights_status": "approved",
                "retrieved_at": "2025-12-31T15:00:00+05:45",
                "available_at": "2025-12-31T15:00:00+05:45",
            }
            for day in self.sessions
        }
        self.records = [self.row(day) for day in self.sessions]

    def source_evidence(self, record_ref, claims=None):
        evidence = {
            "source_id": "nepse-official-v1", "source_record_ref": record_ref,
            "source_url": "https://www.nepalstock.com/api/evidence",
            "evidence_sha256": "9a5df3729917cba86db1a823bdedea240ac08fd1cdacb93ac8d987c09b49bb08",
            "payload_sha256": "9a5df3729917cba86db1a823bdedea240ac08fd1cdacb93ac8d987c09b49bb08",
            "payload_base64": "Zml4dHVyZS1wYXlsb2Fk", "rights_status": "approved",
            "available_at": "2025-12-30T00:00:00+05:45",
            "retrieved_at": "2025-12-31T15:00:00+05:45",
        }
        if claims is not None:
            evidence["claims"] = claims
        return evidence

    def row(self, day):
        return {
            "session_date": day, "symbol": "NABIL", "security_id": "123",
            "open": "100", "high": "105", "low": "95", "close": "102", "volume": "1000",
            "adjustment_basis": "raw", "rights_status": "approved",
            "evidence_sha256": "9a5df3729917cba86db1a823bdedea240ac08fd1cdacb93ac8d987c09b49bb08", "available_at": "2025-12-30T00:00:00+05:45",
            "source_evidence": self.source_evidence("ohlcv:NABIL:123:" + day),
        }

    def evaluate(self, **overrides):
        statuses = overrides.get("session_statuses", self.statuses)
        evidence = {
            day: dict(item, status=statuses.get(day, item["status"]))
            for day, item in self.session_evidence.items()
        }
        args = dict(segment=self.segment, expected_sessions=self.sessions,
                    session_statuses=self.statuses, session_evidence=evidence,
                    records=self.records, required_sessions=120,
                    available_warmup_sessions=20,
                    decision_cutoff="2026-01-01T00:00:00+05:45")
        args.update(overrides)
        return evaluate_historical_segment(**args)


    def test_future_expected_session_is_rejected(self):
        future = "2026-01-02"
        statuses = dict(self.statuses, **{future: "traded"})
        evidence = dict(self.session_evidence, **{
            future: {
                "status": "traded", "source_id": "fixture-calendar-v1",
                "source_record_ref": f"fixture:{future}",
                "source_url": "https://www.nepalstock.com/calendar/2026",
                "evidence_sha256": "b" * 64, "payload_sha256": "b" * 64,
                "rights_status": "approved",
                "retrieved_at": "2025-12-31T15:00:00+05:45",
                "available_at": "2025-12-31T15:00:00+05:45",
            }
        })
        result = self.evaluate(
            expected_sessions=self.sessions + [future],
            session_statuses=statuses,
            session_evidence=evidence,
            records=self.records + [self.row(future)],
        )
        self.assertIn("future_expected_session:" + future, result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_complete_verified_segment_is_exploratory_only(self):
        result = self.evaluate()
        self.assertTrue(result["exploratory_replay_eligible"])
        self.assertFalse(result["approved_backtest_eligible"])
        self.assertFalse(result["production_promotion_allowed"])

    def test_traded_evidence_is_not_eligible_candle_coverage(self):
        records = list(self.records[:-1])
        records[0] = dict(records[0], volume="0")
        records[1] = dict(records[1], rights_status="unknown")
        result = self.evaluate(records=records)
        self.assertEqual(result["verified_traded_session_count"], 120)
        self.assertEqual(result["valid_ohlcv_candle_count"], 118)
        self.assertEqual(result["eligible_ohlcv_candle_count"], 117)
        self.assertIn("insufficient_traded_sessions", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_missing_bar_fails_closed(self):
        result = self.evaluate(records=self.records[:-1])
        self.assertIn("missing_bar:" + self.sessions[-1], result["reasons"])

    def test_verified_no_trade_is_not_missing_or_zero_filled(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "no_trade_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertFalse(result["exploratory_replay_eligible"])
        self.assertEqual(result["verified_no_trade_count"], 1)
        self.assertEqual(result["verified_traded_session_count"], 119)
        self.assertIn("insufficient_traded_sessions", result["reasons"])

    def test_unverified_session_status_fails_closed(self):
        statuses = dict(self.statuses)
        del statuses[self.sessions[0]]
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("session_status_unverified:" + self.sessions[0], result["reasons"])

    def test_lifecycle_or_identity_unknown_fails_closed(self):
        segment = dict(self.segment, identity_verified=False, merger_or_successor_boundary=None)
        result = self.evaluate(segment=segment)
        self.assertIn("instrument_identity_not_verified", result["reasons"])
        self.assertIn("merger_or_successor_boundary_unknown_or_crossed", result["reasons"])

    def test_late_available_data_is_lookahead(self):
        records = list(self.records)
        records[0] = dict(records[0], available_at="2026-01-02T00:00:00+05:45")
        result = self.evaluate(records=records)
        self.assertIn("lookahead_available_after_cutoff:" + self.sessions[0], result["reasons"])

    def test_rights_and_hash_are_required(self):
        records = list(self.records)
        records[0] = dict(records[0], rights_status="unknown", evidence_sha256="bad")
        result = self.evaluate(records=records)
        self.assertIn("source_rights_not_approved:" + self.sessions[0], result["reasons"])
        self.assertIn("evidence_hash_missing_or_invalid:" + self.sessions[0], result["reasons"])

    def test_bar_evidence_hash_must_bind_to_retained_source_payload(self):
        records = list(self.records)
        records[0] = dict(records[0], evidence_sha256="d" * 64)
        result = self.evaluate(records=records)
        self.assertIn("evidence_hash_binding_mismatch:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_duplicate_bars_fail_closed(self):
        result = self.evaluate(records=self.records + [self.records[0]])
        self.assertIn("duplicate_bar:" + self.sessions[0], result["reasons"])

    def test_insufficient_warmup_fails_closed(self):
        result = self.evaluate(available_warmup_sessions=5)
        self.assertIn("insufficient_causal_warmup", result["reasons"])

    def test_no_trade_does_not_count_toward_required_traded_sessions(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "no_trade_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertIn("insufficient_traded_sessions", result["reasons"])
        self.assertEqual(result["verified_traded_session_count"], 119)

    def test_session_outside_effective_lifecycle_fails_closed(self):
        segment = dict(self.segment, effective_to=self.sessions[-2])
        result = self.evaluate(segment=segment)
        self.assertIn("session_outside_instrument_effective_interval:" + self.sessions[-1], result["reasons"])

    def test_no_trade_session_with_bar_is_conflict(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "no_trade_verified"})
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("bar_present_on_verified_no_trade_session:" + day, result["reasons"])


    def test_closed_session_is_distinct_from_verified_no_trade(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "closed_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertEqual(result["verified_closed_session_count"], 1)
        self.assertEqual(result["verified_no_trade_count"], 0)
        self.assertIn("closed_session_in_expected_sessions:" + day, result["reasons"])

    def test_explicit_unknown_session_is_not_assumed_closed(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "unknown"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertEqual(result["unknown_session_count"], 1)
        self.assertEqual(result["verified_closed_session_count"], 0)
        self.assertIn("session_status_unverified:" + day, result["reasons"])

    def test_adjustment_basis_mismatch_fails_closed(self):
        records = list(self.records)
        records[0] = dict(records[0], adjustment_basis="verified_adjusted")
        result = self.evaluate(records=records)
        self.assertIn("adjustment_basis_mismatch:" + self.sessions[0], result["reasons"])

    def test_record_outside_verified_session_grid_is_reported(self):
        records = list(self.records) + [self.row("2025-06-01")]
        result = self.evaluate(records=records)
        self.assertIn("unexpected_bar:2025-06-01", result["reasons"])

    def test_unavailable_or_naive_timestamp_fails_closed(self):
        records = list(self.records)
        records[0] = dict(records[0], available_at="2025-12-31T15:00:00")
        result = self.evaluate(records=records)
        self.assertIn("available_at_unverified:" + self.sessions[0], result["reasons"])

    def test_zero_volume_bar_is_invalid_for_traded_session(self):
        records = list(self.records)
        records[0] = dict(records[0], volume="0")
        result = self.evaluate(records=records)
        self.assertIn("invalid_ohlcv:" + self.sessions[0], result["reasons"])

    def test_fractional_share_volume_is_invalid(self):
        records = list(self.records)
        records[0] = dict(records[0], volume="1000.5")
        result = self.evaluate(records=records)
        self.assertIn("invalid_ohlcv:" + self.sessions[0], result["reasons"])

    def test_untrusted_session_source_host_fails_closed(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], source_url="https://example.invalid/calendar")
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])

    def test_official_nepse_com_np_hosts_are_accepted_for_all_evidence(self):
        for host in ("nepalstock.com.np", "www.nepalstock.com.np"):
            with self.subTest(host=host):
                url = f"https://{host}/api/evidence"
                segment = dict(
                    self.segment,
                    identity_evidence=dict(self.segment["identity_evidence"], source_url=url),
                    lifecycle_evidence=dict(self.segment["lifecycle_evidence"], source_url=url),
                )
                session_evidence = {
                    day: dict(item, source_url=url)
                    for day, item in self.session_evidence.items()
                }
                records = [
                    dict(row, source_evidence=dict(row["source_evidence"], source_url=url))
                    for row in self.records
                ]
                result = self.evaluate(
                    segment=segment, session_evidence=session_evidence, records=records
                )
                self.assertTrue(result["exploratory_replay_eligible"], result["reasons"])

    def test_nepse_com_np_lookalike_host_is_rejected(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(
            evidence[self.sessions[0]],
            source_url="https://nepalstock.com.np.attacker.example/calendar",
        )
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_bar_requires_full_primary_source_evidence(self):
        records = list(self.records)
        records[0] = dict(records[0], source_evidence={"source_url": "https://www.nepalstock.com"})
        result = self.evaluate(records=records)
        self.assertIn("bar_source_evidence_unverified:" + self.sessions[0], result["reasons"])

    def test_identity_claims_must_match_segment_identity(self):
        segment = dict(
            self.segment,
            identity_evidence=self.source_evidence(
                "identity:NABIL:123", claims={"symbol": "OTHER", "security_id": "123"}
            ),
        )
        result = self.evaluate(segment=segment)
        self.assertIn("instrument_identity_claims_mismatch", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_lifecycle_claims_must_match_effective_boundaries(self):
        segment = dict(self.segment)
        segment["lifecycle_evidence"] = self.source_evidence(
            "lifecycle:NABIL:123",
            claims={
                "symbol": "NABIL", "security_id": "123",
                "effective_from": "2024-01-01", "effective_to": None,
                "boundary_reviewed": True, "suspension_overlap": False,
                "merger_or_successor_boundary": False,
            },
        )
        result = self.evaluate(segment=segment)
        self.assertIn("lifecycle_claims_mismatch", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_identity_and_lifecycle_flags_without_source_evidence_fail(self):
        segment = dict(self.segment, identity_evidence=None, lifecycle_evidence=None)
        result = self.evaluate(segment=segment)
        self.assertIn("instrument_identity_source_evidence_unverified", result["reasons"])
        self.assertIn("lifecycle_source_evidence_unverified", result["reasons"])

    def test_adjusted_basis_requires_factor_and_effective_date_evidence(self):
        segment = dict(self.segment, adjustment_basis="verified_adjusted")
        result = self.evaluate(segment=segment)
        self.assertIn("adjustment_factor_evidence_unverified", result["reasons"])

    def adjustment_evidence(self, *, factor="0.5", factor_version="bonus-v1",
                            effective_date="2025-01-01", claims=None):
        evidence = self.source_evidence("corporate-action:CFCL:bonus-v1")
        evidence.update({"factor": factor, "factor_version": factor_version,
                         "effective_date": effective_date})
        evidence["claims"] = claims if claims is not None else {
            "factor": factor, "factor_version": factor_version,
            "effective_date": effective_date,
        }
        return evidence

    def test_adjustment_factor_requires_canonical_effective_date(self):
        segment = dict(self.segment, adjustment_basis="verified_adjusted",
                       adjustment_evidence=self.adjustment_evidence(effective_date="01-01-2025"))
        result = self.evaluate(segment=segment)
        self.assertIn("adjustment_factor_evidence_unverified", result["reasons"])

    def test_future_adjustment_effective_date_fails_point_in_time_gate(self):
        segment = dict(self.segment, adjustment_basis="verified_adjusted",
                       adjustment_evidence=self.adjustment_evidence(effective_date="2026-01-02"))
        result = self.evaluate(segment=segment)
        self.assertIn("adjustment_factor_evidence_unverified", result["reasons"])

    def test_adjustment_factor_claims_must_match_evidence_fields(self):
        evidence = self.adjustment_evidence(
            claims={"factor": "0.25", "factor_version": "bonus-v1",
                    "effective_date": "2025-01-01"})
        segment = dict(self.segment, adjustment_basis="verified_adjusted",
                       adjustment_evidence=evidence)
        result = self.evaluate(segment=segment)
        self.assertIn("adjustment_factor_evidence_unverified", result["reasons"])

    def test_adjustment_factor_requires_matching_claims(self):
        evidence = self.adjustment_evidence()
        evidence.pop("claims")
        segment = dict(self.segment, adjustment_basis="verified_adjusted",
                       adjustment_evidence=evidence)
        result = self.evaluate(segment=segment)
        self.assertIn("adjustment_factor_evidence_unverified", result["reasons"])

    def test_source_payload_hash_must_match_evidence_hash(self):
        records = list(self.records)
        source = dict(records[0]["source_evidence"], payload_sha256="d" * 64)
        records[0] = dict(records[0], source_evidence=source)
        result = self.evaluate(records=records)
        self.assertIn("bar_source_evidence_unverified:" + self.sessions[0], result["reasons"])

    def test_source_retrieval_cannot_precede_source_availability(self):
        records = list(self.records)
        source = dict(records[0]["source_evidence"], retrieved_at="2025-12-29T00:00:00+05:45")
        records[0] = dict(records[0], source_evidence=source)
        result = self.evaluate(records=records)
        self.assertIn("bar_source_evidence_unverified:" + self.sessions[0], result["reasons"])

    def test_expected_session_outside_lifecycle_fails_even_without_bar(self):
        segment = dict(self.segment, effective_to=self.sessions[-2])
        result = self.evaluate(segment=segment, records=self.records[:-1])
        self.assertIn(
            "expected_session_outside_instrument_effective_interval:" + self.sessions[-1],
            result["reasons"],
        )

    def test_status_for_date_outside_expected_grid_fails_closed(self):
        statuses = dict(self.statuses, **{"2025-06-01": "traded"})
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("unexpected_session_status:2025-06-01", result["reasons"])

    def test_expected_sessions_must_be_a_date_list(self):
        with self.assertRaisesRegex(ValueError, "expected_sessions must be a verified date list"):
            self.evaluate(expected_sessions="2025-01-01")

    def test_session_source_url_requires_https_host(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], source_url="https://")
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])
        self.assertEqual(result["unknown_session_count"], 1)

    def test_missing_session_source_provenance_fails_closed(self):
        evidence = dict(self.session_evidence)
        del evidence[self.sessions[0]]
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_missing:" + self.sessions[0], result["reasons"])
        self.assertEqual(result["unknown_session_count"], 1)

    def test_session_source_provenance_must_match_classification(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], status="no_trade_verified")
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_status_mismatch:" + self.sessions[0], result["reasons"])

    def test_primary_evidence_requires_retained_raw_payload_bytes(self):
        evidence = dict(self.session_evidence)
        item = dict(evidence[self.sessions[0]])
        item.pop("payload_base64")
        evidence[self.sessions[0]] = item
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_primary_evidence_recomputes_hash_from_exact_payload_bytes(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(
            evidence[self.sessions[0]], payload_base64="ZGlmZmVyZW50"
        )
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_primary_evidence_rejects_malformed_payload_base64(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(
            evidence[self.sessions[0]], payload_base64="%%%not-base64%%%"
        )
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_late_session_source_evidence_fails_point_in_time_gate(self):
        evidence = dict(self.session_evidence)
        evidence[self.sessions[0]] = dict(
            evidence[self.sessions[0]], available_at="2026-01-02T00:00:00+05:45"
        )
        result = self.evaluate(session_evidence=evidence)
        self.assertIn("session_evidence_lookahead:" + self.sessions[0], result["reasons"])


    def test_expected_sessions_must_be_an_explicit_date_list(self):
        with self.assertRaisesRegex(ValueError, "expected_sessions must be a verified date list"):
            self.evaluate(expected_sessions={"2025-01-01": True})

    def test_session_evidence_url_requires_https_authority(self):
        for bad_url in ("http://example.invalid/calendar", "https:///calendar", "https://[broken"):
            with self.subTest(url=bad_url):
                evidence = dict(self.session_evidence)
                evidence[self.sessions[0]] = dict(evidence[self.sessions[0]], source_url=bad_url)
                result = self.evaluate(session_evidence=evidence)
                self.assertIn("session_evidence_unverified:" + self.sessions[0], result["reasons"])


    def test_duplicate_expected_sessions_fail_closed(self):
        result = self.evaluate(expected_sessions=[self.sessions[0], self.sessions[0]])
        self.assertIn("duplicate_expected_session", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])


    def test_each_required_session_provenance_field_is_mandatory(self):
        day = self.sessions[0]
        invalid_fields = {
            "source_id": "",
            "source_record_ref": "",
            "evidence_sha256": "not-a-sha256",
            "rights_status": "pending",
            "retrieved_at": "not-a-timestamp",
            "available_at": "not-a-timestamp",
        }
        for field, invalid_value in invalid_fields.items():
            with self.subTest(field=field):
                evidence = dict(self.session_evidence)
                evidence[day] = dict(evidence[day], **{field: invalid_value})
                result = self.evaluate(session_evidence=evidence)
                self.assertIn("session_evidence_unverified:" + day, result["reasons"])
                self.assertEqual(result["unknown_session_count"], 1)


    def test_verified_suspension_is_distinct_and_blocks_segment(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "suspended_verified"})
        result = self.evaluate(session_statuses=statuses, records=self.records[:-1])
        self.assertEqual(result["verified_suspended_session_count"], 1)
        self.assertEqual(result["verified_no_trade_count"], 0)
        self.assertIn("suspended_session_in_segment:" + day, result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_bar_during_verified_suspension_is_a_conflict(self):
        day = self.sessions[-1]
        statuses = dict(self.statuses, **{day: "suspended_verified"})
        result = self.evaluate(session_statuses=statuses)
        self.assertIn("bar_on_suspended_session:" + day, result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_unresolved_suspension_overlap_blocks_segment_identity(self):
        segment = dict(self.segment, suspension_overlap=None)
        result = self.evaluate(segment=segment)
        self.assertIn("suspension_overlap_or_unknown", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])


    def test_explicit_suspension_overlap_blocks_segment(self):
        segment = dict(self.segment, suspension_overlap=True)
        result = self.evaluate(segment=segment)
        self.assertIn("suspension_overlap_or_unknown", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_invalid_effective_to_fails_closed(self):
        segment = dict(self.segment, effective_to="not-a-date")
        result = self.evaluate(segment=segment)
        self.assertIn("effective_to_invalid", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])

    def test_reversed_effective_interval_fails_closed(self):
        segment = dict(
            self.segment,
            effective_from=self.sessions[-1],
            effective_to=self.sessions[0],
        )
        result = self.evaluate(segment=segment)
        self.assertIn("invalid_effective_interval", result["reasons"])
        self.assertFalse(result["exploratory_replay_eligible"])


if __name__ == "__main__":
    unittest.main()
