"use strict";
const byId = id => document.getElementById(id);
const labels = {market_structure:"Market structure",ipda:"IPDA 20 / 40 / 60",zone_lifecycle:"FVG and order blocks",multitimeframe:"Multi-timeframe SMC",broker_confluence:"Broker footprint confluence",combined_strategy:"Combined strategy"};
let loadedSymbols = [];
let generation=0;
function set(id,value){byId(id).textContent=String(value);}
async function get(path){const response=await fetch(path,{cache:"no-store",signal:AbortSignal.timeout(10000)});if(!response.ok)throw new Error("HTTP "+response.status);return response.json();}
function renderSymbols(){const q=byId("filter").value.trim().toUpperCase();const fragment=document.createDocumentFragment();for(const symbol of loadedSymbols.filter(s=>s.includes(q))){const el=document.createElement("span");el.textContent=symbol;fragment.append(el);}byId("symbols").replaceChildren(fragment);}
function reset(){for(const id of ["equities","reviewed"])set(id,"—");for(const id of ["universe-status","validation"])set(id,"Unknown");set("policy","UNKNOWN");set("production","Disabled");set("ai","OFF");set("ranking","OFF");byId("module-list").replaceChildren(document.createTextNode("Research readiness unavailable."));loadedSymbols=[];set("symbol-count","Unknown");renderSymbols();}
async function refresh(){const current=++generation;reset();set("connection","Connecting to research API…");const [readiness,symbols]=await Promise.allSettled([get("/v1/research/readiness"),get("/v1/symbols")]);if(current!==generation)return;if(readiness.status==="fulfilled"&&readiness.value?.mode==="research_only"){const d=readiness.value;set("equities",Number.isInteger(d.candidate_equities)?d.candidate_equities:"—");set("reviewed",Number.isInteger(d.canonical_reviewed_rows)?d.canonical_reviewed_rows:"—");set("universe-status",d.universe_available===true?"Available":d.universe_available===false?"Unavailable":"Unknown");set("validation",d.independent_strategy_validation===true?"Reported validated":d.independent_strategy_validation===false?"Not certified":"Unknown");const fragment=document.createDocumentFragment();for(const [key,label] of Object.entries(labels)){const card=document.createElement("article");const heading=document.createElement("h3");heading.textContent=label;const p=document.createElement("p");p.textContent=typeof d.modules?.[key]==="string"?d.modules[key].replaceAll("_"," "):"Unavailable";card.append(heading,p);fragment.append(card);}byId("module-list").replaceChildren(fragment);set("connection",symbols.status==="fulfilled"?"Research API connected.":"Readiness API connected; symbol service unavailable.");}else{set("connection","Research readiness unavailable. No verified live values displayed.");}if(symbols.status==="fulfilled"&&Array.isArray(symbols.value?.symbols)){loadedSymbols=[...new Set(symbols.value.symbols.filter(s=>typeof s==="string"))].sort();set("symbol-count",loadedSymbols.length+" loaded symbols");renderSymbols();}}
byId("refresh").addEventListener("click",refresh);byId("filter").addEventListener("input",renderSymbols);refresh();

/* Market-health is an evidence-readiness view, never a live-feed proxy. */
let marketGeneration=0;
async function refreshMarketHealth(){
 const current=++marketGeneration;
 const status=byId("market-health-status"), detail=byId("market-health-detail");
 status.textContent="Checking market evidence…"; detail.replaceChildren();
 try {
  const d=await get("/v1/market-health");
  if(current!==marketGeneration)return;
  status.textContent="Market evidence: "+(typeof d.status==="string"?d.status.replaceAll("_"," "):"unknown");
  const rows=[["Live feed","Not verified"],["Decision session",d.decision_session??"Unknown"],["Market regime",d.regime??"Unknown"],["Missing evidence",Array.isArray(d.missing_components)?d.missing_components.join(", "):"Unknown"]];
  for(const [name,value] of rows){const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=name;dd.textContent=String(value);detail.append(dt,dd);}
 }catch(e){if(current===marketGeneration)status.textContent="Market evidence unavailable. No live values displayed.";}
}
byId("refresh").addEventListener("click",refreshMarketHealth);
refreshMarketHealth();
