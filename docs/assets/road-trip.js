// Road trip fuel cost calculator (tools/road-trip-cost-calculator.html). The reader types every amount,
// including the fuel price; we publish none. Inputs are kept in localStorage and can travel in the link (#plan=...).
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("rt");
  if (!form) return;
  var KEY = "cp-road-trip";
  var F = ["km", "mileage", "fuelp", "tolls", "parking", "people"];
  var CUR = { INR: ["₹", "en-IN"], USD: ["$", "en-US"], EUR: ["€", "en-IE"], GBP: ["£", "en-GB"], AED: ["AED ", "en-AE"],
    SGD: ["S$", "en-SG"], THB: ["฿", "en-US"], JPY: ["¥", "ja-JP"], AUD: ["A$", "en-AU"] };
  var cur = "INR"; // only the symbol and number format change: no conversion, no rates
  var money = function (n) { var c = CUR[cur]; return c[0] + Math.round(n).toLocaleString(c[1]); };
  var fix = function (n) { return (Math.round(n * 10) / 10).toLocaleString(CUR[cur][1]); };
  var num = function (id) { var v = parseFloat($("rt-" + id).value); return isFinite(v) && v > 0 ? v : 0; };
  var labelOf = function (id) { return $("rt-" + id).parentNode.firstChild; };

  function state() {
    var f = { fuel: $("rt-fuel").value, round: $("rt-round").checked ? 1 : 0, cur: cur, dist: $("rt-dist").value, vol: $("rt-vol").value };
    F.forEach(function (k) { var v = $("rt-" + k).value; if (v !== "") f[k] = v; });
    return f;
  }
  function load(s) {
    if (!s || typeof s !== "object") return;
    if (["petrol", "diesel", "cng"].indexOf(s.fuel) >= 0) $("rt-fuel").value = s.fuel;
    if (typeof s.cur === "string" && CUR[s.cur]) { cur = s.cur; $("rt-cur").value = cur; }
    if (s.dist === "km" || s.dist === "mi") $("rt-dist").value = s.dist;
    if (s.vol === "l" || s.vol === "gal") $("rt-vol").value = s.vol;
    if (s.round != null) $("rt-round").checked = !!s.round;
    F.forEach(function (k) { $("rt-" + k).value = s[k] != null ? String(s[k]).slice(0, 12) : ""; });
  }
  function link() { return location.href.split("#")[0] + "#plan=" + encodeURIComponent(JSON.stringify(state())); }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state())); localStorage.setItem(KEY + "-cur", cur); } catch (err) {}
    $("rt-wa").href = "https://wa.me/?text=" + encodeURIComponent("Our road trip fuel plan on CarryPick: " + link());
  }

  function calc() {
    var cng = $("rt-fuel").value === "cng", mi = $("rt-dist").value === "mi", gal = $("rt-vol").value === "gal" && !cng;
    var d = mi ? "miles" : "km", dShort = mi ? "mile" : "km", vSing = cng ? "kg" : gal ? "US gallon" : "litre", unit = cng ? "kg" : gal ? "US gallons" : "litres";
    $("rt-vol").disabled = cng;
    labelOf("km").nodeValue = "Distance, one way (" + d + ")";
    labelOf("mileage").nodeValue = "Mileage (" + d + " per " + vSing + (mi && gal ? ", mpg" : "") + ")";
    labelOf("fuelp").nodeValue = (cng ? "CNG price" : "Fuel price") + ", per " + vSing;
    var trips = $("rt-round").checked ? 2 : 1;
    var km = num("km") * trips, mil = num("mileage"), people = Math.round(num("people")) || 1;
    var out = $("rt-out"), list = $("rt-list");
    list.innerHTML = "";
    if (!km || !mil) { out.textContent = "Type in the distance, mileage and fuel price to see your fuel cost."; return; }
    var fuel = km / mil, fuelCost = fuel * num("fuelp"), tolls = num("tolls") * trips, parking = num("parking");
    var total = fuelCost + tolls + parking;
    var rows = [["Distance driven", fix(km) + " " + d + (trips === 2 ? " (there and back)" : "")],
      ["Fuel needed", fix(fuel) + " " + unit]];
    if (fuelCost) rows.push(["Fuel cost", money(fuelCost)]);
    if (tolls) rows.push(["Tolls" + (trips === 2 ? " (both ways)" : ""), money(tolls)]);
    if (parking) rows.push(["Parking", money(parking)]);
    if (total) rows.push(["Cost per " + dShort, CUR[cur][0] + (Math.round(total / km * 100) / 100).toLocaleString(CUR[cur][1])]);
    rows.forEach(function (r) {
      var li = document.createElement("li");
      li.appendChild(document.createTextNode(r[0] + ": "));
      var b = document.createElement("strong"); b.textContent = r[1]; li.appendChild(b);
      list.appendChild(li);
    });
    out.textContent = total ? "Total: " + money(total) + (people > 1 ? " · " + money(total / people) + " per person (" + people + " people)" : "")
      : "Fuel needed: " + fix(fuel) + " " + unit + ". Add the fuel price to see the cost.";
  }

  $("rt-cur").addEventListener("change", function () { cur = CUR[this.value] ? this.value : "INR"; });
  form.addEventListener("input", function () { calc(); save(); });
  form.addEventListener("change", function () { calc(); save(); });
  $("rt-copy").addEventListener("click", function () {
    var url = link(), btn = this;
    try { history.replaceState(null, "", url); } catch (err) {}
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { btn.textContent = "Link copied"; }, function () {});
  });
  $("rt-reset").addEventListener("click", function () {
    load({ fuel: "petrol", round: 1, cur: cur, dist: $("rt-dist").value, vol: $("rt-vol").value });
    try { localStorage.removeItem(KEY); history.replaceState(null, "", location.pathname); } catch (err) {}
    calc(); save();
  });

  var start = null, m = location.hash.match(/^#plan=(.+)$/);
  if (m) { try { start = JSON.parse(decodeURIComponent(m[1])); } catch (err) {} }
  if (!start) { try { start = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (err) {} }
  if (!start) { try { var sc = localStorage.getItem(KEY + "-cur"); if (sc && CUR[sc]) start = { cur: sc }; } catch (err) {} }
  load(start);
  form.hidden = false;
  calc(); save();
})();
