import unittest
from datetime import date, timedelta

from app.scanner_v3 import analyze_v3


def fixture_bars(count=80):
    start = date(2025, 1, 1)
    rows = []
    close = 100.0
    for i in range(count):
        close += (1.2 if i % 5 else -0.4) + (i % 3) * 0.1
        rows.append({
            "date": (start + timedelta(days=i)).isoformat(),
            "open": close - 0.25,
            "high": close + 1.7 + (i % 4) * 0.1,
            "low": close - 1.1 - (i % 2) * 0.2,
            "close": close,
            "volume": 800 + i * 13,
        })
    return rows


def reference_rsi(closes, period=14):
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def reference_atr(rows, period=14):
    ranges = []
    for previous, current in zip(rows, rows[1:]):
        ranges.append(max(
            current["high"] - current["low"],
            abs(current["high"] - previous["close"]),
            abs(current["low"] - previous["close"]),
        ))
    value = sum(ranges[:period]) / period
    for current in ranges[period:]:
        value = (value * (period - 1) + current) / period
    return value


class IndependentIndicatorReferenceTests(unittest.TestCase):
    def test_rsi_matches_independent_wilder_reference(self):
        rows = fixture_bars()
        closes = [r["close"] for r in rows]
        expected = round(reference_rsi(closes), 4)
        actual = analyze_v3("REF", rows)["metrics"]["rsi14"]
        self.assertAlmostEqual(actual, expected, places=4)

    def test_atr_matches_independent_true_range_reference(self):
        rows = fixture_bars()
        expected = round(reference_atr(rows), 6)
        actual = analyze_v3("REF", rows)["metrics"]["atr14"]
        self.assertAlmostEqual(actual, expected, places=6)

    def test_moving_averages_and_return_match_direct_calculation(self):
        rows = fixture_bars()
        closes = [r["close"] for r in rows]
        metrics = analyze_v3("REF", rows)["metrics"]
        self.assertAlmostEqual(metrics["sma20"], round(sum(closes[-20:]) / 20, 6))
        self.assertAlmostEqual(metrics["sma50"], round(sum(closes[-50:]) / 50, 6))
        expected_return = (closes[-1] / closes[-21] - 1) * 100
        self.assertAlmostEqual(metrics["return_20_sessions_pct"], round(expected_return, 4))


if __name__ == "__main__":
    unittest.main()
