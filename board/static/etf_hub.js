(function () {
  "use strict";

  function parseMcap(text) {
    if (!text || text === "—") return 0;
    const s = String(text).replace(/,/g, "").replace(/\s/g, "").replace(/억/g, "").replace(/만/g, "");
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : 0;
  }

  function parseYield(text) {
    if (!text || text === "—") return 0;
    const n = parseFloat(String(text).replace("%", ""));
    return Number.isFinite(n) ? n : 0;
  }

  function parseMonths(raw) {
    try {
      const arr = typeof raw === "string" ? JSON.parse(raw) : raw;
      return Array.isArray(arr) ? arr : [];
    } catch {
      return [];
    }
  }

  function renderSparkline(months) {
    const vals = months.map((m) => (m == null ? 0 : Number(m)));
    const positive = vals.filter((v) => v > 0);
    if (!positive.length) {
      return '<span class="sheet-spark-empty">—</span>';
    }
    const max = Math.max(...positive, 1);
    const w = 64;
    const h = 22;
    const barW = Math.max(3, Math.floor(w / 12) - 1);
    let bars = "";
    for (let i = 0; i < 12; i++) {
      const v = vals[i] || 0;
      const bh = v > 0 ? Math.max(2, Math.round((v / max) * (h - 2))) : 1;
      const cls = v > 0 ? "sheet-spark-bar sheet-spark-bar--on" : "sheet-spark-bar";
      bars += `<rect class="${cls}" x="${i * (barW + 1)}" y="${h - bh}" width="${barW}" height="${bh}" rx="1"/>`;
    }
    return `<svg class="sheet-spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">${bars}</svg>`;
  }

  function rowMatches(row, filters) {
    const q = filters.q.trim().toLowerCase();
    if (q) {
      const hay = `${row.dataset.code || ""} ${row.dataset.name || ""} ${row.dataset.brand || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (filters.scope && row.dataset.scope !== filters.scope) return false;
    if (filters.cycle && row.dataset.cycle !== filters.cycle) return false;
    const mcap = parseMcap(row.dataset.mcap);
    if (mcap < filters.mcapMin) return false;
    const y = parseYield(row.dataset.yield);
    if (y < filters.yieldMin) return false;
    return true;
  }

  function getFilters(root) {
    return {
      q: root.querySelector("#etf-filter-q")?.value || "",
      scope: root.querySelector("#etf-filter-scope")?.value || "",
      cycle: root.querySelector("#etf-filter-cycle")?.value || "",
      mcapMin: Number(root.querySelector("#etf-filter-mcap")?.value || 0),
      yieldMin: Number(root.querySelector("#etf-filter-yield")?.value || 0),
    };
  }

  function totalReturnOf(row) {
    let v = parseFloat(row.dataset.totalYield);
    if (Number.isFinite(v)) return v;
    const td = row.querySelector("td.sheet-pct-total");
    if (td) {
      const t = String(td.textContent || "").replace(/%/g, "").trim();
      v = parseFloat(t);
      if (Number.isFinite(v)) return v;
    }
    return -9999;
  }

  /** 총 수익률(total_return_pct) 내림차순 — 헤더 ▼ */
  function sortTableByTotalReturn() {
    const tbody = document.getElementById("etf-sheet-body");
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll("tr.sheet-data-row"));
    rows.sort((a, b) => totalReturnOf(b) - totalReturnOf(a));
    rows.forEach((row, index) => {
      tbody.appendChild(row);
      row.dataset.no = String(index + 1);
    });
  }

  function applyFilters() {
    const root = document.getElementById("etf-sheet-tools");
    const tbody = document.getElementById("etf-sheet-body");
    if (!tbody) return;
    sortTableByTotalReturn();
    if (!root) return;
    const filters = getFilters(root);
    const rows = tbody.querySelectorAll("tr.sheet-data-row");
    let visible = 0;
    rows.forEach((row) => {
      const ok = rowMatches(row, filters);
      row.hidden = !ok;
      if (ok) visible += 1;
    });
    const countEl = root.querySelector("#etf-filter-count");
    if (countEl) {
      countEl.textContent = `${visible} / ${rows.length}종 표시`;
    }
  }

  function csvEscape(v) {
    const s = v == null ? "" : String(v);
    if (s.includes(",") || s.includes('"') || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  }

  function rowToCsv(row) {
    const months = parseMonths(row.getAttribute("data-months"));
    const monthVals = [];
    for (let i = 0; i < 12; i++) monthVals.push(months[i] ?? "");
    return [
      row.dataset.no || "",
      row.dataset.brand || "",
      row.dataset.name || "",
      row.dataset.code || "",
      row.dataset.cycle || "",
      row.dataset.listed || "",
      row.dataset.mcap || "",
      row.dataset.fee || "",
      ...monthVals,
      row.dataset.total || "",
      row.dataset.price || "",
      row.dataset.yield || "",
      row.dataset.priceYield || "",
      row.dataset.totalYield || "",
    ].map(csvEscape);
  }

  function exportVisibleCsv(year) {
    const tbody = document.getElementById("etf-sheet-body");
    if (!tbody) return;
    const headers = [
      "no", "brand", "name", "code", "cycle", "listed", "market_cap", "expense_ratio",
      "1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월",
      "dividend_total", "current_price", "누적배당수익률_pct", "YTD주가수익률_pct", "YTD총수익률_pct",
    ];
    const lines = [headers.join(",")];
    const visible = Array.from(tbody.querySelectorAll("tr.sheet-data-row:not([hidden])"));
    visible.sort((a, b) => totalReturnOf(b) - totalReturnOf(a));
    visible.forEach((row) => {
      lines.push(rowToCsv(row).join(","));
    });
    const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `monthly_dividend_filtered_${year || "sheet"}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function initSparklines() {
    document.querySelectorAll("tr.sheet-data-row").forEach((row) => {
      const td = row.querySelector("td.sheet-spark-cell");
      if (!td) return;
      const months = parseMonths(row.getAttribute("data-months"));
      td.innerHTML = renderSparkline(months);
    });
  }

  function init() {
    const tbody = document.getElementById("etf-sheet-body");
    if (tbody) {
      sortTableByTotalReturn();
      initSparklines();
    } else {
      initSparklines();
    }
    const root = document.getElementById("etf-sheet-tools");
    if (!root) {
      document.getElementById("etf-sort-by-total")?.addEventListener("click", (e) => {
        e.preventDefault();
        applyFilters();
      });
      return;
    }
    applyFilters();
    document.getElementById("etf-sort-by-total")?.addEventListener("click", (e) => {
      e.preventDefault();
      applyFilters();
    });
    document.getElementById("etf-sort-by-total")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        applyFilters();
      }
    });
    root.querySelectorAll("select, input").forEach((el) => {
      el.addEventListener("input", applyFilters);
      el.addEventListener("change", applyFilters);
    });
    root.querySelector("#etf-filter-reset")?.addEventListener("click", (e) => {
      e.preventDefault();
      root.querySelectorAll("select").forEach((s) => { s.selectedIndex = 0; });
      const q = root.querySelector("#etf-filter-q");
      if (q) q.value = "";
      applyFilters();
    });
    root.querySelector("#etf-csv-filtered")?.addEventListener("click", (e) => {
      e.preventDefault();
      exportVisibleCsv(root.dataset.year);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
