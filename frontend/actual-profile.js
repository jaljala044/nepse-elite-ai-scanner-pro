"use strict";
(() => {
const el=id=>document.getElementById(id);
let generation=0;
function reset(){generation++;el("profile-levels").replaceChildren();el("profile-status").textContent="Requires reviewed transaction evidence.";}
el("chart-symbol").addEventListener("input",reset);
el("profile-start").addEventListener("change",reset);
el("profile-end").addEventListener("change",reset);
el("profile-load").addEventListener("click",async()=>{
 reset();const id=generation,symbol=el("chart-symbol").value.trim().toUpperCase(),start=el("profile-start").value,end=el("profile-end").value;
 if(!/^[A-Z0-9]{1,20}$/.test(symbol)||!start||!end||start>end){el("profile-status").textContent="Select a symbol and valid date range.";return;}
 el("profile-status").textContent="Checking independently reviewed floorsheet controls…";
 try{
 const r=await fetch("/v1/volume-profile/"+encodeURIComponent(symbol)+"?"+new URLSearchParams({start,end}),{signal:AbortSignal.timeout(15000),cache:"no-store"});
 if(!r.ok)throw Error("API unavailable");
 const d=await r.json();if(id!==generation)return;
 if(d.status!=="research_only"){el("profile-status").textContent=d.status==="verified_zero_contracts"?"Verified zero contracts for selected sessions.":"UNKNOWN — "+String(d.reason||"reviewed evidence unavailable");return;}
 if(!Array.isArray(d.levels)||d.symbol!==symbol||d.start!==start||d.end!==end)throw Error("Invalid response scope");
 el("profile-status").textContent="Reviewed profile · POC "+d.poc+" · VAH "+d.vah+" · VAL "+d.val+" · Quantity "+d.total_quantity+" · Turnover NPR "+d.total_amount;
 const levels=d.levels.map(l=>({price:Number(l.price),quantity:Number(l.quantity),area:l.in_value_area===true}));
 if(!levels.length||levels.some(l=>!Number.isFinite(l.price)||!Number.isFinite(l.quantity)||l.quantity<=0))throw Error("Invalid profile levels");
 const max=Math.max(...levels.map(l=>l.quantity));
 const svg=document.createElementNS("http://www.w3.org/2000/svg","svg");
 svg.setAttribute("viewBox","0 0 680 "+Math.max(100,levels.length*19+30));svg.setAttribute("role","img");svg.setAttribute("aria-label","Actual executed volume by price");svg.style.width="100%";
 const add=(tag,attrs,value)=>{const n=document.createElementNS(svg.namespaceURI,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(value!==undefined)n.textContent=value;svg.append(n);};
 levels.sort((a,b)=>b.price-a.price).forEach((l,i)=>{const y=i*19+20;const isPoc=l.price===Number(d.poc);add("rect",{x:100,y:y-12,width:460*l.quantity/max,height:14,fill:isPoc?"#e7cb80":l.area?"#45d6c5":"#64748b"});add("text",{x:4,y,fill:"currentColor","font-size":11},String(l.price));add("text",{x:570,y,fill:"currentColor","font-size":11},String(l.quantity));});
 const graph=document.createElement("div");graph.style.maxHeight="440px";graph.style.overflowY="auto";const legend=document.createElement("p");legend.textContent="Exact execution prices · gold: POC · teal: value area · grey: outside value area";el("profile-levels").append(legend,graph);graph.append(svg);
 const table=document.createElement("table"),head=document.createElement("tr");
 for(const label of ["Price","Shares","Turnover (NPR)","Node","Buyer brokers (quantity)","Seller brokers (quantity)"]){const th=document.createElement("th");th.textContent=label;head.append(th);}table.append(head);
 for(const l of d.levels){const tr=document.createElement("tr");const brokers=o=>Object.entries(o||{}).map(([k,v])=>k+": "+v).join(", ");for(const v of [l.price,l.quantity,l.amount,l.local_volume_node||"—",brokers(l.buyer_broker_quantity),brokers(l.seller_broker_quantity)]){const td=document.createElement("td");td.textContent=String(v);tr.append(td);}table.append(tr);}
 const wrap=document.createElement("div");wrap.style.overflowX="auto";wrap.append(table);el("profile-levels").append(wrap);
 }catch(e){if(id===generation){el("profile-levels").replaceChildren();el("profile-status").textContent="UNKNOWN — "+e.message;}}
});
})();