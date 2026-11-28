"""Build an auditable evidence-request workload for unlisted OHLCV dates.

This tool does not classify sessions, infer carry-forward, or promote OHLCV.
Every candidate remains UNKNOWN until independent dated evidence is reviewed.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from collections import defaultdict
from pathlib import Path
from datetime import date

REQUIRED={"symbol","current_date","previous_date"}
OPTIONAL={"source_file","source_line","candidate_id","ohlcv_sha256"}

def build_workload(path: str|Path) -> dict:
    source=Path(path); raw=source.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    batches=defaultdict(list); seen=set()
    with source.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        missing=REQUIRED-set(reader.fieldnames or [])
        if missing: raise ValueError("missing required columns: "+",".join(sorted(missing)))
        for line,row in enumerate(reader,2):
            symbol=(row.get("symbol") or "").strip().upper()
            current=(row.get("current_date") or "").strip()
            previous=(row.get("previous_date") or "").strip()
            if not symbol: raise ValueError(f"line {line}: missing symbol")
            try: date.fromisoformat(current); date.fromisoformat(previous)
            except ValueError as exc: raise ValueError(f"line {line}: invalid ISO date") from exc
            key=(symbol,current,previous)
            if key in seen: raise ValueError(f"line {line}: duplicate candidate pair {key}")
            seen.add(key)
            item={"symbol":symbol,"current_date":current,"previous_date":previous,
                  "candidate_id":(row.get("candidate_id") or "").strip() or hashlib.sha256("|".join(key).encode()).hexdigest(),
                  "source_file":(row.get("source_file") or "").strip(),
                  "source_line":(row.get("source_line") or "").strip(),
                  "ohlcv_sha256":(row.get("ohlcv_sha256") or "").strip().lower(),
                  "disposition":"UNKNOWN","promotion_allowed":False}
            if item["ohlcv_sha256"] and (len(item["ohlcv_sha256"])!=64 or any(c not in "0123456789abcdef" for c in item["ohlcv_sha256"])):
                raise ValueError(f"line {line}: invalid ohlcv_sha256")
            batches[current].append(item)
    ordered={d:sorted(rows,key=lambda x:(x["symbol"],x["previous_date"],x["candidate_id"])) for d,rows in sorted(batches.items())}
    return {"schema":"issue5-unlisted-date-workload-v1","classification":"evidence_request_only",
      "source_file":source.name,"source_sha256":digest,"candidate_count":len(seen),
      "distinct_current_dates":len(ordered),"distinct_symbols":len({x["symbol"] for rows in ordered.values() for x in rows}),
      "status":"UNKNOWN_REVIEW_REQUIRED","rules":{"weekday_is_not_session_evidence":True,
      "repeated_ohlcv_is_not_carry_forward_evidence":True,"no_source_data_modified":True,
      "no_canonical_promotion":True},"batches":[{"current_date":d,"candidate_count":len(rows),
      "symbols":len({x["symbol"] for x in rows}),"candidates":rows} for d,rows in ordered.items()]}

def main():
    p=argparse.ArgumentParser();p.add_argument("input");p.add_argument("output");a=p.parse_args()
    result=build_workload(a.input);Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("candidate_count","distinct_current_dates","distinct_symbols","status")}))
if __name__=="__main__":main()
