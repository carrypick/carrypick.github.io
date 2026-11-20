// Shoe size converter (tools/shoe-size.html). The charts are plain tables built from data/shoe_sizes.json;
// each row carries its sizes and foot-length range, so this script reads them from the page.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  if (!$("ss")) return;
  var tables = {};
  [].forEach.call(document.querySelectorAll("table.ss-table"), function (t) { tables[t.getAttribute("data-group")] = t; });
  [].forEach.call(document.querySelectorAll("#ss [data-js]"), function (el) { el.hidden = false; });

  function rows(group) { return [].slice.call(tables[group].querySelectorAll("tbody tr")); }
  function ukText(r) { return r.getAttribute("data-uk") + (r.getAttribute("data-kids") === "1" ? " (kids)" : ""); }
  function clear() {
    [].forEach.call(document.querySelectorAll("table.ss-table tr.on"), function (r) { r.classList.remove("on"); });
  }

  function fillSizes() {
    var group = $("ss-who").value, sys = $("ss-sys").value, sel = $("ss-size");
    sel.innerHTML = '<option value="">Choose…</option>';
    rows(group).forEach(function (r, i) {
      var o = document.createElement("option");
      o.value = i;
      o.textContent = (sys === "uk" ? "India / UK " + ukText(r) : sys.toUpperCase() + " " + r.getAttribute("data-" + sys));
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
      ? "We don't have kids' shoes yet. These are our travel shoes for adults. Each Amazon page has the brand's own size chart."
      : "Our travel shoes for " + group + ". Each Amazon page has the brand's own size chart: check it before you order.";
  }

  function show(group, r, note) {
    clear();
    r.classList.add("on");
    var label = tables[group].getAttribute("data-label");
    $("ss-r-uk").textContent = ukText(r);
    $("ss-r-us").textContent = r.getAttribute("data-us");
    $("ss-r-eu").textContent = r.getAttribute("data-eu");
    $("ss-r-cm").textContent = r.getAttribute("data-lo") + "–" + r.getAttribute("data-hi") + " cm";
    $("ss-out").textContent = label + " India/UK size " + ukText(r) + " = US " + r.getAttribute("data-us") + " = EU " + r.getAttribute("data-eu") + ".";
    $("ss-r-note").textContent = note || "Sizes vary by brand, so check the size chart on the product page too.";
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
    if (!(cm > 0)) { reset("Type your foot length in cm, or pick a size you know, to see it in every size system."); return; }
    var list = rows(group);
    var lo = parseFloat(list[0].getAttribute("data-lo")), hi = parseFloat(list[list.length - 1].getAttribute("data-hi"));
    if (cm < lo - 0.5 || cm > hi) {
      reset("A " + Math.round(cm * 10) / 10 + " cm foot is outside this chart (" + lo + "–" + hi + " cm). " +
            (cm < lo ? (group === "kids" ? "Ask in a shop for baby shoe sizes." : "Try the kids' chart.")
                      : (group === "men" ? "Look for brands that make bigger sizes." : group === "kids" ? "Try the women's or men's chart." : "Try the men's chart.")));
      return;
    }
    var row = list.filter(function (r) { return parseFloat(r.getAttribute("data-hi")) >= cm; })[0];
    var inRange = cm >= parseFloat(row.getAttribute("data-lo"));
    show(group, row, inRange
      ? "Your " + Math.round(cm * 10) / 10 + " cm foot fits this size on the chart. Sizes vary by brand, so check the product page too."
      : "Your foot is between two sizes, so we picked the bigger one. Sizes vary by brand, so check the product page too.");
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
    if ($("ss-cm").value) byCm(); else if (had !== "") reset("Pick your size again for this chart.");
    else filterPicks(this.value);
  });
  $("ss-sys").addEventListener("change", function () { fillSizes(); reset("Now pick your size."); });
  $("ss-cm").addEventListener("input", byCm);
  $("ss-size").addEventListener("change", bySize);
  fillSizes();
})();
