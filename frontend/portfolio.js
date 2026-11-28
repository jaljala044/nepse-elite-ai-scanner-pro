"use strict";
(() => {
  const byId = id => document.getElementById(id);
  const state = { portfolios: [], activeId: "", generation: 0 };
  const money = value => {
    if (value === null || value === undefined || value === "") return "UNKNOWN";
    const n = Number(value);
    return Number.isFinite(n) ? "NPR " + n.toLocaleString("en-IN", {minimumFractionDigits: 2, maximumFractionDigits: 2}) : "UNKNOWN";
  };
  const node = (tag, value, className) => {
    const el = document.createElement(tag);
    if (value !== undefined) el.textContent = String(value);
    if (className) el.className = className;
    return el;
  };
  async function get(path) {
    const response = await fetch(path, {
      method: "GET", cache: "no-store", credentials: "same-origin",
      headers: { "Accept": "application/json" },
      signal: AbortSignal.timeout(12000)
    });
    if (response.status === 401 || response.status === 403) throw new Error("Private session unavailable. Sign in through the configured account gateway.");
    if (!response.ok) throw new Error("Portfolio API unavailable (HTTP " + response.status + ").");
    return response.json();
  }
  function table(host, headings, rows, emptyText) {
    host.replaceChildren();
    if (!rows.length) {
      host.append(node("p", emptyText, "portfolio-empty"));
      return;
    }
    const wrapper = node("div", undefined, "portfolio-table-wrap");
    const t = node("table");
    const thead = t.createTHead().insertRow();
    for (const heading of headings) thead.append(node("th", heading));
    const tbody = t.createTBody();
    for (const values of rows) {
      const tr = tbody.insertRow();
      for (const value of values) tr.append(node("td", value));
    }
    wrapper.append(t);
    host.append(wrapper);
  }
  function setStatus(value) { byId("portfolio-status").textContent = value; }
  function clearPortfolioView() {
    byId("portfolio-name").textContent = "No portfolio selected";
    byId("portfolio-valuation-note").textContent =
      "Market value and unrealized P&L remain UNKNOWN until eligible timestamped price evidence is connected.";
    for (const id of ["portfolio-positions", "portfolio-transactions", "portfolio-preferences"]) {
      byId(id).replaceChildren();
    }
  }
  function renderPortfolioOptions() {
    const select = byId("portfolio-select");
    select.replaceChildren();
    for (const p of state.portfolios) {
      const option = node("option", p.name);
      option.value = p.id;
      select.append(option);
    }
    select.value = state.activeId;
    byId("portfolio-name").textContent = state.portfolios.find(p => p.id === state.activeId)?.name || "No portfolio selected";
  }
  async function loadPortfolio(id, generation) {
    const [detail, positions, transactions, preferences] = await Promise.all([
      get("/v1/portfolios/" + encodeURIComponent(id)),
      get("/v1/portfolios/" + encodeURIComponent(id) + "/positions"),
      get("/v1/portfolios/" + encodeURIComponent(id) + "/transactions"),
      get("/v1/portfolios/" + encodeURIComponent(id) + "/preferences")
    ]);
    if (generation !== state.generation) return;
    byId("portfolio-name").textContent = detail.name || "Private portfolio";
    const positionRows = (positions.positions || []).map(p => [
      p.symbol, p.quantity, money(p.average_cost), money(p.cost_basis),
      money(p.realized_pnl), "UNKNOWN", "UNKNOWN", String(p.valuation_status || "UNKNOWN").replaceAll("_", " "),
      String(p.corporate_action_status || "UNKNOWN").replaceAll("_", " ")
    ]);
    table(byId("portfolio-positions"),
      ["Symbol", "Quantity", "Average cost", "Cost basis", "Realized P&L", "Market value", "Unrealized P&L", "Valuation", "Corporate-action adjustment"],
      positionRows, "No recorded positions in this portfolio.");
    const transactionRows = (transactions.transactions || []).map(t => [
      t.trade_date, t.symbol, t.side, t.quantity, money(t.price), money(t.fees)
    ]);
    table(byId("portfolio-transactions"),
      ["Trade date", "Symbol", "Side", "Quantity", "Price", "Fees"],
      transactionRows, "No transactions recorded.");
    const preferenceRows = (preferences.preferences || []).map(p => [
      p.symbol, p.horizon, p.risk_preference, p.updated_at || p.created_at || "—"
    ]);
    table(byId("portfolio-preferences"),
      ["Symbol", "Investment horizon", "Risk preference", "Last updated"],
      preferenceRows, "No holding preferences recorded.");
    byId("portfolio-valuation-note").textContent =
      positions.valuation_note || "Market value and unrealized P&L remain UNKNOWN until eligible timestamped price evidence is connected.";
    setStatus("Private portfolio loaded. Data is held in page memory only; no browser storage or market-price inference is used.");
  }
  async function refresh() {
    const generation = ++state.generation;
    setStatus("Loading private portfolio data…");
    clearPortfolioView();
    try {
      const response = await get("/v1/portfolios");
      if (generation !== state.generation) return;
      state.portfolios = Array.isArray(response.portfolios) ? response.portfolios : [];
      if (!state.portfolios.length) {
        state.activeId = "";
        renderPortfolioOptions();
        clearPortfolioView();
        setStatus("No private portfolios found for this account.");
        return;
      }
      if (!state.portfolios.some(p => p.id === state.activeId)) state.activeId = state.portfolios[0].id;
      renderPortfolioOptions();
      await loadPortfolio(state.activeId, generation);
    } catch (error) {
      if (generation !== state.generation) return;
      state.portfolios = [];
      state.activeId = "";
      renderPortfolioOptions();
      clearPortfolioView();
      setStatus(error.message || "Private portfolio unavailable.");
    }
  }
  byId("portfolio-refresh").addEventListener("click", refresh);
  byId("portfolio-select").addEventListener("change", async event => {
    state.activeId = event.target.value;
    const generation = ++state.generation;
    setStatus("Loading selected portfolio…");
    clearPortfolioView();
    try { await loadPortfolio(state.activeId, generation); }
    catch (error) {
      if (generation === state.generation) {
        clearPortfolioView();
        setStatus(error.message || "Portfolio unavailable.");
      }
    }
  });
  refresh();
})();
