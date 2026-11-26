"use strict";
(() => {
const el=id=>document.getElementById(id);
let results=[], scanSummary=null, generation=0;
const status=t=>el("scan-status").textContent=t;
function addDetail(host,label,value){
 const dt=document.createElement("dt"),dd=document.createElement("dd");
 dt.textContent=label;dd.textContent=value===undefined||value===null?"Unavailable":String(value);
 host.append(dt,dd);
}
function describe(r){
 const host=el("scan-detail");host.replaceChildren();
 const title=document.createElement("h3");title.textContent=r.symbol+" — market-wide scan details";host.append(title);
 const dl=document.createElement("dl");
 addDetail(dl,"Scanner status",r.status);
 addDetail(dl,"Result bucket",r.result_bucket);
 addDetail(dl,"Latest observation",r.latest_available_observation);
 addDetail(dl,"Calendar age (days)",r.latest_observation_calendar_age_days);
 addDetail(dl,"Freshness assessment",r.freshness_status);
 addDetail(dl,"Observations",r.observations);
 addDetail(dl,"Eligibility",r.eligibility?.eligible===true?"Reviewed for research":"Not verified");
 addDetail(dl,"Eligibility reasons",(r.eligibility?.reasons||[]).join("; ")||"None reported");
 addDetail(dl,"Signals",(r.signals||[]).join(", ")||"None");
 addDetail(dl,"Metrics",JSON.stringify(r.metrics||{}));
 addDetail(dl,"Limitations",(r.limitations||[]).join("; ")||"None reported");
 host.append(dl);
}
function render(){
 const filter=el("scan-filter").value,host=el("scan-results");
 host.replaceChildren();el("scan-detail").replaceChildren();
 const table=document.createElement("table"),head=document.createElement("tr");
 for(const v of ["Symbol","Status","Latest observation","Age (days)","Freshness","Details"]){
  const th=document.createElement("th");th.textContent=v;head.append(th);
 }
 table.append(head);
 for(const r of results.filter(r=>filter==="all"||r.result_bucket===filter)){
  const tr=document.createElement("tr");
  for(const v of [r.symbol,r.status||"UNKNOWN",r.latest_available_observation||"—",
    r.latest_observation_calendar_age_days??"—",r.freshness_status||"No observation"]){
   const td=document.createElement("td");td.textContent=String(v);tr.append(td);
  }
  const td=document.createElement("td"),b=document.createElement("button");
  b.textContent="Inspect";b.addEventListener("click",()=>describe(r));td.append(b);tr.append(td);table.append(tr);
 }
 host.append(table);
}
el("scan-filter").addEventListener("change",render);
for(const key of ["scan-symbols","scan-date"])el(key).addEventListener("input",()=>{
 generation++;results=[];scanSummary=null;render();status("Inputs changed. Run scan again.");
});
el("scan-run").addEventListener("click",async()=>{
 const id=++generation;results=[];scanSummary=null;render();
 const symbols=[...new Set(el("scan-symbols").value.split(",").map(s=>s.trim().toUpperCase()).filter(Boolean))];
 if(symbols.some(s=>!/^[A-Z0-9]{1,20}$/.test(s))||symbols.length>300){
  status("Invalid symbols or too many symbols.");return;
 }
 const body={symbols:symbols.length?symbols:null,as_of:el("scan-date").value||null};
 status("Scanning candidate equity universe…");
 try{
  const response=await fetch("/v1/scan/market-wide",{
   method:"POST",headers:{"Content-Type":"application/json"},
   body:JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(60000)
  });
  if(!response.ok){
   let detail="HTTP "+response.status;
   try{const error=await response.json();if(error.detail)detail=error.detail;}catch(_){}
   throw Error(detail);
  }
  const data=await response.json();
  if(id!==generation)return;
  if(data.mode!=="research_only"||data.scanner_id!=="3A.01"||!Array.isArray(data.results))
   throw Error("Unexpected market-wide scanner response");
  scanSummary=data;results=data.results;render();
  status(
   data.results.length+" results · "+data.symbols_with_observations+"/"+data.candidate_universe_count+
   " with OHLCV ("+data.observation_coverage_pct+"% observation coverage) · "+data.symbols_without_observations+
   " without observations · "+(data.as_of||"as-of unavailable")+
   " · rankings and recommendations disabled. " +
   (data.coverage_basis === "at_least_one_stored_ohlcv_row_not_data_quality_or_session_validation"
    ? "Coverage counts symbols with at least one stored OHLCV row; it does not validate data quality or session completeness."
    : (data.disclaimer || "Coverage basis unavailable."))
  );
 }catch(e){if(id===generation)status("Market-wide scan unavailable — "+e.message);}
});
})();
