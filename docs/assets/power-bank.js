// Power bank flight checker (tools/power-bank-flight-check.html). Limits come from the page (data/power_banks.json):
// each airline row carries its max Wh; the form carries the default cell voltage. Same rule as power_verdict() in scripts/more_tools.py.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("pb");
  if (!form) return;
  var low = parseFloat(form.getAttribute("data-low")), high = parseFloat(form.getAttribute("data-high"));
  var rows = [].slice.call(document.querySelectorAll("#pb-airlines tbody tr"));
  // The Hindi page puts its own words in <script id="pb-t" type="application/json">; {x} marks a value filled in below.
  var T = { your: "Your power bank is {wh} Wh.", calc: "{mah} mAh x {v} V ÷ 1,000 = {wh} Wh.",
    prompt: "Type your power bank's mAh to see its watt-hours and whether you can fly with it.",
    yes: "Allowed in your cabin bag", close: "Needs airline approval", no: "Not allowed on Indian flights",
    yesNote: "Keep it with you, not in the overhead bin, and don't use or charge it during the flight. Never put it in your check-in bag.",
    closeNote: "It's over {low} Wh. Some airlines here allow it, others don't: ask your airline before you fly, or take a smaller power bank.",
    noNote: "It's over {high} Wh, the highest limit of any airline here, in the cabin or in check-in. Leave it at home.",
    yesCell: "Yes", noCell: "No", over: "over {max} Wh" };
  var tEl = $("pb-t");
  if (tEl) { try { var h = JSON.parse(tEl.textContent); for (var k in h) T[k] = h[k]; } catch (x) {} }
  function say(key, v) { return T[key].replace(/\{(\w+)\}/g, function (m, n) { return v && n in v ? v[n] : m; }); }
  function r1(x) { return Math.round(x * 10) / 10; }

  function check(source) {
    var mah = parseFloat($("pb-mah").value), v = parseFloat($("pb-v").value), wh = parseFloat($("pb-wh").value), how;
    if (source === "wh") { $("pb-mah").value = ""; }
    if (source === "mah" || source === "v") { $("pb-wh").value = ""; wh = NaN; }
    if (wh > 0) {
      how = say("your", { wh: r1(wh) });
    } else if (mah > 0 && v > 0) {
      wh = mah * v / 1000;
      how = say("calc", { mah: mah.toLocaleString("en-IN"), v: v, wh: r1(wh) });
    } else {
      $("pb-result").hidden = true;
      $("pb-out").textContent = T.prompt;
      return;
    }
    var verdict, note;
    if (wh <= low) {
      verdict = '<span class="fit fit-yes">' + T.yes + "</span>";
      note = T.yesNote;
    } else if (wh <= high) {
      verdict = '<span class="fit fit-close">' + T.close + "</span>";
      note = say("closeNote", { low: low });
    } else {
      verdict = '<span class="fit fit-no">' + T.no + "</span>";
      note = say("noNote", { high: high });
    }
    rows.forEach(function (r) {
      var ok = wh <= parseFloat(r.getAttribute("data-max"));
      r.querySelector(".pb-cabin").innerHTML = ok ? '<span class="fit fit-yes">' + T.yesCell + "</span>"
        : '<span class="fit fit-no">' + T.noCell + '</span> <small class="muted">' + say("over", { max: r.getAttribute("data-max") }) + "</small>";
    });
    $("pb-out").innerHTML = verdict + " ";
    $("pb-out").appendChild(document.createTextNode(how));
    $("pb-note").textContent = note;
    $("pb-result").hidden = false;
  }

  $("pb-mah").addEventListener("input", function () { check("mah"); });
  $("pb-v").addEventListener("input", function () { check("v"); });
  $("pb-wh").addEventListener("input", function () { check("wh"); });
})();
