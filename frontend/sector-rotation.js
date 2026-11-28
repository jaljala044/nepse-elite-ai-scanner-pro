"use strict";
// Transparent relative-rotation proxy, not proprietary JdK RS-Ratio/Momentum.
// Use only observed windows in a descriptive research response; no signals.
function sectorView(report,window="1M"){
 if(!["1W","1M","3M","6M"].includes(window))throw Error("Invalid window");
 if(!report||report.mode!=="descriptive_only"||report.status!=="observed"||report.signals_enabled!==false||!report.sectors||typeof report.sectors!=="object")return [];
 return Object.entries(report.sectors).map(([name,s])=>{
  const w=s?.windows?.[window],a=s?.windows?.["1M"],b=s?.windows?.["3M"];
  const observed=v=>v?.status==="observed"&&Number.isFinite(v.median_excess_return_pct)&&Number.isFinite(v.coverage_pct)&&v.coverage_pct>=80&&v.coverage_pct<=100;
  const x=observed(b)?b.median_excess_return_pct:null;
  const y=observed(a)&&x!==null?a.median_excess_return_pct-x/3:null;
  return {name,ratio:x,momentum:y,heat:observed(w)&&Number.isFinite(w.median_return_pct)?w.median_return_pct:null,coverage:observed(w)?w.coverage_pct:null};
 });
}
if(typeof module!=="undefined")module.exports={sectorView};
if(typeof document!=="undefined"){
 const el=id=>document.getElementById(id);let report=null;
 function draw(){
  const out=el("sector-heat"),plot=el("sector-plot"),status=el("sector-status");out.replaceChildren();plot.replaceChildren();
  const rows=sectorView(report,el("sector-window").value);
  if(!rows.length){status.textContent="No qualifying research response. Sector values withheld.";return;}
  status.textContent="User-supplied research artifact, not independently attested or live. Session: "+String(report.as_of_session??"unknown");
  for(const r of rows){const cell=document.createElement("article");cell.textContent=r.name+" · "+(r.heat===null?"UNKNOWN":r.heat.toFixed(2)+"% · coverage "+r.coverage+"%");cell.style.padding="12px";cell.style.border="1px solid #64748b";cell.style.background=r.heat===null?"#334155":r.heat>0?"#14532d":r.heat<0?"#7f1d1d":"#334155";out.append(cell);}
  const pts=rows.filter(r=>r.ratio!==null&&r.momentum!==null);
  if(!pts.length)return;
  const ns="http://www.w3.org/2000/svg",node=(tag,attrs,txt)=>{const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(txt!==undefined)n.textContent=txt;plot.append(n);return n;};
  const sx=Math.max(1,...pts.map(r=>Math.abs(r.ratio))),sy=Math.max(1,...pts.map(r=>Math.abs(r.momentum)));
  node("line",{x1:35,x2:565,y1:150,y2:150,stroke:"#94a3b8"});node("line",{x1:300,x2:300,y1:15,y2:285,stroke:"#94a3b8"});
  for(const r of pts){const x=300+250*r.ratio/sx,y=150-120*r.momentum/sy;const c=node("circle",{cx:x,cy:y,r:5,fill:"#60a5fa"});const t=document.createElementNS(ns,"title");t.textContent=r.name+" "+r.ratio.toFixed(2)+", "+r.momentum.toFixed(2);c.append(t);node("text",{x,y:y-8,fill:"currentColor","font-size":11,"text-anchor":"middle"},r.name);}
 }
 el("sector-window").addEventListener("change",draw);
 el("sector-file").addEventListener("change",async()=>{const f=el("sector-file").files[0];report=null;draw();if(!f)return;try{if(f.size>2000000)throw Error("File too large");const raw=JSON.parse(await f.text());if(el("sector-file").files[0]!==f)return;report=raw;draw();}catch(e){if(el("sector-file").files[0]===f)el("sector-status").textContent="Invalid research artifact."; }});
}
