"""Publish an independently approved research registry; no signing or auto-approval."""
import argparse
import json
from pathlib import Path
from app.market_registry_publisher import publish_approved_registry

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("root","destination","registry","approval","signature","public-key"):
        p.add_argument("--"+name, required=True,type=Path)
    p.add_argument("--reviewer-id",required=True)
    p.add_argument("--decision-time",required=True)
    a=p.parse_args()
    result=publish_approved_registry(a.root,a.destination,a.registry.read_bytes(),
        a.approval.read_bytes(),a.signature.read_bytes().strip(),
        public_key_pem=a.public_key.read_bytes(),expected_reviewer_id=a.reviewer_id,
        decision_time=a.decision_time)
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
