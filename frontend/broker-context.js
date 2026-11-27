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
function bars(label,values){
 const figure=document.createElement("figure"),caption=document.createElement("figcaption");
 caption.textContent=label;figure.append(caption);
 for(const [name,raw] of values){
 if(raw===null||raw===undefined||raw==="")continue;
 const n=Number(raw);if(!Number.isFinite(n)||n<0||n>1)continue;
 const line=document.createElement("div"),title=document.createElement("span"),meter=document.createElement("meter");
 title.textContent=name+" "+percent(n)+" ";meter.min=0;meter.max=1;meter.value=n;
 meter.setAttribute("aria-label",name);line.append(title,meter);figure.append(line);
 }
 host.append(figure);
}
function leaderboards(data,mode){
 const stock=mode==="stock-leaders",groups=stock?data.by_security:data.by_broker;
 if(!Array.isArray(groups))throw Error("Invalid leaderboard response");
 const filter=el("broker-context-symbol").value.trim().toUpperCase();
 const rows=[];
 for(const g of groups){
 for(const [direction,items] of [["Net buyer",g.net_buyers],["Net seller",g.net_sellers]]){
 if(!Array.isArray(items))throw Error("Invalid leaderboard group");
 items.forEach((r,i)=>{
 if(filter && ![r.symbol,r.security_id,r.broker_id].some(v=>String(v).toUpperCase()===filter))return;
 rows.push([stock?g.security_id:g.broker_id,direction,i+1,r.symbol,r.security_id,r.broker_id,r.net_amount,r.gross_broker_side_amount,r.classification]);
 });
 }
 }
 table([stock?"Security group":"Broker group","Flow direction","Rank in supplied group","Symbol","Security ID","Broker","Net NPR","Gross sides NPR","Research label"],rows);
 const p=document.createElement("p");p.textContent="Included profiles: "+data.included_profiles+"; excluded: "+data.excluded_profiles+". "+data.limitations;host.append(p);
}
async function run(){
 const id=++generation;host.replaceChildren();status.textContent="Checking supplied research evidence…";
 try{
 const mode=el("broker-context-mode").value;
 let body;
 if(mode==="ledger"){
 const day=el("broker-ledger-date").value;
 if(!day)throw Error("Choose a historical decision date");
 body={as_of_date:day,decision_time:day+"T23:59:59+05:45",window:el("broker-ledger-window").value};
 }else{
 const f=el("broker-context-file").files[0];if(!f||f.size>5*1024*1024)throw Error("Choose a JSON evidence file under 5 MiB");
 body=JSON.parse(await f.text());
 }
 const path={context:"broker-context",concentration:"broker-concentration",rotation:"broker-context-rotation",ledger:"broker-ledger-profiles","stock-leaders":"broker-leaderboards","broker-leaders":"broker-leaderboards"}[mode];
 const response=await fetch("/v1/research/"+path,{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+el("broker-context-token").value},body:JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error(response.status===401?"Research credential rejected":response.status===503?"Research access not configured":response.status===429?"Request budget exceeded":"Evidence rejected or API unavailable");
 const d=await response.json();if(id!==generation)return;
 if(d.production_eligible!==false||d.signals_enabled!==false)throw Error("Unexpected research safety contract");
 if(d.status==="insufficient_evidence"){status.textContent="UNKNOWN — "+(d.reason||"Incomplete evidence");return;}
 status.textContent="Research only — supplied sources not independently authenticated";
 if(mode==="stock-leaders"||mode==="broker-leaders"){
 leaderboards(d,mode);
 }else if(mode==="ledger"){
 status.textContent="Research coverage only — security-level profiles withheld pending historical identity verification";
 table(["Window","Complete sessions","Observations","Profiles evaluated","Quarantine blocked","Identity unmapped","Snapshot crosswalk clear"],[[d.window,d.complete_sessions,d.observation_count,d.profile_count,d.quarantine_blocked_profiles,d.identity_unmapped_profiles,d.snapshot_crosswalk_clear_profiles]]);
 }else if(mode==="context"){
 if(!Array.isArray(d.profiles))throw Error("Invalid response");
 const symbol=el("broker-context-symbol").value.trim();
 const rows=d.profiles.filter(r=>!symbol||String(r.security_id)===symbol||String(r.symbol||"").toUpperCase()===symbol.toUpperCase());
 table(["Symbol","Security ID","Broker","Status","Research label","Net NPR","Positive sessions","Negative sessions","Mean participation","Peak participation","Price return","Relative return","Volume ratio","Missing evidence"],
 rows.map(r=>[r.symbol,r.security_id,r.broker_id,r.status,r.classification,r.net_amount,percent(r.positive_session_ratio),percent(r.negative_session_ratio),percent(r.mean_participation),percent(r.peak_participation),percent(r.price_return),percent(r.sector_relative_return),r.latest_volume_ratio,r.reason]));
 }else if(mode==="concentration"){
 table(["Broker count","Matched NPR","HHI (0–1)","Top 3","Top 5"],[[d.broker_count,d.matched_turnover,d.hhi,percent(d.top3_share),percent(d.top5_share)]]);
 bars("Concentration (normalized scale 0–1)",[["HHI",d.hhi],["Top 3 participation",d.top3_share],["Top 5 participation",d.top5_share]]);
 }else{
 if(!Array.isArray(d.rows))throw Error("Invalid response");
 table(["Broker","Sector","Prior share","Current share","Change (percentage points)"],d.rows.map(r=>[r.broker_id,r.sector_code,percent(r.prior_share),percent(r.current_share),Number.isFinite(Number(r.share_change))?(100*Number(r.share_change)).toFixed(2):"—"]));
 }
 if(mode==="rotation")for(const r of d.rows.slice(0,30))bars("Broker "+r.broker_id+" · "+r.sector_code,[["Prior",r.prior_share],["Current",r.current_share]]);
 }catch(e){if(id===generation){host.replaceChildren();status.textContent="UNKNOWN — "+e.message;}}
}
el("broker-context-run").addEventListener("click",run);
el("chart-broker-context").addEventListener("click",()=>{const s=el("chart-symbol").value.trim().toUpperCase();if(!/^[A-Z0-9]{1,20}$/.test(s))return;el("broker-context-symbol").value=s;el("broker-context-symbol").dispatchEvent(new Event("change"));el("broker-context").scrollIntoView();});
for(const key of ["broker-context-file","broker-context-mode","broker-context-symbol","broker-ledger-date","broker-ledger-window"]){el(key).addEventListener("change",()=>{generation++;host.replaceChildren();status.textContent="Evidence changed; run again.";});}
})();
