"use strict";
const assert = require("node:assert/strict");
const { allocation, percent } = require("./portfolio-allocation.js");

assert.deepEqual(allocation([
  { symbol: "CFCL", cost_basis: "1482500" },
  { symbol: "NABIL", cost_basis: "741250" },
]), [
  { symbol: "CFCL", cost_basis: "1482500", share_bps: 6667 },
  { symbol: "NABIL", cost_basis: "741250", share_bps: 3333 },
]);
assert.deepEqual(allocation([
  { symbol: "A", cost_basis: "1.25" },
  { symbol: "B", cost_basis: "2.5" },
]), [
  { symbol: "B", cost_basis: "2.5", share_bps: 6667 },
  { symbol: "A", cost_basis: "1.25", share_bps: 3333 },
]);
assert.deepEqual(allocation([{ symbol: "A", cost_basis: "1e3" }, { symbol: "B", cost_basis: "1" }]), [
  { symbol: "A", cost_basis: "1e3", share_bps: 9990 },
  { symbol: "B", cost_basis: "1", share_bps: 10 },
]);
for (const invalid of [
  null, [{ symbol: "A", cost_basis: "0" }],
  [{ symbol: "A", cost_basis: "-1" }],
  [{ symbol: "A", cost_basis: "NaN" }],
  [{ symbol: "A", cost_basis: "Infinity" }],
  [{ symbol: "A", cost_basis: "1" }, { symbol: "A", cost_basis: "2" }],
  [{ symbol: "bad symbol", cost_basis: "1" }],
]) assert.equal(allocation(invalid), null);
assert.deepEqual(allocation([]), []);
const thirds = allocation([{symbol:"AAA",cost_basis:"1"},{symbol:"BBB",cost_basis:"1"},{symbol:"CCC",cost_basis:"1"}]);
assert.deepEqual(thirds,[{symbol:"AAA",cost_basis:"1",share_bps:3334},{symbol:"BBB",cost_basis:"1",share_bps:3333},{symbol:"CCC",cost_basis:"1",share_bps:3333}]);
assert.equal(thirds.reduce((sum,item)=>sum+item.share_bps,0),10000);
const six = allocation(["A","B","C","D","E","F"].map(symbol=>({symbol,cost_basis:"1"})));
assert.equal(six.reduce((sum,item)=>sum+item.share_bps,0),10000);
assert.equal(percent(6667), "66.67%");
assert.equal(percent(0), "0.00%");
assert.equal(percent(10001), "UNKNOWN");
console.log("portfolio ledger allocation: 14 assertions passed");
