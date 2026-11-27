"""Research-only integration of existing technical feature engines."""
from .advanced_technical_adapter import derive_advanced_technical
from .wyckoff_features import wyckoff_event_features
from .volume_vsa_features import volume_vsa_features
from .trend_features import minervini_trend_template
from .scoring_engine import score_scan

def derive_unified_technical(*,symbol,rows,benchmark_rows,sessions,assessment_time):
    advanced=derive_advanced_technical(symbol=symbol,rows=rows,benchmark_rows=benchmark_rows,
                                      sessions=sessions,assessment_time=assessment_time)
    normalized=[dict(r,session_date=r["date"]) for r in rows]
    features={"wyckoff":wyckoff_event_features(normalized),
              "volume":volume_vsa_features(normalized),
              "trend":minervini_trend_template(normalized)}
    components={k:v.get("score") if v.get("status")=="observed" else None
                for k,v in features.items()}
    scoring=score_scan(components,stage1_quality="UNKNOWN",structure_confirmed=False,
                       liquidity_ok=False,market_tradeable=False,reward_risk=None,
                       hard_blocks=["caller_attested_research_only"])
    return dict(symbol=symbol,advanced=advanced,features=features,scoring=scoring,
                production_eligible=False,
                limitations=["Candidate Wyckoff events are not confirmed campaigns.",
                             "VSA observations do not prove absorption or operator intent.",
                             "RS returns are not yet mapped to a calibrated 0–100 score.",
                             "No independent Stage-1 eligibility or execution verification."])
