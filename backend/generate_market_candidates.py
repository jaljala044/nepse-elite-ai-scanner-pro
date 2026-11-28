"""Offline candidate generation; never writes deployment registry."""
import argparse
import json
from pathlib import Path
from app.market_artifact_generation import generate_market_candidates

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
    result = generate_market_candidates(bundle, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
