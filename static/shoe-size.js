// Shoe size converter (tools/shoe-size.html). The charts are plain tables built from data/shoe_sizes.json;
// each row carries its sizes and foot-length range, so this script reads them from the page.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  if (!$("ss")) return;
  // The Hindi page puts its own words in <script id="ss-t" type="application/json">; {x} marks a value filled in below.
  var T = { kids: " (kids)", choose: "Choose…", uk: "India / UK ", cm: " cm",
    picksKids: "We don't have kids' shoes yet. These are our travel shoes for adults. Each Amazon page has the brand's own size chart.",
    picksNote: "Our travel shoes for {g}. Each Amazon page has the brand's own size chart: check it before you order.",
    men: "men", women: "women", sizeOut: "{label} India/UK size {uk} = US {us} = EU {eu}.",
    note: "Sizes vary by brand, so check the size chart on the product page too.",
    prompt: "Type your foot length in cm, or pick a size you know, to see it in every size system.",
    outside: "A {cm} cm foot is outside this chart ({lo}–{hi} cm). ", tryKids: "Try the kids' chart.", babyShop: "Ask in a shop for baby shoe sizes.",
    bigBrands: "Look for brands that make bigger sizes.", tryAdults: "Try the women's or men's chart.", tryMen: "Try the men's chart.",
    fits: "Your {cm} cm foot fits this size on the chart. Sizes vary by brand, so check the product page too.",
    between: "Your foot is between two sizes, so we picked the bigger one. Sizes vary by brand, so check the product page too.",
    again: "Pick your size again for this chart.", now: "Now pick your size." };
  var tEl = $("ss-t");
  if (tEl) { try { var h = JSON.parse(tEl.textContent); for (var k in h) T[k] = h[k]; } catch (x) {} }
  function say(key, v) { return T[key].replace(/\{(\w+)\}/g, function (m, n) { return v && n in v ? v[n] : m; }); }
  var tables = {};
  [].forEach.call(document.querySelectorAll("table.ss-table"), function (t) { tables[t.getAttribute("data-group")] = t; });
  [].forEach.call(document.querySelectorAll("#ss [data-js]"), function (el) { el.hidden = false; });

  function rows(group) { return [].slice.call(tables[group].querySelectorAll("tbody tr")); }
  function ukText(r) { return r.getAttribute("data-uk") + (r.getAttribute("data-kids") === "1" ? T.kids : ""); }
  function clear() {
    [].forEach.call(document.querySelectorAll("table.ss-table tr.on"), function (r) { r.classList.remove("on"); });
  }

  function fillSizes() {
    var group = $("ss-who").value, sys = $("ss-sys").value, sel = $("ss-size");
    sel.innerHTML = "";
    var first = document.createElement("option"); first.value = ""; first.textContent = T.choose; sel.appendChild(first);
    rows(group).forEach(function (r, i) {
      var o = document.createElement("option");
      o.value = i;
      o.textContent = (sys === "uk" ? T.uk + ukText(r) : sys.toUpperCase() + " " + r.getAttribute("data-" + sys));
      sel.appendChild(o);
    });
  }

  function filterPicks(group) {
    var cards = [].slice.call(document.querySelectorAll("#ss-picks [data-for]"));
    if (!cards.length) return;
    var shown = 0;
    cards.forEach(function (c) {
      c.hidden = group !== "kids" && c.getAttribute("data-for") !== group;
      if (!c.hidden) shown++;
    });
    if (!shown) cards.forEach(function (c) { c.hidden = false; });
    $("ss-picks-note").textContent = group === "kids" || !shown
      ? T.picksKids : say("picksNote", { g: T[group] || group });
  }

  function show(group, r, note) {
    clear();
    r.classList.add("on");
    var label = tables[group].getAttribute("data-label");
    $("ss-r-uk").textContent = ukText(r);
    $("ss-r-us").textContent = r.getAttribute("data-us");
    $("ss-r-eu").textContent = r.getAttribute("data-eu");
    $("ss-r-cm").textContent = r.getAttribute("data-lo") + "–" + r.getAttribute("data-hi") + T.cm;
    $("ss-out").textContent = say("sizeOut", { label: label, uk: ukText(r), us: r.getAttribute("data-us"), eu: r.getAttribute("data-eu") });
    $("ss-r-note").textContent = note || T.note;
    $("ss-result").hidden = false;
    filterPicks(group);
  }

  function reset(msg) {
    clear();
    $("ss-result").hidden = true;
    $("ss-out").textContent = msg;
  }

  function byCm() {
    $("ss-size").value = "";
    var group = $("ss-who").value, cm = parseFloat($("ss-cm").value);
    if (!(cm > 0)) { reset(T.prompt); return; }
    var list = rows(group);
    var lo = parseFloat(list[0].getAttribute("data-lo")), hi = parseFloat(list[list.length - 1].getAttribute("data-hi"));
    if (cm < lo - 0.5 || cm > hi) {
      reset(say("outside", { cm: Math.round(cm * 10) / 10, lo: lo, hi: hi }) +
            (cm < lo ? (group === "kids" ? T.babyShop : T.tryKids)
                      : (group === "men" ? T.bigBrands : group === "kids" ? T.tryAdults : T.tryMen)));
      return;
    }
    var row = list.filter(function (r) { return parseFloat(r.getAttribute("data-hi")) >= cm; })[0];
    var inRange = cm >= parseFloat(row.getAttribute("data-lo"));
    show(group, row, inRange
      ? say("fits", { cm: Math.round(cm * 10) / 10 })
      : T.between);
  }

  function bySize() {
    var i = $("ss-size").value;
    if (i === "") { byCm(); return; }
    $("ss-cm").value = "";
    var group = $("ss-who").value;
    show(group, rows(group)[+i]);
  }

  $("ss-who").addEventListener("change", function () {
    var had = $("ss-size").value;
    fillSizes();
    if ($("ss-cm").value) byCm(); else if (had !== "") reset(T.again);
    else filterPicks(this.value);
  });
  $("ss-sys").addEventListener("change", function () { fillSizes(); reset(T.now); });
  $("ss-cm").addEventListener("input", byCm);
  $("ss-size").addEventListener("change", bySize);
  fillSizes();
})();
