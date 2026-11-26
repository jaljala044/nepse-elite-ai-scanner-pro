"use strict";
(() => {
const host=document.getElementById("lwc-chart"), status=document.getElementById("lwc-status"), credit=document.getElementById("lwc-credit");
let rows=[], chart=null, candle=null, volume=null, busy=false;
function render(){if(!chart)return;candle.setData(rows.map(r=>({time:r.date,open:r.open,high:r.high,low:r.low,close:r.close})));volume.setData(rows.map(r=>({time:r.date,value:r.volume,color:r.close>=r.open?"#45d6a0":"#ef6874"})));if(rows.length)chart.timeScale().fitContent();}
document.addEventListener("nepse-chart-data",e=>{rows=e.detail.rows;render();});
document.getElementById("lwc-toggle").addEventListener("click",async()=>{
if(busy)return;if(chart){host.hidden=!host.hidden;credit.hidden=host.hidden;return;}
busy=true;status.textContent="Loading optional locally installed library…";
try{const notice=await fetch("./vendor/NOTICE",{signal:AbortSignal.timeout(10000)});if(!notice.ok)throw Error("Attribution unavailable");document.getElementById("lwc-notice").textContent=await notice.text();const L=await import("./vendor/lightweight-charts.standalone.production.mjs");host.hidden=false;credit.hidden=false;chart=L.createChart(host,{autoSize:true,layout:{background:{color:"#0b111b"},textColor:"#98a8bc",attributionLogo:true},grid:{vertLines:{color:"#293749"},horzLines:{color:"#293749"}}});candle=chart.addSeries(L.CandlestickSeries,{upColor:"#45d6a0",downColor:"#ef6874",borderVisible:false,wickUpColor:"#45d6a0",wickDownColor:"#ef6874"});volume=chart.addSeries(L.HistogramSeries,{priceFormat:{type:"volume"},priceScaleId:""});volume.priceScale().applyOptions({scaleMargins:{top:.8,bottom:0}});render();status.textContent="TradingView renderer active. Research overlays and drawings remain in the original chart.";}catch(e){if(chart)chart.remove();chart=null;host.hidden=true;credit.hidden=true;status.textContent="Optional library unavailable; original chart remains active.";}finally{busy=false;}
});
})();