"""Reconstruct research-only candles from pinned third-party floorsheet bytes."""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import urlopen

def extract(item, raw):
    if len(raw) != item["size_bytes"] or hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest() != item["git_blob_sha"]:
        raise ValueError("source integrity mismatch")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"transaction","symbol","buyer","seller","quantity","rate","amount","date"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("missing source columns")
    targets = set(item["symbols"])
    groups = defaultdict(list)
    errors = Counter()
    target_errors = Counter()
    seen = {}
    for row in reader:
        symbol = row["symbol"].strip().upper()
        try:
            contract = row["transaction"].strip()
            if not contract.isdigit() or not contract.startswith(item["date"].replace("-","")):
                raise ValueError("contract")
            if contract in seen:
                target_errors[seen[contract]] += 1
                raise ValueError("duplicate")
            seen[contract] = symbol
            if row["date"][:10] != item["date"] or not symbol:
                raise ValueError("date_or_symbol")
            if not row["buyer"].isdigit() or not row["seller"].isdigit():
                raise ValueError("broker")
            qty, rate, amount = (Decimal(row[k]) for k in ("quantity","rate","amount"))
            if not all(v.is_finite() and v > 0 for v in (qty, rate, amount)) or qty != qty.to_integral_value():
                raise ValueError("numeric")
            if abs(qty*rate-amount) > Decimal("0.01"):
                raise ValueError("amount")
            if symbol in targets:
                groups[symbol].append((int(contract),rate,qty,amount))
        except (ValueError, InvalidOperation, TypeError) as exc:
            errors[str(exc)] += 1
            target_errors[symbol] += 1
    out = []
    for symbol in sorted(targets):
        trades = sorted(groups[symbol])
        result = {"symbol":symbol,"date":item["date"],"source_sha256":hashlib.sha256(raw).hexdigest(),
                  "contracts":len(trades),"target_errors":target_errors[symbol],
                  "session_errors":sum(errors.values()),"ordering":"contract_number_unverified",
                  "admission_allowed":False,"status":"review_only" if trades and not target_errors[symbol] else "blocked"}
        if trades:
            prices = [t[1] for t in trades]
            result.update(open=str(prices[0]),high=str(max(prices)),low=str(min(prices)),close=str(prices[-1]),
                          volume=str(sum(t[2] for t in trades)),turnover=str(sum(t[3] for t in trades)),
                          first_contract=str(trades[0][0]),last_contract=str(trades[-1][0]))
        out.append(result)
    return out

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    items = json.loads(args.manifest.read_text())["files"]
    records = []
    for item in items:
        url = f"https://raw.githubusercontent.com/{item['source_repository']}/{item['source_commit']}/{item['path']}"
        with urlopen(url,timeout=90) as response:
            raw = response.read(item["size_bytes"]+1)
        records.extend(extract(item,raw))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"schema_version":1,"records":records,"approved_corrections":[]},indent=2)+"\n")
if __name__ == "__main__":
    main()
