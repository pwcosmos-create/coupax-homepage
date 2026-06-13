(function () {
  "use strict";

  function csrfHeaders() {
    var h = { "Content-Type": "application/json" };
    if (window.CSRF_TOKEN) h["X-CSRFToken"] = window.CSRF_TOKEN;
    return h;
  }

  function updateStats(stats) {
    if (!stats) return;
    ["design-learn-total", "design-learn-pending", "design-learn-confirmed", "design-learn-debate"].forEach(
      function (id, i) {
        var el = document.getElementById(id);
        if (!el) return;
        var keys = ["total", "pending", "confirmed", "debate_cards"];
        el.textContent = stats[keys[i]] != null ? stats[keys[i]] : "0";
      }
    );
    var tabLearn = document.getElementById("design-tab-learn-count");
    if (tabLearn) tabLearn.textContent = "(" + (stats.total || 0) + ")";
  }

  function renderCards(cards) {
    var list = document.getElementById("design-learn-card-list");
    if (!list) return;
    if (!cards || !cards.length) {
      list.innerHTML = '<li class="saju-learn-empty">카탈로그 시드 또는 직접 입력으로 플레이북 카드를 만드세요.</li>';
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
              '<button type="button" class="btn btn-primary btn-sm btn-design-confirm" data-card-id="' +
              c.id +
              '">확정</button>' +
              '<button type="button" class="btn btn-gray btn-sm btn-design-delete" data-card-id="' +
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
          "<h4 class=\"saju-learn-card-title\">" +
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

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function refreshLearn() {
    return fetch("/api/agents/office/homepage-design.json", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        updateStats(data.stats);
        renderCards(data.cards);
      });
  }

  function refreshWiki() {
    return fetch("/api/agents/office/knowledge.json?domain=homepage-design", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var wc = document.getElementById("design-wiki-count");
        if (wc) wc.textContent = "Wiki " + (data.wiki_count || 0);
        var tab = document.getElementById("design-tab-wiki-count");
        if (tab) tab.textContent = "(" + (data.wiki_count || 0) + ")";
        var list = document.getElementById("design-wiki-card-list");
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
    document.querySelectorAll(".btn-design-confirm").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-card-id");
        var statusEl = document.getElementById("design-learn-status");
        fetch("/api/agents/office/homepage-design/confirm/" + id, {
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
    document.querySelectorAll(".btn-design-delete").forEach(function (btn) {
      btn.onclick = function () {
        var id = btn.getAttribute("data-card-id");
        fetch("/api/agents/office/homepage-design/delete/" + id, {
          method: "POST",
          credentials: "same-origin",
          headers: csrfHeaders(),
          body: "{}",
        })
          .then(function () {
            refreshLearn();
          });
      };
    });
  }

  var form = document.getElementById("design-learn-form");
  if (form) {
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var body = document.getElementById("design-learn-body");
      var title = document.getElementById("design-learn-title");
      var statusEl = document.getElementById("design-learn-status");
      fetch("/api/agents/office/homepage-design/ingest", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: JSON.stringify({ body: body.value, title: title.value }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (statusEl) statusEl.textContent = data.ok ? "저장됨 #" + (data.card && data.card.id) : data.error || "실패";
          if (data.ok) {
            body.value = "";
            refreshLearn();
          }
        });
    });
  }

  var webBtn = document.getElementById("design-web-research-btn");
  if (webBtn) {
    webBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("design-learn-status");
      if (statusEl) statusEl.textContent = "웹 검색·토론 중…";
      fetch("/api/agents/office/homepage-design/web-research-debate", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: JSON.stringify({ max: 1 }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!statusEl) return;
          if (!data.ok) {
            statusEl.textContent = data.error || (data.result && data.result.errors && data.result.errors[0]) || "실패";
            return;
          }
          var items = (data.result && data.result.items) || [];
          if (items.length) {
            statusEl.textContent =
              "웹리서치 #" + items[0].card_id + " · 출처 " + (items[0].refs || 0) + "건";
          } else {
            statusEl.textContent = "신규 주제 없음";
          }
          refreshLearn();
          refreshWiki();
          refreshDebateTopics();
        });
    });
  }

  var seedBtn = document.getElementById("design-seed-catalog-btn");
  if (seedBtn) {
    seedBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("design-learn-status");
      if (statusEl) statusEl.textContent = "시드 중…";
      fetch("/api/agents/office/homepage-design/seed-catalog", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: "{}",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (statusEl) statusEl.textContent = data.ok ? "카탈로그·토론 반영" : data.error || "실패";
          refreshLearn();
          refreshWiki();
        });
    });
  }

  var refreshBtn = document.getElementById("design-learn-refresh-btn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      refreshLearn();
      refreshWiki();
    });
  }

  document.querySelectorAll("#office-unit-homepage-design .office-knowledge-tab").forEach(function (tab) {
    tab.addEventListener("click", function () {
      var pane = tab.getAttribute("data-tab");
      document.querySelectorAll("#office-unit-homepage-design .office-knowledge-tab").forEach(function (t) {
        t.classList.toggle("is-active", t === tab);
        t.setAttribute("aria-selected", t === tab ? "true" : "false");
      });
      document.querySelectorAll("#office-unit-homepage-design .office-knowledge-panel-pane").forEach(function (p) {
        var show = p.getAttribute("data-pane") === pane;
        p.hidden = !show;
        p.classList.toggle("is-active", show);
      });
    });
  });

  function refreshDebateTopics() {
    return fetch("/api/agents/office/homepage-design/debate-topics.json", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var badge = document.getElementById("design-debate-auto-badge");
        if (badge) {
          badge.textContent = data.auto_enabled ? "자동 ON · " + (data.max_per_run || 1) + "건/회" : "자동 OFF";
        }
        var pending = document.getElementById("design-debate-pending-list");
        if (pending) {
          var pl = data.pending || [];
          pending.innerHTML = pl.length
            ? pl
                .map(function (p) {
                  return "<li>" + escapeHtml(p.title || p.catalog_seed || "") + "</li>";
                })
                .join("")
            : '<li class="wiki-empty">대기 주제 없음 (곧 자동 생성)</li>';
        }
        var recent = document.getElementById("design-debate-recent-list");
        if (recent) {
          var rl = data.recent || [];
          recent.innerHTML = rl.length
            ? rl
                .map(function (t) {
                  return (
                    "<li>" +
                    escapeHtml(t.title || "") +
                    (t.auto ? ' <span class="office-design-auto-tag">auto</span>' : "") +
                    "</li>"
                  );
                })
                .join("")
            : '<li class="wiki-empty">아직 없음</li>';
        }
      })
      .catch(function () {});
  }

  bindCardActions();
  if (document.getElementById("office-unit-homepage-design")) {
    window.refreshDesignLearn = refreshLearn;
    window.refreshDesignWiki = refreshWiki;
    window.refreshDesignDebateTopics = refreshDebateTopics;
    refreshDebateTopics();
  }
})();
