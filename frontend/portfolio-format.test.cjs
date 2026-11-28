"use strict";
const assert = require("node:assert/strict");
const { money } = require("./portfolio-format.js");

const cases = [
  ["1482500", "NPR 14,82,500.00"],
  ["12345678901234567890.125", "NPR 12,34,56,78,90,12,34,56,789.13"],
  ["-80000", "NPR -80,000.00"],
  ["1.005", "NPR 1.01"],
  ["1E+3", "NPR 1,000.00"],
  ["1.25E-2", "NPR 0.01"],
  ["0E-12", "NPR 0.00"],
  [null, "UNKNOWN"],
  ["NaN", "UNKNOWN"],
  ["Infinity", "UNKNOWN"],
  ["not-a-number", "UNKNOWN"],
];
for (const [input, expected] of cases) {
  assert.equal(money(input), expected, "format " + String(input));
}
console.log("portfolio exact-decimal formatter: " + cases.length + " cases passed");
