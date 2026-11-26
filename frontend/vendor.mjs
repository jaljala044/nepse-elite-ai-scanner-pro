import {mkdir,copyFile} from "node:fs/promises";
await mkdir(new URL("./vendor/",import.meta.url),{recursive:true});
for(const name of ["dist/lightweight-charts.standalone.production.mjs","LICENSE","NOTICE"]){await copyFile(new URL("./node_modules/lightweight-charts/"+name,import.meta.url),new URL("./vendor/"+name.split("/").at(-1),import.meta.url));}
