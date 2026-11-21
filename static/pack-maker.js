// Packing list maker: builds a checklist from data/packing.json (embedded in the page as #pm-data).
// An item shows when any of its condition sets matches the choices; counts follow the days, up to the item's cap.
// Choices and ticks are saved in this browser only.
(function () {
  var form = document.getElementById("pm");
  var dataEl = document.getElementById("pm-data");
  if (!form || !dataEl) return;
  var data = JSON.parse(dataEl.textContent);
  // The Hindi page passes its own words in data.t; {x} marks a value filled in below.
  var T = Object.assign({ perAdult: " (for each adult)", by: { flight: "by flight", train: "by train", road: "by car or bus" },
    day: " day", days: " days", abroad: ", abroad", ready: "Ready-made checklist: ", guides: "Packing guides for this trip",
    picks: "Our picks for this trip", title: "Your packing list: {s}", packed: "{done} of {total} packed",
    list: "Packing list: {s}", make: "Make your own list: ", copied: "List copied. Paste it in a note or a chat.",
    nocopy: "Couldn't copy here. Select the list and copy it by hand." }, data.t || {});
  function say(key, v) { return T[key].replace(/\{(\w+)\}/g, function (m, n) { return v && n in v ? v[n] : m; }); }
  var KEY = "cp_packmaker_v1";
  var rules = { per_day: function (n) { return n; }, per_day_plus_1: function (n) { return n + 1; },
                per_day_plus_2: function (n) { return n + 2; }, per_2_days: function (n) { return n / 2; },
                per_3_days: function (n) { return n / 3; }, six_per_day: function (n) { return 6 * n; } };
  var $ = function (id) { return document.getElementById(id); };
  var type = $("pm-type"), days = $("pm-days"), month = $("pm-month");
  var out = $("pm-out"), list = $("pm-list");
  var shown = [];

  function load() { try { return JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (err) { return {}; } }
  var saved = load();
  var ticks = saved.ticks || {};
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ choice: choice(), ticks: ticks })); } catch (err) { /* private mode */ }
  }

  function radio(name) { var r = form.querySelector("input[name=" + name + "]:checked"); return r ? r.value : ""; }
  function choice() {
    var n = Math.min(30, Math.max(1, parseInt(days.value, 10) || 1));
    var who = [].slice.call(form.querySelectorAll("input[name=who]:checked")).map(function (b) { return b.value; });
    return { type: type.value, days: n, month: month.value, season: data.seasons[month.value], who: who,
             by: radio("by"), where: radio("where") };
  }
  function match(sets, c) {
    return sets.some(function (set) {
      return Object.keys(set).every(function (k) {
        if (k === "min_days") return c.days >= set[k];
        if (k === "who") return set[k].some(function (v) { return c.who.indexOf(v) >= 0; });
        return set[k].indexOf(c[k]) >= 0;
      });
    });
  }
  function qty(item, n) {
    if (item.qty === undefined) return 0;
    var v = typeof item.qty === "number" ? item.qty : Math.ceil(rules[item.qty](n) - 1e-9);
    v = Math.max(1, v);
    return item.cap ? Math.min(item.cap, v) : v;
  }
  function el(tag, cls, text) {
    var x = document.createElement(tag);
    if (cls) x.className = cls;
    if (text) x.textContent = text;
    return x;
  }
  function label(list, slug) {
    for (var i = 0; i < list.length; i++) if (list[i].slug === slug) return list[i].label;
    return slug;
  }
  function links(rows, c) {
    var seen = {}, res = [];
    rows.forEach(function (r) {
      if (!match(r.when, c)) return;
      r.links.forEach(function (l) { if (!seen[l[0]]) { seen[l[0]] = 1; res.push(l); } });
    });
    return res;
  }
  function linkList(title, rows) {
    if (!rows.length) return null;
    var box = el("section", "pm-links");
    box.appendChild(el("h2", "", title));
    var ul = el("ul", "airline-links");
    rows.forEach(function (l) {
      var li = el("li"), a = el("a", "", l[1]);
      a.href = l[0];
      li.appendChild(a);
      ul.appendChild(li);
    });
    box.appendChild(ul);
    return box;
  }
  function summary(c) {
    var t = label(data.types, c.type);
    var by = T.by[c.by] || "";
    var month = form.querySelector("#pm-month option[value='" + c.month + "']").textContent;
    return t + ", " + c.days + (c.days === 1 ? T.day : T.days) + ", " + month + ", " + by +
      (c.where === "abroad" && c.type !== "abroad" ? T.abroad : "");
  }

  function render() {
    var c = choice();
    var abroadOnly = data.types.some(function (t) { return t.slug === c.type && t.where === "abroad"; });
    var india = form.querySelector("input[name=where][value=india]");
    india.disabled = abroadOnly;
    if (abroadOnly && c.where !== "abroad") {
      form.querySelector("input[name=where][value=abroad]").checked = true;
      c.where = "abroad";
    }
    var people = c.who.length;
    list.textContent = "";
    shown = [];
    data.groups.forEach(function (g) {
      var items = g.items.filter(function (i) { return match(i.when, c); });
      if (!items.length) return;
      var sec = el("section", "pack-group");
      var perPerson = (g.key || g.name) === "Clothes" && people > 1 && (c.who.indexOf("men") >= 0 || c.who.indexOf("women") >= 0);
      sec.appendChild(el("h2", "", g.name + (perPerson ? T.perAdult : "")));
      var ul = el("ul");
      items.forEach(function (i) {
        var q = qty(i, c.days);
        shown.push({ id: i.id, name: i.name, q: q, group: g.name });
        var li = el("li"), lab = el("label"), box = el("input");
        box.type = "checkbox";
        box.setAttribute("data-id", i.id);
        box.checked = !!ticks[i.id];
        lab.appendChild(box);
        lab.appendChild(document.createTextNode(" "));
        lab.appendChild(el("span", "", i.name));
        if (q) { lab.appendChild(document.createTextNode(" ")); lab.appendChild(el("b", "pk-qty", "× " + q)); }
        li.appendChild(lab);
        if (i.href) {
          var a = el("a", "pk-more", i.more);
          a.href = i.href;
          li.appendChild(document.createTextNode(" "));
          li.appendChild(a);
        }
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      list.appendChild(sec);
    });

    var notes = $("pm-notes");
    notes.textContent = "";
    data.notes.forEach(function (n) {
      if (!match(n.when, c)) return;
      var p = el("p");
      p.innerHTML = n.html; // trusted text from data/packing.json
      notes.appendChild(p);
    });
    notes.hidden = !notes.childNodes.length;

    var after = $("pm-after");
    after.textContent = "";
    var g = links(data.guides, c);
    var t = data.types.filter(function (x) { return x.slug === c.type; })[0];
    if (t && !g.some(function (l) { return l[0] === t.list; })) g.push([t.list, T.ready + t.list_label]);
    var box = linkList(T.guides, g);
    if (box) after.appendChild(box);
    box = linkList(T.picks, links(data.shop, c));
    if (box) after.appendChild(box);

    $("pm-title").textContent = say("title", { s: summary(c) });
    count();
    share();
    save();
  }
  function count() {
    var done = shown.filter(function (s) { return ticks[s.id]; }).length;
    $("pm-count").textContent = say("packed", { done: done, total: shown.length });
  }
  function text() {
    var lines = [say("list", { s: summary(choice()) }), ""], group = "";
    shown.forEach(function (s) {
      if (s.group !== group) { if (group) lines.push(""); group = s.group; lines.push("*" + group + "*"); }
      lines.push((ticks[s.id] ? "✅ " : "⬜ ") + s.name + (s.q ? " × " + s.q : ""));
    });
    lines.push("", T.make + data.url);
    return lines.join("\n");
  }
  function share() { $("pm-wa").href = "https://wa.me/?text=" + encodeURIComponent(text()); }
  function copied(msg) { $("pm-copied").textContent = msg; }

  list.addEventListener("change", function (ev) {
    var id = ev.target.getAttribute("data-id");
    if (!id) return;
    if (ev.target.checked) ticks[id] = 1; else delete ticks[id];
    count(); share(); save();
  });
  form.addEventListener("change", render);
  days.addEventListener("input", render);
  $("pm-clear").addEventListener("click", function () {
    ticks = {};
    list.querySelectorAll("input[type=checkbox]").forEach(function (b) { b.checked = false; });
    count(); share(); save();
  });
  $("pm-print").addEventListener("click", function () { window.print(); });
  $("pm-copy").addEventListener("click", function () {
    var t = text();
    function fallback() {
      var area = document.createElement("textarea");
      area.value = t;
      area.setAttribute("readonly", "");
      area.style.position = "fixed"; area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
      document.body.removeChild(area);
      copied(ok ? T.copied : T.nocopy);
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(t).then(function () { copied(T.copied); }, fallback);
    } else fallback();
  });

  // Start from the last choices, or this month
  var ch = saved.choice || {};
  month.value = String(new Date().getMonth() + 1);
  try {
    if (ch.type && form.querySelector("#pm-type option[value='" + ch.type + "']")) type.value = ch.type;
    if (ch.days) days.value = ch.days;
    if (ch.month) month.value = ch.month;
    if (ch.who) form.querySelectorAll("input[name=who]").forEach(function (b) { b.checked = ch.who.indexOf(b.value) >= 0; });
    ["by", "where"].forEach(function (name) {
      var b = ch[name] && form.querySelector("input[name=" + name + "][value=" + ch[name] + "]");
      if (b) b.checked = true;
    });
  } catch (err) { /* old or broken saved choices: start fresh */ }
  if (!month.value || !data.seasons[month.value]) month.value = String(new Date().getMonth() + 1);
  form.hidden = false;
  out.hidden = false;
  $("pm-nojs").hidden = true;
  render();
})();
