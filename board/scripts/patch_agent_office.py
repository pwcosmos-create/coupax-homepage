import os
import re

JS_PATH = r"C:\커셔\coupax홈페이지\board\static\agent_office.js"

with open(JS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. unitChiefDev 추가
if "const unitChiefDev = document.getElementById(\"office-unit-chief-dev\");" not in content:
    content = content.replace(
        'const unitGwansang = document.getElementById("office-unit-gwansang-learn");',
        'const unitGwansang = document.getElementById("office-unit-gwansang-learn");\n  const unitChiefDev = document.getElementById("office-unit-chief-dev");'
    )

# 2. showOfficeUnit 내 chief-dev 처리
if "if (unitChiefDev) {" not in content:
    chief_dev_block = """
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
"""
    content = content.replace(
        'if (unitGwansang) {',
        chief_dev_block + '    if (unitGwansang) {'
    )

# 3. URL Param 처리
if 'else if (unitParam === "chief-dev" && unitChiefDev) {' not in content:
    content = content.replace(
        '} else if (unitParam === "gwansang-learn" && unitGwansang) {',
        '} else if (unitParam === "chief-dev" && unitChiefDev) {\n    showOfficeUnit("chief-dev");\n  } else if (unitParam === "gwansang-learn" && unitGwansang) {'
    )

# 4. pollOfficeRealtime 처리 (라인 835 쯤)
if 'else if (activeUnit === "chief-dev") {' not in content:
    content = content.replace(
        '} else if (activeUnit === "gwansang-learn") {',
        '} else if (activeUnit === "chief-dev") {\n          if (typeof window.refreshChiefDevFeed === "function") window.refreshChiefDevFeed(false);\n          if (typeof window.refreshChiefDevTasks === "function") window.refreshChiefDevTasks();\n        } else if (activeUnit === "gwansang-learn") {'
    )

# 5. chief-dev 전용 함수 추가
if "function refreshChiefDevFeed" not in content:
    chief_dev_functions = """

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
"""
    content += chief_dev_functions

with open(JS_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("agent_office.js updated.")
