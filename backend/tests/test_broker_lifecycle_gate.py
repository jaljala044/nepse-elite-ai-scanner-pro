import unittest
from app.broker_lifecycle_gate import lifecycle_reason,load_lifecycle
from app.broker_ledger_profiles import quarantine_category

def identity(**changes):
    return dict(dict(security_id="1",symbol="ABC",instrument_type="equity",valid_from="2024-01-01",valid_to=""),**changes)
def event(kind,day):
    return dict(security_id="1",symbol="ABC",event_type=kind,event_date=day)

class LifecycleTests(unittest.TestCase):
    def reason(self,identities=None,events=(),predecessors=(),start="2024-05-01",end="2024-05-31"):
        return lifecycle_reason("1","ABC",start,end,([identity()] if identities is None else identities,events,predecessors))
    def test_uncertified_identity_never_clears(self):
        self.assertEqual(self.reason(),"historical_identity_not_certified")
        self.assertEqual(self.reason([]),"missing_or_ambiguous_lifecycle_identity")
        self.assertEqual(self.reason([identity(),identity()]),"missing_or_ambiguous_lifecycle_identity")
        self.assertEqual(self.reason([identity(valid_from="")]),"trading_start_unverified")
    def test_trading_bounds(self):
        self.assertEqual(self.reason([identity(valid_from="2024-05-02")]),"before_reported_trading_start")
        self.assertEqual(self.reason([identity(valid_to="2024-05-30")]),"after_reported_trading_end")
    def test_inclusive_events(self):
        for kind in ("merger_joint_operations_start","post_merger_shares_listed","post_merger_shares_listed_and_trading_released","trading_suspension_start","trading_resumption","delisting"):
            for day in ("2024-05-01","2024-05-15","2024-05-31"):
                with self.subTest(kind=kind,day=day):
                    self.assertEqual(self.reason(events=[event(kind,day)]),"lifecycle_event_in_window")
    def test_predecessor(self):
        self.assertEqual(self.reason(predecessors=[{"symbol":"ABC","effective_date_verified":False}]),"unresolved_predecessor_identity")
    def test_quarantine_cannot_be_cleared_by_lifecycle(self):
        self.assertEqual(quarantine_category("1",{"1":{"ABC"}},{("ABC","2024-05-01")},"2024-05-01","2024-05-31"),"quarantine_blocked")
        self.assertEqual(self.reason(),"historical_identity_not_certified")
    def test_actual_register(self):
        identities,events,predecessors=load_lifecycle()
        self.assertTrue(identities and events and predecessors)
        for row in events:
            if row["event_type"].startswith(("merger","post_merger")):
                self.assertEqual(lifecycle_reason(row["security_id"],row["symbol"],row["event_date"],row["event_date"],(identities,events,predecessors)),"lifecycle_event_in_window")
