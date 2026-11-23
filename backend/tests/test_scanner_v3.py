from datetime import date, timedelta

from app.scanner_v3 import analyze_v3


def bars(count=60):
    start = date(2025, 1, 1)
    result = []
    for i in range(count):
        close = 100 + i
        result.append({
            "date": (start + timedelta(days=i)).isoformat(),
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1000 + i * 10,
        })
    return result


def test_returns_features_for_valid_history():
    result = analyze_v3("abc", bars())
    assert result["status"] == "ready"
    assert result["engine"] == "v3"
    assert result["symbol"] == "ABC"
    assert result["metrics"]["sma20"] == 150.5
    assert result["metrics"]["sma50"] == 135.5
    assert "positive_20_session_return" in result["evidence"]


def test_short_history_is_explicitly_insufficient():
    result = analyze_v3("ABC", bars(30))
    assert result["status"] == "insufficient_data"
    assert result["metrics"] == {}


def test_duplicate_dates_are_rejected():
    data = bars()
    data.append(data[-1].copy())
    result = analyze_v3("ABC", data)
    assert result["status"] == "data_quality_error"
    assert "duplicate session dates detected" in result["data_quality_errors"]


def test_invalid_ohlc_is_rejected_without_repair():
    data = bars()
    data[10]["high"] = data[10]["close"] - 5
    result = analyze_v3("ABC", data)
    assert result["status"] == "data_quality_error"
    assert any("high is below" in error for error in result["data_quality_errors"])


def test_zero_volume_does_not_create_infinite_ratio():
    data = bars()
    for row in data[-20:]:
        row["volume"] = 0
    result = analyze_v3("ABC", data)
    assert result["status"] == "ready"
    assert result["metrics"]["volume_ratio20"] is None


def test_flat_price_rsi_is_neutral():
    data = bars()
    for row in data:
        row.update(open=100, high=101, low=99, close=100)
    result = analyze_v3("ABC", data)
    assert result["status"] == "ready"
    assert result["metrics"]["rsi14"] == 50.0
