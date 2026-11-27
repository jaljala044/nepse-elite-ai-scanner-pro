"""Compare two pinned third-party trade archives; never authorize corrections."""
import csv
import gzip
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
def get(url,size):
    with urlopen(url,timeout=90) as r:
        raw=r.read(size+1)
    if len(raw)!=size: raise ValueError("size mismatch")
    return raw

def signature(row, alternative=False):
    def pick(*names):
        for n in names:
            if row.get(n): return row[n].strip()
        raise ValueError("missing field: "+str(names))
    symbol=pick("stock_symbol","symbol","scrip").upper()
    contract=pick("contract_no","contractno","contract_id","contractid","transaction")
    day=pick("calculation_date","business_date","businessdate","date")[:10]
    qty,rate,amount=[Decimal(pick(*ns).replace(",","")) for ns in (("quantity","qty"),("rate","price"),("amount","amt","total_amount"))]
    if not all(x.is_finite() and x>0 for x in (qty,rate,amount)) or qty!=qty.to_integral_value() or abs(qty*rate-amount)>Decimal(".01"):
        raise ValueError("invalid trade")
    return symbol,day,contract,qty,rate,amount

def parse(raw,day,targets):
    result={s:Counter() for s in targets}
    errors=Counter()
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    for original in reader:
        row={str(k).strip().lower():str(v or "").strip() for k,v in original.items()}
        symbol=(row.get("stock_symbol") or row.get("symbol") or row.get("scrip") or "").upper()
        if symbol not in targets: continue
        try:
            s,d,c,q,p,a=signature(row)
            if d!=day: raise ValueError("date mismatch")
            result[s][(c,q,p,a)]+=1
        except (ValueError,ArithmeticError):
            errors[s]+=1
    return result,errors

def compare(a,b):
    # Match the full contract/quantity/rate/amount multiset, not just aggregate volume.
    def summary(x):
        return {"rows":sum(x.values()),"unique_contracts":len({k[0] for k in x}),
                "quantity":str(sum((k[1]*n for k,n in x.items()),Decimal(0))),
                "turnover":str(sum((k[3]*n for k,n in x.items()),Decimal(0)))}
    return {"primary":summary(a),"alternative":summary(b),"exact_matches":sum((a&b).values()),
            "primary_only":sum((a-b).values()),"alternative_only":sum((b-a).values()),
            "exact_nonempty_multiset_match":bool(a) and a==b,
            "admission_allowed":False}

def broker_signature(row):
    def pick(names):
        values={str(row[n]).strip() for n in names if row.get(n)}
        if len(values)!=1: raise ValueError("missing or conflicting broker field")
        value=values.pop()
        if not value.isdigit() or int(value)<=0: raise ValueError("invalid broker")
        return int(value)
    return (pick(("buyer","buyer_broker","buyer_broker_id","buyer_member_id","buying_broker","buyer_member","buyer_member_code","buy_member_id")),
            pick(("seller","seller_broker","seller_broker_id","seller_member_id","selling_broker","seller_member","seller_member_code","sell_member_id")))

def parse_broker_trades(raw,day,targets):
    result={s:Counter() for s in targets}
    errors=Counter()
    timestamps=Counter()
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    headers=reader.fieldnames or []
    for original in reader:
        row={str(k).strip().lower():str(v or "").strip() for k,v in original.items()}
        symbol=(row.get("stock_symbol") or row.get("symbol") or row.get("scrip") or "").upper()
        if symbol not in targets: continue
        try:
            s,d,c,q,p,a=signature(row)
            if d!=day: raise ValueError("date mismatch")
            buyer,seller=broker_signature(row)
            result[s][(c,q,p,a,buyer,seller)]+=1
            if any(row.get(n) for n in ("trade_time","transaction_time","execution_time","contract_time","timestamp","time")):
                timestamps[s]+=1
        except (ValueError,ArithmeticError):
            errors[s]+=1
    return result,errors,timestamps,headers

def main():
    base=ROOT/"data/reports"
    primary=json.loads((base/"p443_floorsheet_extraction_manifest.json").read_text())["files"]
    alt=json.loads((base/"p443_alternative_floorsheet_inventory.json").read_text())["records"]
    records=[]
    for f in primary:
        day=f["date"]; targets=set(f["symbols"])
        matches=[x for x in alt if x["date"]==day]
        if {x["symbol"] for x in matches}!=targets: raise ValueError("scope mismatch")
        m=matches[0]
        if any((x["path"],x["size"],x["sha256"])!=(m["path"],m["size"],m["sha256"]) for x in matches): raise ValueError("inconsistent pin")
        raw=get(f"https://raw.githubusercontent.com/{f['source_repository']}/{f['source_commit']}/{f['path']}",f["size_bytes"])
        if hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()!=f["git_blob_sha"]: raise ValueError("primary hash mismatch")
        compressed=get("https://huggingface.co/datasets/urekmazino69/Nepse-floorsheet-and-indices/resolve/main/"+m["path"],m["size"])
        if hashlib.sha256(compressed).hexdigest()!=m["sha256"]: raise ValueError("alternative hash mismatch")
        alternative_raw=gzip.decompress(compressed)
        a,ae=parse(raw,day,targets);b,be=parse(alternative_raw,day,targets)
        ab,abe,at,ah=parse_broker_trades(raw,day,targets)
        bb,bbe,bt,bh=parse_broker_trades(alternative_raw,day,targets)
        for s in sorted(targets):
            records.append({"symbol":s,"date":day,"primary_sha256":hashlib.sha256(raw).hexdigest(),
                "alternative_compressed_sha256":m["sha256"],"primary_errors":ae[s],"alternative_errors":be[s],**compare(a[s],b[s]),
                "broker_parity":compare(ab[s],bb[s]),"primary_broker_errors":abe[s],"alternative_broker_errors":bbe[s],
                "primary_timestamp_rows":at[s],"alternative_timestamp_rows":bt[s],"primary_headers":ah,"alternative_headers":bh,
                "execution_order_verified":False})
    if len(records)!=11: raise ValueError("scope mismatch")
    output={"records":records,"approved_corrections":[],"limitations":"shared lineage and execution order unverified; timestamp presence does not authenticate execution chronology"}
    dest=ROOT/"recovery-output/alternative-comparison.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,indent=2))
if __name__=="__main__": main()
