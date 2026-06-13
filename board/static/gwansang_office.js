(function () {
  "use strict";

  function csrfHeaders() {
    var h = { "Content-Type": "application/json" };
    if (window.CSRF_TOKEN) h["X-CSRFToken"] = window.CSRF_TOKEN;
    return h;
  }

  function updateStats(stats) {
    if (!stats) return;
    ["gwansang-learn-total", "gwansang-learn-pending", "gwansang-learn-confirmed"].forEach(function (id, i) {
      var el = document.getElementById(id);
      if (!el) return;
      var keys = ["total", "pending", "confirmed"];
      el.textContent = stats[keys[i]] != null ? stats[keys[i]] : "0";
    });
    var tabLearn = document.getElementById("gwansang-tab-learn-count");
    if (tabLearn) tabLearn.textContent = "(" + (stats.total || 0) + ")";
    var badge = document.querySelector(".gwansang-learn-badge");
    if (badge) badge.textContent = (stats.pending || 0) + " 대기";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderCards(cards) {
    var list = document.getElementById("gwansang-learn-card-list");
    if (!list) return;
    if (!cards || !cards.length) {
      list.innerHTML =
        '<li class="saju-learn-empty">카탈로그 시드 또는 젬마 갭 제작으로 관상 카드를 만드세요.</li>';
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
              '<button type="button" class="btn btn-primary btn-sm btn-gwansang-confirm" data-card-id="' +
              c.id +
              '">확정</button>' +
              '<button type="button" class="btn btn-gray btn-sm btn-gwansang-delete" data-card-id="' +
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
    return fetch("/api/agents/office/gwansang-learn.json", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        updateStats(data.stats);
        renderCards(data.cards);
      });
  }

  function refreshWiki() {
    return fetch("/api/agents/office/knowledge.json?domain=gwansang-learn", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var wc = document.getElementById("gwansang-wiki-count");
        if (wc) wc.textContent = "Wiki " + (data.wiki_count || 0);
        var tab = document.getElementById("gwansang-tab-wiki-count");
        if (tab) tab.textContent = "(" + (data.wiki_count || 0) + ")";
        var list = document.getElementById("gwansang-wiki-card-list");
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
    document.querySelectorAll(".btn-gwansang-confirm").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-card-id");
        var statusEl = document.getElementById("gwansang-learn-status");
        fetch("/api/agents/office/gwansang-learn/confirm/" + id, {
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
    document.querySelectorAll(".btn-gwansang-delete").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-card-id");
        fetch("/api/agents/office/gwansang-learn/delete/" + id, {
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

  var form = document.getElementById("gwansang-learn-form");
  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var body = document.getElementById("gwansang-learn-body");
      var title = document.getElementById("gwansang-learn-title");
      var statusEl = document.getElementById("gwansang-learn-status");
      fetch("/api/agents/office/gwansang-learn/ingest", {
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

  var seedBtn = document.getElementById("gwansang-seed-catalog-btn");
  if (seedBtn) {
    seedBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("gwansang-learn-status");
      if (statusEl) statusEl.textContent = "카탈로그 시드 중…";
      fetch("/api/agents/office/gwansang-learn/seed-catalog", {
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
            "시드 +" + (r.added || 0) + " ↻" + (r.synced || 0) + " · 확정 " + (data.stats && data.stats.confirmed);
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var gapBtn = document.getElementById("gwansang-compose-gap-btn");
  if (gapBtn) {
    gapBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("gwansang-learn-status");
      if (statusEl) statusEl.textContent = "갭 제작 중…";
      fetch("/api/agents/office/gwansang-learn/compose-gap", {
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

  var refreshBtn = document.getElementById("gwansang-learn-refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      refreshLearn();
      refreshWiki();
    });
  }

  document.querySelectorAll("#office-unit-gwansang-learn .office-knowledge-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      var pane = tab.getAttribute("data-tab");
      document.querySelectorAll("#office-unit-gwansang-learn .office-knowledge-tab").forEach(function (t) {
        var on = t.getAttribute("data-tab") === pane;
        t.classList.toggle("is-active", on);
        t.setAttribute("aria-selected", on ? "true" : "false");
      });
      document.querySelectorAll("#office-unit-gwansang-learn .office-knowledge-panel-pane").forEach(function (p) {
        var on = p.getAttribute("data-pane") === pane;
        p.classList.toggle("is-active", on);
        p.hidden = !on;
      });
      if (pane === "wiki") refreshWiki();
    });
  });

  bindCardActions();
  window.refreshGwansangLearn = refreshLearn;
  window.refreshGwansangWiki = refreshWiki;
})();
