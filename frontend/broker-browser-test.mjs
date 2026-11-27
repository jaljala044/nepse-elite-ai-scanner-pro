import { chromium } from "playwright";
import assert from "node:assert/strict";
const browser=await chromium.launch({headless:true});
try {
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:844}});
  let received;
  await page.route("**/v1/research/broker-ledger-profiles",async route=>{
   received=route.request().postDataJSON();
   assert.equal(route.request().headers().authorization,"Bearer test-only");
   await route.fulfill({json:{status:"insufficient_evidence",reason:"trusted_calendar_incomplete",profiles:[],production_eligible:false,signals_enabled:false}});
  });
  await page.goto("http://127.0.0.1:8765/");
  await page.locator("#broker-context-mode").selectOption("ledger");
  await page.locator("#broker-context-token").fill("test-only");
  await page.locator("#broker-ledger-date").fill("2026-11-25");
  for(const window of ["weekly","monthly","yearly"]){
   await page.locator("#broker-ledger-window").selectOption(window);
   await page.locator("#broker-context-run").click();
   await page.locator("#broker-context-status").filter({hasText:"trusted_calendar_incomplete"}).waitFor();
   assert.equal(received.window,window);
   assert.equal(received.as_of_date,"2026-11-25");
  }
  assert.equal(await page.locator("#broker-context-results").innerText(),"");
  const bounds=await page.locator("#broker-context-run").boundingBox();
  assert.ok(bounds && bounds.width<=width);
  await page.close();
 }
} finally {await browser.close();}
