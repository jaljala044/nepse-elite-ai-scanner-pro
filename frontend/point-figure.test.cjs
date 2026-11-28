const {test}=require("node:test");
const assert=require("node:assert/strict");
const {pointFigure}=require("./point-figure.js");
const rows=(...prices)=>prices.map((close,i)=>({close,date:"2026-01-"+String(i+1).padStart(2,"0")}));
test("extension and exact reversal",()=>{
 const c=pointFigure(rows(100,120,140,120,110,100,130),10,3);
 assert.deepEqual(c.map(({type,low,high})=>[type,low,high]),[["X",11,14],["O",10,13],["X",11,13]]);
});
test("initial decline",()=>assert.deepEqual(pointFigure(rows(100,80),10,3).map(c=>[c.type,c.low,c.high]),[["O",8,9]]));
test("no movement",()=>assert.deepEqual(pointFigure(rows(100,105),10),[]));
test("reject bad inputs",()=>{assert.throws(()=>pointFigure(rows(100),0));assert.throws(()=>pointFigure(rows(100),10,0));assert.throws(()=>pointFigure(rows(100,NaN),10));assert.throws(()=>pointFigure(rows(100,120).reverse(),10));});
test("decimal box boundary",()=>assert.equal(pointFigure(rows(0.2,0.3),0.1)[0].high,3));
