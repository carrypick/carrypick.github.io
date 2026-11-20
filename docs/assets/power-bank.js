// Power bank flight checker (tools/power-bank-flight-check.html). Limits come from the page (data/power_banks.json):
// each airline row carries its max Wh; the form carries the default cell voltage. Same rule as power_verdict() in scripts/more_tools.py.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("pb");
  if (!form) return;
  var low = parseFloat(form.getAttribute("data-low")), high = parseFloat(form.getAttribute("data-high"));
  var rows = [].slice.call(document.querySelectorAll("#pb-airlines tbody tr"));
  function r1(x) { return Math.round(x * 10) / 10; }

  function check(source) {
    var mah = parseFloat($("pb-mah").value), v = parseFloat($("pb-v").value), wh = parseFloat($("pb-wh").value), how;
    if (source === "wh") { $("pb-mah").value = ""; }
    if (source === "mah" || source === "v") { $("pb-wh").value = ""; wh = NaN; }
    if (wh > 0) {
      how = "Your power bank is " + r1(wh) + " Wh.";
    } else if (mah > 0 && v > 0) {
      wh = mah * v / 1000;
      how = mah.toLocaleString("en-IN") + " mAh x " + v + " V ÷ 1,000 = " + r1(wh) + " Wh.";
    } else {
      $("pb-result").hidden = true;
      $("pb-out").textContent = "Type your power bank's mAh to see its watt-hours and whether you can fly with it.";
      return;
    }
    var verdict, note;
    if (wh <= low) {
      verdict = '<span class="fit fit-yes">Allowed in your cabin bag</span>';
      note = "Keep it with you, not in the overhead bin, and don't use or charge it during the flight. Never put it in your check-in bag.";
    } else if (wh <= high) {
      verdict = '<span class="fit fit-close">Needs airline approval</span>';
      note = "It's over " + low + " Wh. Some airlines here allow it, others don't: ask your airline before you fly, or take a smaller power bank.";
    } else {
      verdict = '<span class="fit fit-no">Not allowed on Indian flights</span>';
      note = "It's over " + high + " Wh, the highest limit of any airline here, in the cabin or in check-in. Leave it at home.";
    }
    rows.forEach(function (r) {
      var ok = wh <= parseFloat(r.getAttribute("data-max"));
      r.querySelector(".pb-cabin").innerHTML = ok ? '<span class="fit fit-yes">Yes</span>'
        : '<span class="fit fit-no">No</span> <small class="muted">over ' + r.getAttribute("data-max") + " Wh</small>";
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
