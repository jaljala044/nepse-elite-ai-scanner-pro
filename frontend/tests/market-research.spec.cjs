const {test, expect} = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname,'../index.html'),'utf8').replace(/<script[^>]*><\/script>/g,'').replace(/<link[^>]*>/g,'');
const script = path.join(__dirname,'../market-research.js');
const w = {status:'observed',median_return_pct:4,median_excess_return_pct:2,coverage_pct:100,constituents:[{symbol:'AAA',return_pct:4,excess_return_pct:2}]};
const trail = Array.from({length:6},(_,i)=>({date:'2026-11-'+(22+i),relative_return_pct:i,momentum_change_pp:1,quadrant:'leading'}));
const response = {mode:'research_only',status:'research_only',signals_enabled:false,trade_actions_enabled:false,modules:{
 daily_market_participation:{data:{rankings:{gainers:[{symbol:'AAA',value:'4'}],losers:[],volume:[{symbol:'BBB',value:'100'}]},benchmark_relative:{leaders:[{symbol:'AAA',value:'2'}]}}},
 sector_rotation:{data:{sectors:{BANK:{classification:'Leading',windows:{'1M':w,'1W':{status:'insufficient_evidence'}}}}}},
 index_rotation:{data:{indices:{BANK:{rotation_trail:trail}}}}
}};
async function mount(page, data=response){
 await page.route('http://research.test/',r=>r.fulfill({contentType:'text/html',body:html}));
 await page.route('**/v1/research/market-dashboard',r=>r.fulfill({json:data}));
 await page.goto('http://research.test/');
 await page.addScriptTag({path:script});
 await expect(page.locator('#market-research-status')).toContainText('Research only');
}
test('ranking selector, sector period and drill-down',async({page})=>{
 await mount(page);
 await expect(page.locator('#market-ranking-results')).toContainText('AAA');
 await page.locator('#market-ranking-type').selectOption('volume');
 await expect(page.locator('#market-ranking-results')).toContainText('100 shares');
 await page.getByRole('button',{name:'Inspect BANK'}).click();
 await expect(page.locator('#sector-constituents')).toContainText('AAA');
 await page.locator('#market-sector-period').selectOption('1W');
 await expect(page.locator('#sector-constituents')).toContainText('unavailable');
});
test('rotation trail length and keyboard focus',async({page})=>{
 await mount(page);
 await expect(page.locator('#rotation-chart circle')).toHaveCount(6);
 await page.locator('#rotation-length').evaluate(e=>{e.value=2;e.dispatchEvent(new Event('input'));});
 await expect(page.locator('#rotation-chart circle')).toHaveCount(2);
 await page.locator('#rotation-chart circle').first().focus();
 await expect(page.locator('#rotation-readout')).toContainText('2026-11-26');
});
test('missing evidence stays unavailable',async({page})=>{
 await mount(page,{...response,modules:{},status:'insufficient_evidence'});
 await expect(page.locator('#market-ranking-results')).toContainText('unavailable');
 await expect(page.locator('#rotation-index')).toBeDisabled();
 await expect(page.locator('#market-sector-list')).toContainText('unavailable');
});
