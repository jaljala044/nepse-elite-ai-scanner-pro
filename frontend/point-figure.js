"use strict";
// Close-only, fixed box size, integer grid; no intraday path assumptions.
function pointFigure(rows, box, reversal=3) {
 if(!Number.isFinite(box)||box<=0||!Number.isInteger(reversal)||reversal<1||reversal>20)throw Error("Invalid box or reversal");
 if(!Array.isArray(rows)||rows.length>20000)throw Error("Invalid history");
 let last="", anchor=null, col=null; const columns=[];
 for(const r of rows){
  if(typeof r.date!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||r.date<=last||!Number.isFinite(r.close)||r.close<=0)throw Error("Invalid or unordered close");
  last=r.date;
  const ratio=r.close/box, q=Math.floor(ratio+Math.min(1e-8,Number.EPSILON*Math.abs(ratio)*4));
  if(!Number.isSafeInteger(q)||q>10000000)throw Error("Box size too small");
  if(anchor===null){anchor=q;continue;}
  if(!col){if(q===anchor)continue;col={type:q>anchor?"X":"O",low:Math.min(q,anchor+(q>anchor?1:-1)),high:Math.max(q,anchor+(q>anchor?1:-1)),start:r.date,end:r.date};columns.push(col);continue;}
  if(col.type==="X"&&q>col.high){col.high=q;col.end=r.date;}
  else if(col.type==="O"&&q<col.low){col.low=q;col.end=r.date;}
  else if(col.type==="X"&&col.high-q>=reversal){col={type:"O",low:q,high:col.high-1,start:r.date,end:r.date};columns.push(col);}
  else if(col.type==="O"&&q-col.low>=reversal){col={type:"X",low:col.low+1,high:q,start:r.date,end:r.date};columns.push(col);}
 }
 return columns;
}
if(typeof module!=="undefined")module.exports={pointFigure};
if(typeof document!=="undefined"){
 let rows=[];
 const by=id=>document.getElementById(id);
 function render(){
  const out=by("pnf-output"),status=by("pnf-status");out.replaceChildren();
  try{
   const box=Number(by("pnf-box").value),rev=Number(by("pnf-reversal").value);
   const cols=pointFigure(rows,box,rev);
   if(!cols.length){status.textContent="No completed box movement in displayed history.";return;}
   status.textContent=cols.length+" columns · close-only · observed data, not independently certified";
   const visible=cols.slice(-40),lo=Math.min(...visible.map(c=>c.low)),hi=Math.max(...visible.map(c=>c.high));
   if(hi-lo>200){status.textContent+=" · increase box size to display grid";return;}
   const table=document.createElement("table"),caption=document.createElement("caption");caption.textContent="Latest "+visible.length+" columns";table.append(caption);
   for(let level=hi;level>=lo;level--){const tr=document.createElement("tr"),th=document.createElement("th");th.scope="row";th.textContent=(level*box).toFixed(2);tr.append(th);for(const c of visible){const td=document.createElement("td");td.textContent=level>=c.low&&level<=c.high?c.type:"";td.style.color=c.type==="X"?"#45d6a0":"#ef6874";tr.append(td);}table.append(tr);}
   out.append(table);
  }catch(e){status.textContent=e.message;}
 }
 document.addEventListener("nepse-chart-data",e=>{rows=e.detail.frame==="daily"?e.detail.rows:[];render();});
 by("pnf-run").addEventListener("click",render);
}
