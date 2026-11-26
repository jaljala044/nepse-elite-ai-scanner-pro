"""Audit pinned archive blobs against observed session dates; never promote data."""
import argparse
import csv
import hashlib
import io
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

def audit(raw, dates):
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames != ["Date", "Open", "High", "Low", "Close", "Volume"]:
        raise ValueError("unexpected archive header")
    grouped = defaultdict(list)
    for row in reader:
        grouped[row["Date"]].append(row)
    missing, invalid, duplicate = [], [], []
    valid = 0
    for day in dates:
        rows = grouped[day]
        if not rows:
            missing.append(day)
            continue
        if len(rows) != 1:
            duplicate.append(day)
            continue
        try:
            row = rows[0]
            if None in row:
                raise ValueError("extra columns")
            o,h,l,c,v = (Decimal(row[k]) for k in ("Open","High","Low","Close","Volume"))
            if not all(n.is_finite() for n in (o,h,l,c,v)):
                raise ValueError("nonfinite")
            if not (0 < l <= min(o,c) <= max(o,c) <= h and v > 0 and v == v.to_integral_value()):
                raise ValueError("invalid OHLCV")
        except (InvalidOperation, ValueError, TypeError):
            invalid.append(day)
            continue
        valid += 1
    return valid, ";".join(missing), ";".join(invalid), ";".join(duplicate)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--queue", type=Path, required=True)
    p.add_argument("--sessions", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--skip", type=int, default=32)
    p.add_argument("--group", choices=["priority_1", "exception_review"], default="priority_1")
    args=p.parse_args()
    with args.queue.open(newline="") as f:
        queue=list(csv.DictReader(f))
    with args.sessions.open(newline="") as f:
        dates=[r["date"] for r in csv.DictReader(f)]
    if len(dates)!=120 or len(set(dates))!=120 or len(queue)!=281 or len({r["symbol"] for r in queue})!=281:
        raise ValueError("unexpected universe or date count")
    priority=[r for r in queue if r["review_priority"]==args.group]
    expected=255 if args.group=="priority_1" else 26
    if len(priority)!=expected or not 0<=args.skip<=expected:
        raise ValueError("unexpected priority queue")
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    totals=Counter()
    with args.output.open("x",newline="") as f:
        w=csv.writer(f)
        w.writerow(["symbol","archive_blob_sha","reference_dates","valid_structural_rows","missing_dates","invalid_dates","duplicate_dates","error","backtest_promotion_allowed"])
        for r in priority[args.skip:]:
            sha=r["archive_blob_sha"]
            try:
                if len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
                    raise ValueError("invalid sha")
                raw=subprocess.check_output(["git","-C",str(args.archive),"cat-file","blob",sha],stderr=subprocess.PIPE)
                if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=sha:
                    raise ValueError("blob hash mismatch")
                v,m,i,d=audit(raw.decode("utf-8-sig"),dates)
                w.writerow([r["symbol"],sha,120,v,m,i,d,"","false"])
                totals["audited"]+=1
                totals["valid"]+=v
                for key,val in [("missing",m),("invalid",i),("duplicate",d)]:
                    totals[key]+=len(val.split(";")) if val else 0
            except (subprocess.CalledProcessError,ValueError,UnicodeError) as exc:
                w.writerow([r["symbol"],sha,120,"","","","",type(exc).__name__,"false"])
                totals["failed"]+=1
    print(dict(totals))
    if totals["failed"]:
        raise SystemExit(1)

if __name__=="__main__":
    main()
