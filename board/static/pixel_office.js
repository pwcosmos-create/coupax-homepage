(function () {
  "use strict";

  var UNITS = [
    "finance",
    "chief-dev",
    "saju-learn",
    "gwansang-learn",
    "kiwoom-chasu",
    "stock-watch",
    "homepage-design",
    "workisus-chasu",
  ];

  var THEMES = {
    finance: { label: "금융 블로그 팀장", emoji: "💰", accent: "#B8860B", glow: "#ADD8E6", floor: "#0A1931", meeting: "브리핑실" },
    "chief-dev": { label: "수석 개발자 팀장", emoji: "👨‍💻", accent: "#60a5fa", glow: "#a78bfa", floor: "#0f172a", meeting: "코드 리뷰실" },
    "saju-learn": { label: "사주 학습 팀장", emoji: "✦", accent: "#c9a0dc", glow: "#f0e6ff", floor: "#1a0f24", meeting: "명리 위원회" },
    "gwansang-learn": { label: "관상 학습 팀장", emoji: "👤", accent: "#f4a896", glow: "#ffd4c8", floor: "#1f1410", meeting: "관상 토론실" },
    "kiwoom-chasu": { label: "원히어로 차수 팀장", emoji: "📈", accent: "#4ade80", glow: "#bbf7d0", floor: "#061408", meeting: "매매 회의실" },
    "stock-watch": { label: "주식 시황 팀장", emoji: "🌐", accent: "#38bdf8", glow: "#7dd3fc", floor: "#030712", meeting: "시황 브리핑" },
    "homepage-design": { label: "홈페이지 디자인 팀장", emoji: "🎨", accent: "#4f6ef7", glow: "#a5b4fc", floor: "#0A1931", meeting: "디자인 위원회" },
    "workisus-chasu": { label: "원키스US차수 팀장", emoji: "🇺🇸", accent: "#f59e0b", glow: "#fcd34d", floor: "#1a1206", meeting: "HTS 작전실" },
  };

  function themeForUnit(unit) {
    var base = THEMES[unit] || THEMES.finance;
    var meta = (window.DIVISION_TEAM_LEADERS || {})[unit];
    if (!meta) return base;
    return Object.assign({}, base, {
      label: meta.team_leader || base.label,
      emoji: meta.emoji || base.emoji,
    });
  }

  var FEED_IDS = {
    finance: "agent-office-feed",
    "chief-dev": "chief-dev-agent-office-feed",
    "saju-learn": "saju-agent-office-feed",
    "gwansang-learn": "gwansang-agent-office-feed",
    "kiwoom-chasu": "kiwoom-agent-office-feed",
    "stock-watch": "stock-agent-office-feed",
    "homepage-design": "design-agent-office-feed",
    "workisus-chasu": "workisus-agent-office-feed",
  };

  var ROSTER_PREFIX = {
    finance: "#office-unit-finance",
    "chief-dev": "#office-unit-chief-dev",
    "saju-learn": "#office-unit-saju-learn",
    "gwansang-learn": "#office-unit-gwansang-learn",
    "kiwoom-chasu": "#office-unit-kiwoom-chasu",
    "stock-watch": "#office-unit-stock-watch",
    "homepage-design": "#office-unit-homepage-design",
    "workisus-chasu": "#office-unit-workisus-chasu",
  };

  var activeUnit = "finance";
  var selectedByUnit = {};
  var chatterTimers = {};
  var bannerTimers = {};
  var deskState = {};
  var tickTimer = null;
  var observers = [];

  function agentsForUnit(unit) {
    var map = {
      finance: function () { return window.AGENT_OFFICE_AGENTS || []; },
      "chief-dev": function () { return window.CHIEF_DEV_OFFICE_AGENTS || []; },
      "saju-learn": function () { return window.AGENT_OFFICE_SAJU_AGENTS || []; },
      "gwansang-learn": function () { return window.GWANSANG_OFFICE_AGENTS || []; },
      "kiwoom-chasu": function () { return window.KIWOM_OFFICE_AGENTS || []; },
      "stock-watch": function () { return window.STOCK_OFFICE_AGENTS || []; },
      "homepage-design": function () { return window.DESIGN_OFFICE_AGENTS || []; },
      "workisus-chasu": function () { return window.WORKISUS_OFFICE_AGENTS || []; },
    };
    return (map[unit] || map.finance)();
  }

  function escapeXml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(s, n) {
    s = String(s || "").replace(/\s+/g, " ").trim();
    if (s.length <= n) return s;
    return s.slice(0, n - 1) + "…";
  }

  function parseRunAgeMin(lastRunAt) {
    if (!lastRunAt) return null;
    var s = String(lastRunAt).trim();
    var m = s.match(/(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})/);
    if (!m) return null;
    var d = new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], 0);
    if (isNaN(d.getTime())) return null;
    return (Date.now() - d.getTime()) / 60000;
  }

  function baseState(agent) {
    if (!agent || !agent.mode_on) return "off";
    var age = parseRunAgeMin(agent.last_run_at);
    if (age !== null && age <= 20) return "working";
    if (agent.last_status && agent.last_status !== "idle") return "working";
    return "idle";
  }

  function deskLayout(count) {
    var cols = count > 12 ? 5 : count > 8 ? 4 : Math.min(4, Math.max(1, Math.ceil(Math.sqrt(count * 1.4))));
    var rows = Math.ceil(count / cols);
    var deskW = count > 12 ? 88 : count > 8 ? 108 : 130;
    var deskH = count > 12 ? 56 : count > 8 ? 64 : 72;
    var gapX = count > 12 ? 10 : 18;
    var gapY = count > 12 ? 10 : 16;
    var startX = 16;
    var startY = 48;
    var positions = [];
    for (var i = 0; i < count; i++) {
      var col = i % cols;
      var row = Math.floor(i / cols);
      positions.push({
        x: startX + col * (deskW + gapX),
        y: startY + row * (deskH + gapY),
        w: deskW,
        h: deskH,
      });
    }
    var contentH = startY + rows * (deskH + gapY) + 24;
    var viewH = Math.max(280, Math.min(520, contentH));
    return { positions: positions, cols: cols, rows: rows, deskW: deskW, deskH: deskH, viewH: viewH };
  }

  function renderMeetingRoom(theme, viewH) {
    var roomH = Math.min(200, viewH - 56);
    return (
      '<g class="po-meeting-room">' +
      '<rect x="620" y="36" width="160" height="' + roomH + '" rx="6" fill="' + theme.floor + '" stroke="' + theme.accent + '" stroke-opacity="0.45" stroke-width="1.5"/>' +
      '<rect x="632" y="48" width="136" height="' + Math.max(80, roomH - 68) + '" rx="4" fill="rgba(0,0,0,0.35)" class="po-meeting-glow"/>' +
      '<text x="700" y="' + (36 + roomH - 16) + '" text-anchor="middle" fill="' + theme.glow + '" font-size="11" font-family="system-ui,sans-serif" opacity="0.85">' + escapeXml(theme.meeting) + "</text>" +
      '<ellipse cx="700" cy="' + (48 + (roomH - 68) / 2) + '" rx="42" ry="28" fill="none" stroke="' + theme.accent + '" stroke-opacity="0.35" stroke-width="1" stroke-dasharray="4 3"/>' +
      "</g>"
    );
  }

  function renderDesk(agent, pos, theme, unit) {
    var id = agent.id;
    var st = deskState[unit + ":" + id] || baseState(agent);
    var sel = selectedByUnit[unit] === id ? " is-selected" : "";
    var cls = "po-desk po-desk--" + id + " is-" + st + sel;
    var chatter = deskState[unit + ":" + id + ":chatter"] || "";
    var name = truncate(agent.name || id, pos.w < 100 ? 6 : 8);
    var emoji = agent.emoji || "🤖";
    var dx = pos.x;
    var dy = pos.y;
    var dw = pos.w;
    var dh = pos.h;
    var cx = dx + dw / 2;
    var emojiSize = dw < 100 ? 16 : 22;
    var emojiY = dy + (dh < 64 ? 26 : 34);
    return (
      '<g class="' + cls + '" data-agent-id="' + escapeXml(id) + '" data-pixel-unit="' + escapeXml(unit) + '">' +
      '<rect class="po-desk-surface" x="' + dx + '" y="' + dy + '" width="' + dw + '" height="' + dh + '" rx="4" fill="rgba(255,255,255,0.04)" stroke="' + theme.accent + '" stroke-opacity="0.35" stroke-width="1"/>' +
      '<rect x="' + (dx + 8) + '" y="' + (dy + dh - 14) + '" width="' + (dw - 16) + '" height="6" rx="2" fill="' + theme.accent + '" opacity="0.25"/>' +
      '<text class="po-agent-emoji" x="' + cx + '" y="' + emojiY + '" text-anchor="middle" font-size="' + emojiSize + '">' + emoji + "</text>" +
      '<circle class="po-status-dot" cx="' + (dx + dw - 10) + '" cy="' + (dy + 10) + '" r="4" fill="#64748b"/>' +
      '<text x="' + cx + '" y="' + (dy + dh - 2) + '" text-anchor="middle" fill="rgba(255,255,255,0.7)" font-size="9" font-family="system-ui,sans-serif">' + escapeXml(name) + "</text>" +
      (chatter
        ? '<g class="po-chatter" style="opacity:1">' +
          '<rect x="' + (cx - 52) + '" y="' + (dy - 28) + '" width="104" height="22" rx="4" fill="#1e293b" stroke="' + theme.glow + '" stroke-opacity="0.5"/>' +
          '<text x="' + cx + '" y="' + (dy - 13) + '" text-anchor="middle" fill="#f8fafc" font-size="8" font-family="system-ui,sans-serif">' + escapeXml(chatter) + "</text>" +
          "</g>"
        : '<g class="po-chatter"><rect x="0" y="0" width="0" height="0"/></g>') +
      "</g>"
    );
  }

  function renderFloor(theme, unit, viewH) {
    var floorId = "po-floor-" + unit.replace(/[^a-z0-9-]/gi, "");
    return (
      '<defs>' +
      '<linearGradient id="' + floorId + '" x1="0" y1="0" x2="0" y2="1">' +
      '<stop offset="0%" stop-color="' + theme.floor + '"/>' +
      '<stop offset="100%" stop-color="#050816"/>' +
      "</linearGradient>" +
      '<filter id="po-glow-' + floorId + '"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
      "</defs>" +
      '<rect width="800" height="' + viewH + '" fill="url(#' + floorId + ')"/>' +
      '<line x1="0" y1="' + (viewH - 32) + '" x2="800" y2="' + (viewH - 32) + '" stroke="rgba(255,255,255,0.06)" stroke-width="1"/>' +
      '<text x="16" y="24" fill="rgba(255,255,255,0.35)" font-size="10" font-family="monospace">PIXEL OFFICE</text>' +
      '<text x="784" y="24" text-anchor="end" fill="' + theme.accent + '" font-size="10" font-family="monospace" opacity="0.7">COUPAX</text>'
    );
  }

  function renderUnit(unit) {
    var svg = document.getElementById("pixel-svg-" + unit);
    if (!svg) return;
    var theme = themeForUnit(unit);
    var agents = agentsForUnit(unit).filter(function (a) { return a && a.id; });
    var layout = deskLayout(agents.length || 1);
    var viewH = layout.viewH || 280;
    svg.setAttribute("viewBox", "0 0 800 " + viewH);
    var html = renderFloor(theme, unit, viewH) + renderMeetingRoom(theme, viewH);
    agents.forEach(function (a, i) {
      var pos = layout.positions[i] || layout.positions[0];
      html += renderDesk(a, pos, theme, unit);
    });
    if (!agents.length) {
      html +=
        '<text x="400" y="140" text-anchor="middle" fill="rgba(255,255,255,0.4)" font-size="13" font-family="system-ui,sans-serif">에이전트 없음</text>';
    }
    svg.innerHTML = html;
    svg.querySelectorAll(".po-desk").forEach(function (g) {
      g.addEventListener("click", function () {
        var aid = g.getAttribute("data-agent-id");
        var u = g.getAttribute("data-pixel-unit");
        selectAgentOnRoster(u, aid);
      });
    });
  }

  function selectAgentOnRoster(unit, agentId) {
    selectedByUnit[unit] = agentId;
    var prefix = ROSTER_PREFIX[unit];
    if (!prefix) return;
    var root = document.querySelector(prefix);
    if (!root) return;
    var btn = root.querySelector('.roster-btn--pick[data-agent-id="' + agentId + '"]');
    if (btn) btn.click();
    renderUnit(unit);
  }

  function setAgentChatter(unit, agentId, text, ms) {
    deskState[unit + ":" + agentId + ":chatter"] = truncate(text, 14);
    deskState[unit + ":" + agentId] = "talking";
    renderUnit(unit);
    var key = unit + ":" + agentId;
    if (chatterTimers[key]) clearTimeout(chatterTimers[key]);
    chatterTimers[key] = setTimeout(function () {
      delete deskState[unit + ":" + agentId + ":chatter"];
      var agents = agentsForUnit(unit);
      var ag = agents.find(function (a) { return a.id === agentId; });
      deskState[unit + ":" + agentId] = ag ? baseState(ag) : "idle";
      renderUnit(unit);
    }, ms || 3500);
  }

  function showBanner(unit, text) {
    var el = document.getElementById("pixel-banner-" + unit);
    if (!el) return;
    el.textContent = text;
    el.classList.remove("is-hidden");
    if (bannerTimers[unit]) clearTimeout(bannerTimers[unit]);
    bannerTimers[unit] = setTimeout(function () {
      el.classList.add("is-hidden");
    }, 4000);
  }

  function onFeedMessage(unit, msg) {
    if (!msg) return;
    var from = msg.from || msg.getAttribute && msg.getAttribute("data-from");
    var kind = msg.kind || (msg.getAttribute && msg.getAttribute("data-kind"));
    var text = msg.text || "";
    if (!from && msg.querySelector) {
      from = msg.getAttribute("data-from");
      kind = msg.getAttribute("data-kind");
      var te = msg.querySelector(".office-msg-text");
      text = te ? te.textContent : "";
    }
    if (!from) return;
    var agents = agentsForUnit(unit);
    var known = agents.some(function (a) { return a.id === from; });
    if (!known) return;
    if (kind === "conclusion") {
      showBanner(unit, "회의 완료 · " + truncate(text, 20));
      deskState[unit + ":" + from] = "meeting";
      renderUnit(unit);
      setTimeout(function () {
        deskState[unit + ":" + from] = baseState(agents.find(function (a) { return a.id === from; }));
        renderUnit(unit);
      }, 2000);
    } else {
      setAgentChatter(unit, from, text || "처리 중…");
    }
  }

  function watchFeed(unit) {
    var feedId = FEED_IDS[unit];
    if (!feedId) return;
    var feed = document.getElementById(feedId);
    if (!feed || feed._pixelObserved) return;
    feed._pixelObserved = true;
    var obs = new MutationObserver(function (mutations) {
      if (unit !== activeUnit) return;
      mutations.forEach(function (mu) {
        mu.addedNodes.forEach(function (node) {
          if (node.nodeType !== 1) return;
          if (node.classList && node.classList.contains("office-msg")) {
            onFeedMessage(unit, node);
          }
        });
      });
    });
    obs.observe(feed, { childList: true });
    observers.push(obs);
  }

  function syncDeskStates(unit) {
    var agents = agentsForUnit(unit);
    agents.forEach(function (a) {
      var key = unit + ":" + a.id;
      if (deskState[key] === "talking" || deskState[key] === "meeting") return;
      deskState[key] = baseState(a);
    });
    if (unit === activeUnit) renderUnit(unit);
  }

  function setActiveUnit(unit) {
    activeUnit = unit || "finance";
    UNITS.forEach(function (u) {
      var panel = document.querySelector('.pixel-office-panel[data-pixel-unit="' + u + '"]');
      if (panel) {
        var hidden = false;
        var unitEl = document.getElementById("office-unit-" + u);
        if (unitEl) hidden = unitEl.hidden;
        panel.style.display = u === activeUnit && !hidden ? "" : "none";
      }
      var live = document.getElementById("pixel-live-" + u);
      if (live) {
        live.classList.toggle("is-off", u !== activeUnit);
        live.textContent = u === activeUnit ? "● LIVE" : "○";
      }
    });
    syncDeskStates(activeUnit);
    renderUnit(activeUnit);
  }

  function tick() {
    if (document.hidden) return;
    syncDeskStates(activeUnit);
  }

  function init() {
    UNITS.forEach(function (u) {
      renderUnit(u);
      watchFeed(u);
    });
    var unitParam = new URLSearchParams(window.location.search).get("unit");
    if (unitParam && UNITS.indexOf(unitParam) >= 0) {
      setActiveUnit(unitParam);
    } else {
      setActiveUnit("finance");
    }
    tickTimer = setInterval(tick, 4000);

    document.querySelectorAll("button.office-division-tab[data-office-unit]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        setTimeout(function () {
          setActiveUnit(tab.getAttribute("data-office-unit") || "finance");
        }, 0);
      });
    });
  }

  window.PixelOffice = {
    setActiveUnit: setActiveUnit,
    renderUnit: renderUnit,
    onMessage: onFeedMessage,
    syncAgents: function (unit) {
      syncDeskStates(unit || activeUnit);
      renderUnit(unit || activeUnit);
    },
    highlightAgent: function (unit, agentId, text) {
      setAgentChatter(unit || activeUnit, agentId, text || "…");
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
