import unittest
from app.nepse_historical_universe import build_effective_universe

class EffectiveUniverseTests(unittest.TestCase):
    def test_later_ipo_is_included_only_after_listing(self):
        rows=[{"security_id":"A","symbol":"AAA","effective_from":"2020-01-01","listing_status":"ACTIVE"},
              {"security_id":"B","symbol":"BBB","effective_from":"2024-01-03","listing_status":"ACTIVE"}]
        out=build_effective_universe(universe_rows=rows,session_dates=["2024-01-02","2024-01-03"])
        self.assertEqual(out["active_by_session"]["2024-01-02"],{"A":"AAA"})
        self.assertEqual(out["active_by_session"]["2024-01-03"],{"A":"AAA","B":"BBB"})
    def test_delisted_and_suspended_names_remain_in_history(self):
        rows=[{"security_id":"A","symbol":"AAA","effective_from":"2020-01-01","listing_status":"ACTIVE"},
              {"security_id":"A","symbol":"AAA","effective_from":"2024-01-03","listing_status":"DELISTED"},
              {"security_id":"B","symbol":"BBB","effective_from":"2020-01-01","listing_status":"ACTIVE"},
              {"security_id":"B","symbol":"BBB","effective_from":"2024-01-02","listing_status":"SUSPENDED"}]
        out=build_effective_universe(universe_rows=rows,session_dates=["2024-01-02","2024-01-03"])
        self.assertIn("A",out["active_by_session"]["2024-01-02"])
        self.assertNotIn("A",out["active_by_session"]["2024-01-03"])
        self.assertNotIn("B",out["active_by_session"]["2024-01-02"])
        self.assertIn("A",out["security_ids"])
        self.assertGreater(out["inactive_security_count"],0)
    def test_duplicate_effective_event_blocks(self):
        row={"security_id":"A","symbol":"AAA","effective_from":"2020-01-01","listing_status":"ACTIVE"}
        out=build_effective_universe(universe_rows=[row,dict(row)],session_dates=["2024-01-02"])
        self.assertEqual(out["status"],"blocked")
        self.assertIn("duplicate_universe_effective_date:A",out["errors"])
    def test_invalid_interval_blocks(self):
        row={"security_id":"A","symbol":"AAA","effective_from":"2024-02-01","effective_to":"2024-01-01","listing_status":"ACTIVE"}
        out=build_effective_universe(universe_rows=[row],session_dates=["2024-01-02"])
        self.assertEqual(out["status"],"blocked")

if __name__=="__main__": unittest.main()
