import unittest
from datetime import date, timedelta
from app.market_structure import detect_structure

def bars(values):
    return [dict(date=date(2025,1,1)+timedelta(days=i), open=c, high=h, low=l, close=c, volume=100) for i,(h,l,c) in enumerate(values)]

class MarketStructureTests(unittest.TestCase):
    def test_confirmation_and_break(self):
        rows=bars([(10,8,9),(12,9,11),(11,8,10),(14,11,13)])
        events=detect_structure(rows,1)["events"]
        self.assertTrue(any(e["type"]=="swing_high" and e["date"]=="2025-01-03" for e in events))
        self.assertTrue(any(e["type"]=="bos" and e["date"]=="2025-01-04" for e in events))
    def test_sweep_and_reversal(self):
        rows=bars([(10,8,9),(12,9,11),(11,7,9),(13,8,11),(14,10,13),(10,6,6.5)])
        events=detect_structure(rows,1)["events"]
        self.assertTrue(any(e["type"]=="liquidity_sweep" for e in events))
        self.assertTrue(any(e["type"]=="choch" and e["direction"]=="bearish" for e in events))
    def test_fvg(self):
        rows=bars([(10,8,9),(13,9,12),(15,11,14)])
        self.assertTrue(any(e["type"]=="fvg" and e["lower"]==10 and e["upper"]==11 for e in detect_structure(rows,1)["events"]))
    def test_prefix_invariance(self):
        rows=bars([(10,8,9),(12,9,11),(11,8,10),(14,11,13),(12,9,10)])
        full=detect_structure(rows,1)["events"]
        for n in range(1,len(rows)+1):
            self.assertEqual(detect_structure(rows[:n],1)["events"],[e for e in full if e["date"]<=str(rows[n-1]["date"])])
    def test_invalid(self):
        rows=bars([(10,8,9)])
        rows[0]["high"]=7
        self.assertEqual(detect_structure(rows)["status"],"data_quality_failed")


class ZoneTests(unittest.TestCase):
    def test_order_block_forms_after_break_and_retests_once(self):
        rows = bars([
            (10, 8, 9), (12, 9, 11), (11, 8, 10), (14, 11.5, 13),
            (13, 11, 12), (12, 10, 11), (11, 7, 7.5),
        ])
        rows[2]["open"] = 10.8
        result = detect_structure(rows, 1)
        block = next(e for e in result["events"] if e["type"] == "order_block")
        self.assertEqual(block["date"], "2025-01-04")
        self.assertEqual(block["origin_date"], "2025-01-03")
        self.assertEqual((block["lower"], block["upper"]), (8, 11))
        self.assertEqual(block["trigger"], "bos")
        lifecycle = [(e["type"], e["date"]) for e in result["events"]
                     if e.get("zone_id") == block["zone_id"]]
        self.assertEqual(lifecycle, [
            ("order_block", "2025-01-04"),
            ("zone_retest", "2025-01-05"),
            ("zone_invalidated", "2025-01-07"),
        ])
        for n in range(1, len(rows) + 1):
            cutoff = rows[n - 1]["date"].isoformat()
            self.assertEqual(detect_structure(rows[:n], 1)["events"], [
                event for event in result["events"] if event["date"] <= cutoff
            ])

    def test_gap_invalidation_takes_precedence_over_a_touch(self):
        rows = bars([(10, 8, 9), (13, 9, 12), (15, 11, 14), (12, 9, 9.5)])
        events = detect_structure(rows, 1)["events"]
        zone_id = "fvg:bullish:2025-01-03"
        self.assertEqual([e["type"] for e in events if e.get("zone_id") == zone_id],
                         ["fvg", "zone_invalidated"])

    def test_bearish_zone_uses_upper_bound_and_opposing_candle(self):
        rows = bars([(12, 10, 11), (11, 8, 9), (12, 9, 11), (9, 6, 7), (13, 8, 12.5)])
        rows[2]["open"] = 10
        events = detect_structure(rows, 1)["events"]
        zone = next(e for e in events if e["type"] == "order_block")
        self.assertEqual(zone["direction"], "bearish")
        self.assertEqual(zone["origin_date"], "2025-01-03")
        self.assertEqual(zone["invalidation"], {"field": "close", "operator": ">", "level": 12})
        self.assertTrue(any(e["type"] == "zone_invalidated" and e["zone_id"] == zone["zone_id"]
                            for e in events))


class MarketStructureAPITests(unittest.TestCase):
    def test_api_requires_reviewed_rows_and_tracks_prefix_availability(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from app import main
        from app.scanner_eligibility import load_reviewed_rows

        prefix = [
            dict(date=date(2024, 12, 17) + timedelta(days=i),
                 open=8, high=9, low=7, close=8, volume=100)
            for i in range(15)
        ]
        event_rows = bars([(10, 8, 9), (11, 8.5, 10), (13, 10, 12),
                           (12, 9, 10), (11, 9.5, 10), (15, 11, 14)])
        rows = prefix + event_rows
        for i, candle in enumerate(event_rows):
            candle["date"] = date(2025, 1, 1) + timedelta(days=i)
        rows[18]["open"] = 11.5
        manifest = []
        for i, candle in enumerate(rows):
            day = candle["date"].isoformat()
            manifest.append(dict(
                candle, symbol="TEST", date=day, instrument_type="equity",
                security_status="active", session_status="verified_open",
                source_id="sharehub", evidence_id=f"fixture-{i}", source_payload_sha256="a"*64,
                available_at=f"{day}T11:00:00Z", security_id="fixture-security",
                lifecycle_evidence_id="fixture-lifecycle", session_evidence_id=f"fixture-session-{i}",
                price_basis_reviewed=True, price_basis_status="verified_unadjusted_no_actions",
                corporate_action_status="clear", corporate_action_evidence_id="fixture-action-review",
                canonical_promotion_allowed=True,
            ))
        manifest[1]["available_at"] = "2025-01-06T12:00:00Z"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rows.json"
            path.write_text(json.dumps({"schema_version": 1, "records": manifest}), encoding="utf-8")
            reviewed = load_reviewed_rows(path)
        with patch.dict(main.DATA, {"TEST": rows}, clear=True), patch.object(main, "REVIEWED_ROWS", reviewed), patch.object(main, "EQUITY_UNIVERSE", {"symbols": ["TEST"]}):
            with TestClient(main.app) as client:
                unavailable = client.post("/v1/scan", json={"symbols": ["TEST"], "as_of": "2025-01-05"})
                early = unavailable.json()["results"][0]
                self.assertFalse(early["eligibility"]["eligible"])
                self.assertEqual(early["market_structure"]["events"], [])

                available = client.post("/v1/scan", json={"symbols": ["TEST"], "as_of": "2025-01-06"})
                self.assertEqual(available.status_code, 200)
                result = available.json()["results"][0]
                self.assertTrue(result["eligibility"]["eligible"])
                events = result["market_structure"]["events"]
                swing = next(e for e in events if e["type"] == "swing_high")
                self.assertEqual(swing["date"], "2025-01-05")
                self.assertEqual(swing["available_at"], "2025-01-06T12:00:00+00:00")
                order_block = next(e for e in events if e["type"] == "order_block")
                self.assertIn("fixture-18", {item["evidence_id"] for item in order_block["evidence"]})


class LiquidityRangeTests(unittest.TestCase):
    def test_equal_high_confirmation_is_causal(self):
        rows = bars([(10,8,9),(12,9,11),(10,8,9),(12.04,9,11),(10,8.5,9)])
        events = detect_structure(rows,1)["events"]
        equal = next(e for e in events if e["type"] == "equal_highs")
        self.assertEqual(equal["date"], "2025-01-05")
        self.assertEqual(equal["liquidity_side"], "buy_side")
        self.assertEqual((equal["lower"],equal["upper"]),(12,12.04))
        self.assertFalse(any(e["type"]=="equal_highs" for e in detect_structure(rows[:-1],1)["events"]))
        self.assertFalse(any(e["type"]=="equal_highs" for e in detect_structure(rows,1,0)["events"]))

    def test_equal_lows_and_discount(self):
        rows = bars([(11,9,10),(10,8,9),(12,9,11),(10,8.02,9),(11,9,9.5)])
        result = detect_structure(rows,1)
        equal = next(e for e in result["events"] if e["type"]=="equal_lows")
        self.assertEqual(equal["liquidity_side"],"sell_side")
        self.assertEqual(result["dealing_range"]["location"],"discount")
        self.assertAlmostEqual(result["dealing_range"]["equilibrium"],10.01)

    def test_broken_range_is_not_reused(self):
        rows = bars([(10,8,9),(12,9,11),(10,7,9),(11,8,10),(14,10,13)])
        self.assertIsNotNone(detect_structure(rows[:-1],1)["dealing_range"])
        self.assertIsNone(detect_structure(rows,1)["dealing_range"])

    def test_invalid_tolerance(self):
        for value in (-0.1,0.1,float("nan")):
            with self.assertRaises(ValueError):
                detect_structure([],1,value)
