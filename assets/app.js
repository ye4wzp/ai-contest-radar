(function () {
  var DATA = window.__DATA__ || { updated: "", competitions: [] };
  var TODAY = new Date(); TODAY.setHours(0, 0, 0, 0);
  var MS_DAY = 864e5;

  var STATUS = {
    open:     { label: "报名中",   order: 0 },
    upcoming: { label: "即将开始", order: 1 },
    running:  { label: "进行中",   order: 2 },
    tbd:      { label: "日期待定", order: 3 },
    ended:    { label: "已结束",   order: 4 }
  };

  function parse(d) { return d ? new Date(d + "T00:00:00") : null; }
  function fmt(d) { return d ? d.replace(/-/g, ".") : "待定"; }
  function daysTo(d) { return Math.ceil((parse(d) - TODAY) / MS_DAY); }

  function statusOf(c) {
    var s = parse(c.start), dl = parse(c.deadline), e = parse(c.end);
    var final = e || dl;
    if (!dl && !s) return "tbd";
    if (final && TODAY > final) return "ended";
    if (s && TODAY < s) return "upcoming";
    if (dl && TODAY <= dl) return "open";
    if (e && TODAY <= e) return "running";
    return "tbd";
  }

  var comps = DATA.competitions.map(function (c) {
    c._status = statusOf(c);
    c._days = c.deadline ? daysTo(c.deadline) : null;
    return c;
  });

  // ── 状态 ──
  var state = { q: "", status: "all", type: "all", sort: "deadline", view: "list" };
  var calCursor = new Date(TODAY.getFullYear(), TODAY.getMonth(), 1);

  // ── 报头 ──
  var weekdays = ["日", "一", "二", "三", "四", "五", "六"];
  document.getElementById("today-line").textContent =
    TODAY.getFullYear() + " 年 " + (TODAY.getMonth() + 1) + " 月 " + TODAY.getDate() + " 日 · 星期" + weekdays[TODAY.getDay()];
  document.getElementById("updated-line").textContent = "数据更新于 " + DATA.updated + " · 共收录 " + comps.length + " 场赛事";

  var openCount = comps.filter(function (c) { return c._status === "open"; }).length;
  var weekCount = comps.filter(function (c) { return c._status === "open" && c._days !== null && c._days <= 7; }).length;
  document.getElementById("stats").innerHTML =
    '<div class="stat"><b>' + comps.length + '</b><span>收录赛事</span></div>' +
    '<div class="stat"><b>' + openCount + '</b><span>报名/进行中</span></div>' +
    '<div class="stat hot"><b>' + weekCount + '</b><span>7 天内截止</span></div>';

  // ── 筛选 chips ──
  function chips(el, items, key) {
    el.innerHTML = items.map(function (it) {
      return '<button class="chip' + (it.value === state[key] ? " active" : "") + '" data-value="' + it.value + '">' + it.label + "</button>";
    }).join("");
    el.onclick = function (ev) {
      var b = ev.target.closest(".chip");
      if (!b) return;
      state[key] = b.dataset.value;
      el.querySelectorAll(".chip").forEach(function (x) { x.classList.toggle("active", x === b); });
      render();
    };
  }

  chips(document.getElementById("status-chips"),
    [{ value: "all", label: "全部" }].concat(Object.keys(STATUS).map(function (k) {
      return { value: k, label: STATUS[k].label };
    })), "status");

  var typeCounts = {};
  comps.forEach(function (c) { typeCounts[c.type] = (typeCounts[c.type] || 0) + 1; });
  var topTypes = Object.keys(typeCounts).sort(function (a, b) { return typeCounts[b] - typeCounts[a]; }).slice(0, 5);
  chips(document.getElementById("type-chips"),
    [{ value: "all", label: "所有类型" }].concat(topTypes.map(function (t) {
      return { value: t, label: t + " " + typeCounts[t] };
    })), "type");

  document.getElementById("q").oninput = function () { state.q = this.value.trim().toLowerCase(); render(); };
  document.getElementById("sort").onchange = function () { state.sort = this.value; render(); };

  document.getElementById("view-toggle").onclick = function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    state.view = b.dataset.view;
    this.querySelectorAll("button").forEach(function (x) { x.classList.toggle("active", x === b); });
    render();
  };

  // ── 过滤与排序 ──
  function filtered() {
    return comps.filter(function (c) {
      if (state.status !== "all" && c._status !== state.status) return false;
      if (state.type !== "all" && c.type !== state.type) return false;
      if (state.q) {
        var hay = (c.name + " " + (c.organizer || "") + " " + c.tags.join(" ") + " " + (c.city || "")).toLowerCase();
        if (hay.indexOf(state.q) < 0) return false;
      }
      return true;
    }).sort(function (a, b) {
      if (state.sort === "name") return a.name.localeCompare(b.name, "zh");
      if (state.sort === "start") return (a.start || "9999") < (b.start || "9999") ? -1 : 1;
      var d = STATUS[a._status].order - STATUS[b._status].order;
      if (d) return d;
      return (a.deadline || "9999") < (b.deadline || "9999") ? -1 : 1;
    });
  }

  // ── 卡片 ──
  function badge(c) {
    var s = c._status;
    if (s === "open" && c._days !== null && c._days <= 7)
      return '<span class="badge urgent">急 · ' + (c._days === 0 ? "今天" : c._days + " 天后") + "截止</span>";
    return '<span class="badge ' + s + '">' + STATUS[s].label + "</span>";
  }

  function countdown(c) {
    if (c._status !== "open" || c._days === null) return "";
    var cls = c._days > 30 ? " far" : "";
    return '<span class="countdown' + cls + '">D-' + c._days + "</span>";
  }

  function cardHTML(c, i) {
    return '<article class="card' + (c.featured ? " featured" : "") + '" data-id="' + c.id + '" style="animation-delay:' + Math.min(i * 30, 400) + 'ms">' +
      '<div class="card-top">' + badge(c) + countdown(c) + "</div>" +
      '<h3 class="card-name">' + esc(c.name) + "</h3>" +
      (c.organizer ? '<div class="card-org">主办：' + esc(c.organizer) + "</div>" : "") +
      '<div class="card-tags">' + c.tags.slice(0, 4).map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") +
      (c.city ? '<span class="tag">' + esc(c.city) + "</span>" : "") + "</div>" +
      '<div class="card-dates"><span>' + fmt(c.start) + " → " + fmt(c.deadline) + "</span>" +
      (c.prize ? '<span class="card-prize">' + esc(c.prize) + "</span>" : "") + "</div>" +
      "</article>";
  }

  function esc(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); }

  // ── 渲染 ──
  function render() {
    var list = filtered();
    var isList = state.view === "list";
    document.getElementById("list-view").hidden = !isList;
    document.getElementById("featured-section").hidden = !isList;
    document.getElementById("calendar-view").hidden = isList;
    if (isList) {
      var feat = list.filter(function (c) { return c.featured; });
      var rest = list.filter(function (c) { return !c.featured; });
      document.getElementById("featured-section").hidden = !feat.length;
      document.getElementById("featured-grid").innerHTML = feat.map(cardHTML).join("");
      document.getElementById("card-grid").innerHTML = rest.map(cardHTML).join("");
      document.getElementById("list-count").textContent = "共 " + rest.length + " 场";
      document.getElementById("empty").hidden = list.length > 0;
    } else {
      renderCalendar(list);
    }
  }

  // ── 日历 ──
  function renderCalendar(list) {
    var y = calCursor.getFullYear(), m = calCursor.getMonth();
    document.getElementById("cal-title").textContent = y + " 年 " + (m + 1) + " 月";

    var byDay = {};
    list.forEach(function (c) {
      [["deadline", "deadline"], ["start", "start"]].forEach(function (p) {
        var v = c[p[0]];
        if (v) (byDay[v] = byDay[v] || []).push({ c: c, kind: p[1] });
      });
    });

    var first = new Date(y, m, 1), startPad = first.getDay();
    var daysInMonth = new Date(y, m + 1, 0).getDate();
    var html = weekdays.map(function (w) { return '<div class="cal-dow">' + w + "</div>"; }).join("");

    for (var i = 0; i < startPad; i++) html += '<div class="cal-cell other"></div>';
    for (var d = 1; d <= daysInMonth; d++) {
      var iso = y + "-" + String(m + 1).padStart(2, "0") + "-" + String(d).padStart(2, "0");
      var items = (byDay[iso] || []).filter(function (x) { return x.kind === "deadline"; })
        .concat((byDay[iso] || []).filter(function (x) { return x.kind === "start"; }));
      var isToday = parse(iso).getTime() === TODAY.getTime();
      html += '<div class="cal-cell' + (isToday ? " today-cell" : "") + '"><div class="cal-day">' + d + "</div>";
      items.slice(0, 3).forEach(function (x) {
        html += '<button class="cal-item' + (x.kind === "start" ? " start-mark" : "") + '" data-id="' + x.c.id + '" title="' +
          esc(x.c.name) + (x.kind === "start" ? "（开始）" : "（截止）") + '">' +
          (x.kind === "start" ? "始 " : "止 ") + esc(x.c.name) + "</button>";
      });
      if (items.length > 3) html += '<div class="cal-more">+' + (items.length - 3) + " 场</div>";
      html += "</div>";
    }
    document.getElementById("cal-grid").innerHTML = html;
  }

  document.getElementById("cal-prev").onclick = function () { calCursor.setMonth(calCursor.getMonth() - 1); render(); };
  document.getElementById("cal-next").onclick = function () { calCursor.setMonth(calCursor.getMonth() + 1); render(); };

  // ── 详情弹窗 ──
  var modal = document.getElementById("modal");
  document.body.addEventListener("click", function (ev) {
    var el = ev.target.closest("[data-id]");
    if (!el) return;
    var c = comps.find(function (x) { return x.id === el.dataset.id; });
    if (c) openModal(c);
  });

  function openModal(c) {
    var rows = [
      ["状态", badge(c) + " " + countdown(c)],
      ["主办方", esc(c.organizer || "见官方页面")],
      ["时间", '<span class="mono">' + fmt(c.start) + " → " + fmt(c.deadline) + (c.end && c.end !== c.deadline ? "（决赛/结束 " + fmt(c.end) + "）" : "") + "</span>"],
      ["奖金", c.prize ? '<b style="color:var(--vermilion)">' + esc(c.prize) + "</b>" : "见官方页面"],
      ["类型", esc(c.type) + (c.city ? " · " + esc(c.city) : "")],
      ["标签", c.tags.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join(" ")]
    ];
    document.getElementById("modal-body").innerHTML =
      "<h3>" + esc(c.name) + "</h3>" +
      '<table class="modal-table">' + rows.map(function (r) {
        return "<tr><td>" + r[0] + "</td><td>" + r[1] + "</td></tr>";
      }).join("") + "</table>" +
      (c.description ? '<p class="modal-desc">' + esc(c.description) + "</p>" : "") +
      '<div class="modal-actions">' +
      (c.official_url ? '<a class="btn primary" href="' + esc(c.official_url) + '" target="_blank" rel="noopener">前往官方页面 ↗</a>' : "") +
      c.sources.map(function (s) {
        return '<a class="btn" href="' + esc(s.url) + '" target="_blank" rel="noopener">来源：' + esc(s.name) + " ↗</a>";
      }).join("") + "</div>";
    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal() { modal.hidden = true; document.body.style.overflow = ""; }
  document.getElementById("modal-close").onclick = closeModal;
  modal.onclick = function (ev) { if (ev.target === modal) closeModal(); };
  document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") closeModal(); });

  render();
})();
