(function () {
  "use strict";

  function csrfHeaders(extra) {
    var h = extra || {};
    if (window.CSRF_TOKEN) {
      h["X-CSRFToken"] = window.CSRF_TOKEN;
    }
    return h;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderRl(rl) {
    if (!rl) return;
    var ts = document.getElementById("kiwoom-rl-ts");
    if (ts) ts.textContent = rl.last_run || rl.last_train || "";
    var lead = document.getElementById("kiwoom-rl-lead");
    if (lead) {
      lead.textContent =
        "ε=" +
        (rl.epsilon != null ? rl.epsilon : "—") +
        " · 학습률 " +
        (rl.learning_rate != null ? rl.learning_rate : "—") +
        " · PASS " +
        ((rl.stats && rl.stats.pass) || 0) +
        " · FAIL " +
        ((rl.stats && rl.stats.fail) || 0);
    }
    var chips = document.getElementById("kiwoom-rl-chips");
    if (chips && rl.top_categories && rl.top_categories.length) {
      chips.innerHTML = rl.top_categories
        .map(function (x) {
          return (
            '<span class="stock-rl-chip">' +
            escapeHtml(x.category) +
            " <strong>" +
            escapeHtml(String(x.weight)) +
            "</strong></span>"
          );
        })
        .join("");
    }
    var statsEl = document.getElementById("kiwoom-rl-stats");
    if (statsEl && rl.recent && rl.recent.length) {
      statsEl.innerHTML = rl.recent
        .map(function (h) {
          var ok = h.success ? "✓" : "✗";
          return (
            "<li>" +
            ok +
            " " +
            escapeHtml((h.title || "").slice(0, 36)) +
            " <small>" +
            escapeHtml(h.category || "") +
            "</small></li>"
          );
        })
        .join("");
    }
  }

  function updateStats(st) {
    if (!st) return;
    ["kiwoom-learn-pending", "kiwoom-learn-confirmed"].forEach(function (id, i) {
      var el = document.getElementById(id);
      if (!el) return;
      var keys = ["pending", "confirmed"];
      el.textContent = String(st[keys[i]] != null ? st[keys[i]] : "");
    });
    var learnTab = document.getElementById("kiwoom-tab-learn-count");
    if (learnTab) learnTab.textContent = "(" + (st.total != null ? st.total : 0) + ")";
    var badge = document.querySelector(".kiwoom-learn-badge");
    if (badge) badge.textContent = (st.pending || 0) + " 대기";
  }

  function renderCards(cards) {
    var list = document.getElementById("kiwoom-learn-card-list");
    if (!list) return;
    if (!cards || !cards.length) {
      list.innerHTML = '<li class="saju-learn-empty">전략·메모를 붙여 넣어 주세요.</li>';
      return;
    }
    list.innerHTML = cards
      .map(function (c) {
        var tags = (c.tags || [])
          .map(function (t) {
            return "<span>" + escapeHtml(t) + "</span>";
          })
          .join("");
        var council = "";
        if (c.council_agents && c.council_agents.length) {
          council =
            '<p class="kiwoom-council-badges" title="9젬마 협업 검수">' +
            c.council_agents
              .map(function (aid) {
                return '<span class="kiwoom-council-badge">' + escapeHtml(aid.replace("kiwoom_", "")) + "</span>";
              })
              .join("") +
            "</p>";
        }
        var actions =
          c.status === "pending"
            ? '<div class="saju-learn-card-actions">' +
              '<button type="button" class="btn btn-primary btn-sm btn-kiwoom-confirm" data-card-id="' +
              c.id +
              '">확정</button> ' +
              '<button type="button" class="btn btn-gray btn-sm btn-kiwoom-delete" data-card-id="' +
              c.id +
              '">삭제</button></div>'
            : "";
        return (
          '<li class="saju-learn-card saju-learn-card--' +
          escapeHtml(c.status) +
          '" data-card-id="' +
          c.id +
          '">' +
          '<div class="saju-learn-card-head"><span>#' +
          c.id +
          "</span> <span>" +
          (c.status === "confirmed" ? "확정" : "검수 대기") +
          "</span> <time>" +
          escapeHtml(c.ts || "") +
          "</time></div>" +
          "<h4>" +
          escapeHtml(c.title || "") +
          "</h4><p class=\"saju-learn-card-summary\">" +
          escapeHtml(c.summary || "") +
          "</p>" +
          (tags ? '<p class="saju-learn-card-tags">' + tags + "</p>" : "") +
          council +
          "<details><summary>본문</summary><pre class=\"saju-learn-card-body\">" +
          escapeHtml((c.body || "").slice(0, 4000)) +
          "</pre></details>" +
          (c.wiki_id
            ? '<p class="wiki-card-meta"><span class="wiki-card-link">[wiki] ' +
              escapeHtml(c.wiki_id) +
              "</span></p>"
            : "") +
          actions +
          "</li>"
        );
      })
      .join("");
  }

  function refreshLearn() {
    return fetch("/api/agents/office/kiwoom-chasu.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        updateStats(data.stats);
        renderCards(data.cards);
        renderRl(data.rl);
      })
      .catch(function () {});
  }

  function refreshKnowledge() {
    return fetch("/api/agents/office/knowledge.json?domain=kiwoom-chasu", {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var wc = document.getElementById("kiwoom-wiki-count");
        if (wc && data) wc.textContent = "10_Wiki " + (data.wiki_count || 0);
        var wikiTab = document.getElementById("kiwoom-tab-wiki-count");
        if (wikiTab && data) wikiTab.textContent = "(" + (data.wiki_count || 0) + ")";
        var list = document.getElementById("kiwoom-wiki-card-list");
        if (!list || !data || !data.recent_wiki) return;
        var wiki = data.recent_wiki.slice().reverse();
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

  function renderSkills(agentId) {
    var agents = window.KIWOM_OFFICE_AGENTS || [];
    var panel = document.getElementById("kiwoom-skills-list");
    var title = document.getElementById("kiwoom-skills-panel-title");
    var hint = document.getElementById("kiwoom-skills-panel-hint");
    if (!panel) return;
    var a = agents.find(function (x) {
      return x.id === agentId;
    });
    if (!a) {
      if (title) title.textContent = "에이전트 스킬";
      if (hint) hint.textContent = "왼쪽 명단에서 에이전트를 선택하세요.";
      panel.innerHTML = "";
      return;
    }
    if (title) title.textContent = (a.emoji || "") + " " + a.name + " 스킬";
    if (hint) hint.textContent = a.role || "";
    var skills = a.skills || [];
    panel.innerHTML = skills.length
      ? skills
          .map(function (s) {
            return (
              "<li><strong>" +
              escapeHtml(s.title) +
              "</strong><p>" +
              escapeHtml(s.summary) +
              "</p></li>"
            );
          })
          .join("")
      : "<li>등록된 스킬 없음</li>";
  }

  var form = document.getElementById("kiwoom-learn-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var body = document.getElementById("kiwoom-learn-body");
      var title = document.getElementById("kiwoom-learn-title");
      var statusEl = document.getElementById("kiwoom-learn-status");
      var text = body ? body.value.trim() : "";
      if (!text) return;
      if (statusEl) statusEl.textContent = "저장 중…";
      fetch("/api/agents/office/kiwoom-chasu/ingest", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ title: title ? title.value.trim() : "", body: text }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            if (body) body.value = "";
            if (title) title.value = "";
            if (statusEl) statusEl.textContent = "저장됨";
            updateStats(data.stats);
            refreshLearn();
            refreshKnowledge();
          } else if (statusEl) statusEl.textContent = data.error || "실패";
        });
    });
  }

  document.addEventListener("click", function (e) {
    var confirmBtn = e.target.closest(".btn-kiwoom-confirm");
    if (confirmBtn) {
      var id = confirmBtn.getAttribute("data-card-id");
      if (!id) return;
      confirmBtn.disabled = true;
      fetch("/api/agents/office/kiwoom-chasu/" + id + "/confirm", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "X-Requested-With": "XMLHttpRequest" }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            updateStats(data.stats);
            refreshLearn();
            refreshKnowledge();
          } else {
            alert(data.error || "실패");
            confirmBtn.disabled = false;
          }
        });
      return;
    }
    var delBtn = e.target.closest(".btn-kiwoom-delete");
    if (delBtn) {
      var delId = delBtn.getAttribute("data-card-id");
      if (!delId || !confirm("삭제할까요?")) return;
      fetch("/api/agents/office/kiwoom-chasu/" + delId, {
        method: "DELETE",
        credentials: "same-origin",
        headers: csrfHeaders(),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            updateStats(data.stats);
            refreshLearn();
          }
        });
    }
  });

  document.querySelectorAll("#kiwoom-roster-list .roster-btn--pick").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll("#kiwoom-roster-list .roster-btn--pick").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      renderSkills(btn.getAttribute("data-agent-id") || "");
    });
  });

  var composeNextBtn = document.getElementById("kiwoom-compose-next-btn");
  if (composeNextBtn) {
    composeNextBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("kiwoom-learn-status");
      composeNextBtn.disabled = true;
      if (statusEl) statusEl.textContent = "제목 생성·협업 제작 중…";
      fetch("/api/agents/office/kiwoom-chasu/compose-next", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "X-Requested-With": "XMLHttpRequest" }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          composeNextBtn.disabled = false;
          if (data.ok && data.card) {
            if (statusEl) statusEl.textContent = "추가 #" + data.card.card_id + " · " + (data.card.title || "").slice(0, 40);
            updateStats(data.stats);
            refreshLearn();
            refreshKnowledge();
          } else if (statusEl) statusEl.textContent = data.error || data.message || "완료";
        })
        .catch(function () {
          composeNextBtn.disabled = false;
          if (statusEl) statusEl.textContent = "요청 실패";
        });
    });
  }

  var seedErrBtn = document.getElementById("kiwoom-seed-error-cards-btn");
  if (seedErrBtn) {
    seedErrBtn.addEventListener("click", function () {
      var statusEl = document.getElementById("kiwoom-learn-status");
      if (!confirm("누락된 「카드 제작 오류 해결」 meta 카드를 9젬마 협업으로 제작할까요?")) return;
      seedErrBtn.disabled = true;
      if (statusEl) statusEl.textContent = "오류 해결 카드 제작 중…";
      fetch("/api/agents/office/kiwoom-chasu/seed-error-cards", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "X-Requested-With": "XMLHttpRequest" }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          seedErrBtn.disabled = false;
          if (data.ok) {
            var n = (data.result && data.result.created) || 0;
            var skip = (data.result && data.result.skipped_duplicate) || 0;
            if (statusEl) {
              statusEl.textContent =
                n > 0 ? "추가 " + n + "장 · Wiki 반영" : "신규 없음(중복 " + skip + "건 생략)";
            }
            updateStats(data.stats);
            refreshLearn();
            refreshKnowledge();
          } else if (statusEl) statusEl.textContent = data.error || "실패";
        })
        .catch(function () {
          seedErrBtn.disabled = false;
          if (statusEl) statusEl.textContent = "요청 실패";
        });
    });
  }

  var refreshBtn = document.getElementById("kiwoom-learn-refresh-btn");
  if (refreshBtn) refreshBtn.addEventListener("click", refreshLearn);
  var officeRefresh = document.getElementById("kiwoom-office-refresh-btn");
  if (officeRefresh) {
    officeRefresh.addEventListener("click", function () {
      refreshLearn();
      refreshKnowledge();
      location.reload();
    });
  }

  function renderAccountSummary(summary) {
    var box = document.getElementById("kiwoom-account-summary");
    if (!box) return;
    if (!summary || !summary.trim()) {
      box.innerHTML = '<p class="kiwoom-account-empty">아직 잔고가 등록되지 않았습니다.</p>';
      return;
    }
    var lines = summary.split("\n").filter(Boolean);
    box.innerHTML =
      '<ul class="kiwoom-account-summary-list">' +
      lines.map(function (l) {
        return "<li>" + escapeHtml(l) + "</li>";
      }).join("") +
      "</ul>";
  }

  function refreshAccount() {
    return fetch("/api/agents/office/kiwoom-account.json", {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        renderAccountSummary(data.summary || "");
        var badge = document.getElementById("kiwoom-account-stale-badge");
        if (badge && data.stats) {
          if (!data.stats.has_data) {
            badge.textContent = "미등록";
            badge.classList.add("is-stale");
          } else if (data.stats.stale) {
            badge.textContent = "갱신 필요";
            badge.classList.add("is-stale");
          } else {
            badge.textContent = "연동됨";
            badge.classList.remove("is-stale");
          }
        }
      })
      .catch(function () {});
  }

  var acctForm = document.getElementById("kiwoom-account-form");
  if (acctForm) {
    acctForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var statusEl = document.getElementById("kiwoom-account-status");
      var posEl = document.getElementById("kiwoom-acct-positions");
      var positions = null;
      if (posEl && posEl.value.trim()) {
        try {
          positions = JSON.parse(posEl.value.trim());
        } catch (err) {
          if (statusEl) statusEl.textContent = "보유 JSON 형식 오류";
          return;
        }
      }
      var body = {
        broker: document.getElementById("kiwoom-acct-broker").value.trim(),
        account_mask: document.getElementById("kiwoom-acct-mask").value.trim(),
        deposit: document.getElementById("kiwoom-acct-deposit").value.trim(),
        orderable: document.getElementById("kiwoom-acct-orderable").value.trim(),
        eval_amount: document.getElementById("kiwoom-acct-eval").value.trim(),
        profit_loss: document.getElementById("kiwoom-acct-pl").value.trim(),
        note: document.getElementById("kiwoom-acct-note").value.trim(),
        positions: positions,
      };
      if (statusEl) statusEl.textContent = "저장 중…";
      fetch("/api/agents/office/kiwoom-account", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(body),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok) {
            if (statusEl) statusEl.textContent = "계좌 젬마 반영됨";
            refreshAccount();
          } else if (statusEl) statusEl.textContent = data.error || "실패";
        });
    });
  }

  function scrollToLearnCard(cardId) {
    if (!cardId) return;
    var row = document.querySelector('.saju-learn-card[data-card-id="' + cardId + '"]');
    if (!row) return;
    var tabBtn = document.querySelector(
      '#office-unit-kiwoom-chasu .office-knowledge-tab[data-tab="learn"], #kiwoom-knowledge-hub .office-knowledge-tab[data-tab="learn"]'
    );
    if (tabBtn) tabBtn.click();
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.classList.add("kiwoom-learn-highlight");
    setTimeout(function () {
      row.classList.remove("kiwoom-learn-highlight");
    }, 2400);
  }

  function renderLearnPath(path) {
    if (!path) return;
    var pct = document.getElementById("kiwoom-learn-path-pct");
    if (pct) pct.textContent = (path.progress_pct != null ? path.progress_pct : 0) + "%";
    var nextEl = document.getElementById("kiwoom-learn-path-next");
    if (nextEl) {
      nextEl.textContent = path.next_step
        ? "다음 단계: " + path.next_step + " — 아래에서 카드 본문을 읽고 실습하세요."
        : "모든 단계를 완료했습니다. monitor 카드로 실전 로그를 계속 갱신하세요.";
    }
    var list = document.getElementById("kiwoom-learn-path-list");
    if (!list || !path.steps) return;
    list.innerHTML = path.steps
      .map(function (s) {
        var done = s.status === "done";
        var active = path.next_step === s.step;
        var statusLabel = done ? "완료" : s.status === "missing_card" ? "카드 없음" : "학습 중";
        var practice = (s.practice || [])
          .map(function (p) {
            return "<li>" + escapeHtml(p) + "</li>";
          })
          .join("");
        return (
          '<li class="kiwoom-learn-path-item' +
          (done ? " is-done" : "") +
          (active ? " is-active" : "") +
          '" data-step="' +
          s.step +
          '">' +
          '<div class="kiwoom-learn-path-item-head">' +
          "<strong>단계 " +
          s.step +
          "</strong> " +
          "<span>" +
          escapeHtml(s.title) +
          "</span> " +
          '<span class="kiwoom-learn-badge">' +
          escapeHtml(statusLabel) +
          "</span>" +
          "</div>" +
          (s.summary ? '<p class="saju-learn-summary">' + escapeHtml(s.summary) + "</p>" : "") +
          (practice ? '<ul class="kiwoom-learn-path-practice">' + practice + "</ul>" : "") +
          '<div class="kiwoom-learn-path-actions">' +
          (s.card_id
            ? '<button type="button" class="btn btn-gray btn-sm btn-kiwoom-path-open" data-card-id="' +
              s.card_id +
              '">카드 보기</button>'
            : "") +
          (done
            ? ""
            : '<button type="button" class="btn btn-primary btn-sm btn-kiwoom-path-done" data-step="' +
              s.step +
              '">실습 완료</button>') +
          "</div></li>"
        );
      })
      .join("");
    list.querySelectorAll(".btn-kiwoom-path-open").forEach(function (btn) {
      btn.addEventListener("click", function () {
        scrollToLearnCard(btn.getAttribute("data-card-id"));
      });
    });
    list.querySelectorAll(".btn-kiwoom-path-done").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var step = btn.getAttribute("data-step");
        btn.disabled = true;
        fetch("/api/agents/office/kiwoom-chasu/learn-path/" + step + "/complete", {
          method: "POST",
          headers: csrfHeaders({ "Content-Type": "application/json" }),
        })
          .then(function (r) {
            return r.json();
          })
          .then(function (data) {
            if (data.path) renderLearnPath(data.path);
            btn.disabled = false;
          })
          .catch(function () {
            btn.disabled = false;
          });
      });
    });
  }

  function refreshLearnPath() {
    fetch("/api/agents/office/kiwoom-chasu/learn-path.json", { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(renderLearnPath)
      .catch(function () {});
  }

  function initKnowledgeTabs(scope) {
    var root = scope ? document.getElementById(scope) : document;
    if (!root) return;
    root.querySelectorAll(".office-knowledge-tabs").forEach(function (tabs) {
      var panel = tabs.closest(".office-knowledge-hub, .gemma-knowledge-panel");
      if (!panel) return;
      tabs.querySelectorAll(".office-knowledge-tab").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var tab = btn.getAttribute("data-tab");
          tabs.querySelectorAll(".office-knowledge-tab").forEach(function (b) {
            var on = b === btn;
            b.classList.toggle("is-active", on);
            b.setAttribute("aria-selected", on ? "true" : "false");
          });
          panel.querySelectorAll(".office-knowledge-panel-pane").forEach(function (pane) {
            var show = pane.getAttribute("data-pane") === tab;
            pane.hidden = !show;
            pane.classList.toggle("is-active", show);
          });
        });
      });
    });
  }

  initKnowledgeTabs("office-unit-kiwoom-chasu");
  initKnowledgeTabs("kiwoom-knowledge-hub");
  refreshAccount();
  refreshLearnPath();
  window.refreshLearn = refreshLearn;
  window.refreshAccount = refreshAccount;
  window.refreshLearnPath = refreshLearnPath;
  setInterval(function () {
    if (document.getElementById("office-unit-kiwoom-chasu") && !document.getElementById("office-unit-kiwoom-chasu").hidden) {
      refreshLearn();
      refreshAccount();
      refreshLearnPath();
    }
  }, 8000);
})();
