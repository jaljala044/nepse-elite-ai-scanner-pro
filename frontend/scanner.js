"use strict";
(() => {
const el=id=>document.getElementById(id);
let results=[], generation=0;
const status=t=>el("scan-status").textContent=t;
function describe(r){
 const host=el("scan-detail");host.replaceChildren();
 const title=document.createElement("h3");title.textContent=r.symbol+" — evidence details";host.append(title);
 const entries={"Evidence status":r.data_status||r.status||"UNKNOWN","Rating":"NOT RATED","Eligibility":r.eligibility?.eligible===true?"Reviewed for research":"Not verified","Reasons":(r.eligibility?.reasons||[]).join("; ")||"None reported","Structure":r.market_structure?.status||"Unavailable","Bias":r.market_structure?.bias||"Unavailable","IDPAT":r.idpat_v3?.status||"Unavailable","SMC confluence":r.smc_confluence?.status||"Unavailable","Weekly bias":r.structure_timeframes?.weekly_bias||"Unavailable"};
 const dl=document.createElement("dl");for(const [k,v] of Object.entries(entries)){const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=k;dd.textContent=String(v);dl.append(dt,dd);}host.append(dl);
 const events=Array.isArray(r.market_structure?.events)&&r.eligibility?.eligible===true?r.market_structure.events.filter(e=>Array.isArray(e.evidence)&&e.evidence.length):[];
 const heading=document.createElement("h4");heading.textContent="Recent reviewed structural events";host.append(heading);
 const list=document.createElement("ul");for(const e of events.slice(-15).reverse()){const li=document.createElement("li");li.textContent=[e.date,e.type,e.direction||e.side||"",e.level??""].join(" ");list.append(li);}host.append(list);
 if(!events.length){const p=document.createElement("p");p.textContent="No reviewed events available. Missing evidence does not imply no trading.";host.append(p);}
}
function render(){const filter=el("scan-filter").value,host=el("scan-results");host.replaceChildren();el("scan-detail").replaceChildren();const table=document.createElement("table"),head=document.createElement("tr");for(const v of ["Symbol","Evidence","Structure","Rating","Details"]){const th=document.createElement("th");th.textContent=v;head.append(th);}table.append(head);
 for(const r of results.filter(r=>filter==="all"||r.result_bucket===filter)){const tr=document.createElement("tr");for(const v of [r.symbol,r.data_status||r.status||"UNKNOWN",r.market_structure?.bias||"Unavailable","NOT RATED"]){const td=document.createElement("td");td.textContent=String(v);tr.append(td);}const td=document.createElement("td"),b=document.createElement("button");b.textContent="Inspect";b.addEventListener("click",()=>describe(r));td.append(b);tr.append(td);table.append(tr);}host.append(table);}
el("scan-filter").addEventListener("change",render);
for(const key of ["scan-symbols","scan-date"])el(key).addEventListener("input",()=>{generation++;results=[];render();status("Inputs changed. Run scan again.");});
el("scan-run").addEventListener("click",async()=>{const id=++generation;results=[];render();const symbols=[...new Set(el("scan-symbols").value.split(",").map(s=>s.trim().toUpperCase()).filter(Boolean))];if(symbols.some(s=>!/^[A-Z0-9]{1,20}$/.test(s))||symbols.length>300){status("Invalid symbols or too many symbols.");return;}const body={symbols:symbols.length?symbols:null,as_of:el("scan-date").value||null};status("Checking research evidence…");try{const response=await fetch("/v1/scan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(60000)});if(!response.ok)throw Error("HTTP "+response.status);const data=await response.json();if(id!==generation)return;if(data.mode!=="research_only"||!Array.isArray(data.results))throw Error("Unexpected scanner response");results=data.results;render();status(results.length+" results · "+results.filter(r=>r.result_bucket==="unknown_results").length+" unknown · rankings and recommendations disabled.");}catch(e){if(id===generation)status("Scan unavailable — "+e.message);}});
})();