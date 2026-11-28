(() => {
"use strict";
const el=id=>document.getElementById(id);
let indices={}, generation=0;
const svg=el("rotation-chart"), picker=el("rotation-index"), length=el("rotation-length");
function node(tag,attrs={},text){const n=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n;}
function draw(){
 svg.replaceChildren();el("rotation-readout").textContent="";
 const points=indices[picker.value]?.rotation_trail;
 if(!Array.isArray(points)||!points.length)return;
 const trail=points.slice(-Number(length.value));
 if(trail.some(p=>!Number.isFinite(p.relative_return_pct)||!Number.isFinite(p.momentum_change_pp)))return;
 const mx=Math.max(1,...points.map(p=>Math.abs(p.relative_return_pct))),my=Math.max(1,...points.map(p=>Math.abs(p.momentum_change_pp)));
 const x=p=>320+p.relative_return_pct/mx*260,y=p=>190-p.momentum_change_pp/my*145;
 svg.append(node("line",{x1:40,y1:190,x2:600,y2:190,stroke:"currentColor"}),node("line",{x1:320,y1:30,x2:320,y2:350,stroke:"currentColor"}));
 for(const [a,b,t] of [[50,45,"Improving"],[470,45,"Leading"],[50,345,"Lagging"],[470,345,"Weakening"]])svg.append(node("text",{x:a,y:b,fill:"currentColor","font-size":13},t));
 svg.append(node("polyline",{points:trail.map(p=>x(p)+","+y(p)).join(" "),fill:"none",stroke:"#498fce","stroke-width":3}));
 for(const p of trail){const c=node("circle",{cx:x(p),cy:y(p),r:5,fill:"#498fce",tabindex:0});const label=p.date+" · "+p.relative_return_pct.toFixed(2)+"% · "+p.momentum_change_pp.toFixed(2)+" pp · "+p.quadrant;c.append(node("title",{},label));c.addEventListener("focus",()=>el("rotation-readout").textContent=label);svg.append(c);}
 const p=trail.at(-1);el("rotation-readout").textContent=picker.value+" · "+p.date+" · "+p.quadrant+" · relative return "+p.relative_return_pct.toFixed(2)+"% · momentum "+p.momentum_change_pp.toFixed(2)+" pp";
}
function pair(label,value){const a=document.createElement("dt"),b=document.createElement("dd");a.textContent=label;b.textContent=value??"Unavailable";el("market-research-metrics").append(a,b);}
async function load(){
 const g=++generation;indices={};picker.replaceChildren();picker.disabled=true;draw();el("market-research-metrics").replaceChildren();el("market-sector-list").replaceChildren();el("market-research-status").textContent="Loading reviewed artifacts…";
 try{
 const r=await fetch("/v1/research/market-dashboard",{cache:"no-store",signal:AbortSignal.timeout(10000)});if(!r.ok)throw Error("HTTP "+r.status);const d=await r.json();if(g!==generation)return;
 if(d.mode!=="research_only"||d.signals_enabled!==false||d.trade_actions_enabled!==false)throw Error("Unexpected research contract");
 const m=d.modules||{},health=m.market_health?.data,participation=m.daily_market_participation?.data,sector=m.sector_rotation?.data;
 pair("Market regime",health?.regime);pair("Market health",health?.market_health_score??health?.score);pair("Breadth sentiment",participation?.sentiment);pair("Market pressure",participation?.pressure);pair("Participation session",m.daily_market_participation?.as_of_date);
 for(const [name,item] of Object.entries(sector?.sectors||{})){const p=document.createElement("p");p.textContent=name+" — "+(item.classification||"Unavailable");el("market-sector-list").append(p);}
 if(!el("market-sector-list").childNodes.length)el("market-sector-list").textContent="Verified sector leadership unavailable.";
 indices=m.index_rotation?.data?.indices||{};
 for(const key of Object.keys(indices).filter(k=>k!=="NEPSE").sort()){const opt=document.createElement("option");opt.value=key;opt.textContent=key;picker.append(opt);}
 picker.disabled=!picker.options.length;draw();if(picker.disabled)el("rotation-readout").textContent="Verified relative rotation unavailable.";
 el("market-research-status").textContent="Research only · "+String(d.status).replaceAll("_"," ")+" · no trade recommendations.";
 }catch(e){if(g===generation)el("market-research-status").textContent="Market research unavailable. No demonstration values displayed.";}
}
picker.addEventListener("change",draw);length.addEventListener("input",draw);el("market-reload").addEventListener("click",load);load();
})();
