"use strict";
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.NepsePortfolioFormat = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  function indianGrouping(integer) {
    if (integer.length <= 3) return integer;
    const tail = integer.slice(-3);
    let head = integer.slice(0, -3);
    const groups = [];
    while (head.length > 2) {
      groups.unshift(head.slice(-2));
      head = head.slice(0, -2);
    }
    if (head) groups.unshift(head);
    return groups.join(",") + "," + tail;
  }

  function money(value) {
    if (value === null || value === undefined || value === "") return "UNKNOWN";
    const match = /^([+-]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(String(value).trim());
    if (!match) return "UNKNOWN";
    const sign = match[1] === "-" ? -1 : 1;
    const whole = match[2];
    const fraction = match[3] || "";
    const exponent = Number(match[4] || 0);
    if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 10000) return "UNKNOWN";

    const digits = whole + fraction;
    const decimalPosition = whole.length + exponent;
    let integerPart, fractionalPart;
    if (decimalPosition <= 0) {
      integerPart = "0";
      fractionalPart = "0".repeat(-decimalPosition) + digits;
    } else if (decimalPosition >= digits.length) {
      integerPart = digits + "0".repeat(decimalPosition - digits.length);
      fractionalPart = "";
    } else {
      integerPart = digits.slice(0, decimalPosition);
      fractionalPart = digits.slice(decimalPosition);
    }
    integerPart = integerPart.replace(/^0+(?=\d)/, "") || "0";
    fractionalPart = (fractionalPart + "000").slice(0, 3);

    let cents = BigInt(integerPart) * 100n + BigInt(fractionalPart.slice(0, 2));
    if (fractionalPart[2] >= "5") cents += 1n;
    const roundedInteger = (cents / 100n).toString();
    const roundedFraction = (cents % 100n).toString().padStart(2, "0");
    const prefix = sign < 0 && cents !== 0n ? "-" : "";
    return "NPR " + prefix + indianGrouping(roundedInteger) + "." + roundedFraction;
  }

  return Object.freeze({ money });
});
