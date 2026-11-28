"""Inventory corporate action source files without inferring ex dates or factors."""
import argparse,csv,subprocess,hashlib,io
from collections import Counter
def main():
    p=argparse.ArgumentParser()
    for k in ("repo","revision","queue","output"):p.add_argument("--"+k,required=True)
    a=p.parse_args()
    with open(a.queue,newline="") as f:symbols=[r["symbol"] for r in csv.DictReader(f)]
    if len(symbols)!=281 or len(set(symbols))!=281:raise ValueError("universe mismatch")
    counts=Counter()
    with open(a.output,"x",newline="") as f:
        w=csv.writer(f);w.writerow(["symbol","source_type","source_path","blob_sha","source_rows","status","adjustment_allowed"])
        for s in sorted(symbols):
            for name,fields in [("dividend",{"fiscal_year","bonus_share","cash_dividend","total_dividend","book_closure_date"}),("right-share",{"ratio","total_units","issue_price","opening_date","closing_date","status","issue_manager"})]:
                path="data/company-wise/"+s+"/"+name+".csv"
                try:raw=subprocess.check_output(["git","-C",a.repo,"show",a.revision+":"+path],stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    counts[name+"_unavailable"]+=1;w.writerow([s,name,path,"",0,"source_unavailable","false"]);continue
                sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
                reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                if not fields<=set(reader.fieldnames or []):raise ValueError("unexpected schema: "+path)
                rows=list(reader)
                counts[name+"_files"]+=1;counts[name+"_rows"]+=len(rows)
                w.writerow([s,name,path,sha,len(rows),"candidate_source_only_ex_date_unverified","false"])
    print(dict(counts))
if __name__=="__main__":main()
