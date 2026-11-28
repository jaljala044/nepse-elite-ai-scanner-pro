(() => {
"use strict";
const el=id=>document.getElementById(id);
let indices={}, generation=0;
const categories = [['gainers','Top gainers','%'],['losers','Top losers','%'],['volume','Top volume',' shares'],['turnover','Top turnover',' NPR'],['leaders','Benchmark leaders',' pp'],['laggards','Benchmark laggards',' pp']];
let rankings={}, sectors={}, selectedSector=null;
function renderSectorDetail(){const target=el('sector-constituents');target.replaceChildren();const w=sectors[selectedSector]?.windows?.[el('market-sector-period').value];if(!selectedSector){target.textContent='Select a sector to inspect constituents.';return;}const title=document.createElement('h4');title.textContent=selectedSector+' — reviewed constituent leadership';target.append(title);if(w?.status!=='observed'||!Array.isArray(w.constituents)){const p=document.createElement('p');p.textContent='Verified constituent rankings unavailable.';target.append(p);return;}const list=document.createElement('ol');for(const r of w.constituents){if(typeof r.symbol!=='string'||!Number.isFinite(r.return_pct)||!Number.isFinite(r.excess_return_pct))continue;const li=document.createElement('li');li.textContent=r.symbol+' · '+r.return_pct.toFixed(2)+'% · vs NEPSE '+r.excess_return_pct.toFixed(2)+' pp';list.append(li);}target.append(list);}

function renderSectors(){const target=el('market-sector-list');target.replaceChildren();const period=el('market-sector-period').value;const entries=Object.entries(sectors).sort(([a],[b])=>a.localeCompare(b));if(!entries.length){target.textContent='Verified sector leadership unavailable.';return;}for(const [name,item] of entries){const w=item?.windows?.[period], observed=w?.status==='observed'&&Number.isFinite(w.median_return_pct)&&Number.isFinite(w.median_excess_return_pct)&&Number.isFinite(w.coverage_pct)&&w.coverage_pct>0&&w.coverage_pct<=100;const tile=document.createElement('article');tile.className='sector-tile';tile.dataset.direction=observed?(w.median_excess_return_pct>0?'positive':w.median_excess_return_pct<0?'negative':'neutral'):'unknown';const h=document.createElement('h4');h.textContent=name;const value=document.createElement('strong');value.textContent=observed?w.median_return_pct.toFixed(2)+'%':'Unavailable';const detail=document.createElement('p');detail.textContent=observed?'vs NEPSE: '+w.median_excess_return_pct.toFixed(2)+' pp · coverage '+w.coverage_pct.toFixed(1)+'%':'Insufficient reviewed evidence';const label=document.createElement('small');label.textContent='Overall classification: '+(item?.classification||'Unavailable');const button=document.createElement('button');button.type='button';button.textContent='Inspect '+name;button.addEventListener('click',()=>{selectedSector=name;renderSectorDetail();});tile.append(h,value,detail,label,button);target.append(tile);}}

function renderRanking(){const target=el('market-ranking-results');target.replaceChildren();const key=el('market-ranking-type').value;const rows=rankings[key];if(!Array.isArray(rows)){target.textContent='Verified ranking unavailable.';return;}if(!rows.length){target.textContent='No qualifying stocks.';return;}const table=document.createElement('table');const head=document.createElement('tr');for(const label of ['Rank','Symbol','Value']){const th=document.createElement('th');th.scope='col';th.textContent=label;head.append(th);}const thead=document.createElement('thead');thead.append(head);table.append(thead);const body=document.createElement('tbody');const unit=categories.find(c=>c[0]===key)?.[2]||'';rows.forEach((r,i)=>{const tr=document.createElement('tr');for(const v of [i+1,r.symbol,String(r.value)+unit]){const td=document.createElement('td');td.textContent=v;tr.append(td);}body.append(tr);});table.append(body);target.append(table);}

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
 for(const p of trail){const c=node("circle",{cx:x(p),cy:y(p),r:5,fill:"#498fce",tabindex:0});const label=p.date+" · "+p.relative_return_pct.toFixed(2)+"% · "+p.momentum_change_pp.toFixed(2)+" pp · "+p.quadrant;c.append(node("title",{},label));c.setAttribute("aria-label",label);for(const event of ["focus","pointerenter","click"])c.addEventListener(event,()=>el("rotation-readout").textContent=label);svg.append(c);}
 const p=trail.at(-1);el("rotation-readout").textContent=picker.value+" · "+p.date+" · "+p.quadrant+" · relative return "+p.relative_return_pct.toFixed(2)+"% · momentum "+p.momentum_change_pp.toFixed(2)+" pp";
}
function pair(label,value){const a=document.createElement("dt"),b=document.createElement("dd");a.textContent=label;b.textContent=value??"Unavailable";el("market-research-metrics").append(a,b);}
async function load(){
 const g=++generation;indices={};rankings={};sectors={};selectedSector=null;renderRanking();renderSectors();renderSectorDetail();picker.replaceChildren();picker.disabled=true;draw();el("market-research-metrics").replaceChildren();renderSectors();el("market-research-status").textContent="Loading reviewed artifacts…";
 try{
 const r=await fetch("/v1/research/market-dashboard",{cache:"no-store",signal:AbortSignal.timeout(10000)});if(!r.ok)throw Error("HTTP "+r.status);const d=await r.json();if(g!==generation)return;
 if(d.mode!=="research_only"||d.signals_enabled!==false||d.trade_actions_enabled!==false)throw Error("Unexpected research contract");
 const m=d.modules||{},health=m.market_health?.data,participation=m.daily_market_participation?.data,sector=m.sector_rotation?.data;
 rankings={...participation?.rankings,leaders:participation?.benchmark_relative?.leaders,laggards:participation?.benchmark_relative?.laggards};renderRanking();
 pair("Market regime",health?.regime);pair("Market health",health?.market_health_score??health?.score);pair("Breadth sentiment",participation?.sentiment);pair("Market pressure",participation?.pressure);pair("Participation session",m.daily_market_participation?.as_of_date);
 sectors=sector?.sectors||{};renderSectors();
 indices=m.index_rotation?.data?.indices||{};
 for(const key of Object.keys(indices).filter(k=>k!=="NEPSE").sort()){const opt=document.createElement("option");opt.value=key;opt.textContent=key;picker.append(opt);}
 picker.disabled=!picker.options.length;draw();if(picker.disabled)el("rotation-readout").textContent="Verified relative rotation unavailable.";
 el("market-research-status").textContent="Research only · "+String(d.status).replaceAll("_"," ")+" · no trade recommendations.";
 }catch(e){if(g===generation)el("market-research-status").textContent="Market research unavailable. No demonstration values displayed.";}
}
for(const [key,label] of categories){const opt=document.createElement("option");opt.value=key;opt.textContent=label;el("market-ranking-type").append(opt);}el("market-ranking-type").addEventListener("change",renderRanking);
el("market-sector-period").addEventListener("change",()=>{renderSectors();renderSectorDetail();});
picker.addEventListener("change",draw);length.addEventListener("input",draw);el("market-reload").addEventListener("click",load);load();
})();
