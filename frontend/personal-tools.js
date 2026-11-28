"use strict";
function symbolsFrom(value,max=300){
 const list=[...new Set(value.split(/[\s,]+/).filter(Boolean).map(s=>s.toUpperCase()))];
 if(list.length>max||list.some(s=>!/^[A-Z0-9]{1,20}$/.test(s)))throw Error("Invalid symbol list");
 return list;
}
function compareHistory(series){
 if(!Array.isArray(series)||series.length<2||series.length>5)throw Error("Choose 2–5 symbols");
 const maps=series.map(s=>{const m=new Map();for(const r of s.rows){if(typeof r.date!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||m.has(r.date)||!Number.isFinite(r.close)||r.close<=0)throw Error("Invalid or duplicate history");m.set(r.date,r.close);}return m;});
 const dates=[...maps[0].keys()].filter(d=>maps.every(m=>m.has(d))).sort();
 if(dates.length<2)throw Error("Fewer than two common observed dates");
 const start=dates[0],end=dates.at(-1);
 return {start,end,count:dates.length,rows:series.map((s,i)=>({symbol:s.symbol,start:maps[i].get(start),end:maps[i].get(end),returnPct:(maps[i].get(end)/maps[i].get(start)-1)*100}))};
}
function tradeEstimate(qty,buy,sell,buyCosts,sellCosts,taxRate){
 if(![qty,buy,sell,buyCosts,sellCosts,taxRate].every(Number.isFinite)||!Number.isSafeInteger(qty)||qty<1||buy<=0||sell<=0||buyCosts<0||sellCosts<0||taxRate<0||taxRate>100)throw Error("Invalid inputs");
 const cost=qty*buy+buyCosts, proceeds=qty*sell-sellCosts, gain=proceeds-cost, tax=Math.max(0,gain)*taxRate/100;
 if(![cost,proceeds,gain,tax].every(Number.isFinite))throw Error("Input too large");
 return {cost,proceeds,tax,net:gain-tax,returnPct:(gain-tax)/cost*100};
}
if(typeof module!=="undefined")module.exports={symbolsFrom,compareHistory,tradeEstimate};
if(typeof document!=="undefined"){
 const el=id=>document.getElementById(id),put=(id,v)=>el(id).textContent=v;
 let compareRun=0,watchBusy=false,watchLoaded=false;
 async function request(path,opts={}){const r=await fetch(path,{cache:"no-store",credentials:"same-origin",signal:AbortSignal.timeout(10000),...opts});if(!r.ok)throw Error(r.status===401?"Sign in through configured private deployment":"HTTP "+r.status);return r.json();}
 async function session(){put("account-status","Checking session…");try{const r=await request("/v1/account/session");if(r.authenticated!==true||!["administrator","researcher"].includes(r.role)||r.mode!=="research_only")throw Error("Invalid session response");put("account-status","Authenticated: "+r.role+" · research only · AI recommendations disabled");}catch(e){put("account-status","Session unavailable: "+e.message);}}
 el("account-check").addEventListener("click",session);
 el("compare-run").addEventListener("click",async()=>{
  const run=++compareRun;put("compare-result","Loading observed history…");
  try{const list=symbolsFrom(el("compare-symbols").value,5);if(list.length<2)throw Error("Choose 2–5 symbols");
   const data=await Promise.all(list.map(async symbol=>{const r=await request("/v1/data/"+encodeURIComponent(symbol));if(r.symbol!==symbol||!Array.isArray(r.rows))throw Error("Invalid history");return r;}));
   const c=compareHistory(data);if(run!==compareRun)return;put("compare-result",c.start+" to "+c.end+" · "+c.count+" common observed dates (not calendar-certified)\n"+c.rows.map(r=>r.symbol+" | "+r.start+" → "+r.end+" | "+r.returnPct.toFixed(2)+"%").join("\n"));
  }catch(e){if(run===compareRun)put("compare-result",e.message);}
 });
 async function watch(save){
  if(watchBusy)return;watchBusy=true;el("watch-load").disabled=true;el("watch-save").disabled=true;put("watch-status","Working…");
  try{if(save&&!watchLoaded)throw Error("Load account watchlist first");
   const payload=save?{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({symbols:symbolsFrom(el("watch-symbols").value)})}:{};
   const r=await request("/v1/account/watchlist",payload);
   if(!Array.isArray(r.symbols)||r.symbols.some(s=>typeof s!=="string"||!/^[A-Z0-9]{1,20}$/.test(s)))throw Error("Invalid account response");
   el("watch-symbols").value=r.symbols.join(", ");watchLoaded=true;put("watch-status",save?"Saved to authenticated account.":"Account watchlist loaded.");
  }catch(e){watchLoaded=false;put("watch-status",e.message);}
  finally{watchBusy=false;el("watch-load").disabled=false;el("watch-save").disabled=!watchLoaded;}
 }
 el("watch-load").addEventListener("click",()=>watch(false));el("watch-save").addEventListener("click",()=>watch(true));
 el("calc-run").addEventListener("click",()=>{try{const ids=["calc-qty","calc-buy","calc-sell","calc-buycost","calc-sellcost","calc-tax"];const values=ids.map(id=>{const v=el(id).value;if(v.trim()==="")throw Error("Enter all inputs");return Number(v);});const r=tradeEstimate(...values);put("calc-result",Object.entries(r).map(([k,v])=>k+": "+v.toFixed(2)+(k==="returnPct"?"%":" NPR")).join("\n"));}catch(e){put("calc-result",e.message);}});
}
