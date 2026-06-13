(function () {
  "use strict";

  const cfg = window.POST_THREAD_CHAT || {};
  const postId = cfg.postId;
  const GEMMA = cfg.gemmaAuthor || "\uC810\uB9C824";
  const POLL_MS = 2500;

  if (!postId) return;

  const listEl = document.getElementById("post-thread-comments-list");
  const countEl = document.getElementById("post-thread-count");
  const liveEl = document.getElementById("post-thread-live-status");
  const bannerEl = document.getElementById("post-thread-new-banner");
  const bannerBtn = document.getElementById("post-thread-new-banner-btn");
  const refreshBtn = document.getElementById("post-thread-refresh-btn");
  const composeForm = document.getElementById("post-thread-compose-form");
  const composeStatus = document.getElementById("post-thread-compose-status");

  let lastSig = "";
  let knownIds = new Set();
  let pollTimer = null;
  let loading = false;
  let wasAtBottom = true;

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function nl2br(text) {
    return escapeHtml(String(text || "")).replace(/\n/g, "<br>");
  }

  function threadSig(messages) {
    let last = 0;
    (messages || []).forEach(function (m) {
      if (m.id > last) last = m.id;
    });
    return (messages ? messages.length : 0) + "|" + last;
  }

  function setLive(on) {
    if (!liveEl) return;
    liveEl.classList.toggle("is-on", !!on);
    liveEl.classList.toggle("is-off", !on);
    liveEl.textContent = on ? "\u25CF \uC2E4\uC2DC\uAC04" : "\u25CF \uC5F0\uACB0 \uB04A\uAE40";
  }

  function hideBanner() {
    if (bannerEl) bannerEl.classList.add("is-hidden");
  }

  function showBanner(n) {
    if (!bannerEl || !bannerBtn) return;
    bannerBtn.textContent = "\uC0C8 \uBA54\uC2DC\uC9C0 " + n + "\uAC74";
    bannerEl.classList.remove("is-hidden");
  }

  function nearBottom() {
    if (!listEl) return true;
    const max = listEl.scrollHeight - listEl.clientHeight;
    if (max <= 0) return true;
    return listEl.scrollTop >= max - 80;
  }

  function scrollBottom() {
    if (!listEl) return;
    listEl.scrollTop = listEl.scrollHeight;
  }

  function renderComment(m) {
    const isGemma = m.role === "assistant" || m.author === GEMMA;
    const delUrl = "/comment/" + m.id + "/delete";
    const label = isGemma ? "\uB2F5\uBCC0 \u00B7 " : "\uC9C8\uBB38 \u00B7 ";
    const delId = "del-" + m.id;
    return (
      '<div class="comment-item' +
      (isGemma ? " comment-item--gemma" : " comment-item--user") +
      (m._isNew ? " comment-item--new" : "") +
      '" data-comment-id="' +
      m.id +
      '">' +
      '<div class="comment-meta">' +
      "<strong>" +
      label +
      escapeHtml(m.author || "") +
      "</strong>" +
      '<span class="comment-date">' +
      escapeHtml(m.created || "") +
      "</span>" +
      '<button type="button" class="btn-text btn-danger-text" data-del-toggle="' +
      delId +
      '">\uC0AD\uC81C</button>' +
      "</div>" +
      '<div class="comment-body">' +
      nl2br(m.content) +
      "</div>" +
      '<form id="' +
      delId +
      '" method="post" action="' +
      escapeHtml(delUrl) +
      '" style="display:none;margin-top:6px;" class="post-thread-del-form">' +
      (cfg.csrfToken
        ? '<input type="hidden" name="csrf_token" value="' +
          escapeHtml(cfg.csrfToken) +
          '">'
        : "") +
      '<input type="password" name="password" placeholder="\uB313\uAE00 \uBE44\uBC00\uBC88\uD638" class="inline-input" required>' +
      '<button type="submit" class="btn btn-danger btn-sm">\uC0AD\uC81C</button>' +
      '<button type="button" class="btn btn-gray btn-sm" data-del-cancel="' +
      delId +
      '">\uCDE8\uC18C</button>' +
      "</form></div>"
    );
  }

  function bindListUi() {
    if (!listEl) return;
    listEl.querySelectorAll("[data-del-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const id = btn.getAttribute("data-del-toggle");
        const el = document.getElementById(id);
        if (el) el.style.display = el.style.display === "none" ? "block" : "none";
      });
    });
    listEl.querySelectorAll("[data-del-cancel]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const id = btn.getAttribute("data-del-cancel");
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
      });
    });
  }

  function applyMessages(messages, opts) {
    opts = opts || {};
    if (!listEl) return;
    const prev = new Set(knownIds);
    let newCount = 0;
    (messages || []).forEach(function (m) {
      if (m.id && !prev.has(m.id)) newCount++;
      m._isNew = !!(m.id && !prev.has(m.id) && prev.size > 0);
    });
    knownIds = new Set();
    (messages || []).forEach(function (m) {
      if (m.id) knownIds.add(m.id);
    });
    lastSig = threadSig(messages);

    if (countEl) countEl.textContent = String((messages || []).length);

    if (!messages || !messages.length) {
      listEl.innerHTML = '<p class="empty">\uCCAB \uC9C8\uBB38\uC744 \uB0A8\uACA8 \uBCF4\uC138\uC694.</p>';
    } else {
      listEl.innerHTML = messages.map(renderComment).join("");
      bindListUi();
      if (opts.forceTop || wasAtBottom) {
        scrollBottom();
        hideBanner();
      } else if (newCount > 0) {
        showBanner(newCount);
      }
      window.setTimeout(function () {
        listEl.querySelectorAll(".comment-item--new").forEach(function (el) {
          el.classList.remove("comment-item--new");
        });
      }, 2500);
    }
  }

  function fetchThread() {
    return fetch("/api/home-chat/" + postId, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      cache: "no-store",
    }).then(function (r) {
      return r.json().then(function (data) {
        return { ok: r.ok, data: data };
      });
    });
  }

  function refresh(opts) {
    if (loading) return Promise.resolve();
    loading = true;
    if (!opts || !opts.silent) {
      wasAtBottom = nearBottom();
    }
    return fetchThread()
      .then(function (o) {
        if (!o.ok || !o.data.ok) throw new Error(o.data.error || "\uBD88\uB7EC\uC624\uAE30 \uC2E4\uD328");
        applyMessages(o.data.messages || [], opts || {});
        setLive(true);
      })
      .catch(function () {
        setLive(false);
      })
      .finally(function () {
        loading = false;
      });
  }

  function poll() {
    if (document.hidden || loading) return;
    fetch("/api/home-chat/" + postId + "/pulse", {
      credentials: "same-origin",
      cache: "no-store",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, data: data };
        });
      })
      .then(function (o) {
        if (!o.ok || !o.data || !o.data.ok) {
          setLive(false);
          return;
        }
        setLive(true);
        if (o.data.sig && o.data.sig !== lastSig) {
          wasAtBottom = nearBottom();
          refresh({ silent: true });
        }
      })
      .catch(function () {
        setLive(false);
      });
  }

  function startPoll() {
    if (pollTimer) window.clearInterval(pollTimer);
    pollTimer = window.setInterval(poll, POLL_MS);
  }

  if (listEl) {
    listEl.querySelectorAll(".comment-item").forEach(function (el) {
      const id = parseInt(el.getAttribute("data-comment-id") || "0", 10);
      if (id) knownIds.add(id);
    });
    listEl.addEventListener("scroll", function () {
      wasAtBottom = nearBottom();
      if (wasAtBottom) hideBanner();
    });
    const bootMsgs = [];
    listEl.querySelectorAll(".comment-item").forEach(function (el) {
      const id = parseInt(el.getAttribute("data-comment-id") || "0", 10);
      if (id) bootMsgs.push({ id: id });
    });
    lastSig = threadSig(bootMsgs);
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      wasAtBottom = true;
      refresh({ forceTop: true });
    });
  }

  if (bannerBtn) {
    bannerBtn.addEventListener("click", function () {
      wasAtBottom = true;
      hideBanner();
      scrollBottom();
      refresh({ forceTop: true });
    });
  }

  if (composeForm) {
    composeForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (loading) return;
      const fd = new FormData(composeForm);
      if (cfg.csrfToken) fd.append("csrf_token", cfg.csrfToken);
      loading = true;
      if (composeStatus) {
        composeStatus.textContent = "\uC810\uB9C824 \uB2F5\uBCC0 \uC0DD\uC131 \uC911\u2026";
        composeStatus.hidden = false;
      }
      const submitBtn = composeForm.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;

      fetch(cfg.commentUrl || composeForm.action, {
        method: "POST",
        body: fd,
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRF-Token": cfg.csrfToken || "",
        },
      })
        .then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, data: data };
          });
        })
        .then(function (o) {
          var data = o.data || {};
          if (!o.ok || !data.ok) {
            throw new Error(
              data.error ||
                (o.ok ? "\uC804\uC1A1 \uC2E4\uD328" : "\uC11C\uBC84 \uC624\uB958(" + (data.error || "500") + ")")
            );
          }
          const ta = composeForm.querySelector('textarea[name="content"]');
          if (ta) ta.value = "";
          wasAtBottom = true;
          applyMessages(data.messages || [], { forceTop: true });
          if (composeStatus) composeStatus.hidden = true;
          refresh({ silent: true });
        })
        .catch(function (err) {
          if (composeStatus) {
            composeStatus.textContent = err.message || "\uC804\uC1A1 \uC2E4\uD328";
            composeStatus.hidden = false;
          }
          refresh({ silent: true });
        })
        .finally(function () {
          loading = false;
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) poll();
  });

  setLive(true);
  startPoll();
  window.PostThreadLive = { refresh: refresh };
})();
