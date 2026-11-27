"""Research-only field candidates. Never emit a usable canonical candle."""
import json
import hashlib
from pathlib import Path
from decimal import Decimal, InvalidOperation

ROOT=Path(__file__).resolve().parents[2]
FIELDS=("open","high","low","close","volume")

def build_partial_view(quarantine, reconstruction, chronology):
    keys=[(r["symbol"],r["date"]) for r in quarantine]
    if len(keys)!=len(set(keys)): raise ValueError("duplicate quarantine key")
    def index(rows):
        out={}
        for r in rows:
            k=(r["symbol"],r["date"])
            if k in out or k not in keys: raise ValueError("invalid candidate scope")
            out[k]=r
        return out
    rec=index(reconstruction)
    chron=index(chronology)
    output=[]
    for symbol,day in sorted(keys):
        k=(symbol,day)
        r=rec.get(k,{})
        t=chron.get(k,{})
        candidates={f:None for f in FIELDS}
        if r.get("target_errors")==0 and r.get("contracts",0)>0:
            for f in ("high","low","volume"):
                try:
                    v=Decimal(str(r[f]))
                    if v.is_finite() and v>0 and (f!="volume" or v==v.to_integral_value()):
                        candidates[f]=str(v)
                except (InvalidOperation,KeyError,TypeError): pass
            for f in ("open","close"):
                if t.get(f+"_match") is True and t.get("errors")==0 and t.get("unique_contracts") is True and t.get("timestamp_rows")==r.get("contracts"):
                    try:
                        v=Decimal(str(t["timestamp_"+f+"_candidate"]))
                        if v.is_finite() and v>0 and v==Decimal(str(r[f])):
                            candidates[f]=str(v)
                    except (InvalidOperation,KeyError,TypeError): pass
        output.append({"symbol":symbol,"date":day,"research_candidates":candidates,
            "canonical_fields":{f:None for f in FIELDS},"complete":False,
            "admission_allowed":False,"scanner_eligible":False,
            "source_sha256":r.get("source_sha256"),"independent_evidence_authenticated":False})
    return {"schema_version":1,"dataset_kind":"quarantined_partial_field_research","records":output,"approved_corrections":[]}

def main():
    paths=[ROOT/"data/reference/p443_equity_quarantine.json",ROOT/"data/reports/p443_reconstructed_candle_comparison_v1.json",ROOT/"data/reports/p443_timestamp_chronology_comparison_v1.json"]
    raw=[p.read_bytes() for p in paths]
    result=build_partial_view(*(json.loads(b)["records"] for b in raw))
    result["input_sha256"]={str(p.relative_to(ROOT)):hashlib.sha256(b).hexdigest() for p,b in zip(paths,raw)}
    dest=ROOT/"recovery-output/partial-field-research.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__": main()
