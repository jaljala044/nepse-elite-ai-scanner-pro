"""Preflight point-in-time benchmark and sector evidence before scanner admission."""
import csv,hashlib,json
from pathlib import Path

def inventory(root):
    candidates=[]
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".csv",".json",".parquet"):
            continue
        name=p.name.lower()
        if any(k in name for k in ("index","sector","nepse")):
            raw=p.read_bytes()
            candidates.append({"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
    return candidates

def run(root):
    files=inventory(Path(root))
    sector=Path(root)/"data/silver/indices"
    partitions=sorted(sector.glob("date=*/indices.csv")) if sector.exists() else []
    index_files=[x for x in files if "index" in x["path"].lower() or "nepse" in x["path"].lower()]
    return {"classification":"evidence_inventory_only","root":str(root),
      "index_candidate_files":index_files,"sector_partition_count":len(partitions),
      "sector_partition_paths":[str(x) for x in partitions],
      "benchmark_admission":"blocked_pending_point_in_time_reconciliation" if not index_files else "candidate_evidence_requires_crosscheck",
      "sector_admission":"blocked_missing_partitions" if not partitions else "candidate_evidence_requires_audit",
      "production_eligible":False}

if __name__=="__main__":
    import sys
    print(json.dumps(run(sys.argv[1]),indent=2))
