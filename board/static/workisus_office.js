(function () {
  "use strict";

  function csrfHeaders() {
    var h = { "Content-Type": "application/json" };
    if (window.CSRF_TOKEN) h["X-CSRFToken"] = window.CSRF_TOKEN;
    return h;
  }

  function updateStats(stats) {
    if (!stats) return;
    ["workisus-learn-total", "workisus-learn-pending", "workisus-learn-confirmed"].forEach(function (id, i) {
      var el = document.getElementById(id);
      if (!el) return;
      var keys = ["total", "pending", "confirmed"];
      el.textContent = stats[keys[i]] != null ? stats[keys[i]] : "0";
    });
    var tabLearn = document.getElementById("workisus-tab-learn-count");
    if (tabLearn) tabLearn.textContent = "(" + (stats.total || 0) + ")";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderCards(cards) {
    var list = document.getElementById("workisus-learn-card-list");
    if (!list) return;
    if (!cards || !cards.length) {
      list.innerHTML =
        '<li class="saju-learn-empty">카탈로그 시드 또는 직접 입력으로 원키스 US 카드를 만드세요.</li>';
      return;
    }
    list.innerHTML = cards
      .map(function (c) {
        var tags = (c.tags || [])
          .map(function (t) {
            return "<span>" + escapeHtml(t) + "</span>";
          })
          .join("");
        var actions =
          c.status === "pending"
            ? '<div class="saju-learn-card-actions">' +
              '<button type="button" class="btn btn-primary btn-sm btn-workisus-confirm" data-card-id="' +
              c.id +
              '">확정</button>' +
              '<button type="button" class="btn btn-gray btn-sm btn-workisus-delete" data-card-id="' +
              c.id +
              '">삭제</button></div>'
            : "";
        return (
          '<li class="saju-learn-card saju-learn-card--' +
          escapeHtml(c.status || "pending") +
          '" data-card-id="' +
          c.id +
          '">' +
          '<div class="saju-learn-card-head"><span class="saju-learn-card-id">#' +
          c.id +
          '</span><span class="saju-learn-card-status">' +
          (c.status === "confirmed" ? "확정" : "검수 대기") +
          "</span><time>" +
          escapeHtml(c.ts || "") +
          "</time></div>" +
          '<h4 class="saju-learn-card-title">' +
          escapeHtml(c.title || "") +
          "</h4>" +
          '<p class="saju-learn-card-summary">' +
          escapeHtml(c.summary || "") +
          "</p>" +
          (tags ? '<p class="saju-learn-card-tags">' + tags + "</p>" : "") +
          "<details><summary>본문</summary><pre class=\"saju-learn-card-body\">" +
          escapeHtml((c.body || "").slice(0, 4000)) +
          "</pre></details>" +
          (c.wiki_id ? '<p class="wiki-card-meta">' + escapeHtml(c.wiki_id) + "</p>" : "") +
          actions +
          "</li>"
        );
      })
      .join("");
    bindCardActions();
  }

  function refreshLearn() {
    return fetch("/api/agents/office/workisus-chasu.json", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        updateStats(data.stats);
        renderCards(data.cards);
      });
  }

  function refreshWiki() {
    return fetch("/api/agents/office/knowledge.json?domain=workisus-chasu", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var wc = document.getElementById("workisus-wiki-count");
        if (wc) wc.textContent = "Wiki " + (data.wiki_count || 0);
        var tab = document.getElementById("workisus-tab-wiki-count");
        if (tab) tab.textContent = "(" + (data.wiki_count || 0) + ")";
        var list = document.getElementById("workisus-wiki-card-list");
        if (!list) return;
        var wiki = data.recent_wiki || [];
        if (!wiki.length) {
          list.innerHTML = '<li class="wiki-empty">확정 카드가 Wiki에 쌓입니다.</li>';
          return;
        }
        list.innerHTML = wiki
          .slice()
          .reverse()
          .map(function (w) {
            return (
              '<li class="wiki-card-item"><span class="wiki-card-id">' +
              escapeHtml(w.id || "") +
              '</span><strong class="wiki-card-title">' +
              escapeHtml(w.title || "") +
              '</strong><p class="wiki-card-summary">' +
              escapeHtml(w.summary || "") +
              "</p></li>"
            );
          })
          .join("");
      });
  }

  function bindCardActions() {
    document.querySelectorAll(".btn-workisus-confirm").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-card-id");
        var statusEl = document.getElementById("workisus-learn-status");
        fetch("/api/agents/office/workisus-chasu/confirm/" + id, {
          method: "POST",
          credentials: "same-origin",
          headers: csrfHeaders(),
          body: "{}",
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (statusEl) statusEl.textContent = data.ok ? "확정됨" : data.error || "실패";
            refreshLearn();
            refreshWiki();
          });
      };
    });
    document.querySelectorAll(".btn-workisus-delete").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-card-id");
        fetch("/api/agents/office/workisus-chasu/delete/" + id, {
          method: "POST",
          credentials: "same-origin",
          headers: csrfHeaders(),
          body: "{}",
        }).then(function () {
          refreshLearn();
        });
      };
    });
  }

  var form = document.getElementById("workisus-learn-form");
  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var body = document.getElementById("workisus-learn-body");
      var title = document.getElementById("workisus-learn-title");
      var statusEl = document.getElementById("workisus-learn-status");
      fetch("/api/agents/office/workisus-chasu/ingest", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: JSON.stringify({ body: body.value, title: title.value }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (statusEl)
            statusEl.textContent = data.ok ? "저장됨 #" + (data.card && data.card.id) : data.error || "실패";
          if (data.ok) {
            body.value = "";
            refreshLearn();
          }
        });
    });
  }

  var gapBtn = document.getElementById("workisus-compose-gap-btn");
  if (gapBtn) {
    gapBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("workisus-learn-status");
      if (statusEl) statusEl.textContent = "갭 제작 중…";
      fetch("/api/agents/office/workisus-chasu/compose-gap", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: "{}",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!statusEl) return;
          if (!data.ok) {
            statusEl.textContent = data.error || "실패";
            return;
          }
          var c = data.composed;
          statusEl.textContent = c
            ? "제작 #" + c.card_id + " " + (c.title || "").slice(0, 24)
            : "갭 없음 · pack " + (data.pack_count || "");
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var atrRlBtn = document.getElementById("workisus-atr-rl-btn");
  if (atrRlBtn) {
    atrRlBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("workisus-learn-status");
      if (statusEl) statusEl.textContent = "ATR RL 제작 중…";
      fetch("/api/agents/office/workisus-chasu/atr-rl-autofill", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: JSON.stringify({ max_add: 3 }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!statusEl) return;
          if (!data.ok) {
            statusEl.textContent = data.error || "실패";
            return;
          }
          var r = data.result || {};
          var added = r.added || [];
          statusEl.textContent =
            "ATR RL +" + added.length + " · 확정 " + (data.stats && data.stats.confirmed);
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var atrBtn = document.getElementById("workisus-seed-atr-btn");
  if (atrBtn) {
    atrBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("workisus-learn-status");
      if (statusEl) statusEl.textContent = "ATR 카드 시드 중…";
      fetch("/api/agents/office/workisus-chasu/seed-atr", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: "{}",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!statusEl) return;
          if (!data.ok) {
            statusEl.textContent = data.error || "실패";
            return;
          }
          var r = data.result || {};
          statusEl.textContent =
            "ATR +" + (r.added || 0) + " ↻" + (r.synced || 0) + " · 확정 " + (data.stats && data.stats.confirmed);
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var errBtn = document.getElementById("workisus-seed-error-btn");
  if (errBtn) {
    errBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("workisus-learn-status");
      if (statusEl) statusEl.textContent = "오류카드 시드 중…";
      fetch("/api/agents/office/workisus-chasu/seed-errors", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: "{}",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!statusEl) return;
          if (!data.ok) {
            statusEl.textContent = data.error || "실패";
            return;
          }
          var e = data.result || {};
          statusEl.textContent =
            "오류 +" + (e.added || 0) + " ↻" + (e.synced || 0) + " · 확정 " + (data.stats && data.stats.confirmed);
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var seedBtn = document.getElementById("workisus-seed-catalog-btn");
  if (seedBtn) {
    seedBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("workisus-learn-status");
      if (statusEl) statusEl.textContent = "시드 중…";
      fetch("/api/agents/office/workisus-chasu/seed-catalog", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: "{}",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (statusEl) {
            var er = data.errors || {};
            statusEl.textContent = data.ok
              ? "카탈로그+오류 반영 · 확정 " + (data.stats && data.stats.confirmed) +
                " (오류 +" + (er.added || 0) + ")"
              : data.error || "실패";
          }
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var refreshBtn = document.getElementById("workisus-learn-refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      refreshLearn();
      refreshWiki();
    });
  }

  document.querySelectorAll("#office-unit-workisus-chasu .office-knowledge-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      var pane = tab.getAttribute("data-tab");
      document.querySelectorAll("#office-unit-workisus-chasu .office-knowledge-tab").forEach(function (t) {
        t.classList.toggle("is-active", t === tab);
        t.setAttribute("aria-selected", t === tab ? "true" : "false");
      });
      document.querySelectorAll("#office-unit-workisus-chasu .office-knowledge-panel-pane").forEach(function (p) {
        var show = p.getAttribute("data-pane") === pane;
        p.hidden = !show;
        p.classList.toggle("is-active", show);
      });
    });
  });

  bindCardActions();
  if (document.getElementById("office-unit-workisus-chasu")) {
    window.refreshWorkisusLearn = refreshLearn;
    window.refreshWorkisusWiki = refreshWiki;
  }
})();
