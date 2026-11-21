// What-to-wear helper: pick a place, a month and who it's for, then show the ready-made result for it.
// Every result is worked out at build time by scripts/what_to_wear.py and sits in #ww-cases; this file only chooses one,
// shows the everyone / women / men wording (<span data-for>) and that pick list (data-picks, data-picks-women, data-picks-men).
// Links like what-to-wear.html#manali, #manali-dec or #dubai-dec-women open with that place (month, who) chosen.
// The Hindi page passes its own words in #ww-data ("t").
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("ww"), dataEl = $("ww-data"), cases = $("ww-cases"), pool = $("ww-pool");
  if (!form || !dataEl || !cases || !pool || !("content" in cases)) return;
  var data = JSON.parse(dataEl.textContent);
  var t = data.t || { more: "We have checked numbers for {m} so far. More months coming.", sep: ", " };
  var place = $("ww-place"), month = $("ww-month"), who = $("ww-for"), more = $("ww-more");
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
    more.textContent = p.months.length < 12 ? t.more.replace("{m}", names.join(t.sep)) : "";
  }

  function show(focus) {
    var key = place.value + "-" + month.value, w = who ? who.value : "all";
    var src = cases.content.querySelector('[data-case="' + key + '"]');
    if (!src) return;
    box.innerHTML = "";
    var node = src.cloneNode(true);
    Array.prototype.forEach.call(node.querySelectorAll("[data-for]"), function (s) {
      s.hidden = s.getAttribute("data-for") !== w;
    });
    box.appendChild(node);
    grid.innerHTML = "";
    var picks = node.getAttribute(w === "all" ? "data-picks" : "data-picks-" + w) || "";
    picks.split(" ").forEach(function (a) {
      var card = a && pool.content.querySelector('[data-asin="' + a + '"]');
      if (card) grid.appendChild(card.cloneNode(true));
    });
    $("ww-picks-head").hidden = !grid.children.length;
    result.hidden = false;
    var hash = key + (w === "all" ? "" : "-" + w);
    wa.href = "https://wa.me/?text=" + encodeURIComponent(base + "#" + hash);
    if (focus !== null && history.replaceState) history.replaceState(null, "", "#" + hash);
    if (focus) { var h = node.querySelector(".ww-title"); if (h) h.focus(); }
  }

  function fromHash() {
    var h = decodeURIComponent(location.hash.slice(1));
    var m = h.match(/^(.+?)(?:-(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))?(?:-(women|men))?$/);
    if (m && data.places[m[1]]) return { slug: m[1], mon: m[2] || "", who: m[3] || "all" };
    return null;
  }

  var start = fromHash();
  place.value = start ? start.slug : place.options[0].value;
  if (who && start) who.value = start.who;
  fillMonths(place.value, start ? start.mon : "");
  form.hidden = false;
  var nojs = $("ww-nojs");
  if (nojs) nojs.hidden = true;
  place.addEventListener("change", function () { fillMonths(place.value, month.value); show(false); });
  month.addEventListener("change", function () { show(false); });
  if (who) who.addEventListener("change", function () { show(false); });
  show(start ? false : null);
  if (start) form.scrollIntoView({ block: "start" });
})();
