(function () {
  const feedEl = document.getElementById("agent-office-feed");

  const kindLabels = window.AGENT_OFFICE_KIND_LABELS || {};
  let agents = window.AGENT_OFFICE_AGENTS || [];
  let sajuAgents = window.AGENT_OFFICE_SAJU_AGENTS || [];
  let allAgents = window.AGENT_OFFICE_ALL_AGENTS || agents.concat(sajuAgents);
  let activeUnit = "finance";
  const controlEnabled = !!window.AGENT_OFFICE_CONTROL_ENABLED;
  const tokenInput = document.getElementById("office-control-token");
  const officeOnEl = document.getElementById("office-always-on");
  const masterSwitch = document.getElementById("office-master-switch");
  const masterStatus = document.getElementById("office-master-status");
  let officeAlwaysOn = !!window.AGENT_OFFICE_ALWAYS_ON;
  const T = {
    ceoName: "\uB300\uD45C\uB2D8",
    ceoEmoji: "\uD83D\uDC64",
    masterOn: "\uAC00\uB3D9 \uC911 \u2014 \uBAA8\uB978 \uC5D0\uC774\uC804\uD2B8\uAC00 \uC8FC\uAE30 \uC791\uC5C5\uC744 \uC218\uD589\uD569\uB2C8\uB2E4",
    masterOff: "\uD734\uBB34 \u2014 \uAC1C\uBCC4 ON \uC5D0\uC774\uC804\uD2B8\uB9CC \uC791\uC5C5\uD569\uB2C8\uB2E4",
    skillsTitle: "\uC5D0\uC774\uC804\uD2B8 \uC2A4\uD0AC",
    skillsHint: "\uC67C\uCABD \uBA85\uB2E8\uC5D0\uC11C \uC5D0\uC774\uC804\uD2B8\uB97C \uC120\uD0DD\uD558\uBA74 \uBCF4\uC720 \uC2A4\uD0AC\uC744 \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.",
    skillsEmpty: "\uB4F1\uB85D\uB41C \uC2A4\uD0AC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.",
    skillSuffix: " \u00B7 \uC2A4\uD0AC",
    dot: "\u00B7",
    intervalAlways: "\uC0C1\uC2DC",
    intervalMin: "\uBD84",
    modeOn: "ON (\uC0C1\uC2DC \uC2E4\uD589)",
    tokenAlert: "\uC81C\uC5B4 \uD1A0\uD070\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uC0C1\uB2E8\uC5D0 \uC785\uB825\uD574 \uC8FC\uC138\uC694.",
    saveFail: "\uC800\uC7A5 \uC2E4\uD328",
    modeFail: "\uBAA8\uB4DC \uBCC0\uACBD \uC2E4\uD328",
    officeOnFail: "\uC0AC\uBB34\uC2E4 \uC804\uCCB4 ON \uBCC0\uACBD \uC2E4\uD328",
    sessionExpired: "\uC138\uC158\uC774 \uB9CC\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uB85C\uADF8\uC778\uD574 \uC8FC\uC138\uC694.",
    newMsgs: "\uC0C8 \uBA54\uC2DC\uC9C0 ",
    newMsgsSuffix: "\uAC74",
    feedEmpty: "\uC544\uC9C1 \uB300\uD654 \uB85C\uADF8\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    liveOn: "\u25CF \uC2E4\uC2DC\uAC04",
    liveOff: "\u25CF \uC5F0\uACB0 \uB04A\uAE40",
    wikiEmptyFinance: "\uC544\uC9C1 \uBC18\uC601\uB41C Wiki \uCE74\uB4DC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uC9C0\uC2DC \uC644\uB8CC \uD6C4 \uC790\uB3D9 \uC0DD\uC131\uB429\uB2C8\uB2E4.",
    wikiEmptySaju: "\uC544\uC9C1 \uC0AC\uC8FC Wiki \uCE74\uB4DC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uD480\uC774 \uD655\uC815 \uD6C4 \uC790\uB3D9 \uBC18\uC601\uB429\uB2C8\uB2E4.",
    taskQueued: "\uB300\uAE30",
    taskProgress: "\uCC98\uB9AC \uC911",
    taskDone: "\uC644\uB8CC",
    taskCancel: "\uCDE8\uC18C",
    assignPrefix: "\uB2F4\uB2F9: ",
    handledPrefix: "\uCC98\uB9AC: ",
    allPending: "\uC804\uCCB4(\uCC98\uB9AC \uB300\uAE30)",
    urgent: "\uAE34\uAE09",
    reserved: "\uC608\uC57D",
    taskEmpty: "\uC544\uC9C1 \uB0B4\uB9B0 \uC9C0\uC2DC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    blogDraft: "\uBE14\uB85C\uADF8 \uCD08\uC548 #",
    view: "\uBCF4\uAE30",
    edit: "\uC218\uC815",
    publish: "\uBC1C\uD589",
    publishQueue: "\uBC1C\uD589 \uC608\uC57D",
    publishing: "\uBC1C\uD589 \uC911\u2026",
    published: "\uBC1C\uD589\uB428",
    publishQueued: "\uBC1C\uD589 \uC608\uC57D\uB428",
    submitPending: "\uC804\uB2EC \uC911\u2026",
    publishFail: "\uBC1C\uD589 \uC2E4\uD328",
    networkErr: "\uB124\uD2B8\uC6CC\uD06C \uC624\uB958",
    sajuFeedEmpty: "\uC544\uC9C1 \uC0AC\uC8FC \uD559\uC2B5 \uBA54\uC2DC\uC9C0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    sajuCardsEmpty: "\uC544\uC9C1 \uD559\uC2B5 \uCE74\uB4DC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.",
    pendingBadge: " \uB300\uAE30",
    confirm: "\uD655\uC815",
    delete: "\uC0AD\uC81C",
    confirmed: "\uD655\uC815",
    pendingReview: "\uAC80\uC218 \uB300\uAE30",
    bodyToggle: "\uBCF8\uBB38 \uBCF4\uAE30",
    saving: "\uC800\uC7A5 \uC911\u2026",
    cardSaved: "\uD559\uC2B5 \uCE74\uB4DC\uAC00 \uC800\uC7A5\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uD655\uC815\uD558\uBA74 Wiki\uC5D0 \uBC18\uC601\uB429\uB2C8\uB2E4.",
    confirmFail: "\uD655\uC815 \uC2E4\uD328",
    deleteConfirm: "\uC774 \uD559\uC2B5 \uCE74\uB4DC\uB97C \uC0AD\uC81C\uD560\uAE4C\uC694?",
    globalTaskId: "\uC804\uCCB4 \uC791\uC5C5 \uBC88\uD638"
  };


  let rosterMap = {};
  function rebuildMap() {
    rosterMap = { ceo: { id: "ceo", name: T.ceoName, emoji: T.ceoEmoji } };
    allAgents.forEach(function (a) {
      if (a && a.id) rosterMap[a.id] = a;
    });
  }

  function sajuAgentIds() {
    const ids = new Set();
    sajuAgents.forEach(function (a) {
      if (a && a.id) ids.add(a.id);
    });
    return ids;
  }

  function kiwoomAgentIds() {
    const ids = new Set();
    (window.KIWOM_OFFICE_AGENTS || []).forEach(function (a) {
      if (a && a.id) ids.add(a.id);
    });
    return ids;
  }

  function stockAgentIds() {
    const ids = new Set();
    (window.STOCK_OFFICE_AGENTS || []).forEach(function (a) {
      if (a && a.id) ids.add(a.id);
    });
    return ids;
  }

  function designAgentIds() {
    const ids = new Set();
    (window.DESIGN_OFFICE_AGENTS || []).forEach(function (a) {
      if (a && a.id) ids.add(a.id);
    });
    return ids;
  }

  function workisusAgentIds() {
    const ids = new Set();
    (window.WORKISUS_OFFICE_AGENTS || []).forEach(function (a) {
      if (a && a.id) ids.add(a.id);
    });
    return ids;
  }

  function gwansangAgentIds() {
    const ids = new Set();
    (window.GWANSANG_OFFICE_AGENTS || []).forEach(function (a) {
      if (a && a.id) ids.add(a.id);
    });
    return ids;
  }

  function messageForUnit(m, unit) {
    if (!m) return false;
    const d = m.division || "";
    if (d) return d === unit;
    const sajuIds = sajuAgentIds();
    const kiwoomIds = kiwoomAgentIds();
    const stockIds = stockAgentIds();
    const designIds = designAgentIds();
    const workisusIds = workisusAgentIds();
    const gwansangIds = gwansangAgentIds();
    const fr = m.from || "";
    const to = m.to || "";
    if (unit === "saju-learn") {
      return sajuIds.has(fr) || (to && sajuIds.has(to));
    }
    if (unit === "kiwoom-chasu") {
      return kiwoomIds.has(fr) || (to && kiwoomIds.has(to));
    }
    if (unit === "stock-watch") {
      return stockIds.has(fr) || (to && stockIds.has(to));
    }
    if (unit === "homepage-design") {
      return designIds.has(fr) || (to && designIds.has(to));
    }
    if (unit === "workisus-chasu") {
      return workisusIds.has(fr) || (to && workisusIds.has(to));
    }
    if (unit === "gwansang-learn") {
      return gwansangIds.has(fr) || (to && gwansangIds.has(to));
    }
    return (
      !sajuIds.has(fr) &&
      !kiwoomIds.has(fr) &&
      !stockIds.has(fr) &&
      !designIds.has(fr) &&
      !workisusIds.has(fr) &&
      !gwansangIds.has(fr) &&
      (!to ||
        (!sajuIds.has(to) &&
          !kiwoomIds.has(to) &&
          !stockIds.has(to) &&
          !designIds.has(to) &&
          !workisusIds.has(to) &&
          !gwansangIds.has(to)))
    );
  }
  window.messageForUnit = messageForUnit;
  rebuildMap();

  let filterAgent = "";
  let filterKind = "";
  let selectedAgentId = "";

  const POLL_MS = 2500;
  let lastFeedSig = "";
  let lastSajuFeedSig = "";
  let lastTasksSig = "";
  let lastKnowledgeSig = "";
  let lastSajuKnowledgeSig = "";
  let knownMessageIds = new Set();
  let knownSajuMessageIds = new Set();
  let highlightNewIds = new Set();
  let sajuHighlightNewIds = new Set();
  let pollTimer = null;
  let feedWasAtTop = true;
  let sajuFeedWasAtTop = true;

  const TOKEN_KEY = "coupax_office_control_token";

  function csrfHeaders(extra) {
    const base = { "X-CSRF-Token": window.CSRF_TOKEN || "" };
    if (!extra) return base;
    return Object.assign({}, base, extra);
  }
  if (tokenInput) {
    try {
      const saved = localStorage.getItem(TOKEN_KEY);
      if (saved) tokenInput.value = saved;
    } catch (e) {}
    tokenInput.addEventListener("change", function () {
      try {
        localStorage.setItem(TOKEN_KEY, tokenInput.value || "");
      } catch (e) {}
    });
  }

  function getToken() {
    return tokenInput ? (tokenInput.value || "").trim() : "";
  }

  function applyFilters() {
    if (!feedEl) return;
    feedEl.querySelectorAll(".office-msg").forEach(function (el) {
      const from = el.getAttribute("data-from") || "";
      const to = el.getAttribute("data-to") || "";
      const kind = el.getAttribute("data-kind") || "";
      let show = true;
      if (filterAgent && from !== filterAgent && to !== filterAgent) show = false;
      if (filterKind && kind !== filterKind) show = false;
      el.classList.toggle("is-hidden", !show);
    });
  }

  function formatInterval(a) {
    if (!a) return "?";
    if (a.interval_label) return a.interval_label;
    var iv = a.interval_minutes;
    if (iv === 0 || iv === "0") return T.intervalAlways;
    if (iv == null || iv === "") return "?";
    return String(iv) + T.intervalMin;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderSkills(agentId, unit) {
    unit = unit || activeUnit;
    const isSaju = unit === "saju-learn";
    const isKiwoom = unit === "kiwoom-chasu";
    const title = document.getElementById(
      isSaju ? "saju-skills-panel-title" : isKiwoom ? "kiwoom-skills-panel-title" : "skills-panel-title"
    );
    const hint = document.getElementById(
      isSaju ? "saju-skills-panel-hint" : isKiwoom ? "kiwoom-skills-panel-hint" : "skills-panel-hint"
    );
    const list = document.getElementById(
      isSaju ? "saju-skills-list" : isKiwoom ? "kiwoom-skills-list" : "skills-list"
    );
    const meta = document.getElementById(
      isSaju ? "saju-agent-meta-dl" : isKiwoom ? null : "agent-meta-dl"
    );
    if (!list) return;

    const a = rosterMap[agentId];
    if (!a) {
      if (title) title.textContent = T.skillsTitle;
      if (hint) {
        hint.hidden = false;
        hint.textContent =
          unit === "saju-learn"
            ? T.skillsHint
            : T.skillsHint;
      }
      list.innerHTML = "";
      if (meta) meta.hidden = true;
      return;
    }

    if (title) title.textContent = (a.emoji || "") + " " + (a.name || agentId) + T.skillSuffix;
    if (hint) hint.hidden = true;
    const skills = a.skills || [];
    if (!skills.length) {
      list.innerHTML = '<li class="skills-empty">' + T.skillsEmpty + '</li>';
    } else {
      list.innerHTML = skills
        .map(function (sk) {
          const path = sk.path
            ? '<code class="skill-path">' + escapeHtml(sk.path) + "</code>"
            : "";
          return (
            '<li class="skill-card">' +
            "<strong>" +
            escapeHtml(sk.title || sk.id || "") +
            "</strong>" +
            "<p>" +
            escapeHtml(sk.summary || "") +
            "</p>" +
            path +
            "</li>"
          );
        })
        .join("");
    }

    if (meta) {
      meta.hidden = false;
      const iv = document.getElementById(
        isSaju ? "saju-meta-interval" : "meta-interval"
      );
      const jb = document.getElementById(isSaju ? "saju-meta-job" : "meta-job");
      const md = document.getElementById(isSaju ? "saju-meta-mode" : "meta-mode");
      if (iv) iv.textContent = formatInterval(a);
      if (jb) jb.textContent = a.job || "?";
      if (md) md.textContent = a.mode_on ? T.modeOn : "OFF";
    }
  }

  function updateOnCount() {
    const el = document.getElementById("office-on-count");
    if (!el) return;
    let n = 0;
    allAgents.forEach(function (a) {
      if (a.mode_on) n++;
    });
    el.textContent = String(n);
  }

  function syncModeSwitch(cb) {
    const wrap = cb.closest(".mode-on-switch");
    const label = wrap && wrap.querySelector(".mode-on-label");
    const on = !!cb.checked;
    if (wrap) wrap.classList.toggle("is-on", on);
    if (label) label.textContent = on ? "ON" : "OFF";
  }

  function syncModeCheckboxes() {
    document.querySelectorAll(".agent-mode-on").forEach(function (cb) {
      const id = cb.getAttribute("data-agent-id");
      const a = rosterMap[id];
      if (a) cb.checked = !!a.mode_on;
      cb.disabled = !controlEnabled;
      syncModeSwitch(cb);
    });
    if (officeOnEl) officeOnEl.checked = officeAlwaysOn;
    if (masterSwitch) masterSwitch.classList.toggle("is-on", officeAlwaysOn);
    if (masterStatus) {
      masterStatus.textContent = officeAlwaysOn
        ? T.masterOn
        : T.masterOff;
    }
    updateOnCount();
  }

  function postMode(body) {
    if (!controlEnabled) {
      alert(T.tokenAlert);
      return Promise.reject();
    }
    const headers = csrfHeaders({ "Content-Type": "application/json" });
    const token = getToken();
    if (token) headers["X-Office-Token"] = token;
    return fetch("/api/agents/office/mode", {
      method: "POST",
      headers: headers,
      credentials: "same-origin",
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok || !data.ok) {
          throw new Error((data && data.error) || T.saveFail);
        }
        return data;
      });
    });
  }

  document.querySelectorAll("#office-unit-finance .roster-btn--pick").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#office-unit-finance .roster-btn--pick").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      filterAgent = btn.getAttribute("data-filter-agent") || "";
      selectedAgentId = btn.getAttribute("data-agent-id") || "";
      applyFilters();
      renderSkills(selectedAgentId, "finance");
    });
  });

  document.querySelectorAll("#office-unit-finance .roster-btn").forEach(function (btn) {
    if (!btn.classList.contains("roster-btn--pick")) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("#office-unit-finance .roster-btn--pick").forEach(function (b) {
          b.classList.remove("is-active");
        });
        document
          .querySelectorAll("#office-unit-finance .roster-list > li:first-child .roster-btn")
          .forEach(function (b) {
            b.classList.add("is-active");
          });
        filterAgent = "";
        selectedAgentId = "";
        applyFilters();
        renderSkills("", "finance");
      });
    }
  });

  document.querySelectorAll("#office-unit-finance .kind-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#office-unit-finance .kind-btn").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      filterKind = btn.getAttribute("data-filter-kind") || "";
      applyFilters();
    });
  });

  document.querySelectorAll(".mode-on-switch").forEach(function (wrap) {
    wrap.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  });

  document.querySelectorAll(".agent-mode-on").forEach(function (cb) {
    cb.addEventListener("change", function () {
      const id = cb.getAttribute("data-agent-id");
      const want = cb.checked;
      syncModeSwitch(cb);
      postMode({ agent_id: id, mode_on: want })
        .then(function (data) {
          if (rosterMap[id]) rosterMap[id].mode_on = want;
          if (data && data.agent) rosterMap[id] = Object.assign(rosterMap[id] || {}, data.agent);
          if (!want && officeAlwaysOn) {
            officeAlwaysOn = false;
            if (officeOnEl) officeOnEl.checked = false;
            if (masterSwitch) masterSwitch.classList.remove("is-on");
            if (masterStatus) {
              masterStatus.textContent = T.masterOff;
            }
          }
          updateOnCount();
          if (selectedAgentId === id) renderSkills(id);
        })
        .catch(function (err) {
          cb.checked = !want;
          syncModeSwitch(cb);
          alert(err.message || T.modeFail);
        });
    });
  });

  if (officeOnEl) {
    officeOnEl.addEventListener("change", function () {
      const want = officeOnEl.checked;
      postMode({ office_always_on: want })
        .then(function () {
          officeAlwaysOn = want;
          agents.forEach(function (a) {
            a.mode_on = want;
          });
          syncModeCheckboxes();
        })
        .catch(function (err) {
          officeOnEl.checked = !want;
          alert(err.message || T.officeOnFail);
        });
    });
  }

  function renderMessage(m) {
    const fromA = rosterMap[m.from] || {};
    const toA = m.to ? rosterMap[m.to] || {} : null;
    const kindLabel = kindLabels[m.kind] || m.kind || "";
    const toHtml = m.to
      ? '<span class="office-msg-arrow">\u2192</span><span class="office-msg-to">' +
        escapeHtml(toA.name || m.to) +
        "</span>"
      : "";
    const isNew =
      m.id && (highlightNewIds.has(m.id) || sajuHighlightNewIds.has(m.id));
    return (
      '<article class="office-msg office-msg--' +
      escapeHtml(m.kind || "task") +
      (isNew ? " office-msg--new" : "") +
      '" data-msg-id="' +
      escapeHtml(String(m.id || "")) +
      '" data-from="' +
      escapeHtml(m.from || "") +
      '" data-to="' +
      escapeHtml(m.to || "") +
      '" data-kind="' +
      escapeHtml(m.kind || "task") +
      '">' +
      '<header class="office-msg-head">' +
      '<span class="office-msg-avatar">' +
      escapeHtml(fromA.emoji || "\uD83E\uDD16") +
      "</span>" +
      '<span class="office-msg-from">' +
      escapeHtml(fromA.name || m.from) +
      "</span>" +
      toHtml +
      '<span class="office-msg-kind">' +
      escapeHtml(kindLabel) +
      "</span>" +
      '<time class="office-msg-ts">' +
      escapeHtml(m.ts || "") +
      "</time>" +
      "</header>" +
      '<p class="office-msg-text">' +
      escapeHtml(m.text || "") +
      "</p>" +
      "</article>"
    );
  }
  window.renderMessage = renderMessage;

  function parseJsonResponse(r) {
    var ct = r.headers.get("content-type") || "";
    if (ct.indexOf("application/json") === -1) {
      throw new Error(T.sessionExpired);
    }
    return r.json();
  }

  function sortMessages(messages) {
    return (messages || []).slice().sort(function (a, b) {
      const ta = a && a.ts ? String(a.ts) : "";
      const tb = b && b.ts ? String(b.ts) : "";
      if (ta !== tb) return ta < tb ? 1 : ta > tb ? -1 : 0;
      return (b && b.id ? b.id : 0) - (a && a.id ? a.id : 0);
    });
  }

  function feedSignature(data) {
    const messages = data.messages || [];
    let lastId = 0;
    messages.forEach(function (m) {
      if (m && m.id > lastId) lastId = m.id;
    });
    return (data.updated_at || "") + "|" + messages.length + "|" + lastId;
  }

  function sajuFeedSignature(msgs) {
    let lastId = 0;
    (msgs || []).forEach(function (m) {
      if (m && m.id > lastId) lastId = m.id;
    });
    return (msgs ? msgs.length : 0) + "|" + lastId;
  }

  function hideNewBanner() {
    const banner = document.getElementById("office-new-banner");
    if (banner) banner.classList.add("is-hidden");
  }

  function showNewBanner(n) {
    const banner = document.getElementById("office-new-banner");
    const btn = document.getElementById("office-new-banner-btn");
    if (!banner || !btn) return;
    btn.textContent = T.newMsgs + n + T.newMsgsSuffix;
    banner.classList.remove("is-hidden");
  }

  function hideSajuNewBanner() {
    const banner = document.getElementById("saju-office-new-banner");
    if (banner) banner.classList.add("is-hidden");
  }

  function showSajuNewBanner(n) {
    const banner = document.getElementById("saju-office-new-banner");
    const btn = document.getElementById("saju-office-new-banner-btn");
    if (!banner || !btn) return;
    btn.textContent = T.newMsgs + n + T.newMsgsSuffix;
    banner.classList.remove("is-hidden");
  }

  function refreshFeed(forceScrollTop) {
    if (!feedEl) return Promise.resolve();
    if (!forceScrollTop && feedEl.scrollTop > 60) {
      feedWasAtTop = false;
    } else if (feedEl.scrollTop <= 60) {
      feedWasAtTop = true;
    }

    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href = "/agents/office/login?next=" + encodeURIComponent(window.location.pathname);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        const sig = feedSignature(data);
        const prevIds = new Set(knownMessageIds);
        agents = data.agents || agents;
        if (data.office_always_on !== undefined) officeAlwaysOn = !!data.office_always_on;
        rebuildMap();
        syncModeCheckboxes();
        const messages = sortMessages(data.messages).filter(function (m) {
          return messageForUnit(m, "finance");
        });
        const updated = document.getElementById("office-updated-at");
        const count = document.getElementById("office-msg-count");
        if (updated) updated.textContent = data.updated_at || "?";
        if (count) count.textContent = String(messages.length);

        highlightNewIds = new Set();
        let newCount = 0;
        messages.forEach(function (m) {
          if (m && m.id && !prevIds.has(m.id)) {
            newCount++;
            highlightNewIds.add(m.id);
          }
        });

        knownMessageIds = new Set();
        messages.forEach(function (m) {
          if (m && m.id) knownMessageIds.add(m.id);
        });
        lastFeedSig = sig;

        if (!messages.length) {
          feedEl.innerHTML = '<p class="office-empty">' + T.feedEmpty + '</p>';
        } else {
          feedEl.innerHTML = messages.map(renderMessage).join("");
          if (forceScrollTop || feedWasAtTop) {
            feedEl.scrollTop = 0;
            hideNewBanner();
          } else if (newCount > 0) {
            showNewBanner(newCount);
          }
          window.setTimeout(function () {
            feedEl.querySelectorAll(".office-msg--new").forEach(function (el) {
              el.classList.remove("office-msg--new");
            });
          }, 2500);
        }
        applyFilters();
        if (selectedAgentId) renderSkills(selectedAgentId);
        setLiveStatus(true);
      })
      .catch(function () {
        setLiveStatus(false);
      });
  }

  function setLiveStatus(ok) {
    const el = document.getElementById("office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  }

  function refreshKnowledge() {
    const list = document.getElementById("wiki-card-list");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/knowledge.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        const sig = (data.updated_at || "") + "|" + (data.wiki_count || 0);
        if (sig === lastKnowledgeSig) return;
        lastKnowledgeSig = sig;
        const countEl = document.querySelector(".wiki-count");
        if (countEl) {
          countEl.textContent =
            "10_Wiki " + (data.wiki_count || 0) + " " + T.dot + " 20_Meta " + (data.meta_count || 0);
        }
        const items = (data.recent_wiki || []).slice().reverse();
        if (!items.length) {
          list.innerHTML =
            '<li class="wiki-empty">' + T.wikiEmptyFinance + '</li>';
          return;
        }
        list.innerHTML = items
          .map(function (w) {
            const tags = (w.tags || []).join(", ");
            return (
              '<li class="wiki-card-item">' +
              '<span class="wiki-card-id">' +
              escapeHtml(w.id || "") +
              "</span>" +
              "<strong class=\"wiki-card-title\">" +
              escapeHtml(w.title || "") +
              "</strong>" +
              '<p class="wiki-card-summary">' +
              escapeHtml(w.summary || "") +
              "</p>" +
              '<p class="wiki-card-meta">#' +
              escapeHtml(String(w.task_id || "")) +
              " " + T.dot + " " +
              escapeHtml(w.ts || "") +
              (tags ? " " + T.dot + " " + escapeHtml(tags) : "") +
              "</p></li>"
            );
          })
          .join("");
      })
      .catch(function () {});
  }

  function refreshSajuKnowledge() {
    const list = document.getElementById("saju-wiki-card-list");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/knowledge.json?domain=saju-learn", {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        if (r.status === 401) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        const sig = (data.updated_at || "") + "|" + (data.wiki_count || 0);
        if (sig === lastSajuKnowledgeSig) return;
        lastSajuKnowledgeSig = sig;
        const countEl = document.getElementById("saju-wiki-count");
        if (countEl) {
          countEl.textContent =
            "10_Wiki " + (data.wiki_count || 0) + " " + T.dot + " 20_Meta " + (data.meta_count || 0);
        }
        const items = (data.recent_wiki || []).slice().reverse();
        if (!items.length) {
          list.innerHTML =
            '<li class="wiki-empty">' + T.wikiEmptySaju + '</li>';
          return;
        }
        list.innerHTML = items
          .map(function (w) {
            const tags = (w.tags || []).join(", ");
            let tierBadge = "";
            if (w.council_tier === "certified" || w.council_pass) {
              tierBadge =
                '<span class="saju-wiki-tier saju-wiki-tier--cert" title="명리 위원회 PASS">' +
                '<span class="saju-wiki-tier__icon" aria-hidden="true">✓</span>사주위원회 인증</span>';
            } else if (w.council_tier === "review") {
              tierBadge =
                '<span class="saju-wiki-tier saju-wiki-tier--review" title="지식 반영·PASS 대기">' +
                '<span class="saju-wiki-tier__icon" aria-hidden="true">◷</span>사주위원회 검수 반영</span>';
            }
            const itemClass =
              "wiki-card-item" +
              (w.council_tier === "certified" ? " wiki-card-item--cert" : "") +
              (w.council_tier === "review" ? " wiki-card-item--review" : "") +
              (w.council_tier === "excluded" ? " wiki-card-item--excluded" : "");
            return (
              '<li class="' + itemClass + '">' +
              '<span class="wiki-card-id">' +
              escapeHtml(w.id || "") +
              "</span>" +
              tierBadge +
              "<strong class=\"wiki-card-title\">" +
              escapeHtml(w.title || "") +
              "</strong>" +
              '<p class="wiki-card-summary">' +
              escapeHtml(w.summary || "") +
              "</p>" +
              '<p class="wiki-card-meta">#' +
              escapeHtml(String(w.task_id || w.saju_card_id || "")) +
              " " + T.dot + " " +
              escapeHtml(w.ts || "") +
              (tags ? " " + T.dot + " " + escapeHtml(tags) : "") +
              "</p></li>"
            );
          })
          .join("");
      })
      .catch(function () {});
  }

  function pollOfficeRealtime() {
    if (document.hidden) return;
    fetch("/api/agents/office/pulse.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href = "/agents/office/login?next=" + encodeURIComponent(window.location.pathname);
          return null;
        }
        return r.json();
      })
      .then(function (pulse) {
        if (!pulse) return;
        setLiveStatus(true);
        setSajuLiveStatus(true);
        if (activeUnit === "saju-learn") {
          var sajuSig = pulse.saju_feed_sig || pulse.feed_sig || "";
          if (!lastSajuFeedSig || sajuSig !== lastSajuFeedSig) {
            refreshSajuFeed(false);
          }
          if (pulse.tasks_sig && pulse.tasks_sig !== lastTasksSig) {
            refreshSajuLearn();
            refreshSajuTasks();
          }
        } else if (activeUnit === "kiwoom-chasu") {
          var kiwoomSig = pulse.kiwoom_feed_sig || pulse.feed_sig || "";
          if (!lastKiwoomFeedSig || kiwoomSig !== lastKiwoomFeedSig) {
            refreshKiwoomFeed(false);
          }
          if (pulse.tasks_sig && pulse.tasks_sig !== lastTasksSig) {
            if (typeof refreshLearn === "function") refreshLearn();
            if (typeof refreshAccount === "function") refreshAccount();
            refreshKiwoomTasks();
          }
        } else if (activeUnit === "stock-watch") {
          var stockSig = pulse.stock_feed_sig || pulse.feed_sig || "";
          if (!lastStockFeedSig || stockSig !== lastStockFeedSig) {
            if (typeof window.refreshStockFeed === "function") window.refreshStockFeed(false);
          }
          if (typeof window.refreshStockWatch === "function") window.refreshStockWatch();
        } else if (activeUnit === "homepage-design") {
          refreshDesignFeed(false);
          refreshDesignTasks();
        } else if (activeUnit === "workisus-chasu") {
          refreshWorkisusFeed(false);
          refreshWorkisusTasks();
        } else if (activeUnit === "chief-dev") {
          if (typeof window.refreshChiefDevFeed === "function") window.refreshChiefDevFeed(false);
          if (typeof window.refreshChiefDevTasks === "function") window.refreshChiefDevTasks();
        } else if (activeUnit === "gwansang-learn") {
          refreshGwansangFeed(false);
          refreshGwansangTasks();
        } else if (pulse.feed_sig && pulse.feed_sig !== lastFeedSig) {
          refreshFeed(false);
        }
        if (pulse.tasks_sig && pulse.tasks_sig !== lastTasksSig) {
          lastTasksSig = pulse.tasks_sig;
          refreshTasks();
          if (activeUnit !== "saju-learn") refreshSajuTasks();
        }
        if (pulse.knowledge_sig && pulse.knowledge_sig !== lastKnowledgeSig) {
          refreshKnowledge();
        }
        if (pulse.knowledge_sig && pulse.knowledge_sig !== lastSajuKnowledgeSig) {
          refreshSajuKnowledge();
        }
        if (activeUnit === "kiwoom-chasu" && pulse.knowledge_sig) {
          refreshKiwoomKnowledge();
        }
      })
      .catch(function () {
        setLiveStatus(false);
        setSajuLiveStatus(false);
      });
  }

  function startRealtime() {
    document.querySelectorAll(".office-msg").forEach(function (el) {
      const id = parseInt(el.getAttribute("data-msg-id") || "0", 10);
      if (id) knownMessageIds.add(id);
    });
    refreshFeed(true);
    refreshTasks().then(function () {
      fetch("/api/agents/office/pulse.json", { cache: "no-store", credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(function (pulse) {
          if (pulse) {
            lastFeedSig = pulse.feed_sig || "";
            lastSajuFeedSig = pulse.saju_feed_sig || "";
            lastTasksSig = pulse.tasks_sig || "";
            lastKnowledgeSig = pulse.knowledge_sig || "";
          }
        })
        .catch(function () {});
    });
    refreshKnowledge();
    refreshSajuKnowledge();
    var sajuFeedBoot = document.getElementById("saju-agent-office-feed");
    if (sajuFeedBoot) {
      sajuFeedBoot.querySelectorAll(".office-msg").forEach(function (el) {
        var id = parseInt(el.getAttribute("data-msg-id") || "0", 10);
        if (id) knownSajuMessageIds.add(id);
      });
    }
    refreshSajuFeed(false);
    if (pollTimer) window.clearInterval(pollTimer);
    pollTimer = window.setInterval(pollOfficeRealtime, POLL_MS);
  }

  const newBannerBtn = document.getElementById("office-new-banner-btn");
  if (newBannerBtn) {
    newBannerBtn.addEventListener("click", function () {
      feedWasAtTop = true;
      if (feedEl) feedEl.scrollTop = 0;
      hideNewBanner();
      refreshFeed(true);
    });
  }

  if (feedEl) {
    feedEl.addEventListener("scroll", function () {
      feedWasAtTop = feedEl.scrollTop <= 60;
      if (feedWasAtTop) hideNewBanner();
    });
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      pollOfficeRealtime();
    }
  });

  const refreshBtn = document.getElementById("office-refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      feedWasAtTop = true;
      refreshFeed(true);
      refreshTasks();
      refreshKnowledge();
    });
  }

  const TASK_STATUS = { queued: T.taskQueued, in_progress: T.taskProgress, done: T.taskDone, cancelled: T.taskCancel };

  function renderTaskItem(t) {
    const resolved = t.resolved_to || t.handled_by;
    const assignLabel =
      t.assign_to === "all"
        ? resolved
          ? T.handledPrefix + ((rosterMap[resolved] && rosterMap[resolved].name) || resolved)
          : T.allPending
        : (rosterMap[t.assign_to] && rosterMap[t.assign_to].name) || t.assign_to;
    const prio =
      t.priority === "high" ? '<span class="task-priority">' + T.urgent + '</span>' : "";
    const reserved =
      t.source === "reserved"
        ? '<span class="task-reserved-badge">' + T.reserved + "</span>"
        : t.source === "council_finance"
          ? '<span class="task-reserved-badge">\uC704\uC6D0\uD68C</span>'
          : "";
    const title = t.title
      ? '<p class="task-title">' + escapeHtml(t.title) + "</p>"
      : "";
    return (
      '<li class="task-item task-item--' +
      escapeHtml(t.status || "queued") +
      " task-item--prio-" +
      escapeHtml(t.priority || "normal") +
      '" data-task-id="' +
      t.id +
      '">' +
      '<div class="task-item-head">' +
      '<span class="task-id">#' +
      t.id +
      "</span>" +
      reserved +
      '<span class="task-status">' +
      escapeHtml(TASK_STATUS[t.status] || t.status) +
      "</span>" +
      prio +
      '<time class="task-ts">' +
      escapeHtml(t.ts || "") +
      "</time>" +
      "</div>" +
      '<p class="task-assign">' + T.assignPrefix +
      escapeHtml(assignLabel) +
      "</p>" +
      title +
      '<p class="task-body">' +
      escapeHtml(t.body || "") +
      "</p>" +
      (t.wiki_id
        ? '<p class="task-wiki-link">Wiki: ' + escapeHtml(t.wiki_id) + "</p>"
        : "") +
      (t.blog_draft_id
        ? '<p class="task-blog-draft" data-post-id="' +
          t.blog_draft_id +
          '">' + T.blogDraft +
          t.blog_draft_id +
          ' <a href="/post/' +
          t.blog_draft_id +
          '" target="_blank" rel="noopener">' + T.view + '</a> \u00B7 <a href="/post/' +
          t.blog_draft_id +
          '/edit" target="_blank" rel="noopener">' + T.edit + '</a> \u00B7 <button type="button" class="btn-draft-publish btn-sm" data-post-id="' +
          t.blog_draft_id +
          '">' + T.publish + '</button></p>'
        : "") +
      "</li>"
    );
  }

  function renderSajuTaskItem(t, seq) {
    const resolved = t.resolved_to || t.handled_by;
    const assignLabel =
      t.assign_to === "all"
        ? resolved
          ? T.handledPrefix + ((rosterMap[resolved] && rosterMap[resolved].name) || resolved)
          : T.allPending
        : (rosterMap[t.assign_to] && rosterMap[t.assign_to].name) || t.assign_to;
    const prio =
      t.priority === "high" ? '<span class="task-priority">' + T.urgent + '</span>' : "";
    const reserved =
      t.source === "reserved_saju"
        ? '<span class="task-reserved-badge">' + T.reserved + "</span>"
        : t.source === "council_saju" || t.source === "council_saju_card"
          ? '<span class="task-reserved-badge">\uC704\uC6D0\uD68C</span>'
          : "";
    const title = t.title
      ? '<p class="task-title">' + escapeHtml(t.title) + "</p>"
      : "";
    return (
      '<li class="task-item task-item--' +
      escapeHtml(t.status || "queued") +
      " task-item--prio-" +
      escapeHtml(t.priority || "normal") +
      '" data-task-id="' +
      t.id +
      '">' +
      '<div class="task-item-head">' +
      '<span class="task-id">#' +
      seq +
      "</span>" +
      '<span class="task-global-id" title="' + T.globalTaskId + '">(' +
      t.id +
      ")</span>" +
      reserved +
      '<span class="task-status">' +
      escapeHtml(TASK_STATUS[t.status] || t.status) +
      "</span>" +
      prio +
      '<time class="task-ts">' +
      escapeHtml(t.ts || "") +
      "</time>" +
      "</div>" +
      '<p class="task-assign">' + T.assignPrefix +
      escapeHtml(assignLabel) +
      "</p>" +
      title +
      '<p class="task-body">' +
      escapeHtml(t.body || "") +
      "</p>" +
      (t.wiki_id
        ? '<p class="task-wiki-link">Wiki: ' + escapeHtml(t.wiki_id) + "</p>"
        : "") +
      (t.result ? '<pre class="task-result">' + escapeHtml(t.result) + "</pre>" : "") +
      "</li>"
    );
  }

  function taskForDivision(t, division) {
    return ((t && t.division) || "finance") === division;
  }

  function refreshTasks() {
    const list = document.getElementById("task-list");
    const countEl = document.getElementById("task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks.filter(function (t) {
          return taskForDivision(t, "finance");
        });
        if (countEl) countEl.textContent = String(tasks.length);
        if (!tasks.length) {
          list.innerHTML = '<li class="task-empty">' + T.taskEmpty + '</li>';
          return;
        }
        list.innerHTML = tasks.map(renderTaskItem).join("");
      })
      .catch(function () {});
  }

  function refreshSajuTasks() {
    const list = document.getElementById("saju-task-list");
    const countEl = document.getElementById("saju-task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks
          .filter(function (t) {
            return taskForDivision(t, "saju-learn");
          })
          .sort(function (a, b) {
            return (b.id || 0) - (a.id || 0);
          });
        if (countEl) countEl.textContent = String(tasks.length);
        const hintEl = document.getElementById("saju-reserved-hint");
        if (hintEl && data.saju_reserved_queue_target != null) {
          const active = data.saju_reserved_active != null ? data.saju_reserved_active : "—";
          const label = data.saju_reserved_queue_label || "\uBA85\uB9AC \uC608\uC57D";
          hintEl.innerHTML =
            "\u00B7 " +
            label +
            " <strong>" +
            active +
            "</strong>/" +
            data.saju_reserved_queue_target +
            "\uAC74 (\uC790\uB3D9 \uD559\uC2B5 \uD050)";
        }
        if (!tasks.length) {
          list.innerHTML =
            '<li class="task-empty">직접 내린 지시가 없습니다. 「예약」 배지가 붙은 항목은 명리 학습 자동 큐입니다.</li>';
          return;
        }
        list.innerHTML = tasks
          .map(function (t, idx) {
            return renderSajuTaskItem(t, idx + 1);
          })
          .join("");
      })
      .catch(function () {});
  }

  const instructForm = document.getElementById("office-instruct-form");
  if (instructForm) {
    instructForm.addEventListener("submit", function (e) {
      const body = document.getElementById("instruct-body");
      const text = body ? body.value.trim() : "";
      if (!text) {
        e.preventDefault();
        return;
      }
      const btn = document.getElementById("instruct-submit");
      const statusEl = document.getElementById("instruct-status");
      if (btn) {
        btn.disabled = true;
        btn.textContent = T.submitPending;
      }
      if (statusEl) statusEl.textContent = "";
      /* ? POST ?? (form action). JSON fetch? ??/????? ? ?? */
    });
  }

  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-draft-publish");
    if (!btn || btn.disabled) return;
    const postId = btn.getAttribute("data-post-id");
    if (!postId) return;
    btn.disabled = true;
    btn.textContent = T.publishing;
    fetch("/api/agents/office/draft/" + postId + "/publish", {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders({ "X-Requested-With": "XMLHttpRequest" }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (res) {
        if (res.ok && res.j && res.j.ok) {
          if (res.j.queued) {
            btn.textContent = T.publishQueued;
            btn.disabled = true;
            const msg = res.j.message || "";
            if (msg) alert(msg);
          } else {
            btn.textContent = T.published;
            const wrap = btn.closest(".task-blog-draft");
            if (wrap) wrap.classList.add("is-published");
          }
        } else {
          btn.disabled = false;
          btn.textContent = T.publish;
          alert((res.j && res.j.error) || T.saveFail);
        }
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = T.publish;
        alert(T.networkErr);
      });
  });

  /* ?? ??? */
  const unitFinance = document.getElementById("office-unit-finance");
  const unitSaju = document.getElementById("office-unit-saju-learn");
  const unitKiwoom = document.getElementById("office-unit-kiwoom-chasu");
  const unitStock = document.getElementById("office-unit-stock-watch");
  const unitDesign = document.getElementById("office-unit-homepage-design");
  const unitWorkisus = document.getElementById("office-unit-workisus-chasu");
  const unitGwansang = document.getElementById("office-unit-gwansang-learn");
  const unitChiefDev = document.getElementById("office-unit-chief-dev");
  let lastKiwoomFeedSig = "";
  let lastStockFeedSig = "";
  let knownKiwoomMessageIds = new Set();
  let kiwoomFeedWasAtTop = true;
  function refreshSajuFeed(forceScrollTop) {
    const sajuFeed = document.getElementById("saju-agent-office-feed");
    if (!sajuFeed) return Promise.resolve();
    if (!forceScrollTop && sajuFeed.scrollTop > 60) {
      sajuFeedWasAtTop = false;
    } else if (sajuFeed.scrollTop <= 60) {
      sajuFeedWasAtTop = true;
    }
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href =
            "/agents/office/login?next=" + encodeURIComponent(window.location.pathname);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        rebuildMap();
        const raw =
          data.saju_messages && data.saju_messages.length
            ? data.saju_messages
            : (data.messages || []).filter(function (m) {
                return messageForUnit(m, "saju-learn");
              });
        const msgs = sortMessages(raw);
        const sig = sajuFeedSignature(msgs);
        const prevIds = new Set(knownSajuMessageIds);
        sajuHighlightNewIds = new Set();
        var newCount = 0;
        msgs.forEach(function (m) {
          if (m && m.id && !prevIds.has(m.id)) {
            newCount++;
            sajuHighlightNewIds.add(m.id);
          }
        });
        knownSajuMessageIds = new Set();
        msgs.forEach(function (m) {
          if (m && m.id) knownSajuMessageIds.add(m.id);
        });
        lastSajuFeedSig = sig;

        if (!msgs.length) {
          sajuFeed.innerHTML =
            '<p class="office-empty">\uC544\uC9C1 \uC0AC\uC8FC \uD559\uC2B5 \uBA54\uC2DC\uC9C0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.</p>';
          hideSajuNewBanner();
        } else {
          sajuFeed.innerHTML = msgs.map(renderMessage).join("");
          if (forceScrollTop || sajuFeedWasAtTop) {
            sajuFeed.scrollTop = 0;
            hideSajuNewBanner();
          } else if (newCount > 0) {
            showSajuNewBanner(newCount);
          }
          window.setTimeout(function () {
            sajuFeed.querySelectorAll(".office-msg--new").forEach(function (el) {
              el.classList.remove("office-msg--new");
            });
          }, 2500);
        }
        applySajuFeedFilter();
        setSajuLiveStatus(true);
        if (sajuSelectedAgentId) renderSkills(sajuSelectedAgentId, "saju-learn");
      })
      .catch(function () {
        setSajuLiveStatus(false);
      });
  }

  let sajuFilterAgent = "";
  let sajuFilterKind = "";
  let sajuSelectedAgentId = "";

  function applySajuFeedFilter() {
    const sajuFeed = document.getElementById("saju-agent-office-feed");
    if (!sajuFeed) return;
    sajuFeed.querySelectorAll(".office-msg").forEach(function (el) {
      const from = el.getAttribute("data-from") || "";
      const to = el.getAttribute("data-to") || "";
      const kind = el.getAttribute("data-kind") || "";
      let show = true;
      if (sajuFilterAgent && from !== sajuFilterAgent && to !== sajuFilterAgent) show = false;
      if (sajuFilterKind && kind !== sajuFilterKind) show = false;
      el.classList.toggle("is-hidden", !show);
    });
  }

  function setSajuLiveStatus(ok) {
    const el = document.getElementById("saju-office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  }

  function refreshKiwoomFeed(forceScrollTop) {
    const feed = document.getElementById("kiwoom-agent-office-feed");
    if (!feed) return Promise.resolve();
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        rebuildMap();
        const raw =
          data.kiwoom_messages && data.kiwoom_messages.length
            ? data.kiwoom_messages
            : (data.messages || []).filter(function (m) {
                return messageForUnit(m, "kiwoom-chasu");
              });
        const msgs = sortMessages(raw);
        lastKiwoomFeedSig = msgs.map(function (m) { return m.id; }).join(",");
        if (!msgs.length) {
          feed.innerHTML = '<p class="office-empty">아직 원히어로 차수거래 로그가 없습니다.</p>';
        } else {
          feed.innerHTML = msgs.map(renderMessage).join("");
          if (forceScrollTop) feed.scrollTop = 0;
        }
        setKiwoomLiveStatus(true);
      })
      .catch(function () {
        setKiwoomLiveStatus(false);
      });
  }

  function setDesignLiveStatus(ok) {
    const el = document.getElementById("design-office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  }

  function refreshDesignFeed(forceScrollTop) {
    const feed = document.getElementById("design-agent-office-feed");
    if (!feed) return Promise.resolve();
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        rebuildMap();
        const raw =
          data.design_messages && data.design_messages.length
            ? data.design_messages
            : (data.messages || []).filter(function (m) {
                return messageForUnit(m, "homepage-design");
              });
        const msgs = sortMessages(raw);
        if (!msgs.length) {
          feed.innerHTML =
            '<p class="office-empty">아직 홈페이지 디자인 로그가 없습니다.</p>';
        } else {
          feed.innerHTML = msgs.map(renderMessage).join("");
          if (forceScrollTop) feed.scrollTop = 0;
        }
        setDesignLiveStatus(true);
      })
      .catch(function () {
        setDesignLiveStatus(false);
      });
  }

  function refreshDesignTasks() {
    const list = document.getElementById("design-task-list");
    const countEl = document.getElementById("design-task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks
          .filter(function (t) {
            return taskForDivision(t, "homepage-design");
          })
          .sort(function (a, b) {
            return (b.id || 0) - (a.id || 0);
          });
        if (countEl) countEl.textContent = String(tasks.length);
        if (!tasks.length) {
          list.innerHTML =
            '<li class="task-empty">디자인 관련 지시가 없습니다.</li>';
          return;
        }
        list.innerHTML = tasks.map(renderTaskItem).join("");
      });
  }

  function setWorkisusLiveStatus(ok) {
    const el = document.getElementById("workisus-office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  }

  function refreshWorkisusFeed(forceScrollTop) {
    const feed = document.getElementById("workisus-agent-office-feed");
    if (!feed) return Promise.resolve();
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        rebuildMap();
        const raw =
          data.workisus_messages && data.workisus_messages.length
            ? data.workisus_messages
            : (data.messages || []).filter(function (m) {
                return messageForUnit(m, "workisus-chasu");
              });
        const msgs = sortMessages(raw);
        if (!msgs.length) {
          feed.innerHTML =
            '<p class="office-empty">아직 원키스 US 차수 로그가 없습니다.</p>';
        } else {
          feed.innerHTML = msgs.map(renderMessage).join("");
          if (forceScrollTop) feed.scrollTop = 0;
        }
        setWorkisusLiveStatus(true);
      })
      .catch(function () {
        setWorkisusLiveStatus(false);
      });
  }

  function refreshWorkisusTasks() {
    const list = document.getElementById("workisus-task-list");
    const countEl = document.getElementById("workisus-task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks
          .filter(function (t) {
            return taskForDivision(t, "workisus-chasu");
          })
          .sort(function (a, b) {
            return (b.id || 0) - (a.id || 0);
          });
        if (countEl) countEl.textContent = String(tasks.length);
        if (!tasks.length) {
          list.innerHTML =
            '<li class="task-empty">원키스 US 관련 지시가 없습니다.</li>';
          return;
        }
        list.innerHTML = tasks.map(renderTaskItem).join("");
      });
  }

  function setGwansangLiveStatus(ok) {
    const el = document.getElementById("gwansang-office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  }

  function refreshGwansangFeed(forceScrollTop) {
    const feed = document.getElementById("gwansang-agent-office-feed");
    if (!feed) return Promise.resolve();
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        rebuildMap();
        const raw =
          data.gwansang_messages && data.gwansang_messages.length
            ? data.gwansang_messages
            : (data.messages || []).filter(function (m) {
                return messageForUnit(m, "gwansang-learn");
              });
        const msgs = sortMessages(raw);
        if (!msgs.length) {
          feed.innerHTML =
            '<p class="office-empty">아직 관상 학습 로그가 없습니다.</p>';
        } else {
          feed.innerHTML = msgs.map(renderMessage).join("");
          if (forceScrollTop) feed.scrollTop = 0;
        }
        setGwansangLiveStatus(true);
      })
      .catch(function () {
        setGwansangLiveStatus(false);
      });
  }

  function refreshGwansangTasks() {
    const list = document.getElementById("gwansang-task-list");
    const countEl = document.getElementById("gwansang-task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks
          .filter(function (t) {
            return taskForDivision(t, "gwansang-learn");
          })
          .sort(function (a, b) {
            return (b.id || 0) - (a.id || 0);
          });
        if (countEl) countEl.textContent = String(tasks.length);
        if (!tasks.length) {
          list.innerHTML =
            '<li class="task-empty">관상 학습 관련 지시가 없습니다.</li>';
          return;
        }
        list.innerHTML = tasks.map(renderTaskItem).join("");
      });
  }

  function refreshKiwoomTasks() {
    const list = document.getElementById("kiwoom-task-list");
    const countEl = document.getElementById("kiwoom-task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks
          .filter(function (t) {
            return taskForDivision(t, "kiwoom-chasu");
          })
          .sort(function (a, b) {
            return (b.id || 0) - (a.id || 0);
          });
        if (countEl) countEl.textContent = String(tasks.length);
        const hintEl = document.getElementById("kiwoom-reserved-hint");
        if (hintEl && data.kiwoom_reserved_queue_target != null) {
          hintEl.innerHTML =
            "· " +
            escapeHtml(data.kiwoom_reserved_queue_label || "차수 예약") +
            " <strong>" +
            (data.kiwoom_reserved_active != null ? data.kiwoom_reserved_active : "—") +
            "</strong>/" +
            data.kiwoom_reserved_queue_target +
            "건";
        }
        if (!tasks.length) {
          list.innerHTML =
            '<li class="task-empty">직접 지시가 없습니다. 「예약」은 원히어로 차수거래 자동 학습 큐입니다.</li>';
          return;
        }
        list.innerHTML = tasks.map(renderTaskItem).join("");
      });
  }

  function refreshKiwoomKnowledge() {
    return fetch("/api/agents/office/knowledge.json?domain=kiwoom-chasu", {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        const wc = document.getElementById("kiwoom-wiki-count");
        if (wc && data) wc.textContent = "10_Wiki " + (data.wiki_count || 0);
        const wikiTab = document.getElementById("kiwoom-tab-wiki-count");
        if (wikiTab && data) wikiTab.textContent = "(" + (data.wiki_count || 0) + ")";
        const list = document.getElementById("kiwoom-wiki-card-list");
        if (!list || !data || !data.recent_wiki) return;
        const wiki = data.recent_wiki.slice().reverse();
        if (!wiki.length) return;
        list.innerHTML = wiki
          .map(function (w) {
            return (
              '<li class="wiki-card-item"><span class="wiki-card-id">' +
              escapeHtml(w.id) +
              '</span><strong class="wiki-card-title">' +
              escapeHtml(w.title) +
              '</strong><p class="wiki-card-summary">' +
              escapeHtml(w.summary) +
              "</p></li>"
            );
          })
          .join("");
      })
      .catch(function () {});
  }

  function setKiwoomLiveStatus(ok) {
    const el = document.getElementById("kiwoom-office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  }

  function showOfficeUnit(unit) {
    activeUnit = unit || "finance";
    document.querySelectorAll("button.office-division-tab[data-office-unit]").forEach(function (t) {
      t.classList.toggle("is-active", t.getAttribute("data-office-unit") === activeUnit);
    });
    if (unitFinance) {
      unitFinance.hidden = activeUnit !== "finance";
      unitFinance.classList.toggle("is-active", activeUnit === "finance");
    }
    if (unitSaju) {
      unitSaju.hidden = activeUnit !== "saju-learn";
      unitSaju.classList.toggle("is-active", activeUnit === "saju-learn");
      if (activeUnit === "saju-learn") {
        unitSaju.scrollIntoView({ behavior: "smooth", block: "start" });
        sajuFeedWasAtTop = true;
        setSajuLiveStatus(true);
        refreshSajuLearn();
        refreshSajuFeed(true);
        refreshSajuTasks();
        refreshSajuKnowledge();
        pollOfficeRealtime();
      }
    }
    if (unitKiwoom) {
      unitKiwoom.hidden = activeUnit !== "kiwoom-chasu";
      unitKiwoom.classList.toggle("is-active", activeUnit === "kiwoom-chasu");
      if (activeUnit === "kiwoom-chasu") {
        unitKiwoom.scrollIntoView({ behavior: "smooth", block: "start" });
        kiwoomFeedWasAtTop = true;
        setKiwoomLiveStatus(true);
        if (typeof refreshLearn === "function") refreshLearn();
        if (typeof refreshAccount === "function") refreshAccount();
        refreshKiwoomFeed(true);
        refreshKiwoomTasks();
        refreshKiwoomKnowledge();
        pollOfficeRealtime();
      }
    }
    if (unitStock) {
      unitStock.hidden = activeUnit !== "stock-watch";
      unitStock.classList.toggle("is-active", activeUnit === "stock-watch");
      if (activeUnit === "stock-watch") {
        unitStock.scrollIntoView({ behavior: "smooth", block: "start" });
        if (typeof window.refreshStockWatch === "function") window.refreshStockWatch();
        if (typeof window.refreshStockFeed === "function") window.refreshStockFeed(true);
        pollOfficeRealtime();
      }
    }
    if (unitDesign) {
      unitDesign.hidden = activeUnit !== "homepage-design";
      unitDesign.classList.toggle("is-active", activeUnit === "homepage-design");
      if (activeUnit === "homepage-design") {
        unitDesign.scrollIntoView({ behavior: "smooth", block: "start" });
        setDesignLiveStatus(true);
        refreshDesignFeed(true);
        refreshDesignTasks();
        if (typeof window.refreshDesignLearn === "function") window.refreshDesignLearn();
        if (typeof window.refreshDesignWiki === "function") window.refreshDesignWiki();
        if (typeof window.refreshDesignDebateTopics === "function") window.refreshDesignDebateTopics();
        pollOfficeRealtime();
      }
    }
    if (unitWorkisus) {
      unitWorkisus.hidden = activeUnit !== "workisus-chasu";
      unitWorkisus.classList.toggle("is-active", activeUnit === "workisus-chasu");
      if (activeUnit === "workisus-chasu") {
        unitWorkisus.scrollIntoView({ behavior: "smooth", block: "start" });
        setWorkisusLiveStatus(true);
        refreshWorkisusFeed(true);
        refreshWorkisusTasks();
        if (typeof window.refreshWorkisusLearn === "function") window.refreshWorkisusLearn();
        if (typeof window.refreshWorkisusWiki === "function") window.refreshWorkisusWiki();
        pollOfficeRealtime();
      }
    }
    
    if (unitChiefDev) {
      unitChiefDev.hidden = activeUnit !== "chief-dev";
      unitChiefDev.classList.toggle("is-active", activeUnit === "chief-dev");
      if (activeUnit === "chief-dev") {
        unitChiefDev.scrollIntoView({ behavior: "smooth", block: "start" });
        if (typeof window.setChiefDevLiveStatus === "function") window.setChiefDevLiveStatus(true);
        if (typeof window.refreshChiefDevFeed === "function") window.refreshChiefDevFeed(true);
        if (typeof window.refreshChiefDevTasks === "function") window.refreshChiefDevTasks();
        pollOfficeRealtime();
      }
    }
    if (unitGwansang) {
      unitGwansang.hidden = activeUnit !== "gwansang-learn";
      unitGwansang.classList.toggle("is-active", activeUnit === "gwansang-learn");
      if (activeUnit === "gwansang-learn") {
        unitGwansang.scrollIntoView({ behavior: "smooth", block: "start" });
        setGwansangLiveStatus(true);
        refreshGwansangFeed(true);
        refreshGwansangTasks();
        if (typeof window.refreshGwansangLearn === "function") window.refreshGwansangLearn();
        if (typeof window.refreshGwansangWiki === "function") window.refreshGwansangWiki();
        pollOfficeRealtime();
      }
    }
    if (window.PixelOffice) window.PixelOffice.setActiveUnit(activeUnit);
  }

  const unitParam = new URLSearchParams(window.location.search).get("unit");
  if (unitParam === "saju-learn" && unitSaju) {
    showOfficeUnit("saju-learn");
  } else if (unitParam === "kiwoom-chasu" && unitKiwoom) {
    showOfficeUnit("kiwoom-chasu");
  } else if (unitParam === "stock-watch" && unitStock) {
    showOfficeUnit("stock-watch");
  } else if (unitParam === "homepage-design" && unitDesign) {
    showOfficeUnit("homepage-design");
  } else if (unitParam === "workisus-chasu" && unitWorkisus) {
    showOfficeUnit("workisus-chasu");
  } else if (unitParam === "chief-dev" && unitChiefDev) {
    showOfficeUnit("chief-dev");
  } else if (unitParam === "gwansang-learn" && unitGwansang) {
    showOfficeUnit("gwansang-learn");
  } else if (window.PixelOffice) {
    window.PixelOffice.setActiveUnit(activeUnit);
  }

  document.querySelectorAll("button.office-division-tab[data-office-unit]").forEach(function (tab) {
    tab.addEventListener("click", function () {
      showOfficeUnit(tab.getAttribute("data-office-unit") || "finance");
    });
  });

  document.querySelectorAll("#office-unit-saju-learn .roster-btn--pick").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#office-unit-saju-learn .roster-btn--pick").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      sajuFilterAgent = btn.getAttribute("data-filter-agent") || "";
      sajuSelectedAgentId = btn.getAttribute("data-agent-id") || "";
      applySajuFeedFilter();
      renderSkills(sajuSelectedAgentId, "saju-learn");
    });
  });

  document.querySelectorAll("#office-unit-saju-learn .roster-btn").forEach(function (btn) {
    if (!btn.classList.contains("roster-btn--pick")) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("#office-unit-saju-learn .roster-btn--pick").forEach(function (b) {
          b.classList.remove("is-active");
        });
        document
          .querySelectorAll("#office-unit-saju-learn .roster-list > li:first-child .roster-btn")
          .forEach(function (b) {
            b.classList.add("is-active");
          });
        sajuFilterAgent = "";
        sajuSelectedAgentId = "";
        applySajuFeedFilter();
        renderSkills("", "saju-learn");
      });
    }
  });

  document.querySelectorAll("#office-unit-saju-learn .saju-kind-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#office-unit-saju-learn .saju-kind-btn").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      sajuFilterKind = btn.getAttribute("data-filter-kind") || "";
      applySajuFeedFilter();
    });
  });

  let kiwoomFilterAgent = "";
  document.querySelectorAll("#office-unit-kiwoom-chasu .roster-btn--pick").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#office-unit-kiwoom-chasu .roster-btn--pick").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      kiwoomFilterAgent = btn.getAttribute("data-filter-agent") || "";
      const feed = document.getElementById("kiwoom-agent-office-feed");
      if (feed) {
        feed.querySelectorAll(".office-msg").forEach(function (el) {
          const from = el.getAttribute("data-from") || "";
          const to = el.getAttribute("data-to") || "";
          let show = true;
          if (kiwoomFilterAgent && from !== kiwoomFilterAgent && to !== kiwoomFilterAgent) show = false;
          el.classList.toggle("is-hidden", !show);
        });
      }
      renderSkills(btn.getAttribute("data-agent-id") || "", "kiwoom-chasu");
    });
  });

  const kiwoomOfficeRefresh = document.getElementById("kiwoom-office-refresh-btn");
  if (kiwoomOfficeRefresh) {
    kiwoomOfficeRefresh.addEventListener("click", function () {
      refreshKiwoomFeed(true);
      if (typeof refreshLearn === "function") refreshLearn();
      if (typeof refreshAccount === "function") refreshAccount();
      refreshKiwoomTasks();
      refreshKiwoomKnowledge();
    });
  }

  const sajuOfficeRefresh = document.getElementById("saju-office-refresh-btn");
  if (sajuOfficeRefresh) {
    sajuOfficeRefresh.addEventListener("click", function () {
      sajuFeedWasAtTop = true;
      refreshSajuFeed(true);
      refreshSajuLearn();
      refreshSajuTasks();
      refreshSajuKnowledge();
    });
  }

  const sajuNewBannerBtn = document.getElementById("saju-office-new-banner-btn");
  if (sajuNewBannerBtn) {
    sajuNewBannerBtn.addEventListener("click", function () {
      sajuFeedWasAtTop = true;
      var sajuFeedEl = document.getElementById("saju-agent-office-feed");
      if (sajuFeedEl) sajuFeedEl.scrollTop = 0;
      hideSajuNewBanner();
      refreshSajuFeed(true);
    });
  }

  var sajuFeedEl = document.getElementById("saju-agent-office-feed");
  if (sajuFeedEl) {
    sajuFeedEl.addEventListener("scroll", function () {
      sajuFeedWasAtTop = sajuFeedEl.scrollTop <= 60;
      if (sajuFeedWasAtTop) hideSajuNewBanner();
    });
    sajuFeedEl.querySelectorAll(".office-msg").forEach(function (el) {
      var id = parseInt(el.getAttribute("data-msg-id") || "0", 10);
      if (id) knownSajuMessageIds.add(id);
    });
  }

  function updateSajuStats(st) {
    if (!st) return;
    const el = function (id, v) {
      const n = document.getElementById(id);
      if (n) n.textContent = String(v);
    };
    el("saju-learn-total", st.total);
    el("saju-learn-pending", st.pending);
    el("saju-learn-confirmed", st.confirmed);
    const badge = document.querySelector(".saju-learn-badge");
    if (badge) badge.textContent = st.pending + T.pendingBadge;
  }

  function isSajuCouncilCertified(c) {
    return c && (c.council_status === "pass" || c.council_pass === true);
  }

  function sajuCouncilCertHtml(c) {
    if (isSajuCouncilCertified(c)) {
      const at = c.council_at ? " · " + c.council_at : "";
      return (
        '<span class="saju-council-cert" title="명리 위원회 검증 PASS' +
        escapeHtml(at) +
        '"><span class="saju-council-cert__icon" aria-hidden="true">✓</span>사주위원회 인증</span>'
      );
    }
    if (c && c.council_status === "fail") {
      return (
        '<span class="saju-council-badge saju-council-badge--fail" title="명리위원회 FAIL">위원회 재검토</span>'
      );
    }
    return "";
  }

  function renderSajuCards(cards) {
    const list = document.getElementById("saju-learn-card-list");
    if (!list) return;
    if (!cards || !cards.length) {
      list.innerHTML = '<li class="saju-learn-empty">' + T.sajuCardsEmpty + '</li>';
      return;
    }
    list.innerHTML = cards
      .map(function (c) {
        const tags = (c.tags || [])
          .map(function (t) {
            return "<span>" + escapeHtml(t) + "</span>";
          })
          .join("");
        const actions =
          c.status === "pending"
            ? '<div class="saju-learn-card-actions">' +
              '<button type="button" class="btn btn-primary btn-sm btn-saju-confirm" data-card-id="' +
              c.id +
              '">' + T.confirm + '</button> ' +
              '<button type="button" class="btn btn-gray btn-sm btn-saju-delete" data-card-id="' +
              c.id +
              '">' + T.delete + '</button></div>'
            : "";
        const certClass = isSajuCouncilCertified(c) ? " saju-learn-card--council-certified" : "";
        return (
          '<li class="saju-learn-card saju-learn-card--' +
          escapeHtml(c.status) +
          certClass +
          '" data-card-id="' +
          c.id +
          '">' +
          '<div class="saju-learn-card-head"><span>#' +
          c.id +
          "</span> <span>" +
          (c.status === "confirmed" ? T.confirmed : T.pendingReview) +
          "</span>" +
          sajuCouncilCertHtml(c) +
          " <time>" +
          escapeHtml(c.ts || "") +
          '</time> <span class="saju-learn-card-source">' +
          escapeHtml(c.source || "") +
          "</span></div>" +
          "<h4 class=\"saju-learn-card-title\">" +
          escapeHtml(c.title || "") +
          "</h4>" +
          '<p class="saju-learn-card-summary">' +
          escapeHtml(c.summary || "") +
          "</p>" +
          (tags ? '<p class="saju-learn-card-tags">' + tags + "</p>" : "") +
          '<details><summary>' + T.bodyToggle + '</summary><pre class="saju-learn-card-body">' +
          escapeHtml((c.body || "").slice(0, 4000)) +
          "</pre></details>" +
          actions +
          "</li>"
        );
      })
      .join("");
  }

  function updateSajuCardsCount(shown, total) {
    const el = document.getElementById("saju-learn-cards-count");
    if (!el) return;
    const t = total != null ? total : shown;
    el.innerHTML =
      "표시 <strong>" + (shown != null ? shown : "—") + "</strong> / 전체 <strong>" + t + "</strong>건";
  }

  function refreshSajuLearn() {
    return fetch("/api/agents/office/saju-learn.json", {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href =
            "/agents/office/login?next=" + encodeURIComponent(window.location.pathname + window.location.search);
          return null;
        }
        if (!r.ok) return null;
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        if (data.stats) updateSajuStats(data.stats);
        if (Array.isArray(data.cards)) {
          renderSajuCards(data.cards);
          updateSajuCardsCount(
            data.cards.length,
            data.stats && data.stats.total != null ? data.stats.total : data.cards.length
          );
        }
      })
      .catch(function () {});
  }

  const sajuForm = document.getElementById("saju-learn-form");
  if (sajuForm) {
    sajuForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const body = document.getElementById("saju-learn-body");
      const title = document.getElementById("saju-learn-title");
      const statusEl = document.getElementById("saju-learn-status");
      const text = body ? body.value.trim() : "";
      if (!text) return;
      if (statusEl) statusEl.textContent = T.saving;
      fetch("/api/agents/office/saju-learn/ingest", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          title: title ? title.value.trim() : "",
          body: text,
        }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            if (body) body.value = "";
            if (title) title.value = "";
            if (statusEl) statusEl.textContent = T.cardSaved;
            updateSajuStats(data.stats);
            refreshSajuLearn();
            refreshSajuFeed();
            refreshSajuKnowledge();
          } else if (statusEl) {
            statusEl.textContent = data.error || T.saveFail;
          }
        })
        .catch(function () {
          if (statusEl) statusEl.textContent = T.networkErr;
        });
    });
  }

  document.addEventListener("click", function (e) {
    const confirmBtn = e.target.closest(".btn-saju-confirm");
    if (confirmBtn) {
      const id = confirmBtn.getAttribute("data-card-id");
      if (!id) return;
      confirmBtn.disabled = true;
      fetch("/api/agents/office/saju-learn/" + id + "/confirm", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "X-Requested-With": "XMLHttpRequest" }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            updateSajuStats(data.stats);
            refreshSajuLearn();
            refreshSajuFeed();
            refreshSajuKnowledge();
          } else {
            alert(data.error || T.saveFail);
            confirmBtn.disabled = false;
          }
        });
      return;
    }
    const delBtn = e.target.closest(".btn-saju-delete");
    if (delBtn) {
      const id = delBtn.getAttribute("data-card-id");
      if (!id || !confirm(T.deleteConfirm)) return;
      fetch("/api/agents/office/saju-learn/" + id, {
        method: "DELETE",
        credentials: "same-origin",
        headers: csrfHeaders(),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            updateSajuStats(data.stats);
            refreshSajuLearn();
          }
        });
    }
  });

  const sajuRefresh = document.getElementById("saju-learn-refresh-btn");
  if (sajuRefresh) sajuRefresh.addEventListener("click", refreshSajuLearn);

  syncModeCheckboxes();
  startRealtime();
})();


  /* CHIEF-DEV FUNCTIONS */
  let chiefDevFeedWasAtTop = true;
  window.setChiefDevLiveStatus = function(ok) {
    const el = document.getElementById("chief-dev-office-live-status");
    if (!el) return;
    el.classList.toggle("is-on", !!ok);
    el.classList.toggle("is-off", !ok);
    el.textContent = ok ? T.liveOn : T.liveOff;
  };

  window.refreshChiefDevFeed = function(forceScrollTop) {
    const feed = document.getElementById("chief-dev-agent-office-feed");
    if (!feed) return Promise.resolve();
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        rebuildMap();
        const raw =
          data.chief_dev_messages && data.chief_dev_messages.length
            ? data.chief_dev_messages
            : (data.messages || []).filter(function (m) {
                return messageForUnit(m, "chief-dev");
              });
        const msgs = sortMessages(raw);
        if (!msgs.length) {
          feed.innerHTML =
            '<p class="office-empty">아직 수석 개발자 대화 로그가 없습니다.</p>';
        } else {
          feed.innerHTML = msgs.map(renderMessage).join("");
          if (forceScrollTop) feed.scrollTop = 0;
        }
        window.setChiefDevLiveStatus(true);
      })
      .catch(function () {
        window.setChiefDevLiveStatus(false);
      });
  };

  window.refreshChiefDevTasks = function() {
    const list = document.getElementById("chief-dev-task-list");
    const countEl = document.getElementById("chief-dev-task-count");
    if (!list) return Promise.resolve();
    return fetch("/api/agents/office/tasks.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.tasks) return;
        const tasks = data.tasks
          .filter(function (t) {
            return taskForDivision(t, "chief-dev");
          })
          .sort(function (a, b) {
            return (b.id || 0) - (a.id || 0);
          });
        if (countEl) countEl.textContent = String(tasks.length);
        if (!tasks.length) {
          list.innerHTML =
            '<li class="task-empty">수석 개발자 관련 지시가 없습니다.</li>';
          return;
        }
        list.innerHTML = tasks.map(renderTaskItem).join("");
      });
  };

  /* CHIEF-DEV UI HANDLERS */
  document.querySelectorAll("#office-unit-chief-dev .roster-btn--pick").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#office-unit-chief-dev .roster-btn--pick").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      const agentId = btn.getAttribute("data-agent-id") || "";
      renderSkills(agentId, "chief-dev");
    });
  });

  document.querySelectorAll("#office-unit-chief-dev .roster-btn").forEach(function (btn) {
    if (!btn.classList.contains("roster-btn--pick")) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("#office-unit-chief-dev .roster-btn--pick").forEach(function (b) {
          b.classList.remove("is-active");
        });
        document
          .querySelectorAll("#office-unit-chief-dev .roster-list > li:first-child .roster-btn")
          .forEach(function (b) {
            b.classList.add("is-active");
          });
        renderSkills("", "chief-dev");
      });
    }
  });
