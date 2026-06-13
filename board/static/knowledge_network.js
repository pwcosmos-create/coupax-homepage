(function () {
  "use strict";

  const container = document.getElementById("kn-graph-container");
  if (!container || typeof ForceGraph !== "function") return;

  const statsEl = document.getElementById("kn-stats");
  const legendEl = document.getElementById("kn-legend-list");
  const detailEl = document.getElementById("kn-detail");
  const detailBadge = document.getElementById("kn-detail-badge");
  const detailTitle = document.getElementById("kn-detail-title");
  const detailDesc = document.getElementById("kn-detail-desc");
  const closeBtn = document.getElementById("kn-detail-close");
  const POLL_MS = 8000;
  let lastSig = "";
  let graph = null;

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function renderLegend(folders) {
    if (!legendEl) return;
    const order = [
      "00_Raw",
      "10_Wiki",
      "20_Meta",
      "40_템플릿",
      "_company",
      "Coupax",
      "Saju",
      "office",
      "_root",
      "Topics",
    ];
    const colors = {
      "00_Raw": "#3b82f6",
      "10_Wiki": "#10b981",
      "20_Meta": "#f97316",
      "40_템플릿": "#a855f7",
      _company: "#eab308",
      Coupax: "#10b981",
      Saju: "#a78bfa",
      office: "#06b6d4",
      _root: "#14b8a6",
      Topics: "#8b5cf6",
    };
    const keys = Object.keys(folders || {}).sort(function (a, b) {
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      if (ia === -1 && ib === -1) return a.localeCompare(b);
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    });
    legendEl.innerHTML = keys
      .map(function (k) {
        const c = colors[k] || "#64748b";
        return (
          '<div class="kn-legend-item">' +
          '<span class="label"><span class="dot" style="background:' +
          c +
          ";color:" +
          c +
          '"></span>' +
          escapeHtml(k) +
          "</span>" +
          '<span class="cnt">' +
          (folders[k] || 0) +
          "</span></div>"
        );
      })
      .join("");
  }

  function showDetail(node) {
    if (!detailEl || !node) return;
    detailBadge.textContent = node.group || "";
    detailBadge.style.background = node.color || "#10b981";
    detailBadge.style.color =
      node.group === "40_템플릿" || node.group === "00_Raw" ? "#fff" : "#000";
    detailTitle.textContent = node.name || node.id || "";
    detailDesc.textContent = node.desc || "";
    detailEl.classList.add("is-open");
    if (graph && node.x != null) {
      graph.centerAt(node.x, node.y, 800);
      graph.zoom(1.6, 800);
    }
  }

  function closeDetail() {
    if (detailEl) detailEl.classList.remove("is-open");
    if (graph) graph.zoom(1.1, 600);
  }

  if (closeBtn) closeBtn.addEventListener("click", closeDetail);

  function applyGraph(data) {
    const gData = {
      nodes: data.nodes || [],
      links: (data.links || []).map(function (l) {
        return { source: l.source, target: l.target, value: l.value || 1 };
      }),
    };
    if (!graph) {
      graph = ForceGraph()(container)
        .graphData(gData)
        .backgroundColor("#0b0f19")
        .nodeRelSize(6)
        .nodeVal(function (n) {
          return n.size || 12;
        })
        .nodeColor(function (n) {
          return n.color || "#10b981";
        })
        .nodeLabel(function (n) {
          return (n.name || n.id) + " (" + (n.group || "") + ")";
        })
        .linkColor(function () {
          return "rgba(255,255,255,0.12)";
        })
        .linkWidth(function (l) {
          return Math.min(3, (l.value || 1) * 0.5);
        })
        .linkDirectionalParticles(1)
        .linkDirectionalParticleWidth(2)
        .linkDirectionalParticleSpeed(0.004)
        .onNodeClick(showDetail)
        .onBackgroundClick(closeDetail);
      graph.d3Force("charge").strength(-220);
      graph.d3Force("link").distance(60);
    } else {
      graph.graphData(gData);
    }

    const st = data.stats || {};
    if (statsEl) {
      statsEl.textContent =
        (st.node_count || gData.nodes.length) +
        " 지식 · " +
        (st.link_count || gData.links.length) +
        " 연결 · " +
        Object.keys(st.folders || {}).length +
        " 폴더";
    }
    renderLegend(st.folders || {});
  }

  function loadGraph() {
    return fetch("/api/agents/office/knowledge-graph.json", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("load failed");
        return r.json();
      })
      .then(function (data) {
        if (!data.ok) throw new Error(data.error || "error");
        const sig =
          (data.updated_at || "") +
          "|" +
          (data.stats && data.stats.node_count) +
          "|" +
          (data.stats && data.stats.link_count);
        if (sig === lastSig && graph) return;
        lastSig = sig;
        applyGraph(data);
      })
      .catch(function () {
        if (statsEl) statsEl.textContent = "데이터를 불러오지 못했습니다.";
      });
  }

  loadGraph();
  window.setInterval(function () {
    if (!document.hidden) loadGraph();
  }, POLL_MS);
})();
