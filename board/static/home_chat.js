(function () {
  "use strict";

  const cfg = window.HOME_CHAT_CONFIG || {};
  const GEMMA = cfg.gemmaAuthor || "젬마24";
  const messagesEl = document.getElementById("home-chat-messages");
  const composeEl = document.getElementById("home-chat-compose");
  const headerEl = document.getElementById("home-chat-header");
  const placeholderEl = document.getElementById("home-chat-placeholder");
  const errEl = document.getElementById("home-chat-error");
  const authorInp = document.getElementById("home-chat-author");
  const pwInp = document.getElementById("home-chat-password");
  const contentTa = document.getElementById("home-chat-content");
  const sendBtn = document.getElementById("home-chat-send");
  const blogLink = document.getElementById("home-chat-blog-link");

  const state = { postId: null, loading: false };
  const POLL_MS = 2500;
  let pollTimer = null;
  let lastSig = "";
  let knownIds = new Set();
  let chatWasAtBottom = true;

  function pwKey(id) {
    return "homeChatPw:" + id;
  }
  function authorKey(id) {
    return "homeChatAuthor:" + id;
  }

  function csrfHeaders() {
    const headers = { "X-Requested-With": "XMLHttpRequest" };
    if (cfg.csrfToken) headers["X-CSRF-Token"] = cfg.csrfToken;
    return headers;
  }

  function parseJsonResponse(res) {
    return res.text().then(function (text) {
      try {
        return JSON.parse(text);
      } catch (e) {
        return { ok: false, error: res.ok ? "응답 형식 오류" : "서버 오류 (" + res.status + ")" };
      }
    }).then(function (data) {
      return { res: res, data: data };
    });
  }

  function showError(msg) {
    if (!errEl) return;
    if (msg) {
      errEl.textContent = msg;
      errEl.hidden = false;
    } else {
      errEl.textContent = "";
      errEl.hidden = true;
    }
  }

  function showLoading(text) {
    if (!messagesEl) return;
    if (placeholderEl) placeholderEl.hidden = true;
    messagesEl.innerHTML =
      '<p class="home-chat-loading">' + escapeHtml(text || "처리 중…") + "</p>";
    const panel = document.getElementById("home-chat");
    if (panel) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function formatBubbleText(text) {
    return escapeHtml(String(text || "")).replace(/\n/g, "<br>");
  }

  function scrollMessages() {
    if (!messagesEl) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function renderMessages(messages) {
    if (!messagesEl) return;
    messagesEl.innerHTML = "";
    (messages || []).forEach(function (m) {
      const wrap = document.createElement("div");
      wrap.className =
        "home-chat-bubble home-chat-bubble--" +
        (m.role === "assistant" ? "assistant" : "user");
      const who =
        m.role === "assistant" ? GEMMA : escapeHtml(m.author || "질문");
      wrap.innerHTML =
        '<p class="home-chat-bubble-meta">' +
        who +
        " · " +
        escapeHtml(m.created || "") +
        "</p>" +
        '<div class="home-chat-bubble-body">' +
        formatBubbleText(m.content) +
        "</div>";
      messagesEl.appendChild(wrap);
    });
    scrollMessages();
  }

  function updateHeader(thread) {
    if (!headerEl) return;
    if (!thread) {
      headerEl.hidden = true;
      return;
    }
    headerEl.hidden = false;
    headerEl.innerHTML =
      "<h4>" +
      escapeHtml(thread.title) +
      "</h4>" +
      '<p class="home-chat-header-meta">' +
      escapeHtml(thread.author) +
      " · " +
      escapeHtml(thread.created) +
      "</p>";
    if (blogLink && thread.url) {
      blogLink.href = thread.url;
      blogLink.hidden = false;
    }
  }

  function setComposeVisible(on) {
    if (composeEl) composeEl.hidden = !on;
    if (placeholderEl) placeholderEl.hidden = on;
  }

  function rememberSession(postId, author, password) {
    try {
      if (author) sessionStorage.setItem(authorKey(postId), author);
      if (password) sessionStorage.setItem(pwKey(postId), password);
    } catch (e) {
      /* ignore */
    }
  }

  function restoreSession(postId) {
    try {
      if (authorInp) {
        authorInp.value =
          sessionStorage.getItem(authorKey(postId)) || authorInp.value || "";
      }
      if (pwInp) {
        pwInp.value = sessionStorage.getItem(pwKey(postId)) || "";
      }
    } catch (e) {
      /* ignore */
    }
  }

  function threadSig(messages) {
    var last = 0;
    (messages || []).forEach(function (m) {
      if (m && m.id > last) last = m.id;
    });
    return (messages ? messages.length : 0) + "|" + last;
  }

  function stopPoll() {
    if (pollTimer) {
      window.clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function startPoll() {
    stopPoll();
    if (!state.postId) return;
    pollTimer = window.setInterval(function () {
      if (!state.postId || state.loading || document.hidden) return;
      fetch("/api/home-chat/" + state.postId + "/pulse", {
        credentials: "same-origin",
        cache: "no-store",
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!data.ok || !data.sig || data.sig === lastSig) return;
          loadThread(state.postId, { silent: true });
        })
        .catch(function () {});
    }, POLL_MS);
  }

  function applyThread(thread) {
    if (!thread || !thread.post_id) return;
    state.postId = thread.post_id;
    updateHeader(thread);
    renderMessages(thread.messages || []);
    knownIds = new Set();
    (thread.messages || []).forEach(function (m) {
      if (m && m.id) knownIds.add(m.id);
    });
    lastSig = threadSig(thread.messages || []);
    setComposeVisible(true);
    restoreSession(thread.post_id);
    showError("");
    startPoll();
    const panel = document.getElementById("home-chat");
    if (panel) panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function loadThread(postId, opts) {
    opts = opts || {};
    if (state.loading && !opts.silent) return;
    if (!opts.silent) {
      state.loading = true;
      showError("");
      showLoading("대화를 불러오는 중…");
    }
    fetch("/api/home-chat/" + postId, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(parseJsonResponse)
      .then(function (o) {
        if (!o.res.ok || !o.data.ok) {
          throw new Error(o.data.error || "불러오기 실패");
        }
        if (opts.author || opts.password) {
          rememberSession(postId, opts.author, opts.password);
        }
        if (opts.silent && messagesEl) {
          var prev = new Set(knownIds);
          var msgs = o.data.messages || [];
          var hasNew = msgs.some(function (m) {
            return m && m.id && !prev.has(m.id);
          });
          if (hasNew) {
            applyThread(o.data);
          } else {
            lastSig = threadSig(msgs);
          }
        } else {
          applyThread(o.data);
        }
      })
      .catch(function (err) {
        if (!opts.silent) {
          showError(err.message || "대화를 불러오지 못했습니다.");
          setComposeVisible(false);
          if (placeholderEl) placeholderEl.hidden = false;
        }
      })
      .finally(function () {
        state.loading = false;
      });
  }

  function openThread(postId, opts) {
    opts = opts || {};
    if (opts.author && authorInp) authorInp.value = opts.author;
    if (opts.password && pwInp) pwInp.value = opts.password;
    loadThread(postId, opts);
  }

  function applyThreadData(thread, opts) {
    opts = opts || {};
    if (opts.author && authorInp) authorInp.value = opts.author;
    if (opts.password && pwInp) pwInp.value = opts.password;
    if (thread && thread.post_id) {
      if (opts.author || opts.password) {
        rememberSession(thread.post_id, opts.author, opts.password);
      }
      applyThread(thread);
    }
  }

  function sendMessage(e) {
    e.preventDefault();
    if (!state.postId || state.loading) return;
    showError("");
    const author = (authorInp && authorInp.value.trim()) || "";
    const password = (pwInp && pwInp.value) || "";
    const content = (contentTa && contentTa.value.trim()) || "";
    if (!author || !password || !content) {
      showError("닉네임, 비밀번호, 메시지를 입력해 주세요.");
      return;
    }
    rememberSession(state.postId, author, password);
    const fd = new FormData();
    fd.append("author", author);
    fd.append("password", password);
    fd.append("content", content);
    if (cfg.csrfToken) fd.append("csrf_token", cfg.csrfToken);

    state.loading = true;
    showLoading("젬마24 답변 생성 중…");
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.textContent = "전송 중…";
    }

    fetch("/api/home-chat/" + state.postId + "/message", {
      method: "POST",
      body: fd,
      credentials: "same-origin",
      headers: csrfHeaders(),
    })
      .then(parseJsonResponse)
      .then(function (o) {
        if (!o.res.ok || !o.data.ok) {
          throw new Error(o.data.error || "전송 실패");
        }
        applyThread(o.data);
        if (contentTa) contentTa.value = "";
      })
      .catch(function (err) {
        showError(err.message || "메시지 전송에 실패했습니다.");
      })
      .finally(function () {
        state.loading = false;
        if (sendBtn) {
          sendBtn.disabled = false;
          sendBtn.textContent = "보내기";
        }
      });
  }

  function submitAskForm(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = document.getElementById("home-ask-submit");
    const errBox = document.getElementById("home-ask-error");
    const askContent = document.getElementById("home-ask-content");

    if (errBox) {
      errBox.hidden = true;
      errBox.textContent = "";
    }
    showError("");

    const fd = new FormData(form);
    if (state.loading) return;

    state.loading = true;
    showLoading("젬마24 답변 생성 중…");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "젬마24 답변 생성 중…";
    }

    fetch(form.action, {
      method: "POST",
      body: fd,
      credentials: "same-origin",
      headers: csrfHeaders(),
    })
      .then(parseJsonResponse)
      .then(function (o) {
        if (!o.res.ok || !o.data.ok) {
          throw new Error(o.data.error || "질문 등록에 실패했습니다.");
        }
        const q = o.data.question;
        const pw = fd.get("password");
        if (o.data.thread) {
          applyThreadData(o.data.thread, { author: q.author, password: pw });
        } else if (q && q.post_id) {
          openThread(q.post_id, { author: q.author, password: pw });
        } else {
          throw new Error("답변을 표시할 수 없습니다. 잠시 후 다시 시도해 주세요.");
        }
        if (askContent) askContent.value = "";
      })
      .catch(function (err) {
        const msg = err.message || "오류가 발생했습니다.";
        showError(msg);
        if (errBox) {
          errBox.textContent = msg;
          errBox.hidden = false;
        }
        if (placeholderEl) placeholderEl.hidden = false;
      })
      .finally(function () {
        state.loading = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "질문 등록";
        }
      });
  }

  function initAskForm() {
    const NICKS = cfg.randomNicks || [];
    const inp = document.getElementById("home-ask-author");
    const btn = document.getElementById("home-ask-random-author");
    function pickOne(exclude) {
      const pool = exclude
        ? NICKS.filter(function (n) {
            return n !== exclude;
          })
        : NICKS.slice();
      return pool[Math.floor(Math.random() * pool.length)] || NICKS[0];
    }
    if (btn && inp) {
      btn.addEventListener("click", function () {
        inp.value = pickOne(String(inp.value || "").trim());
      });
    }

    const form = document.querySelector(".home-ask-form");
    if (form) form.addEventListener("submit", submitAskForm);
  }

  if (composeEl) composeEl.addEventListener("submit", sendMessage);
  initAskForm();

  window.HomeChat = {
    openThread: openThread,
    loadThread: loadThread,
    applyThreadData: applyThreadData,
  };
})();
