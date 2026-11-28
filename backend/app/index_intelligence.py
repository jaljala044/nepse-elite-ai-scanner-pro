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
from datetime import datetime, timezone, timedelta
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


def build_verified_index_intelligence(rows, *, verified_session_dates, index_code="NEPSE", decision_time):
    """Calculate exact-session point-in-time index returns and trend metrics.

    The caller must supply an independently verified, ascending NEPSE session
    calendar. Every horizon is measured on that calendar, never by row count
    alone. Missing observations remain missing; no forward-fill is performed.
    """
    if not isinstance(index_code, str) or not index_code.strip():
        raise ValueError("index_code_required")
    cutoff = _aware_utc(decision_time, "decision_time")
    if not isinstance(verified_session_dates, list):
        raise ValueError("verified_session_dates_must_be_a_list")
    calendar = []
    for value in verified_session_dates:
        try:
            parsed = date.fromisoformat(str(value)).isoformat()
        except (TypeError, ValueError):
            raise ValueError("verified_session_dates_must_be_iso_dates") from None
        if parsed != value:
            raise ValueError("verified_session_dates_must_use_yyyy_mm_dd")
        calendar.append(parsed)
    if not calendar or calendar != sorted(set(calendar)):
        raise ValueError("verified_session_dates_must_be_unique_ascending")
    decision_day = cutoff.astimezone(timezone(timedelta(hours=5, minutes=45))).date().isoformat()
    calendar = [day for day in calendar if day <= decision_day]
    if not calendar:
        raise ValueError("no_verified_sessions_at_or_before_decision_date")

    if not isinstance(rows, list):
        raise ValueError("rows_must_be_a_list")
    accepted = {}
    excluded = {
        "wrong_index_or_record_type": 0,
        "unverified_or_nonfinal": 0,
        "invalid_provenance": 0,
        "not_available_by_cutoff": 0,
        "outside_verified_session_calendar": 0,
    }
    source_ids = set()
    calendar_set = set(calendar)
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
        if session not in calendar_set:
            excluded["outside_verified_session_calendar"] += 1
            continue
        if session in accepted:
            raise ValueError(f"duplicate_index_session:{session}")
        accepted[session] = close
        source_ids.add(source_id)

    # Metrics are calculated against exact calendar slices. A missing session
    # invalidates only metrics whose required slice contains that session.
    def values_for(days):
        if any(day not in accepted for day in days):
            return None
        return [accepted[day] for day in days]

    metrics = {}
    missing = []
    for name, intervals in _VERIFIED_RETURN_WINDOWS.items():
        window = calendar[-(intervals + 1):]
        vals = values_for(window) if len(window) == intervals + 1 else None
        if vals is not None:
            metrics[f"return_{name}_pct"] = round((vals[-1] / vals[0] - 1) * 100, 4)
            metrics[f"return_{name}_start_session"] = window[0]
        else:
            metrics[f"return_{name}_pct"] = None
            metrics[f"return_{name}_start_session"] = None
            missing.append(f"return_{name}")

    averages = {}
    for window in _VERIFIED_SMA_WINDOWS:
        days = calendar[-window:]
        vals = values_for(days) if len(days) == window else None
        key = f"sma_{window}"
        averages[key] = round(sum(vals) / window, 4) if vals is not None else None
        if averages[key] is None:
            missing.append(key)
    metrics["moving_averages"] = averages

    if len(calendar) >= 220:
        current_vals = values_for(calendar[-200:])
        prior_vals = values_for(calendar[-220:-20])
    else:
        current_vals = prior_vals = None
    if current_vals is not None and prior_vals is not None:
        current_200 = sum(current_vals) / 200
        prior_200 = sum(prior_vals) / 200
        metrics["sma_200_slope_20_sessions_pct"] = round((current_200 / prior_200 - 1) * 100, 4)
        metrics["sma_200_rising"] = current_200 > prior_200
    else:
        metrics["sma_200_slope_20_sessions_pct"] = None
        metrics["sma_200_rising"] = None
        missing.append("sma_200_slope")

    high_values = values_for(calendar[-_VERIFIED_FULL_HISTORY:]) if len(calendar) >= _VERIFIED_FULL_HISTORY else None
    if high_values is not None:
        high = max(high_values)
        latest = high_values[-1]
        metrics["high_52w"] = round(high, 4)
        metrics["distance_from_52w_high_pct"] = round((latest / high - 1) * 100, 4)
    else:
        metrics["high_52w"] = None
        metrics["distance_from_52w_high_pct"] = None
        missing.append("52w_high")

    vol_values = values_for(calendar[-21:]) if len(calendar) >= 21 else None
    if vol_values is not None:
        daily_returns = [vol_values[i] / vol_values[i - 1] - 1 for i in range(1, len(vol_values))]
        daily_vol = stdev(daily_returns)
        metrics["volatility_20d_pct"] = round(daily_vol * 100, 4)
        metrics["volatility_20d_annualized_pct"] = round(daily_vol * math.sqrt(250) * 100, 4)
    else:
        metrics["volatility_20d_pct"] = None
        metrics["volatility_20d_annualized_pct"] = None
        missing.append("volatility_20d")

    latest_day = calendar[-1]
    current = accepted.get(latest_day)
    sma = averages
    if current is None or sma["sma_50"] is None or sma["sma_150"] is None or sma["sma_200"] is None:
        regime = "unknown"
    elif current > sma["sma_50"] > sma["sma_150"] > sma["sma_200"] and metrics["sma_200_rising"] is True:
        regime = "strong_uptrend"
    elif current < sma["sma_200"] and metrics["sma_200_rising"] is False:
        regime = "downtrend"
    else:
        regime = "mixed_or_sideways"

    complete = len(calendar) >= _VERIFIED_FULL_HISTORY and not missing
    missing_sessions = [day for day in calendar[-_VERIFIED_FULL_HISTORY:] if day not in accepted]
    return {
        "status": "observed" if complete else "insufficient_evidence",
        "mode": "descriptive_only",
        "index_code": index_code,
        "as_of_session": latest_day,
        "decision_time": cutoff.isoformat(),
        "history_sessions": len(calendar),
        "observed_sessions": len(accepted),
        "missing_sessions": missing_sessions,
        "source_ids": sorted(source_ids),
        "excluded_rows": excluded,
        "current_close": current,
        "regime": regime,
        "metrics": metrics,
        "missing_metrics": sorted(set(missing)),
        "production_score": None,
        "probability": None,
        "action": "NOT_EVALUATED",
        "limitations": [
            "Session horizons use the caller-supplied independently verified exchange calendar.",
            "A 253-session verified calendar and complete index observations are required for full 52-week context.",
            "Missing observations are not interpolated or forward-filled.",
            "Index regime is descriptive, not a forecast or trade signal.",
            "Sub-indices require separately verified index identities and records.",
        ],
    }


def build_verified_rotation_dashboard(rows, *, verified_session_dates,
                                      expected_indices, decision_time):
    """Gate the existing rotation proxy on exact final point-in-time index rows.

    The caller is a trusted backend with an independently verified calendar
    and index identities. This is not a proprietary RRG calculation.
    """
    cutoff = _aware_utc(decision_time, "decision_time")
    local_day = cutoff.astimezone(timezone(timedelta(hours=5, minutes=45))).date().isoformat()
    if (not isinstance(verified_session_dates, list)
            or any(not isinstance(d, str) or date.fromisoformat(d).isoformat() != d
                   for d in verified_session_dates)
            or verified_session_dates != sorted(set(verified_session_dates))):
        raise ValueError("invalid_verified_calendar")
    days = [d for d in verified_session_dates if d <= local_day]
    if (not isinstance(expected_indices, list) or "NEPSE" not in expected_indices
            or any(not isinstance(k, str) or not k.strip() for k in expected_indices)
            or len(set(expected_indices)) != len(expected_indices)):
        raise ValueError("invalid_expected_indices")
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("invalid_index_rows")
    accepted, seen, sources = [], set(), set()
    for r in rows:
        k, day = r.get("index_code"), r.get("session_date")
        if not isinstance(k, str) or not isinstance(day, str) or k not in expected_indices or day not in days:
            continue
        key = (k, day)
        if key in seen:
            raise ValueError("duplicate_index_session")
        seen.add(key)
        if (r.get("record_type") != "index_ohlcv"
                or r.get("source_validation_status") != "verified"
                or r.get("finality_status") != "final"
                or not isinstance(r.get("source_id"), str) or not r["source_id"].strip()
                or not _sha256(r.get("source_payload_sha256"))):
            continue
        try:
            if _aware_utc(r.get("available_at"), "available_at") > cutoff:
                continue
            if isinstance(r.get("close"), bool):
                continue
            close = float(r["close"])
            if not isfinite(close) or close <= 0:
                continue
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        accepted.append(dict(index=k, date=day, close=close, reviewed=True,
                             evidence_id=r["source_payload_sha256"]))
        sources.add(r["source_id"])
    result = index_intelligence(accepted, sessions=days, benchmark="NEPSE",
                                expected_indices=expected_indices, calendar_verified=True)
    indices = result.get("indices", {})
    missing = sorted(k for k in expected_indices if not indices.get(k, {}).get("rotation_trail"))
    return dict(result, status="research_only" if not missing else "insufficient_evidence",
                missing_indices=missing, coverage_ratio=(len(expected_indices)-len(missing))/len(expected_indices),
                source_ids=sorted(sources), signals_enabled=False, trade_actions_enabled=False,
                production_score=None, probability=None)
