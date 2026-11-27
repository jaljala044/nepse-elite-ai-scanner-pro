"use strict";
(() => {
const el=id=>document.getElementById(id);
const status=el("broker-context-status"), host=el("broker-context-results");
let generation=0;
const percent=v=>v===null||v===undefined||!Number.isFinite(Number(v))?"—":(100*Number(v)).toFixed(2)+"%";
function table(headers,rows){
 const t=document.createElement("table"), h=t.createTHead().insertRow();
 for(const v of headers){const c=document.createElement("th");c.textContent=v;h.append(c);}
 const b=t.createTBody();
 for(const row of rows){const tr=b.insertRow();for(const v of row){tr.insertCell().textContent=String(v??"—");}}
 host.append(t);
}
async function run(){
 const id=++generation;host.replaceChildren();status.textContent="Checking supplied research evidence…";
 try{
 const f=el("broker-context-file").files[0];if(!f||f.size>5*1024*1024)throw Error("Choose a JSON evidence file under 5 MiB");
 const body=JSON.parse(await f.text());
 const mode=el("broker-context-mode").value;
 const path={context:"broker-context",concentration:"broker-concentration",rotation:"broker-context-rotation"}[mode];
 const response=await fetch("/v1/research/"+path,{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+el("broker-context-token").value},body:JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error(response.status===401?"Research credential rejected":response.status===503?"Research access not configured":response.status===429?"Request budget exceeded":"Evidence rejected or API unavailable");
 const d=await response.json();if(id!==generation)return;
 if(d.production_eligible!==false||d.signals_enabled!==false)throw Error("Unexpected research safety contract");
 if(d.status==="insufficient_evidence"){status.textContent="UNKNOWN — "+(d.reason||"Incomplete evidence");return;}
 status.textContent="Research only — supplied sources not independently authenticated";
 if(mode==="context"){
 if(!Array.isArray(d.profiles))throw Error("Invalid response");
 const symbol=el("broker-context-symbol").value.trim();
 const rows=d.profiles.filter(r=>!symbol||String(r.security_id)===symbol||String(r.symbol||"").toUpperCase()===symbol.toUpperCase());
 table(["Symbol","Security ID","Broker","Status","Research label","Net NPR","Positive sessions","Relative return","Volume ratio","Missing evidence"],
 rows.map(r=>[r.symbol,r.security_id,r.broker_id,r.status,r.classification,r.net_amount,percent(r.positive_session_ratio),percent(r.sector_relative_return),r.latest_volume_ratio,r.reason]));
 }else if(mode==="concentration"){
 table(["Broker count","Matched NPR","HHI (0–1)","Top 3","Top 5"],[[d.broker_count,d.matched_turnover,d.hhi,percent(d.top3_share),percent(d.top5_share)]]);
 }else{
 if(!Array.isArray(d.rows))throw Error("Invalid response");
 table(["Broker","Sector","Prior share","Current share","Change (percentage points)"],d.rows.map(r=>[r.broker_id,r.sector_code,percent(r.prior_share),percent(r.current_share),Number.isFinite(Number(r.share_change))?(100*Number(r.share_change)).toFixed(2):"—"]));
 }
 }catch(e){if(id===generation){host.replaceChildren();status.textContent="UNKNOWN — "+e.message;}}
}
el("broker-context-run").addEventListener("click",run);
el("chart-broker-context").addEventListener("click",()=>{const s=el("chart-symbol").value.trim().toUpperCase();if(!/^[A-Z0-9]{1,20}$/.test(s))return;el("broker-context-symbol").value=s;el("broker-context-symbol").dispatchEvent(new Event("change"));el("broker-context").scrollIntoView();});
for(const key of ["broker-context-file","broker-context-mode","broker-context-symbol"]){el(key).addEventListener("change",()=>{generation++;host.replaceChildren();status.textContent="Evidence changed; run again.";});}
})();
