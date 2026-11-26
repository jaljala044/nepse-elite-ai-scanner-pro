"use strict";
const byId = id => document.getElementById(id);
const labels = {market_structure:"Market structure",ipda:"IPDA 20 / 40 / 60",zone_lifecycle:"FVG and order blocks",multitimeframe:"Multi-timeframe SMC",broker_confluence:"Broker footprint confluence",combined_strategy:"Combined strategy",broker_behaviour_memory:"Broker behaviour memory",broker_early_patterns:"Early entry / exit patterns"};
let loadedSymbols = [];
let generation=0;
function set(id,value){byId(id).textContent=String(value);}
async function get(path){const response=await fetch(path,{cache:"no-store",signal:AbortSignal.timeout(10000)});if(!response.ok)throw new Error("HTTP "+response.status);return response.json();}
function renderSymbols(){const q=byId("filter").value.trim().toUpperCase();const fragment=document.createDocumentFragment();for(const symbol of loadedSymbols.filter(s=>s.includes(q))){const el=document.createElement("span");el.textContent=symbol;fragment.append(el);}byId("symbols").replaceChildren(fragment);}
function reset(){for(const id of ["equities","reviewed"])set(id,"—");for(const id of ["universe-status","validation"])set(id,"Unknown");set("policy","UNKNOWN");set("production","Disabled");set("ai","OFF");set("ranking","OFF");byId("module-list").replaceChildren(document.createTextNode("Research readiness unavailable."));loadedSymbols=[];set("symbol-count","Unknown");renderSymbols();}
async function refresh(){const current=++generation;reset();set("connection","Connecting to research API…");const [readiness,symbols]=await Promise.allSettled([get("/v1/research/readiness"),get("/v1/symbols")]);if(current!==generation)return;if(readiness.status==="fulfilled"&&readiness.value?.mode==="research_only"){const d=readiness.value;set("equities",Number.isInteger(d.candidate_equities)?d.candidate_equities:"—");set("reviewed",Number.isInteger(d.canonical_reviewed_rows)?d.canonical_reviewed_rows:"—");set("universe-status",d.universe_available===true?"Available":d.universe_available===false?"Unavailable":"Unknown");set("validation",d.independent_strategy_validation===true?"Reported validated":d.independent_strategy_validation===false?"Not certified":"Unknown");const fragment=document.createDocumentFragment();for(const [key,label] of Object.entries(labels)){const card=document.createElement("article");const heading=document.createElement("h3");heading.textContent=label;const p=document.createElement("p");p.textContent=typeof d.modules?.[key]==="string"?d.modules[key].replaceAll("_"," "):"Unavailable";card.append(heading,p);fragment.append(card);}byId("module-list").replaceChildren(fragment);set("connection",symbols.status==="fulfilled"?"Research API connected.":"Readiness API connected; symbol service unavailable.");}else{set("connection","Research readiness unavailable. No verified live values displayed.");}if(symbols.status==="fulfilled"&&Array.isArray(symbols.value?.symbols)){loadedSymbols=[...new Set(symbols.value.symbols.filter(s=>typeof s==="string"))].sort();set("symbol-count",loadedSymbols.length+" loaded symbols");renderSymbols();}}
byId("refresh").addEventListener("click",()=>{refresh();refreshBrokerMemoryStatus();});byId("filter").addEventListener("input",renderSymbols);
function node(tag, text, className){const el=document.createElement(tag);if(text!==undefined)el.textContent=String(text);if(className)el.className=className;return el;}
function renderChannelTable(container, channels){
  if(!channels?.length){container.append(node("p","No execution-channel observations in this horizon."));return;}
  const table=node("table");const head=node("thead");const hr=node("tr");
  for(const label of ["Code","Flow","Buy amount","Sell amount","Net amount","Gross share","Active sessions"]){hr.append(node("th",label));}
  head.append(hr);table.append(head);const body=node("tbody");
  for(const item of channels){const tr=node("tr");for(const value of [
    item.execution_channel_code,item.flow_class,item.buy_amount,item.sell_amount,item.net_amount,
    item.gross_participation_pct==null?"—":item.gross_participation_pct+"%",
    item.active_sessions
  ])tr.append(node("td",value));body.append(tr);}
  table.append(body);container.append(table);
}
function renderDailyActivity(container, rows){
  if(!rows?.length)return;
  container.append(node("h4","Recent daily execution-channel history"));
  const table=node("table");const head=node("thead");const hr=node("tr");
  for(const label of ["Session","Buy amount","Sell amount","Net amount"])hr.append(node("th",label));
  head.append(hr);table.append(head);const body=node("tbody");
  for(const item of rows){const tr=node("tr");for(const value of [item.session_date,item.buy_amount,item.sell_amount,item.net_amount])tr.append(node("td",value));body.append(tr);}
  table.append(body);container.append(table);
}
function renderBrokerMemory(data, symbol, code){
  const root=byId("broker-memory-results");root.replaceChildren();
  root.append(node("p","As of "+(data.as_of_trade_date||"unknown")+" · "+(data.status||"unknown"),"memory-asof"));
  root.append(node("p","Observed execution-channel activity only. This does not establish beneficial ownership, proprietary holdings or intent."));
  const patterns=data.selected_early_patterns||[];
  const patternCard=node("article",undefined,"memory-card");
  patternCard.append(node("h3","Early entry / exit pattern review"));
  if(!patterns.length){
    patternCard.append(node("p","No stored candidate pattern for this filter. Verified NEPSE context and complete historical windows are required."));
  }else{
    for(const pattern of patterns){
      const item=node("div");
      item.append(node("strong",pattern.status+" · "+pattern.symbol+" · code "+pattern.execution_channel_code));
      item.append(node("p",pattern.reason||"No reason supplied."));
      item.append(node("p","Rule: "+(pattern.rule_id||"unknown")+" · "+(pattern.calibration_status||"uncalibrated")+" · Confidence: not calibrated"));
      patternCard.append(item);
    }
  }
  root.append(patternCard);
  if(code){
    const matches=data.execution_channel_matches||[];
    if(!matches.length){root.append(node("p","No matching execution-channel history."));return;}
    for(const item of matches){const card=node("article",undefined,"memory-card");card.append(node("h3",item.scope+" · "+item.horizon));renderChannelTable(card,[item]);if(item.horizon==="1D")renderDailyActivity(card,item.daily_activity);root.append(card);}
    return;
  }
  const all=data.execution_channel_features||{};
  const windows=symbol?(all.securities?.[symbol]||{}):(all.market||{});
  for(const horizon of ["1D","1W","1M","1Y"]){
    const w=windows[horizon];const card=node("article",undefined,"memory-card");card.append(node("h3",horizon+" · "+(w?.status||"insufficient evidence")));
    card.append(node("p","Observed sessions: "+(w?.observed_sessions??0)+" · Complete covered sessions: "+(w?.calendar_sessions_available??0)+" · Code coverage: "+(w?.coded_amount_coverage_pct==null?"unknown":w.coded_amount_coverage_pct+"%")));
    renderChannelTable(card,w?.execution_channels||[]);root.append(card);
  }
}
function renderLineage(container, data){
  const card=node("article",undefined,"memory-card");card.append(node("h3","Source evidence drill-down"));
  card.append(node("p",data.total_observations+" party observations · showing "+data.observations.length));
  if(!data.observations.length){card.append(node("p","No source rows available for this filter."));container.append(card);return;}
  const table=node("table");const head=node("thead");const hr=node("tr");
  for(const label of ["Session","Side","Code","Quantity","Amount","Source","Row","Rights","Evidence ID"])hr.append(node("th",label));
  head.append(hr);table.append(head);const body=node("tbody");
  for(const item of data.observations){const tr=node("tr");for(const value of [
    item.trade_date,item.side,item.source_broker_code,item.quantity,item.amount,
    item.source_id,item.source_row_number,item.source_rights_status,item.evidence_id
  ])tr.append(node("td",value??"—"));body.append(tr);}
  table.append(body);card.append(table);container.append(card);
}
async function loadBrokerLineage(symbol, code){
  const params=new URLSearchParams({symbol,limit:"50"});
  if(code)params.set("broker_code",code);
  const data=await get("/v1/broker-memory/lineage?"+params.toString());
  renderLineage(byId("broker-memory-results"),data);
}
async function refreshBrokerMemoryStatus(){
  try{
    const d=await get("/v1/broker-memory/status");
    const status=d.snapshot_count>0
      ? "Persistent broker memory available · "+d.snapshot_count+" snapshots · "+d.observation_count+" observations · latest "+(d.latest_as_of_trade_date||"unknown")
      : "No eligible broker-memory observations stored yet. Live ingestion is not connected.";
    set("broker-memory-status",status);
  }catch(error){set("broker-memory-status","Broker-memory API unavailable. No live broker data displayed.");}
}
async function loadBrokerMemory(){
  const symbol=byId("broker-symbol").value.trim().toUpperCase();
  const code=byId("broker-code").value.trim();
  const asOf=byId("broker-as-of").value;
  if(!symbol&&!code){set("broker-memory-status","Enter a stock symbol or broker execution code.");return;}
  const params=new URLSearchParams();
  if(symbol)params.set("symbol",symbol);
  if(code)params.set("broker_code",code);
  if(asOf)params.set("as_of",asOf);
  set("broker-memory-status","Loading historical broker memory…");
  byId("broker-memory-results").replaceChildren(node("p","Loading…"));
  try{
    const d=await get("/v1/broker-memory?"+params.toString());
    if(d.status==="insufficient_evidence"){
      set("broker-memory-status",d.message||"Insufficient eligible evidence for this query.");
      byId("broker-memory-results").replaceChildren(node("p","No eligible persisted profile. The system will not invent missing observations."));
      return;
    }
    set("broker-memory-status","Historical broker memory loaded · read-only research data.");
    renderBrokerMemory(d,symbol,code);
    if(symbol)loadBrokerLineage(symbol,code).catch(error=>set("broker-memory-status","Profile loaded; evidence drill-down unavailable: "+error.message));
  }catch(error){
    set("broker-memory-status","Unable to load broker memory: "+error.message);
    byId("broker-memory-results").replaceChildren(node("p","No verified result returned."));
  }
}
byId("broker-search").addEventListener("click",loadBrokerMemory);
byId("broker-symbol").addEventListener("keydown",e=>{if(e.key==="Enter")loadBrokerMemory();});
byId("broker-code").addEventListener("keydown",e=>{if(e.key==="Enter")loadBrokerMemory();});
refresh();refreshBrokerMemoryStatus();