"""Create a source-referenced corporate action review queue, without approving factors."""
import argparse,csv,subprocess,hashlib,io
from collections import Counter
from datetime import date
from decimal import Decimal,InvalidOperation

def main():
    p=argparse.ArgumentParser()
    for k in ("repo","revision","inventory","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    with open(a.inventory,newline="") as f: inventory=list(csv.DictReader(f))
    counts=Counter();seen=set()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f)
        w.writerow(["symbol","source_type","source_blob_sha","source_row_number","source_row_sha256","event_candidate_type","source_date_kind","source_date","date_status","duplicate_source_record","effective_date_verified","adjustment_factor_verified","promotion_allowed"])
        for item in inventory:
            if item["status"]=="source_unavailable":continue
            raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":"+item["source_path"]])
            sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            if sha!=item["blob_sha"]:raise ValueError("source fingerprint mismatch")
            rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
            if len(rows)!=int(item["source_rows"]):raise ValueError("source row count mismatch")
            for i,r in enumerate(rows,2):
                import json
                fingerprint=hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                key=(item["symbol"],item["source_type"],fingerprint)
                duplicate=key in seen;seen.add(key)
                if item["source_type"]=="dividend":
                    kind="bonus_cash_dividend_review";field="book_closure_date"
                else:
                    kind="rights_issue_review";field="opening_date"
                value=(r.get(field) or "").strip().split(" ")[0]
                try:
                    date.fromisoformat(value);status="source_date_parseable_not_effective_date"
                except ValueError:
                    status="source_date_missing_or_non_iso"
                counts["source_records"]+=1;counts[kind]+=1;counts[status]+=1
                counts["duplicate_source_records"]+=int(duplicate)
                w.writerow([item["symbol"],item["source_type"],sha,i,fingerprint,kind,field,value,status,str(duplicate).lower(),"false","false","false"])
    if counts["source_records"]!=1414:raise ValueError(str(counts))
    print(dict(counts))
if __name__=="__main__":main()
