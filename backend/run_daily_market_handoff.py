"""Generate review-only research candidates after collection."""
import argparse
import json
from pathlib import Path
from app.daily_market_candidate_handoff import run_daily_candidate_handoff

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir",required=True,type=Path)
    parser.add_argument("--candidate-dir",required=True,type=Path)
    parser.add_argument("--trusted-registry",required=True,type=Path)
    parser.add_argument("--session-date",required=True)
    parser.add_argument("--decision-time",required=True)
    args=parser.parse_args()
    result=run_daily_candidate_handoff(args.bundle_dir,args.candidate_dir,
        session_date=args.session_date,decision_time=args.decision_time,
        trusted_registry_path=args.trusted_registry)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="review_required" else 2

if __name__=="__main__":
    raise SystemExit(main())
