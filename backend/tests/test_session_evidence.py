import unittest
from datetime import date
from app.session_evidence import SessionEvidence, resolve_session_state


def evidence(state="confirmed_trading_session", tier="exchange", available="2026-11-24T10:00:00Z", eid="E1"):
    return SessionEvidence(date(2026, 11, 24), state, "nepse", tier, eid, available)


class SessionEvidenceTests(unittest.TestCase):
    def test_primary_visible_evidence_resolves_session(self):
        r = resolve_session_state(date(2026, 11, 24), [evidence()],
                                  "2026-11-25T00:00:00Z")
        self.assertTrue(r["is_confirmed_trading_session"])

    def test_future_published_evidence_not_visible(self):
        r = resolve_session_state(date(2026, 11, 24),
                                  [evidence(available="2026-11-26T00:00:00Z")],
                                  "2026-11-25T00:00:00Z")
        self.assertEqual(r["session_state"], "unknown")

    def test_secondary_weekday_claim_does_not_verify(self):
        r = resolve_session_state(date(2026, 11, 24), [evidence(tier="secondary")],
                                  "2026-11-25T00:00:00Z")
        self.assertEqual(r["status"], "unknown")

    def test_conflicting_primary_sources_remain_unknown(self):
        r = resolve_session_state(date(2026, 11, 24),
                                  [evidence(eid="E1"), evidence("confirmed_exchange_closure", eid="E2")],
                                  "2026-11-25T00:00:00Z")
        self.assertEqual(r["status"], "conflicting_evidence")
        self.assertEqual(r["session_state"], "unknown")

    def test_no_evidence_never_means_closed(self):
        r = resolve_session_state(date(2026, 11, 24), [], "2026-11-25T00:00:00Z")
        self.assertFalse(r["is_confirmed_closed"])
        self.assertFalse(r["missing_evidence_means_closed"])

    def test_naive_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            evidence(available="2026-11-24T10:00:00")


if __name__ == "__main__":
    unittest.main()
