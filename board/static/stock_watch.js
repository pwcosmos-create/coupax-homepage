(function () {
  "use strict";

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  const krMarket = {
    indices: [],
    kospi200: [],
    kosdaq150: [],
    watchlist: [],
    tab: "kospi200",
    search: "",
    sort: "chg_desc",
  };

  function formatPrice(v) {
    const n = Number(v);
    if (!isFinite(n)) return escapeHtml(v == null ? "—" : String(v));
    if (Math.abs(n) >= 1000) return n.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
    return n.toLocaleString("ko-KR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function chgClass(pct) {
    if (pct > 0) return "stock-up";
    if (pct < 0) return "stock-down";
    return "";
  }

  function renderQuoteRow(q, opts) {
    opts = opts || {};
    const pct = Number(q.change_pct) || 0;
    const cls = chgClass(pct);
    const name = escapeHtml(q.name || q.symbol || "");
    const sym = escapeHtml(q.symbol || "");
    const showSym = opts.showSym !== false;
    return (
      "<tr><td class=\"col-name\"><strong>" +
      name +
      "</strong>" +
      (showSym ? '<span class="stock-sym">' + sym + "</span>" : "") +
      '</td><td class="col-price">' +
      formatPrice(q.price) +
      (q.currency
        ? '<span class="stock-currency">' + escapeHtml(q.currency) + "</span>"
        : "") +
      '</td><td class="col-chg ' +
      cls +
      '">' +
      (pct >= 0 ? "+" : "") +
      pct.toFixed(2) +
      "%</td></tr>"
    );
  }

  function renderQuoteRows(quotes, opts) {
    if (!quotes || !quotes.length) {
      return (
        '<tr><td colspan="3" class="stock-empty">시세 없음 — 「지금 수집」을 눌러 주세요.</td></tr>'
      );
    }
    return quotes.map(function (q) {
      return renderQuoteRow(q, opts);
    }).join("");
  }

  function sortQuotes(rows, mode) {
    const list = rows.slice();
    if (mode === "name") {
      list.sort(function (a, b) {
        return String(a.name || a.symbol || "").localeCompare(
          String(b.name || b.symbol || ""),
          "ko"
        );
      });
    } else if (mode === "chg_asc") {
      list.sort(function (a, b) {
        return (Number(a.change_pct) || 0) - (Number(b.change_pct) || 0);
      });
    } else {
      list.sort(function (a, b) {
        return (Number(b.change_pct) || 0) - (Number(a.change_pct) || 0);
      });
    }
    return list;
  }

  function filterQuotes(rows, term) {
    const t = (term || "").trim().toLowerCase();
    if (!t) return rows;
    return rows.filter(function (q) {
      const name = String(q.name || "").toLowerCase();
      const sym = String(q.symbol || "").toLowerCase();
      return name.indexOf(t) >= 0 || sym.indexOf(t) >= 0;
    });
  }

  function findIndexQuote(quotes, hints) {
    for (let i = 0; i < quotes.length; i++) {
      const sym = String(quotes[i].symbol || "");
      const name = String(quotes[i].name || "");
      for (let h = 0; h < hints.length; h++) {
        if (sym.indexOf(hints[h]) >= 0 || name.indexOf(hints[h]) >= 0) return quotes[i];
      }
    }
    return null;
  }

  function updateStatCard(elPrice, elPct, q) {
    if (!elPrice || !elPct) return;
    if (!q) {
      elPrice.textContent = "—";
      elPct.textContent = "—";
      elPct.className = "stock-stat-chg";
      return;
    }
    const pct = Number(q.change_pct) || 0;
    elPrice.textContent = formatPrice(q.price);
    elPct.textContent = (pct >= 0 ? "+" : "") + pct.toFixed(2) + "%";
    elPct.className = "stock-stat-chg " + chgClass(pct);
  }

  function renderMovers(kospi, kosdaq) {
    const bar = document.getElementById("stock-movers-bar");
    const list = document.getElementById("stock-movers-list");
    if (!bar || !list) return;
    const pool = (kospi || []).concat(kosdaq || []).filter(function (q) {
      return q && q.symbol && !String(q.symbol).startsWith("^");
    });
    pool.sort(function (a, b) {
      return Math.abs(Number(b.change_pct) || 0) - Math.abs(Number(a.change_pct) || 0);
    });
    const top = pool.slice(0, 8);
    if (!top.length) {
      bar.hidden = true;
      return;
    }
    bar.hidden = false;
    list.innerHTML = top
      .map(function (q) {
        const pct = Number(q.change_pct) || 0;
        return (
          "<li><strong>" +
          escapeHtml(q.name || q.symbol) +
          '</strong><span class="stock-mover-pct ' +
          chgClass(pct) +
          '">' +
          (pct >= 0 ? "+" : "") +
          pct.toFixed(2) +
          "%</span></li>"
        );
      })
      .join("");
  }

  function renderKrTable() {
    const body = document.getElementById("stock-kr-tbody");
    const countEl = document.getElementById("stock-kr-row-count");
    if (!body) return;
    let rows = krMarket[krMarket.tab] || [];
    rows = filterQuotes(rows, krMarket.search);
    rows = sortQuotes(rows, krMarket.sort);
    if (countEl) {
      countEl.textContent = rows.length + "종목 표시";
    }
    body.innerHTML = renderQuoteRows(rows, { showSym: krMarket.tab !== "indices" });
  }

  function renderUsMarket(us) {
    const idxEl = document.getElementById("stock-us-indices");
    const body = document.getElementById("stock-us-tbody");
    const countEl = document.getElementById("stock-us-row-count");
    const indices = us.indices || [];
    const stocks = us.watchlist || [];
    if (idxEl) {
      idxEl.innerHTML = indices
        .map(function (q) {
          const pct = Number(q.change_pct) || 0;
          return (
            '<div class="stock-us-index-card">' +
            '<span class="stock-stat-label">' +
            escapeHtml(q.name || q.symbol) +
            '</span><span class="stock-stat-value">' +
            formatPrice(q.price) +
            '</span><span class="stock-stat-chg ' +
            chgClass(pct) +
            '">' +
            (pct >= 0 ? "+" : "") +
            pct.toFixed(2) +
            "%</span></div>"
          );
        })
        .join("");
    }
    const sorted = sortQuotes(stocks.slice(), "chg_desc");
    if (countEl) countEl.textContent = sorted.length + "종목";
    if (body) body.innerHTML = renderQuoteRows(sorted);
  }

  function bindKrToolbar() {
    document.querySelectorAll("[data-kr-tab]").forEach(function (btn) {
      if (btn._stockBound) return;
      btn._stockBound = true;
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-kr-tab]").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        krMarket.tab = btn.getAttribute("data-kr-tab") || "kospi200";
        renderKrTable();
      });
    });
    const search = document.getElementById("stock-kr-search");
    if (search && !search._stockBound) {
      search._stockBound = true;
      search.addEventListener("input", function () {
        krMarket.search = search.value;
        renderKrTable();
      });
    }
    const sort = document.getElementById("stock-kr-sort");
    if (sort && !sort._stockBound) {
      sort._stockBound = true;
      sort.addEventListener("change", function () {
        krMarket.sort = sort.value;
        renderKrTable();
      });
    }
  }

  function applyMarketSnapshot(snap, stats) {
    const mk = snap.markets || {};
    const kr = mk.kr || {};
    const us = mk.us || {};
    krMarket.indices = kr.indices || [];
    krMarket.kospi200 = kr.kospi200 || [];
    krMarket.kosdaq150 = kr.kosdaq150 || [];
    krMarket.watchlist = kr.watchlist || [];

    const kospi = findIndexQuote(krMarket.indices, ["KS11", "KOSPI"]);
    const kosdaq = findIndexQuote(krMarket.indices, ["KQ11", "Kosdaq"]);
    updateStatCard(
      document.querySelector("[data-stat=kospi-price]"),
      document.querySelector("[data-stat=kospi-pct]"),
      kospi
    );
    updateStatCard(
      document.querySelector("[data-stat=kosdaq-price]"),
      document.querySelector("[data-stat=kosdaq-pct]"),
      kosdaq
    );
    const c200 = document.getElementById("stock-count-k200");
    const c150 = document.getElementById("stock-count-k150");
    if (c200 && stats) c200.textContent = (stats.kr_kospi200 || krMarket.kospi200.length) + "종목";
    if (c150 && stats) c150.textContent = (stats.kr_kosdaq150 || krMarket.kosdaq150.length) + "종목";

    renderMovers(krMarket.kospi200, krMarket.kosdaq150);
    bindKrToolbar();
    renderKrTable();
    renderUsMarket(us);
  }

  function renderAlerts(alerts) {
    if (!alerts || !alerts.length) {
      return '<li class="stock-empty">등락률 임계치 이상 변동 시 표시됩니다.</li>';
    }
    return alerts
      .map(function (a) {
        return (
          "<li>" +
          escapeHtml(a.name || a.symbol) +
          " — " +
          escapeHtml(a.note || "") +
          "</li>"
        );
      })
      .join("");
  }

  function renderInsights(ins) {
    if (!ins) return;
    const keyByList = {
      "stock-chart-list": "chart",
      "stock-finance-list": "finance",
      "stock-news-list": "news",
      "stock-risk-list": "risk",
      "stock-disclosure-list": "disclosure",
      "stock-government-list": "government",
      "stock-press-list": "press",
    };
    renderRlPredictions(ins.rl_predictions || {});
    renderAnalystReports(ins.analyst_reports || {});
    renderYoutube(ins.youtube || {});
    renderCeoRemarks(ins.ceo_remarks || {});
    renderCommentVerify(ins.comments || {});
    renderRatesDollar(ins.rates_dollar || {});
    renderBonds(ins.bonds || {});
    renderOilWar(ins.oil_war || {});
    renderCommodities(ins.commodities || {});
    function fillList(id, tsId, items, renderItem, emptyText) {
      const list = document.getElementById(id);
      const tsEl = document.getElementById(tsId);
      const block = ins[keyByList[id]] || {};
      if (tsEl && block.ts) tsEl.textContent = block.ts;
      if (!list) return;
      const rows = items || block.items || [];
      if (!rows.length) {
        list.innerHTML = '<li class="stock-empty">' + escapeHtml(emptyText) + "</li>";
        return;
      }
      list.innerHTML = rows.map(renderItem).join("");
    }
    fillList(
      "stock-chart-list",
      "stock-chart-ts",
      null,
      function (it) {
        return (
          "<li><strong>" +
          escapeHtml(it.name) +
          '</strong> <span class="stock-signal">' +
          escapeHtml(it.signal) +
          "</span> " +
          escapeHtml(it.note) +
          "</li>"
        );
      },
      "차트 신호 대기"
    );
    fillList(
      "stock-finance-list",
      "stock-finance-ts",
      null,
      function (it) {
        return (
          "<li><strong>" +
          escapeHtml(it.name || it.symbol) +
          "</strong> — " +
          escapeHtml(it.title) +
          '<br><span class="stock-snippet">' +
          escapeHtml((it.snippet || "").slice(0, 120)) +
          "…</span></li>"
        );
      },
      "제무 팩트 대기"
    );
    fillList(
      "stock-news-list",
      "stock-news-ts",
      null,
      function (it) {
        return (
          "<li><a href=\"" +
          escapeHtml(it.url) +
          '" rel="noopener noreferrer" target="_blank">' +
          escapeHtml(it.title) +
          '</a><br><span class="stock-snippet">' +
          escapeHtml((it.snippet || "").slice(0, 100)) +
          "…</span></li>"
        );
      },
      "뉴스 대기"
    );
    fillList(
      "stock-risk-list",
      "stock-risk-ts",
      null,
      function (it) {
        return (
          "<li>" +
          escapeHtml(it.name) +
          " — " +
          escapeHtml(it.change_pct) +
          "% (" +
          escapeHtml(it.note) +
          ")</li>"
        );
      },
      "리스크 양호"
    );
    fillList(
      "stock-disclosure-list",
      "stock-disclosure-ts",
      null,
      function (it) {
        return (
          "<li><a href=\"" +
          escapeHtml(it.url) +
          '" rel="noopener noreferrer" target="_blank">[' +
          escapeHtml(it.source_type || "") +
          "] " +
          escapeHtml((it.title || "").slice(0, 72)) +
          "</a></li>"
        );
      },
      "공시 대기"
    );
    fillList(
      "stock-government-list",
      "stock-government-ts",
      null,
      function (it) {
        return (
          "<li><a href=\"" +
          escapeHtml(it.url) +
          '" rel="noopener noreferrer" target="_blank">' +
          escapeHtml((it.title || "").slice(0, 72)) +
          "</a></li>"
        );
      },
      "정부 보도 대기"
    );
    fillList(
      "stock-press-list",
      "stock-press-ts",
      null,
      function (it) {
        return (
          "<li><a href=\"" +
          escapeHtml(it.url) +
          '" rel="noopener noreferrer" target="_blank">' +
          escapeHtml((it.title || "").slice(0, 72)) +
          "</a></li>"
        );
      },
      "기사 대기"
    );
  }

  function renderRatesDollar(block) {
    const tsEl = document.getElementById("stock-rates-ts");
    const list = document.getElementById("stock-rates-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    if (!list) return;
    const fx = block.usdkrw || {};
    let fxHtml = "";
    if (fx.price) {
      const cls =
        Number(fx.change_pct) > 0 ? "stock-up" : Number(fx.change_pct) < 0 ? "stock-down" : "";
      fxHtml =
        '<p class="stock-fx-spot">USD/KRW <strong>' +
        escapeHtml(fx.price) +
        '</strong> <span class="' +
        cls +
        '">' +
        (Number(fx.change_pct) >= 0 ? "+" : "") +
        Number(fx.change_pct || 0).toFixed(2) +
        "%</span></p>";
    }
    const items = block.items || [];
    if (!items.length && !fx.price) {
      list.innerHTML =
        '<li class="stock-empty">기준금리·원달러·증시 영향 해석</li>';
      return;
    }
    list.innerHTML =
      fxHtml +
      items
        .map(function (it) {
          const topic = escapeHtml(it.topic || "");
          const tit = escapeHtml((it.title || "").slice(0, 72));
          const snip = it.snippet
            ? '<br><span class="stock-snippet">' +
              escapeHtml(it.snippet.slice(0, 100)) +
              "…</span>"
            : "";
          const link = it.url
            ? '<a href="' +
              escapeHtml(it.url) +
              '" rel="noopener noreferrer" target="_blank">' +
              tit +
              "</a>"
            : tit;
          return (
            "<li><span class=\"stock-macro-topic\">[" +
            topic +
            "]</span> " +
            link +
            snip +
            "</li>"
          );
        })
        .join("");
  }

  function renderBonds(block) {
    const tsEl = document.getElementById("stock-bond-ts");
    const quotesEl = document.getElementById("stock-bond-quotes");
    const list = document.getElementById("stock-bond-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    const yields = (block.quotes || []).filter(function (q) {
      return q.kind === "yield";
    });
    if (quotesEl) {
      if (!yields.length) {
        quotesEl.innerHTML = '<li class="stock-empty">국채 수익률·채권 ETF</li>';
      } else {
        quotesEl.innerHTML = yields
          .map(function (q) {
            const chg = Number(q.change_pct || 0);
            const cls = chg > 0 ? "stock-up" : chg < 0 ? "stock-down" : "";
            const unit = q.unit || "%";
            return (
              "<li><span class=\"stock-bond-name\">" +
              escapeHtml(q.name || q.symbol || "") +
              "</span><strong>" +
              escapeHtml(String(q.price ?? "")) +
              escapeHtml(unit) +
              '</strong> <span class="' +
              cls +
              '">' +
              (chg >= 0 ? "+" : "") +
              chg.toFixed(2) +
              "%</span></li>"
            );
          })
          .join("");
      }
    }
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML = '<li class="stock-empty">국채·회사채·금리곡선 해석</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const topic = escapeHtml(it.topic || "");
        const tit = escapeHtml((it.title || "").slice(0, 72));
        const snip = it.snippet
          ? '<br><span class="stock-snippet">' +
            escapeHtml(it.snippet.slice(0, 100)) +
            "…</span>"
          : "";
        const link = it.url
          ? '<a href="' +
            escapeHtml(it.url) +
            '" rel="noopener noreferrer" target="_blank">' +
            tit +
            "</a>"
          : tit;
        return (
          "<li><span class=\"stock-macro-topic\">[" +
          topic +
          "]</span> " +
          link +
          snip +
          "</li>"
        );
      })
      .join("");
  }

  function renderOilWar(block) {
    const tsEl = document.getElementById("stock-oil-war-ts");
    const quotesEl = document.getElementById("stock-oil-war-quotes");
    const list = document.getElementById("stock-oil-war-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    const quotes = block.oil_quotes || [];
    if (quotesEl) {
      if (!quotes.length) {
        quotesEl.innerHTML = '<li class="stock-empty">WTI·브렌트 원유</li>';
      } else {
        quotesEl.innerHTML = quotes
          .map(function (q) {
            const chg = Number(q.change_pct || 0);
            const cls = chg > 0 ? "stock-up" : chg < 0 ? "stock-down" : "";
            return (
              "<li><span class=\"stock-oil-name\">" +
              escapeHtml(q.name || "") +
              "</span><strong>" +
              escapeHtml(String(q.price ?? "")) +
              '</strong> <span class="' +
              cls +
              '">' +
              (chg >= 0 ? "+" : "") +
              chg.toFixed(2) +
              "%</span></li>"
            );
          })
          .join("");
      }
    }
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML =
        '<li class="stock-empty">지정학·공급·유가→증시 해석</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const topic = escapeHtml(it.topic || "");
        const tit = escapeHtml((it.title || "").slice(0, 72));
        const snip = it.snippet
          ? '<br><span class="stock-snippet">' +
            escapeHtml(it.snippet.slice(0, 100)) +
            "…</span>"
          : "";
        const link = it.url
          ? '<a href="' +
            escapeHtml(it.url) +
            '" rel="noopener noreferrer" target="_blank">' +
            tit +
            "</a>"
          : tit;
        return (
          "<li><span class=\"stock-macro-topic\">[" +
          topic +
          "]</span> " +
          link +
          snip +
          "</li>"
        );
      })
      .join("");
  }

  function renderCommodities(block) {
    const tsEl = document.getElementById("stock-commodity-ts");
    const quotesEl = document.getElementById("stock-commodity-quotes");
    const list = document.getElementById("stock-commodity-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    const quotes = block.quotes || [];
    if (quotesEl) {
      if (!quotes.length) {
        quotesEl.innerHTML = '<li class="stock-empty">유가·금·구리·가스 시세</li>';
      } else {
        quotesEl.innerHTML = quotes
          .map(function (q) {
            const chg = Number(q.change_pct || 0);
            const cls = chg > 0 ? "stock-up" : chg < 0 ? "stock-down" : "";
            return (
              "<li><span class=\"stock-commodity-name\">" +
              escapeHtml(q.name || q.symbol || "") +
              "</span><strong>" +
              escapeHtml(String(q.price ?? "")) +
              '</strong> <span class="' +
              cls +
              '">' +
              (chg >= 0 ? "+" : "") +
              chg.toFixed(2) +
              "%</span></li>"
            );
          })
          .join("");
      }
    }
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML =
        '<li class="stock-empty">원자재 동향·증시 영향 해석</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const topic = escapeHtml(it.topic || "");
        const tit = escapeHtml((it.title || "").slice(0, 72));
        const snip = it.snippet
          ? '<br><span class="stock-snippet">' +
            escapeHtml(it.snippet.slice(0, 100)) +
            "…</span>"
          : "";
        const link = it.url
          ? '<a href="' +
            escapeHtml(it.url) +
            '" rel="noopener noreferrer" target="_blank">' +
            tit +
            "</a>"
          : tit;
        return (
          "<li><span class=\"stock-macro-topic\">[" +
          topic +
          "]</span> " +
          link +
          snip +
          "</li>"
        );
      })
      .join("");
  }

  const rlMarket = {
    items: [],
    tab: "all",
    search: "",
    sort: "conf_desc",
  };

  function predBadge(pred, predKo) {
    const p = pred || "flat";
    const label = escapeHtml(predKo || (p === "up" ? "상승" : p === "down" ? "하락" : "횡보"));
    return (
      '<span class="stock-rl-badge stock-rl-badge--' +
      escapeHtml(p) +
      '">' +
      label +
      "</span>"
    );
  }

  function poolLabel(bucket) {
    if (bucket === "kospi200") return "K200";
    if (bucket === "kosdaq150") return "KQ150";
    return "";
  }

  function filterRlItems(items) {
    let rows = items.slice();
    const tab = rlMarket.tab;
    if (tab === "kospi200" || tab === "kosdaq150") {
      rows = rows.filter(function (it) {
        return it.bucket === tab;
      });
    } else if (tab === "up" || tab === "down" || tab === "flat") {
      rows = rows.filter(function (it) {
        return (it.predicted || "flat") === tab;
      });
    }
    const t = (rlMarket.search || "").trim().toLowerCase();
    if (t) {
      rows = rows.filter(function (it) {
        return (
          String(it.name || "").toLowerCase().indexOf(t) >= 0 ||
          String(it.symbol || "").toLowerCase().indexOf(t) >= 0
        );
      });
    }
    if (rlMarket.sort === "name") {
      rows.sort(function (a, b) {
        return String(a.name || "").localeCompare(String(b.name || ""), "ko");
      });
    } else if (rlMarket.sort === "chg_desc") {
      rows.sort(function (a, b) {
        return Math.abs(Number(b.change_pct) || 0) - Math.abs(Number(a.change_pct) || 0);
      });
    } else {
      rows.sort(function (a, b) {
        return (Number(b.confidence) || 0) - (Number(a.confidence) || 0);
      });
    }
    return rows;
  }

  function renderRlSummary(items, stats) {
    const sumEl = document.getElementById("stock-rl-summary");
    const statEl = document.getElementById("stock-rl-stats");
    let up = 0;
    let down = 0;
    let flat = 0;
    items.forEach(function (it) {
      const p = it.predicted || "flat";
      if (p === "up") up++;
      else if (p === "down") down++;
      else flat++;
    });
    if (sumEl) {
      sumEl.innerHTML =
        '<span class="stock-rl-chip stock-rl-chip--up">상승 <strong>' +
        up +
        '</strong></span><span class="stock-rl-chip stock-rl-chip--down">하락 <strong>' +
        down +
        '</strong></span><span class="stock-rl-chip stock-rl-chip--flat">횡보 <strong>' +
        flat +
        "</strong></span>";
    }
    if (statEl && stats) {
      const hit = Number(stats.hits) || 0;
      const settled = Number(stats.settled) || 0;
      const acc = settled > 0 ? Math.round((hit / settled) * 100) : null;
      statEl.innerHTML =
        settled > 0
          ? "누적 적중 " + hit + "/" + settled + (acc != null ? " (" + acc + "%)" : "")
          : "학습 데이터 수집 중";
    }
  }

  function renderRlTable() {
    const body = document.getElementById("stock-rl-body");
    const countEl = document.getElementById("stock-rl-row-count");
    if (!body) return;
    const rows = filterRlItems(rlMarket.items);
    if (countEl) countEl.textContent = rows.length + "건";
    if (!rows.length) {
      body.innerHTML =
        '<tr><td colspan="4" class="stock-empty">조건에 맞는 예측이 없습니다.</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map(function (it) {
        const pct = Number(it.change_pct) || 0;
        const conf = Math.round(Number(it.confidence || 0) * 100);
        const pool = poolLabel(it.bucket);
        return (
          '<tr class="rl-' +
          escapeHtml(it.predicted || "flat") +
          '"><td class="col-name"><strong>' +
          escapeHtml(it.name || it.symbol) +
          "</strong>" +
          (pool ? '<span class="stock-rl-pool">' + pool + "</span>" : "") +
          '</td><td class="col-pred">' +
          predBadge(it.predicted, it.predicted_ko) +
          '</td><td class="col-conf"><div class="stock-rl-conf-wrap">' +
          '<span class="stock-rl-conf-pct">' +
          conf +
          '%</span><span class="stock-rl-conf-bar" aria-hidden="true"><span style="width:' +
          conf +
          '%"></span></span></div></td><td class="col-chg ' +
          chgClass(pct) +
          '">' +
          (pct >= 0 ? "+" : "") +
          pct.toFixed(2) +
          "%</td></tr>"
        );
      })
      .join("");
  }

  function bindRlToolbar() {
    document.querySelectorAll("[data-rl-tab]").forEach(function (btn) {
      if (btn._rlBound) return;
      btn._rlBound = true;
      btn.addEventListener("click", function () {
        document.querySelectorAll("[data-rl-tab]").forEach(function (b) {
          b.classList.remove("is-active");
        });
        btn.classList.add("is-active");
        rlMarket.tab = btn.getAttribute("data-rl-tab") || "all";
        renderRlTable();
      });
    });
    const search = document.getElementById("stock-rl-search");
    if (search && !search._rlBound) {
      search._rlBound = true;
      search.addEventListener("input", function () {
        rlMarket.search = search.value;
        renderRlTable();
      });
    }
    const sort = document.getElementById("stock-rl-sort");
    if (sort && !sort._rlBound) {
      sort._rlBound = true;
      sort.addEventListener("change", function () {
        rlMarket.sort = sort.value;
        renderRlTable();
      });
    }
  }

  function renderRlPredictions(block) {
    const tsEl = document.getElementById("stock-rl-ts");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    rlMarket.items = (block.items || []).filter(function (it) {
      return (
        it.bucket === "kospi200" ||
        it.bucket === "kosdaq150" ||
        it.bucket === "watchlist" ||
        !it.bucket
      );
    });
    const stats = (block.stats && typeof block.stats === "object") ? block.stats : {};
    renderRlSummary(rlMarket.items, stats);
    bindRlToolbar();
    renderRlTable();
  }

  function renderAnalystReports(block) {
    const tsEl = document.getElementById("stock-analyst-ts");
    const list = document.getElementById("stock-analyst-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML = '<li class="stock-empty">리포트·목표가·투자의견</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const company = it.company
          ? '<span class="stock-analyst-company">' +
            escapeHtml(it.company) +
            (it.market_change_pct != null
              ? " <small>(" +
                (Number(it.market_change_pct) >= 0 ? "+" : "") +
                Number(it.market_change_pct).toFixed(2) +
                "%)</small>"
              : "") +
            "</span>"
          : "";
        const broker = it.broker
          ? '<span class="stock-analyst-broker">' + escapeHtml(it.broker) + "</span>"
          : "";
        const tp = it.target_price
          ? '<span class="stock-analyst-tp">목표 ' +
            escapeHtml(it.target_price) +
            "</span>"
          : "";
        const topic = escapeHtml(it.topic || "");
        const tit = escapeHtml((it.title || "").slice(0, 68));
        const snip = it.snippet
          ? '<br><span class="stock-snippet">' +
            escapeHtml(it.snippet.slice(0, 90)) +
            "…</span>"
          : "";
        const link = it.url
          ? '<a href="' +
            escapeHtml(it.url) +
            '" rel="noopener noreferrer" target="_blank">' +
            tit +
            "</a>"
          : tit;
        return (
          '<li class="stock-analyst-item">' +
          company +
          broker +
          tp +
          '<span class="stock-macro-topic">[' +
          topic +
          "]</span> " +
          link +
          snip +
          "</li>"
        );
      })
      .join("");
  }

  function renderYoutube(block) {
    const tsEl = document.getElementById("stock-youtube-ts");
    const list = document.getElementById("stock-youtube-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML =
        '<li class="stock-empty">증시·매크로·종목·CEO 관련 영상</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const topic = escapeHtml(it.topic || "");
        const tit = escapeHtml((it.title || "").slice(0, 70));
        const snip = it.snippet
          ? '<br><span class="stock-snippet">' +
            escapeHtml(it.snippet.slice(0, 90)) +
            "…</span>"
          : "";
        const link = it.url
          ? '<a href="' +
            escapeHtml(it.url) +
            '" rel="noopener noreferrer" target="_blank" class="stock-yt-link">▶ ' +
            tit +
            "</a>"
          : tit;
        return (
          '<li class="stock-youtube-item"><span class="stock-macro-topic">[' +
          topic +
          "]</span> " +
          link +
          snip +
          "</li>"
        );
      })
      .join("");
  }

  function renderCeoRemarks(block) {
    const tsEl = document.getElementById("stock-ceo-ts");
    const list = document.getElementById("stock-ceo-list");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML =
        '<li class="stock-empty">관심종목·대형주 CEO 발언·실적 코멘트</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const company = it.company
          ? '<span class="stock-ceo-company">' +
            escapeHtml(it.company) +
            (it.market_change_pct != null
              ? " <small>(" +
                (Number(it.market_change_pct) >= 0 ? "+" : "") +
                Number(it.market_change_pct).toFixed(2) +
                "%)</small>"
              : "") +
            "</span>"
          : "";
        const exec = it.executive
          ? '<span class="stock-ceo-exec">' + escapeHtml(it.executive) + "</span>"
          : "";
        const topic = escapeHtml(it.topic || "");
        const tit = escapeHtml((it.title || "").slice(0, 68));
        const link = it.url
          ? '<a href="' +
            escapeHtml(it.url) +
            '" rel="noopener noreferrer" target="_blank">' +
            tit +
            "</a>"
          : tit;
        let quote = "";
        if (it.quote) {
          const q = escapeHtml(it.quote.slice(0, 120));
          quote =
            '<p class="stock-ceo-quote">「' +
            q +
            (it.quote.length > 120 ? "…" : "") +
            "」</p>";
        } else if (it.snippet) {
          quote =
            '<p class="stock-ceo-quote"><span class="stock-snippet">' +
            escapeHtml(it.snippet.slice(0, 100)) +
            "…</span></p>";
        }
        return (
          '<li class="stock-ceo-item">' +
          company +
          exec +
          '<span class="stock-macro-topic">[' +
          topic +
          "]</span> " +
          link +
          quote +
          "</li>"
        );
      })
      .join("");
  }

  function renderCommentVerify(block) {
    const list = document.getElementById("stock-comments-list");
    const tsEl = document.getElementById("stock-comments-ts");
    if (tsEl && block.ts) tsEl.textContent = block.ts;
    if (!list) return;
    const items = block.items || [];
    if (!items.length) {
      list.innerHTML =
        '<li class="stock-empty">증시 관련 최근 댓글이 없거나 아직 검증 전입니다.</li>';
      return;
    }
    list.innerHTML = items
      .map(function (it) {
        const sources = (it.web_sources || [])
          .slice(0, 2)
          .map(function (s) {
            return (
              "<li><a href=\"" +
              escapeHtml(s.url) +
              '" rel="noopener noreferrer" target="_blank">' +
              escapeHtml((s.title || "").slice(0, 56)) +
              "</a> <span class=\"stock-snippet\">(" +
              escapeHtml(s.provider || "") +
              ")</span></li>"
            );
          })
          .join("");
        return (
          '<li class="stock-comment-item stock-comment-item--' +
          escapeHtml(it.verdict || "") +
          '">' +
          '<div class="stock-comment-head"><span class="stock-comment-verdict">' +
          escapeHtml(it.verdict) +
          '</span><span class="stock-comment-meta">글#' +
          escapeHtml(it.post_id) +
          " · 댓글#" +
          escapeHtml(it.comment_id) +
          " · " +
          escapeHtml(it.author) +
          "</span></div>" +
          '<p class="stock-comment-excerpt">「' +
          escapeHtml(it.excerpt) +
          "」</p>" +
          '<p class="stock-comment-detail">' +
          escapeHtml(it.verdict_detail) +
          "</p>" +
          '<p class="stock-comment-market"><small>시세: ' +
          escapeHtml(it.market_check) +
          "</small></p>" +
          (sources ? '<ul class="stock-comment-sources">' + sources + "</ul>" : "") +
          "</li>"
        );
      })
      .join("");
  }

  window.refreshStockWatch = function () {
    return fetch("/api/agents/office/stock-watch.json", {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        if (r.status === 401) {
          window.location.href =
            "/agents/office/login?next=" + encodeURIComponent(window.location.pathname);
          return null;
        }
        return r.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return;
        const snap = data.snapshot || {};
        applyMarketSnapshot(snap, data.stats || {});
        const alertsList = document.getElementById("stock-alerts-list");
        if (alertsList) alertsList.innerHTML = renderAlerts(snap.alerts);
        renderInsights(data.insights || {});
        const updated = document.getElementById("stock-watch-updated");
        if (updated) updated.textContent = (data.stats && data.stats.updated_at) || "미수집";
        const tabBadge = document.getElementById("stock-watch-tab-badge");
        if (tabBadge && data.stats && data.stats.updated_at) {
          tabBadge.textContent = data.stats.updated_at.slice(-5);
        }
        const live = document.getElementById("stock-office-live-status");
        if (live) {
          live.classList.add("is-on");
          live.classList.remove("is-off");
          live.textContent = data.stats.last_sync_ok ? "연결됨" : "수집 대기";
        }
      })
      .catch(function () {
        const live = document.getElementById("stock-office-live-status");
        if (live) {
          live.classList.add("is-off");
          live.classList.remove("is-on");
          live.textContent = "오프라인";
        }
      });
  };

  window.refreshStockFeed = function (forceScrollTop) {
    const feed = document.getElementById("stock-agent-office-feed");
    if (!feed) return Promise.resolve();
    return fetch("/api/agents/office.json", { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        const raw =
          data.stock_messages && data.stock_messages.length
            ? data.stock_messages
            : (data.messages || []).filter(function (m) {
                return window.messageForUnit && window.messageForUnit(m, "stock-watch");
              });
        if (!raw.length) {
          feed.innerHTML =
            '<p class="office-empty">아직 주식 시황부 로그가 없습니다.</p>';
          return;
        }
        if (typeof window.renderMessage === "function") {
          feed.innerHTML = raw.map(window.renderMessage).join("");
        }
        if (forceScrollTop) feed.scrollTop = 0;
      })
      .catch(function () {});
  };

  document.addEventListener("DOMContentLoaded", function () {
    const officialBtn = document.getElementById("stock-official-research-btn");
    if (officialBtn) {
      officialBtn.addEventListener("click", function () {
        officialBtn.disabled = true;
        officialBtn.textContent = "조사 중…";
        const headers = { "Content-Type": "application/json" };
        if (window.CSRF_TOKEN) headers["X-CSRFToken"] = window.CSRF_TOKEN;
        fetch("/api/agents/office/stock-watch/official-research", {
          method: "POST",
          credentials: "same-origin",
          headers: headers,
        })
          .then(function (r) {
            return r.json();
          })
          .then(function () {
            return window.refreshStockWatch();
          })
          .finally(function () {
            officialBtn.disabled = false;
            officialBtn.textContent = "공시·정부·기사";
          });
      });
    }

    const verifyBtn = document.getElementById("stock-comments-verify-btn");
    if (verifyBtn) {
      verifyBtn.addEventListener("click", function () {
        verifyBtn.disabled = true;
        verifyBtn.textContent = "검증 중…";
        const headers = { "Content-Type": "application/json" };
        if (window.CSRF_TOKEN) headers["X-CSRFToken"] = window.CSRF_TOKEN;
        fetch("/api/agents/office/stock-watch/verify-comments", {
          method: "POST",
          credentials: "same-origin",
          headers: headers,
        })
          .then(function (r) {
            return r.json();
          })
          .then(function () {
            return window.refreshStockWatch();
          })
          .then(function () {
            return window.refreshStockFeed(true);
          })
          .finally(function () {
            verifyBtn.disabled = false;
            verifyBtn.textContent = "댓글 검증";
          });
      });
    }

    bindKrToolbar();
    bindRlToolbar();
    if (typeof window.refreshStockWatch === "function") {
      window.refreshStockWatch();
    }

    const syncBtn = document.getElementById("stock-watch-sync-btn");
    if (syncBtn) {
      syncBtn.addEventListener("click", function () {
        syncBtn.disabled = true;
        syncBtn.textContent = "수집 중…";
        const headers = { "Content-Type": "application/json" };
        if (window.CSRF_TOKEN) headers["X-CSRFToken"] = window.CSRF_TOKEN;
        fetch("/api/agents/office/stock-watch/sync", {
          method: "POST",
          credentials: "same-origin",
          headers: headers,
        })
          .then(function (r) {
            return r.json();
          })
          .then(function () {
            return window.refreshStockWatch();
          })
          .then(function () {
            return window.refreshStockFeed(true);
          })
          .finally(function () {
            syncBtn.disabled = false;
            syncBtn.textContent = "지금 수집";
          });
      });
    }
  });
})();
