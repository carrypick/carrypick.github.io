// Gift finder quiz: who -> occasion -> optional size, then pick cards and guide links.
// Data comes from data/gift_finder.json (embedded as #gf-data); the rule matches results() in scripts/gift_finder.py.
// Links like gift-finder.html#for=her start the quiz with that person chosen.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var box = $("gf"), dataEl = $("gf-data"), pool = $("gf-pool");
  if (!box || !dataEl || !pool) return;
  var data = JSON.parse(dataEl.textContent);
  var steps = ["who", "occ", "size"];
  var pick = { who: "", occ: "", size: "" };
  var step = 0;
  var result = $("gf-result");

  function find(list, slug) { for (var i = 0; i < list.length; i++) if (list[i].slug === slug) return list[i]; return null; }

  function results(who, occ, size) {
    var w = find(data.who, who), o = find(data.occasions, occ), pair = data.pairs[who + "+" + occ] || {};
    var occPicks = (o.not_for || []).indexOf(who) >= 0 ? [] : o.picks;
    var order = [];
    function add(list) { list.forEach(function (a) { if (order.indexOf(a) < 0) order.push(a); }); }
    add(pair.picks || []);
    if (o.lead && occPicks.length) { add(occPicks); add(w.picks); }
    else { add(w.picks.slice(0, 4)); add(occPicks.slice(0, 2)); add(w.picks); }
    var filled = false;
    if (size) {
      var match = order.filter(function (a) { return data.size_of[a] === size; });
      filled = match.length < 3;
      order = filled ? match.concat(order.filter(function (a) { return match.indexOf(a) < 0; })) : match;
    }
    var guides = [];
    (pair.guides || []).concat(o.guides, w.guides).forEach(function (g) {
      if (!guides.some(function (x) { return x[0].split("#")[0] === g[0].split("#")[0]; })) guides.push(g);
    });
    return { asins: order.slice(0, data.show), guides: guides.slice(0, 3), filled: filled };
  }

  function show(n) {
    step = n;
    steps.forEach(function (s, i) { $("gf-q-" + s).hidden = i !== n; });
    var total = n > 0 && find(data.who, pick.who) && find(data.who, pick.who).occasion ? 2 : 3;
    var shown = n === 2 && total === 2 ? 2 : n + 1;
    $("gf-step").textContent = "Question " + shown + " of " + total;
    $("gf-nav").hidden = n === 0;
    box.querySelectorAll(".gf-opt").forEach(function (b) {
      b.setAttribute("aria-pressed", pick[b.getAttribute("data-q")] === b.getAttribute("data-v") && b.getAttribute("data-v") !== "" ? "true" : "false");
    });
  }

  function render() {
    var w = find(data.who, pick.who), o = find(data.occasions, pick.occ);
    var r = results(pick.who, pick.occ, pick.size);
    $("gf-title").textContent = o.head + " for " + w.for;
    var size = find(data.sizes, pick.size);
    $("gf-answers").textContent = [w.label, o.label].concat(size ? [size.label] : []).join(" · ");
    var note = $("gf-note");
    note.hidden = !r.filled;
    if (r.filled) note.textContent = "We have only a few “" + size.label.toLowerCase() + "” ideas for " + w.for + ", so we added our other picks below them.";
    var grid = $("gf-grid");
    grid.innerHTML = "";
    r.asins.forEach(function (a) {
      var card = pool.content.querySelector('[data-asin="' + a + '"]');
      if (card) grid.appendChild(card.cloneNode(true));
    });
    $("gf-guides").innerHTML = "";
    r.guides.forEach(function (g) {
      var li = document.createElement("li"), link = document.createElement("a");
      link.href = g[0];
      link.textContent = g[1] + " →";
      li.appendChild(link);
      $("gf-guides").appendChild(li);
    });
    box.hidden = true;
    result.hidden = false;
    $("gf-title").focus({ preventScroll: true });
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function choose(q, v) {
    pick[q] = v;
    if (q === "who") {
      var w = find(data.who, v);
      if (w.occasion) { pick.occ = w.occasion; pick.size = pick.size || w.size || ""; show(2); return; }
      show(1);
    } else if (q === "occ") {
      show(2);
    } else {
      render();
    }
  }

  box.addEventListener("click", function (ev) {
    var b = ev.target.closest(".gf-opt");
    if (b) choose(b.getAttribute("data-q"), b.getAttribute("data-v"));
  });
  $("gf-back").addEventListener("click", function () {
    var w = find(data.who, pick.who);
    show(step === 2 && w && w.occasion ? 0 : Math.max(0, step - 1));
  });
  function again(keep) {
    if (!keep) pick = { who: "", occ: "", size: "" };
    result.hidden = true;
    box.hidden = false;
    show(0);
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  $("gf-change").addEventListener("click", function () { again(true); });
  $("gf-again").addEventListener("click", function () { again(false); });

  $("gf-nojs").hidden = true;
  box.hidden = false;
  show(0);
  var m = /(?:^|[#&])for=([a-z-]+)/.exec(location.hash);
  if (m && find(data.who, m[1])) choose("who", m[1]);
})();
