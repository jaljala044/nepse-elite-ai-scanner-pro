"""Reviewed index trends and transparent relative-rotation proxies."""
from datetime import date
from math import isfinite
WINDOWS=(5,21,63,126,252)

def index_intelligence(rows, *, sessions, benchmark, expected_indices, calendar_verified=False):
    base={"status":"unavailable","production_score":None,"indices":{}}
    days=[date.fromisoformat(str(x)).isoformat() for x in sessions]
    if not calendar_verified or len(days)<51 or days!=sorted(set(days)):
        return dict(base,reason="verified_calendar_or_history_missing")
    expected=set(expected_indices)
    if benchmark not in expected:return dict(base,reason="benchmark_missing")
    series={k:{} for k in expected}
    for r in rows:
        k=r.get("index");day=str(r.get("date"))
        if k not in expected or day not in days or day in series[k]:
            return dict(base,reason="duplicate_or_out_of_scope")
        if r.get("reviewed") is not True or not r.get("evidence_id"):
            return dict(base,reason="unreviewed_index_row")
        try:
            if isinstance(r["close"],bool):raise ValueError()
            p=float(r["close"])
            if not isfinite(p) or p<=0:raise ValueError()
        except (ValueError,TypeError,KeyError,OverflowError):
            return dict(base,reason="invalid_index_close")
        series[k][day]=p
    out={}
    for k,s in sorted(series.items()):
        if any(d not in s for d in days[-51:]):
            out[k]={"status":"unavailable","reason":"missing_recent_sessions"};continue
        v=s[days[-1]]
        sma20=sum(s[d] for d in days[-20:])/20
        sma50=sum(s[d] for d in days[-50:])/50
        trend="bullish" if v>sma20>sma50 else "bearish" if v<sma20<sma50 else "mixed"
        returns={str(n):100*(v/s[days[-n-1]]-1) if len(days)>n and all(d in s for d in days[-n-1:]) else None for n in WINDOWS}
        out[k]={"status":"research_only","close":v,"sma20":sma20,"sma50":sma50,"trend":trend,"returns_pct":returns}
    b=series[benchmark]
    for k,item in out.items():
        s=series[k]
        if item["status"]!="research_only" or any(d not in b for d in days[-51:]):continue
        trail=[]
        for i in range(max(26,len(days)-6),len(days)):
            segment=days[i-26:i+1]
            if any(d not in s or d not in b for d in segment):continue
            ratio=lambda j:s[days[j]]/b[days[j]]
            strength=100*(ratio(i)/ratio(i-21)-1)
            prior=100*(ratio(i-5)/ratio(i-26)-1)
            momentum=strength-prior
            quadrant="leading" if strength>=0 and momentum>=0 else "weakening" if strength>=0 else "improving" if momentum>=0 else "lagging"
            trail.append({"date":days[i],"relative_return_pct":strength,"momentum_change_pp":momentum,"quadrant":quadrant})
        item["rotation_trail"]=trail
    return dict(base,status="research_only" if out.get(benchmark,{}).get("status")=="research_only" else "unavailable",
                as_of=days[-1],benchmark=benchmark,indices=out,
                methodology="21-session relative return and five-session change; not proprietary RRG",
                independent_validation=False)


# Evidence-gated point-in-time index trend metrics. The legacy function above is
# retained for existing research consumers; new Part 2 integrations should use
# this function and pass only source-validated exchange-session records.
from datetime import datetime, timezone
from statistics import stdev
import math

_VERIFIED_RETURN_WINDOWS = {"1w": 5, "1m": 21, "3m": 63, "6m": 126}
_VERIFIED_SMA_WINDOWS = (20, 50, 100, 150, 200)
_VERIFIED_FULL_HISTORY = 253


def _aware_utc(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_must_be_timezone_aware")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field}_must_be_timezone_aware") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _sha256(value):
    text = str(value or "").lower()
    return len(text) == 64 and all(ch in "0123456789abcdef" for ch in text)


def build_verified_index_intelligence(rows, *, index_code="NEPSE", decision_time):
    """Calculate point-in-time returns, moving averages and volatility.

    Admits only verified final index_ohlcv rows available by decision_time.
    The function is descriptive only: it does not infer missing sessions,
    produce a score/probability, or authorize a trade.
    """
    if not isinstance(index_code, str) or not index_code.strip():
        raise ValueError("index_code_required")
    cutoff = _aware_utc(decision_time, "decision_time")
    if not isinstance(rows, list):
        raise ValueError("rows_must_be_a_list")

    accepted = {}
    excluded = {
        "wrong_index_or_record_type": 0,
        "unverified_or_nonfinal": 0,
        "invalid_provenance": 0,
        "not_available_by_cutoff": 0,
    }
    source_ids = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row_{i}_must_be_an_object")
        if row.get("record_type") != "index_ohlcv" or row.get("index_code") != index_code:
            excluded["wrong_index_or_record_type"] += 1
            continue
        if row.get("source_validation_status") != "verified" or row.get("finality_status") != "final":
            excluded["unverified_or_nonfinal"] += 1
            continue
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip() or not _sha256(row.get("source_payload_sha256")):
            excluded["invalid_provenance"] += 1
            continue
        try:
            available = _aware_utc(row.get("available_at"), "available_at")
        except ValueError:
            excluded["not_available_by_cutoff"] += 1
            continue
        if available > cutoff:
            excluded["not_available_by_cutoff"] += 1
            continue
        try:
            session = date.fromisoformat(str(row["session_date"])).isoformat()
            close = float(row["close"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError(f"row_{i}_invalid_session_or_close") from None
        if isinstance(row.get("close"), bool) or not math.isfinite(close) or close <= 0:
            raise ValueError(f"row_{i}_invalid_session_or_close")
        if session in accepted:
            raise ValueError(f"duplicate_index_session:{session}")
        accepted[session] = close
        source_ids.add(source_id)

    dates = sorted(accepted)
    closes = [accepted[day] for day in dates]
    count = len(closes)
    metrics = {}
    missing = []
    for name, intervals in _VERIFIED_RETURN_WINDOWS.items():
        if count > intervals:
            metrics[f"return_{name}_pct"] = round((closes[-1] / closes[-intervals-1] - 1) * 100, 4)
            metrics[f"return_{name}_start_session"] = dates[-intervals-1]
        else:
            metrics[f"return_{name}_pct"] = None
            metrics[f"return_{name}_start_session"] = None
            missing.append(f"return_{name}")

    averages = {}
    for window in _VERIFIED_SMA_WINDOWS:
        key = f"sma_{window}"
        averages[key] = round(sum(closes[-window:]) / window, 4) if count >= window else None
        if averages[key] is None:
            missing.append(key)
    metrics["moving_averages"] = averages

    if count >= 220:
        current_200 = sum(closes[-200:]) / 200
        prior_200 = sum(closes[-220:-20]) / 200
        metrics["sma_200_slope_20_sessions_pct"] = round((current_200 / prior_200 - 1) * 100, 4)
        metrics["sma_200_rising"] = current_200 > prior_200
    else:
        metrics["sma_200_slope_20_sessions_pct"] = None
        metrics["sma_200_rising"] = None
        missing.append("sma_200_slope")

    if count >= _VERIFIED_FULL_HISTORY:
        high = max(closes[-_VERIFIED_FULL_HISTORY:])
        metrics["high_52w"] = round(high, 4)
        metrics["distance_from_52w_high_pct"] = round((closes[-1] / high - 1) * 100, 4)
    else:
        metrics["high_52w"] = None
        metrics["distance_from_52w_high_pct"] = None
        missing.append("52w_high")

    if count >= 21:
        daily_returns = [closes[i] / closes[i - 1] - 1 for i in range(count - 20, count)]
        daily_vol = stdev(daily_returns)
        metrics["volatility_20d_pct"] = round(daily_vol * 100, 4)
        metrics["volatility_20d_annualized_pct"] = round(daily_vol * math.sqrt(250) * 100, 4)
    else:
        metrics["volatility_20d_pct"] = None
        metrics["volatility_20d_annualized_pct"] = None
        missing.append("volatility_20d")

    current = closes[-1] if closes else None
    sma = averages
    if current is None or sma["sma_50"] is None or sma["sma_150"] is None or sma["sma_200"] is None:
        regime = "unknown"
    elif current > sma["sma_50"] > sma["sma_150"] > sma["sma_200"] and metrics["sma_200_rising"] is True:
        regime = "strong_uptrend"
    elif current < sma["sma_200"] and metrics["sma_200_rising"] is False:
        regime = "downtrend"
    else:
        regime = "mixed_or_sideways"

    complete = count >= _VERIFIED_FULL_HISTORY and not missing
    return {
        "status": "observed" if complete else "insufficient_evidence",
        "mode": "descriptive_only",
        "index_code": index_code,
        "as_of_session": dates[-1] if dates else None,
        "decision_time": cutoff.isoformat(),
        "history_sessions": count,
        "source_ids": sorted(source_ids),
        "excluded_rows": excluded,
        "current_close": closes[-1] if closes else None,
        "regime": regime,
        "metrics": metrics,
        "missing_metrics": sorted(set(missing)),
        "production_score": None,
        "probability": None,
        "action": "NOT_EVALUATED",
        "limitations": [
            "A 253-session verified history is required for complete 52-week index context.",
            "Missing sessions are not interpolated or forward-filled.",
            "Index regime is descriptive, not a forecast or trade signal.",
            "Sub-indices require separately verified index identities and records.",
        ],
    }
