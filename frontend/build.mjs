import {mkdir,copyFile,rm} from "node:fs/promises";
const root=new URL("./",import.meta.url);
const out=new URL("public-build/",root);
await rm(out,{recursive:true,force:true});
await mkdir(new URL("vendor/",out),{recursive:true});
for(const name of ["index.html","styles.css","app.js","chart.js","lightweight.js","actual-profile.js"]){
 await copyFile(new URL(name,root),new URL(name,out));
}
for(const name of ["dist/lightweight-charts.standalone.production.mjs","LICENSE","NOTICE"]){
 await copyFile(new URL("node_modules/lightweight-charts/"+name,root),new URL("vendor/"+name.split("/").at(-1),out));
}
