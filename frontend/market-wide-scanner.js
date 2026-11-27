"use strict";
(() => {
  const el = id => document.getElementById(id);
  const runButton = el("market-wide-scan-run");
  if (!runButton) return;

  let results = [];
  let generation = 0;

  const status = message => { el("market-wide-scan-status").textContent = message; };
  const appendText = (host, label, value) => {
    const row = document.createElement("p");
    const strong = document.createElement("strong");
    strong.textContent = label + ": ";
    row.append(strong, document.createTextNode(value == null ? "Unavailable" : String(value)));
    host.append(row);
  };

  function inspect(result) {
    const host = el("market-wide-scan-detail");
    host.replaceChildren();
    const heading = document.createElement("h3");
    heading.textContent = result.symbol + " — 3A.01 scan details";
    host.append(heading);
    appendText(host, "Status", result.status || "unknown");
    appendText(host, "Result bucket", result.result_bucket || "unknown_results");
    appendText(host, "Latest stored observation", result.latest_available_observation);
    appendText(host, "Calendar age (days; not session age)", result.latest_observation_calendar_age_days);
    appendText(host, "Freshness interpretation", result.freshness_status || "unavailable");
    appendText(host, "Eligibility", result.eligibility?.eligible === true ? "Reviewed for research" : "Not verified");
    appendText(host, "Eligibility reasons", (result.eligibility?.reasons || []).join("; ") || "None reported");
    appendText(host, "Signals", JSON.stringify(result.signals || []));
    appendText(host, "Metrics", JSON.stringify(result.metrics || {}));
    appendText(host, "Limitations", (result.limitations || []).join("; ") || "None reported");
    appendText(host, "Ranking eligible", "No");
    appendText(host, "BUY-list eligible", "No");
  }

  function render() {
    const host = el("market-wide-scan-results");
    host.replaceChildren();
    el("market-wide-scan-detail").replaceChildren();
    if (!results.length) return;

    const table = document.createElement("table");
    const header = document.createElement("tr");
    for (const label of ["Symbol", "Status", "Latest observation", "Calendar age (days)", "Freshness", "Details"]) {
      const cell = document.createElement("th");
      cell.textContent = label;
      header.append(cell);
    }
    table.append(header);

    for (const result of results) {
      const row = document.createElement("tr");
      for (const value of [
        result.symbol,
        result.status || "unknown",
        result.latest_available_observation || "—",
        result.latest_observation_calendar_age_days ?? "—",
        result.freshness_status || "unavailable"
      ]) {
        const cell = document.createElement("td");
        cell.textContent = String(value);
        row.append(cell);
      }
      const cell = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Inspect";
      button.addEventListener("click", () => inspect(result));
      cell.append(button);
      row.append(cell);
      table.append(row);
    }
    host.append(table);
  }

  runButton.addEventListener("click", async () => {
    const requestId = ++generation;
    results = [];
    render();
    el("market-wide-scan-summary").replaceChildren();

    const symbols = [...new Set(el("scan-symbols").value.split(",").map(s => s.trim().toUpperCase()).filter(Boolean))];
    if (symbols.some(s => !/^[A-Z0-9]{1,20}$/.test(s)) || symbols.length > 300) {
      status("Invalid symbols or too many symbols. Use at most 300 valid symbols.");
      return;
    }
    const payload = { symbols: symbols.length ? symbols : null, as_of: el("scan-date").value || null };
    status("Scanning the candidate universe…");
    runButton.disabled = true;

    try {
      const response = await fetch("/v1/scan/market-wide", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
        signal: AbortSignal.timeout(60000)
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (requestId !== generation) return;
      if (data.scanner_id !== "3A.01" || data.mode !== "research_only" || !Array.isArray(data.results)) {
        throw new Error("Unexpected all-market scanner response");
      }
      results = data.results;
      render();

      const summary = el("market-wide-scan-summary");
      appendText(summary, "Candidate symbols scanned", data.candidate_universe_count);
      appendText(summary, "Symbols with at least one stored observation", data.symbols_with_observations);
      appendText(summary, "Symbols without stored observations", data.symbols_without_observations);
      appendText(summary, "Observation coverage", (data.observation_coverage_pct ?? 0) + "%");
      appendText(summary, "As of (Nepal date)", data.as_of || "Unavailable");
      appendText(summary, "Universe source", data.candidate_universe_provenance?.source || "Unverified");
      appendText(summary, "Universe snapshot date", data.candidate_universe_provenance?.observed_on || "Unavailable");
      appendText(summary, "Universe warning", data.candidate_universe_provenance?.warning || "Candidate membership is not authoritative.");
      appendText(summary, "Ranking / BUY lists", "Disabled");

      status(results.length + " results · " + (data.symbols_without_observations || 0) +
        " symbols without stored observations. Coverage counts row presence only, not data quality or verified trading sessions.");
    } catch (error) {
      if (requestId === generation) status("All-market scan unavailable — " + error.message);
    } finally {
      runButton.disabled = false;
    }
  });
})();
