(function () {
  function csrfHeaders() {
    var h = { "Content-Type": "application/json" };
    var el = document.querySelector('meta[name="csrf-token"]');
    if (el && el.content) h["X-CSRFToken"] = el.content;
    var inp = document.querySelector('input[name="csrf_token"]');
    if (inp && inp.value) h["X-CSRFToken"] = inp.value;
    return h;
  }

  function bindWebResearch(btnId, statusId, unit, refreshFn) {
    var btn = document.getElementById(btnId);
    if (!btn) return;
    btn.addEventListener("click", function () {
      var statusEl = statusId ? document.getElementById(statusId) : null;
      if (statusEl) statusEl.textContent = "웹 검색·토론 중…";
      fetch("/api/agents/office/" + unit + "/web-research-debate", {
        method: "POST",
        credentials: "same-origin",
        headers: csrfHeaders(),
        body: JSON.stringify({ max: 1 }),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!statusEl) {
            if (typeof refreshFn === "function") refreshFn();
            return;
          }
          if (!data.ok) {
            statusEl.textContent =
              data.error || (data.result && data.result.errors && data.result.errors[0]) || "실패";
            return;
          }
          var items = (data.result && data.result.items) || [];
          if (items.length) {
            statusEl.textContent =
              "웹리서치 #" + items[0].card_id + " · 출처 " + (items[0].refs || 0) + "건";
          } else {
            statusEl.textContent = "신규 주제 없음";
          }
          if (typeof refreshFn === "function") refreshFn();
        })
        .catch(function () {
          if (statusEl) statusEl.textContent = "네트워크 오류";
        });
    });
  }

  window.OFFICE_WEB_RESEARCH_BIND = bindWebResearch;

  bindWebResearch("finance-web-research-btn", "finance-web-research-status", "finance");
  bindWebResearch("saju-web-research-btn", "saju-learn-status", "saju-learn");
  bindWebResearch("gwansang-web-research-btn", "gwansang-learn-status", "gwansang-learn");
  bindWebResearch("kiwoom-web-research-btn", "kiwoom-learn-status", "kiwoom-chasu");
  bindWebResearch("stock-web-research-btn", "stock-web-research-status", "stock-watch");
  bindWebResearch("workisus-web-research-btn", "workisus-learn-status", "workisus-chasu");
})();
