import {mkdir,copyFile,rm,writeFile} from "node:fs/promises";
const root=new URL("./",import.meta.url);
const out=new URL("public-build/",root);
await rm(out,{recursive:true,force:true});
await mkdir(new URL("vendor/",out),{recursive:true});
for(const name of ["index.html","styles.css","app.js","chart.js","lightweight.js","actual-profile.js","scanner.js","broker-strategy.js","reliability.js"]){
 await copyFile(new URL(name,root),new URL(name,out));
}
for(const name of ["dist/lightweight-charts.standalone.production.mjs","LICENSE"]){
 await copyFile(new URL("node_modules/lightweight-charts/"+name,root),new URL("vendor/"+name.split("/").at(-1),out));
}
try { await copyFile(new URL("node_modules/lightweight-charts/NOTICE",root),new URL("vendor/NOTICE",out)); } catch(e) { if(e.code!=="ENOENT")throw e; await writeFile(new URL("vendor/NOTICE",out),"Lightweight Charts™ by TradingView — https://www.tradingview.com/\nLicensed under Apache-2.0; see LICENSE.\nThe npm distribution did not include a separate NOTICE file.\n"); }
