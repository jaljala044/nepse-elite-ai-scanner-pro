"""Generate review-only research candidates from a detached-signature protected bundle."""
import argparse
import json
import os
from pathlib import Path
from app.daily_market_candidate_handoff import run_daily_candidate_handoff

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir",required=True,type=Path)
    parser.add_argument("--signature-dir",required=True,type=Path)
    parser.add_argument("--candidate-dir",required=True,type=Path)
    parser.add_argument("--trusted-registry",required=True,type=Path)
    parser.add_argument("--session-date",required=True)
    parser.add_argument("--decision-time",required=True)
    parser.add_argument("--public-key-env",default="NEPSE_INPUT_BUNDLE_PUBLIC_KEY")
    args=parser.parse_args()
    public_key=os.environ.get(args.public_key_env,"").encode()
    if not public_key:
        parser.error("protected input-bundle public key is not configured")
    result=run_daily_candidate_handoff(args.bundle_dir,args.candidate_dir,
        session_date=args.session_date,decision_time=args.decision_time,
        trusted_registry_path=args.trusted_registry,signature_dir=args.signature_dir,
        public_key_pem=public_key)
    print(json.dumps(result,sort_keys=True))
    return 0 if result["status"]=="review_required" else 2

if __name__=="__main__":
    raise SystemExit(main())
