// Luggage size chart: converts inches/cm and kg/lb, and turns a bag size in inches into a cabin bag checker link.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  if (!$("cv-n")) return;
  var rules = { in: [2.54, "cm"], cm: [1 / 2.54, "inches"], kg: [2.20462, "lb"], lb: [0.453592, "kg"] };
  function round(x) { return Math.round(x * 10) / 10; }
  function convert() {
    var n = parseFloat($("cv-n").value), unit = $("cv-unit"), r = rules[unit.value];
    $("cv-out").textContent = n > 0 ? n + " " + unit.options[unit.selectedIndex].text + " = " + round(n * r[0]) + " " + r[1] : "";
  }
  function bag() {
    var raw = ["cv-l", "cv-w", "cv-h"].map(function (id) { return parseFloat($(id).value) * 2.54; });
    var cm = raw.map(round);
    var ok = cm.every(function (x) { return x > 0; });
    $("cv-bag").textContent = ok ? "Your bag: " + cm.join(" x ") + " cm, " + round(raw[0] + raw[1] + raw[2]) + " cm in total" : "";
    $("cv-check").href = ok ? "checker.html?l=" + cm[0] + "&w=" + cm[1] + "&h=" + cm[2] : "checker.html";
    $("cv-check").textContent = ok ? "Check this bag against every airline" : "Open the cabin bag checker";
  }
  $("cv-n").addEventListener("input", convert);
  $("cv-unit").addEventListener("change", convert);
  ["cv-l", "cv-w", "cv-h"].forEach(function (id) { $(id).addEventListener("input", bag); });
  convert();
  bag();
})();
