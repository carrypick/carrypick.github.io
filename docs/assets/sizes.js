// Luggage size chart: converts inches/cm and kg/lb, and turns a bag size in inches into a cabin bag checker link.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  if (!$("cv-n")) return;
  // The Hindi size chart passes its own words in data- attributes; the English page uses the defaults.
  var units = ($("cv-out").getAttribute("data-units") || "cm|inches|lb|kg").split("|");
  var rules = { in: [2.54, units[0]], cm: [1 / 2.54, units[1]], kg: [2.20462, units[2]], lb: [0.453592, units[3]] };
  var link = $("cv-check"), base = link.getAttribute("data-base") || "checker.html";
  var bagText = $("cv-bag").getAttribute("data-bag") || "Your bag: {cm} cm, {total} cm in total";
  function round(x) { return Math.round(x * 10) / 10; }
  function convert() {
    var n = parseFloat($("cv-n").value), unit = $("cv-unit"), r = rules[unit.value];
    $("cv-out").textContent = n > 0 ? n + " " + unit.options[unit.selectedIndex].text + " = " + round(n * r[0]) + " " + r[1] : "";
  }
  function bag() {
    var raw = ["cv-l", "cv-w", "cv-h"].map(function (id) { return parseFloat($(id).value) * 2.54; });
    var cm = raw.map(round);
    var ok = cm.every(function (x) { return x > 0; });
    $("cv-bag").textContent = ok ? bagText.replace("{cm}", cm.join(" x ")).replace("{total}", round(raw[0] + raw[1] + raw[2])) : "";
    link.href = ok ? base + "?l=" + cm[0] + "&w=" + cm[1] + "&h=" + cm[2] : base;
    link.textContent = ok ? (link.getAttribute("data-ready") || "Check this bag against every airline")
                          : (link.getAttribute("data-open") || "Open the cabin bag checker");
  }
  $("cv-n").addEventListener("input", convert);
  $("cv-unit").addEventListener("change", convert);
  ["cv-l", "cv-w", "cv-h"].forEach(function (id) { $(id).addEventListener("input", bag); });
  convert();
  bag();
})();
