const {chromium}=require("playwright");
const assert=require("node:assert/strict");
const http=require("node:http");
const fs=require("node:fs/promises");
const path=require("node:path");
const root=path.resolve(__dirname,"public-build");
let unavailable=false;
const server=http.createServer(async(req,res)=>{
 try {
  const url=new URL(req.url,"http://localhost");
  if(url.pathname.startsWith("/v1/")){
   const fixtures={
    "/v1/research/readiness":{mode:"research_only",candidate_equities:281,canonical_reviewed_rows:0,universe_available:true,independent_strategy_validation:false,modules:{}},
    "/v1/symbols":{symbols:["NABIL","HDL","NABIL"]},
    "/v1/market-health":{status:"insufficient_evidence",decision_session:null,regime:"unknown",missing_components:["breadth","turnover"]},
   };
   const body=fixtures[url.pathname];
   res.writeHead(unavailable||!body?503:200,{"Content-Type":"application/json"});
   return res.end(JSON.stringify(unavailable||!body?{detail:"Unavailable"}:body));
  }
  const file=path.resolve(root,"."+ (url.pathname==="/" ? "/index.html":url.pathname));
  if(!file.startsWith(root+path.sep)){res.writeHead(403);return res.end();}
  const mime={".html":"text/html",".css":"text/css",".js":"text/javascript",".mjs":"text/javascript"};
  const data=await fs.readFile(file);
  res.writeHead(200,{"Content-Type":mime[path.extname(file)]||"application/octet-stream"});
  res.end(data);
 }catch{res.writeHead(404);res.end();}
});
(async()=>{
 let browser;
 try{
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  browser=await chromium.launch({headless:true});
  const page=await browser.newPage();
  const errors=[];
  page.on("pageerror",error=>errors.push(error.message));
  const origin="http://127.0.0.1:"+server.address().port;
  await page.route("**/*",route=>route.request().url().startsWith(origin+"/")?route.continue():route.abort());
  await page.goto(origin);
  await page.waitForFunction(()=>document.querySelector("#connection").textContent==="Research API connected.");
  await page.waitForFunction(()=>document.querySelector("#market-health-status").textContent.includes("insufficient evidence"));
  assert.equal(await page.locator("#equities").textContent(),"281");
  assert.equal(await page.locator("#reviewed").textContent(),"0");
  assert.match(await page.locator("#market-health-detail").textContent(),/Not verified/);
  assert.match(await page.locator("#market-health-detail").textContent(),/breadth, turnover/);
  assert.equal(await page.locator("#symbol-count").textContent(),"2 loaded symbols");
  await page.locator("#filter").fill("nabil");
  assert.equal(await page.locator("#symbols span").count(),1);
  unavailable=true;
  await page.locator("#refresh").click();
  await page.waitForFunction(()=>document.querySelector("#market-health-status").textContent.includes("unavailable"));
  await page.waitForFunction(()=>document.querySelector("#connection").textContent.includes("unavailable"));
  assert.equal(await page.locator("#market-health-detail dd").count(),0);
  assert.equal(await page.locator("#reviewed").textContent(),"—");
  assert.equal(await page.locator("#ai").textContent(),"OFF");
  assert.equal(await page.locator("#ranking").textContent(),"OFF");
  unavailable=false;
  await page.locator("#refresh").click();
  await page.waitForFunction(()=>document.querySelector("#market-health-status").textContent.includes("insufficient evidence"));
  await page.waitForFunction(()=>document.querySelector("#connection").textContent==="Research API connected.");
  assert.deepEqual(errors,[]);
  console.log("Chromium smoke passed: readiness, symbol filter, outage reset, recovery, recommendations OFF");
 }finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exitCode=1;});
