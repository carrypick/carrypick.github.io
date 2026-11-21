// Visa guide for Indians: a search box and a status filter over the table that scripts/visa_india.py builds.
// Without JavaScript the full table shows and the form stays hidden.
// Links like visa-free-countries-for-indians.html#s=visa-free open with that status chosen.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("vz"), q = $("vz-q"), s = $("vz-s"), out = $("vz-out"), table = $("vz-t");
  if (!form || !q || !s || !out || !table) return;
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  form.hidden = false;
  // Hindi page: its words come from <script type="application/json" id="vz-t">; the English page has none and uses the English defaults.
  var words = {};
  try { words = JSON.parse(($("vz-t") || {}).textContent || "{}"); } catch (err) { words = {}; }
  function say(key, fallback, n, label) {
    return (words[key] || fallback).replace("{n}", n).replace("{label}", label);
  }
  function run() {
    var term = q.value.trim().toLowerCase(), st = s.value, n = 0;
    rows.forEach(function (r) {
      var ok = (!st || r.getAttribute("data-status") === st) && (!term || r.getAttribute("data-q").indexOf(term) >= 0);
      r.hidden = !ok;
      if (ok) n++;
    });
    var label = st ? s.options[s.selectedIndex].text.replace(/ \(\d+\)$/, "").toLowerCase() : "";
    out.textContent = n === rows.length ? say("all", "Showing all {n} countries.", n, label) :
      n ? (label ? say("someLabel", "Showing {n} {label} " + (n === 1 ? "country" : "countries") + ".", n, label) :
        say("some", "Showing {n} " + (n === 1 ? "country" : "countries") + ".", n, label)) :
      say("none", "No country matches. We cover {n} popular countries so far; for others, check the country's embassy in India.", rows.length, label);
  }
  var m = /s=([a-z-]+)/.exec(location.hash);
  if (m && s.querySelector('option[value="' + m[1] + '"]')) s.value = m[1];
  q.addEventListener("input", run);
  s.addEventListener("change", run);
  run();
})();
