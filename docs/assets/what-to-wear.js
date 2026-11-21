// What-to-wear helper: pick a place and a month, then show the ready-made result for it.
// Every result is worked out at build time by scripts/what_to_wear.py and sits in #ww-cases; this file only chooses one.
// Links like what-to-wear.html#manali or #manali-dec open with that place (and month) chosen.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("ww"), dataEl = $("ww-data"), cases = $("ww-cases"), pool = $("ww-pool");
  if (!form || !dataEl || !cases || !pool || !("content" in cases)) return;
  var data = JSON.parse(dataEl.textContent);
  var place = $("ww-place"), month = $("ww-month"), more = $("ww-more");
  var result = $("ww-result"), box = $("ww-case"), grid = $("ww-grid"), wa = $("ww-wa");
  var keys = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  var base = location.href.split("#")[0];

  function fillMonths(slug, want) {
    var p = data.places[slug];
    month.innerHTML = "";
    p.months.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m; o.textContent = data.months[m];
      month.appendChild(o);
    });
    var now = keys[new Date().getMonth()];
    month.value = p.months.indexOf(want) >= 0 ? want : (p.months.indexOf(now) >= 0 ? now : p.months[0]);
    var names = p.months.map(function (m) { return data.months[m]; });
    more.textContent = p.months.length < 12 ? "We have checked numbers for " + names.join(", ") + " so far. More months coming." : "";
  }

  function show(focus) {
    var key = place.value + "-" + month.value;
    var src = cases.content.querySelector('[data-case="' + key + '"]');
    if (!src) return;
    box.innerHTML = "";
    var node = src.cloneNode(true);
    box.appendChild(node);
    grid.innerHTML = "";
    (node.getAttribute("data-picks") || "").split(" ").forEach(function (a) {
      var card = a && pool.content.querySelector('[data-asin="' + a + '"]');
      if (card) grid.appendChild(card.cloneNode(true));
    });
    $("ww-picks-head").hidden = !grid.children.length;
    result.hidden = false;
    var url = base + "#" + key;
    wa.href = "https://wa.me/?text=" + encodeURIComponent(url);
    if (focus !== null && history.replaceState) history.replaceState(null, "", "#" + key);
    if (focus) { var h = node.querySelector(".ww-title"); if (h) h.focus(); }
  }

  function fromHash() {
    var h = decodeURIComponent(location.hash.slice(1));
    var m = h.match(/^(.+?)(?:-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))?$/);
    if (m && data.places[m[1]]) return { slug: m[1], mon: m[2] || "" };
    return null;
  }

  var start = fromHash();
  place.value = start ? start.slug : place.options[0].value;
  fillMonths(place.value, start ? start.mon : "");
  form.hidden = false;
  var nojs = $("ww-nojs");
  if (nojs) nojs.hidden = true;
  place.addEventListener("change", function () { fillMonths(place.value, month.value); show(false); });
  month.addEventListener("change", function () { show(false); });
  show(start ? false : null);
  if (start) form.scrollIntoView({ block: "start" });
})();
