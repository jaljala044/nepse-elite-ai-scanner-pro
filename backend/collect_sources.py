import argparse
import json
from app.source_collector import collect

def main():
    parser = argparse.ArgumentParser(description="Collect read-only NEPSE source snapshots")
    parser.add_argument("--source", action="append", dest="sources",
                        help="Source name; repeat to select multiple. Defaults to all.")
    args = parser.parse_args()
    result = collect(args.sources)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
