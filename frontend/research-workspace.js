"use strict";
function calendarRows(rows){
 if(!Array.isArray(rows)||rows.length>5000)throw Error("Invalid calendar");
 const seen=new Set();
 return rows.map(r=>{
  if(!r||typeof r.date!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!Number.isFinite(Date.parse(r.date))||new Date(r.date).toISOString().slice(0,10)!==r.date||!["IPO","AGM","DIVIDEND","BONUS","RIGHTS","FPO","LOCK_IN_EXPIRY"].includes(r.type)||typeof r.symbol!=="string"||!/^[A-Z0-9]{1,20}$/.test(r.symbol)||typeof r.source!=="string"||!r.source.trim())throw Error("Invalid calendar record");
  const url=new URL(r.source);if(url.protocol!=="https:"||url.username||url.password)throw Error("HTTPS source required");
  const key=[r.date,r.symbol,r.type].join("|");if(seen.has(key))throw Error("Duplicate calendar event");seen.add(key);
  return {date:r.date,type:r.type,symbol:r.symbol,source:url.href};
 }).sort((a,b)=>a.date.localeCompare(b.date));
}
function holdingsSummary(rows){
 if(!Array.isArray(rows)||!rows.length||rows.length>300)throw Error("Invalid holdings");
 const seen=new Set();
 const items=rows.map(r=>{
  if(!r||typeof r.symbol!=="string"||!/^[A-Z0-9]{1,20}$/.test(r.symbol)||seen.has(r.symbol)||!Number.isSafeInteger(r.quantity)||r.quantity<1||!Number.isFinite(r.cost)||r.cost<=0||!Number.isFinite(r.mark)||r.mark<=0)throw Error("Invalid or duplicate holding");
  seen.add(r.symbol);const invested=r.quantity*r.cost,value=r.quantity*r.mark;if(!Number.isFinite(invested)||!Number.isFinite(value))throw Error("Invalid position value");return {symbol:r.symbol,invested,value,pnl:value-invested};
 });
 const invested=items.reduce((a,r)=>a+r.invested,0),value=items.reduce((a,r)=>a+r.value,0);
 if(!Number.isFinite(invested)||!Number.isFinite(value))throw Error("Invalid totals");
 return {invested,value,pnl:value-invested,items:items.map(r=>({...r,weight:100*r.value/value}))};
}
if(typeof module!=="undefined")module.exports={calendarRows,holdingsSummary};
if(typeof document!=="undefined"){
 const el=id=>document.getElementById(id);
 el("events-load").addEventListener("click",()=>{const out=el("events-result");out.replaceChildren();try{
 const rows=calendarRows(JSON.parse(el("events-input").value));for(const r of rows){const p=document.createElement("p"),a=document.createElement("a");a.href=r.source;a.target="_blank";a.rel="noopener noreferrer";a.textContent="Source";p.append(document.createTextNode(r.date+" · "+r.symbol+" · "+r.type+" · "),a);out.append(p);}el("events-status").textContent=rows.length+" user-supplied events; not independently verified.";
 }catch(e){el("events-status").textContent=e.message;}});
 el("holdings-run").addEventListener("click",()=>{const out=el("holdings-result");try{
 const r=holdingsSummary(JSON.parse(el("holdings-input").value));out.textContent="Invested: NPR "+r.invested.toFixed(2)+"\nMarked value: NPR "+r.value.toFixed(2)+"\nUnrealized P/L: NPR "+r.pnl.toFixed(2)+"\n"+r.items.map(i=>i.symbol+" · weight "+i.weight.toFixed(2)+"% · P/L "+i.pnl.toFixed(2)).join("\n");
 }catch(e){out.textContent=e.message;}});
}
