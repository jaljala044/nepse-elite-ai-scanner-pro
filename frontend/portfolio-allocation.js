"use strict";
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.NepsePortfolioAllocation = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  function parseDecimal(value) {
    const match = /^([+]?)(\d+)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(String(value ?? "").trim());
    if (!match) return null;
    const exponent = Number(match[4] || 0);
    if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 1000) return null;
    const digits = (match[2] + (match[3] || "")).replace(/^0+(?=\d)/, "");
    const decimalPlaces = (match[3] || "").length - exponent;
    if (decimalPlaces < 0) return { digits: BigInt(digits || "0") * (10n ** BigInt(-decimalPlaces)), scale: 0 };
    return { digits: BigInt(digits || "0"), scale: decimalPlaces };
  }

  function allocation(positions) {
    if (!Array.isArray(positions)) return null;
    if (!positions.length) return [];
    const seen = new Set();
    const parsed = [];
    let maxScale = 0;
    for (const position of positions) {
      const symbol = String(position?.symbol || "").trim().toUpperCase();
      const amount = parseDecimal(position?.cost_basis);
      if (!/^[A-Z0-9]{1,20}$/.test(symbol) || seen.has(symbol) || !amount || amount.digits <= 0n) return null;
      seen.add(symbol);
      maxScale = Math.max(maxScale, amount.scale);
      parsed.push({ symbol, cost_basis: String(position.cost_basis), amount });
    }
    const normalized = parsed.map(item => ({
      symbol: item.symbol,
      cost_basis: item.cost_basis,
      value: item.amount.digits * (10n ** BigInt(maxScale - item.amount.scale))
    }));
    const total = normalized.reduce((sum, item) => sum + item.value, 0n);
    if (total <= 0n) return null;
    return normalized.map(item => ({
      symbol: item.symbol,
      cost_basis: item.cost_basis,
      share_bps: Number((item.value * 10000n + total / 2n) / total)
    })).sort((a, b) => b.share_bps - a.share_bps || a.symbol.localeCompare(b.symbol));
  }

  function percent(shareBps) {
    if (!Number.isInteger(shareBps) || shareBps < 0 || shareBps > 10000) return "UNKNOWN";
    return Math.floor(shareBps / 100) + "." + String(shareBps % 100).padStart(2, "0") + "%";
  }

  return Object.freeze({ allocation, percent });
});
