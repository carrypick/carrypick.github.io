// Clothing size converter (tools/clothing-size.html). The charts are plain tables built from data/clothing_sizes.json;
// each row carries its body measurements in cm (data-m-chest="lo,hi" ...), so this script reads them from the page.
// Each brand's chart is matched on its own: we never turn one brand's size into another's.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("cs");
  if (!form) return;
  var garments = JSON.parse(form.getAttribute("data-garments"));
  // The Hindi page puts its own words in <script id="cs-t" type="application/json">; {x} marks a value filled in below.
  var T = { measures: { chest: "chest", bust: "bust", waist: "waist", hips: "hips", height: "height" }, letter: "Letter", plainHead: "^(Size|UK size|Age)",
    inch: " in", cm: " cm", bigger: "bigger", smaller: "smaller", chartEnd: "{what} than this chart goes, by {m}.", between: ". You're between two sizes, so we picked the bigger one.",
    or: " or ", sep: ": ", note: "Brands differ, so check the size chart on the product page too.", choose: "Choose…",
    prompt: "Type your measurement, or pick a size you know, to see it on each brand's chart.", forA: "For a {x}:",
    add: "Add your {m} too: the size that fits all of them is the one to buy.", andWord: " and ", fits: "{size} on {title} fits a {body}.",
    others: "The other charts are matched on the same body size. Brands differ, so check the product page too.",
    picksKids: "Our travel clothes for kids: a thermal set, a hoodie, a jacket and a track suit. Each Amazon page has the brand's own age size chart: check it before you order.",
    picksNote: "Our travel clothes for {who}. Each Amazon page has the brand's own size chart: check it before you order.", men: "men", women: "women" };
  var tEl = $("cs-t");
  if (tEl) { try { var h = JSON.parse(tEl.textContent); for (var k in h) T[k] = h[k]; } catch (x) {} }
  function say2(key, v) { return T[key].replace(/\{(\w+)\}/g, function (m, n) { return v && n in v ? v[n] : m; }); }
  var LABEL = T.measures;
  form.hidden = false;

  function table(id) { return $("cs-t-" + id); }
  function rows(id) { return [].slice.call(table(id).querySelectorAll("tbody tr")); }
  function garment() {
    var slug = $("cs-garment").value;
    return garments.filter(function (g) { return g.slug === slug; })[0];
  }
  function span(r, m) {
    var v = r.getAttribute("data-m-" + m);
    if (!v) return null;
    var p = v.split(",");
    return [parseFloat(p[0]), parseFloat(p[1])];
  }
  function fmt(x) { return String(Math.round(x * 10) / 10); }
  function clear() {
    [].forEach.call(document.querySelectorAll("table.cs-table tr.on"), function (r) { r.classList.remove("on"); });
  }

  // The extra columns (letter, US, EU, collar) of a row, as "Letter M · US 8–10".
  function extras(id, r) {
    var heads = [].slice.call(table(id).querySelectorAll("thead th.x"));
    var cells = [].slice.call(r.querySelectorAll("td.x"));
    return heads.map(function (h, i) {
      var v = cells[i].textContent;
      return v === "–" ? "" : (h.textContent === T.letter ? v : h.textContent + " " + v);
    }).filter(Boolean).join(" · ");
  }

  // Rows right after r with the same body numbers (ONLY gives 27 and 28 one row of numbers): "27 or 28".
  function twins(id, r) {
    var list = rows(id), i = list.indexOf(r), key = function (x) {
      return [].slice.call(x.attributes).filter(function (a) { return a.name.indexOf("data-m-") === 0; })
        .map(function (a) { return a.name + "=" + a.value; }).join(";");
    }, out = [];
    while (++i < list.length && key(list[i]) === key(r)) out.push(list[i].querySelector("th").textContent);
    return out;
  }

  // How a row reads in the result: the table's data-say template, or "UK 12 (M · US 8–10 · EU 40–42)".
  function say(id, r) {
    var t = table(id), tpl = t.getAttribute("data-say"), size = r.querySelector("th").textContent;
    if (tpl) {
      var heads = [].slice.call(t.querySelectorAll("thead th.x")), cells = [].slice.call(r.querySelectorAll("td.x"));
      return tpl.replace(/\{([^}]+)\}/g, function (all, k) {
        if (k === "size") return size;
        for (var i = 0; i < heads.length; i++) if (heads[i].textContent === k) return cells[i].textContent;
        return "";
      });
    }
    var head = t.getAttribute("data-head"), x = extras(id, r);
    return (new RegExp(T.plainHead).test(head) ? size : head + " " + size) + (x ? " (" + x + ")" : "");
  }

  // Smallest row that fits every measure given (in cm). Returns {row, between} or {over|under: true}.
  function match(id, vals) {
    var list = rows(id), best = -1, between = false, used = 0;
    for (var m in vals) {
      var withM = list.filter(function (r) { return span(r, m); });
      if (!withM.length) continue;
      used++;
      var v = vals[m], first = span(withM[0], m), last = span(withM[withM.length - 1], m);
      if (v > last[1] + 0.5) return { over: true, m: m };
      if (v < first[0] - 5) return { under: true, m: m };
      var r = withM.filter(function (x) { return span(x, m)[1] >= v - 0.5; })[0];
      var i = list.indexOf(r);
      if (i > best) { best = i; between = v < span(r, m)[0] - 0.5 || v > span(r, m)[1] + 0.5; }
      else if (i === best && (v < span(r, m)[0] - 0.5)) between = true;
    }
    if (!used || best < 0) return null;
    return { row: list[best], between: between };
  }

  function line(id, res) {
    var t = table(id), li = document.createElement("li"), b = document.createElement("strong");
    b.textContent = t.getAttribute("data-title") + T.sep;
    li.appendChild(b);
    if (res.over || res.under) {
      li.appendChild(document.createTextNode(say2("chartEnd", { what: res.over ? T.bigger : T.smaller, m: LABEL[res.m] })));
    } else {
      res.row.classList.add("on");
      var tw = twins(id, res.row);
      tw.forEach(function (s) { rows(id).filter(function (x) { return x.querySelector("th").textContent === s; })[0].classList.add("on"); });
      li.appendChild(document.createTextNode(say(id, res.row).replace(/^(\S+)/, function (s) { return tw.length ? s + T.or + tw.join(T.or) : s; }) +
        (res.between ? T.between : "")));
    }
    return li;
  }

  function show(lines, out, note) {
    var ul = $("cs-r-list");
    ul.innerHTML = "";
    lines.forEach(function (l) { ul.appendChild(l); });
    $("cs-out").textContent = out;
    $("cs-r-note").textContent = note || T.note;
    $("cs-result").hidden = false;
  }

  function reset(msg) {
    clear();
    $("cs-result").hidden = true;
    $("cs-out").textContent = msg || T.prompt;
  }

  function byMeasure() {
    $("cs-size").value = "";
    clear();
    var g = garment(), k = $("cs-unit").value === "in" ? 2.54 : 1, vals = {}, said = [];
    g.measures.forEach(function (m) {
      var v = parseFloat($("cs-" + m).value);
      if (v > 0) { vals[m] = v * k; said.push(LABEL[m] + " " + fmt(v) + ($("cs-unit").value === "in" ? T.inch : T.cm)); }
    });
    if (!said.length) { reset(); return; }
    var lines = g.charts.map(function (id) { var r = match(id, vals); return r ? line(id, r) : null; }).filter(Boolean);
    show(lines, say2("forA", { x: said.join(", ") }), g.measures.length > 1 && said.length < g.measures.length
      ? say2("add", { m: g.measures.filter(function (m) { return !vals[m]; }).map(function (m) { return LABEL[m]; }).join(T.andWord) })
      : "");
  }

  function bySize() {
    var v = $("cs-size").value;
    if (!v) { byMeasure(); return; }
    var g = garment(), p = v.split(":"), id = p[0], r = rows(id)[+p[1]];
    g.measures.forEach(function (m) { $("cs-" + m).value = ""; });
    clear();
    var vals = {};
    g.measures.forEach(function (m) { var s = span(r, m); if (s) vals[m] = (s[0] + s[1]) / 2; });
    var lines = [line(id, { row: r })];
    g.charts.forEach(function (o) {
      if (o === id) return;
      var res = match(o, vals);
      if (res) lines.push(line(o, res));
    });
    var body = g.measures.filter(function (m) { return span(r, m); }).map(function (m) {
      var s = span(r, m);
      return LABEL[m] + " " + (s[0] === s[1] ? fmt(s[0]) : fmt(s[0]) + "–" + fmt(s[1])) + T.cm;
    }).join(", ");
    show(lines, say2("fits", { size: r.querySelector("th").textContent, title: table(id).getAttribute("data-title"), body: body }),
      lines.length > 1 ? T.others : "");
  }

  function fillGarments() {
    var who = $("cs-who").value, sel = $("cs-garment");
    sel.innerHTML = "";
    garments.filter(function (g) { return g.who === who; }).forEach(function (g) {
      var o = document.createElement("option");
      o.value = g.slug;
      o.textContent = g.label;
      sel.appendChild(o);
    });
  }

  function fillForm() {
    var g = garment();
    [].forEach.call(form.querySelectorAll("label[data-m]"), function (l) {
      l.hidden = g.measures.indexOf(l.getAttribute("data-m")) < 0;
    });
    var sel = $("cs-size");
    sel.innerHTML = "";
    var first = document.createElement("option"); first.value = ""; first.textContent = T.choose; sel.appendChild(first);
    g.charts.forEach(function (id) {
      var grp = document.createElement("optgroup"), t = table(id);
      grp.label = t.getAttribute("data-title");
      rows(id).forEach(function (r, i) {
        var o = document.createElement("option");
        o.value = id + ":" + i;
        o.textContent = say(id, r);
        grp.appendChild(o);
      });
      sel.appendChild(grp);
    });
  }

  function filterPicks() {
    var who = $("cs-who").value, cards = [].slice.call(document.querySelectorAll("#cs-picks [data-for]"));
    if (!cards.length) return;
    cards.forEach(function (c) {
      var f = c.getAttribute("data-for").split(" and ");
      c.hidden = f.indexOf(who) < 0;
    });
    $("cs-picks-note").textContent = who === "kids" ? T.picksKids : say2("picksNote", { who: T[who] || who });
  }

  function changed() {
    fillForm();
    filterPicks();
    if (garment().measures.some(function (m) { return $("cs-" + m).value; })) byMeasure(); else reset();
  }

  $("cs-who").addEventListener("change", function () {
    ["chest", "bust", "waist", "hips", "height"].forEach(function (m) { $("cs-" + m).value = ""; });
    fillGarments();
    changed();
  });
  $("cs-garment").addEventListener("change", changed);
  $("cs-unit").addEventListener("change", byMeasure);
  ["chest", "bust", "waist", "hips", "height"].forEach(function (m) { $("cs-" + m).addEventListener("input", byMeasure); });
  $("cs-size").addEventListener("change", bySize);
  fillGarments();
  fillForm();
  filterPicks();
})();
