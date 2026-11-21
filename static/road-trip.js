// Road trip fuel cost calculator (tools/road-trip-cost-calculator.html). The reader types every amount,
// including the fuel price; we publish none. Inputs are kept in localStorage and can travel in the link (#plan=...).
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("rt");
  if (!form) return;
  var KEY = "cp-road-trip";
  var F = ["km", "mileage", "fuelp", "tolls", "parking", "people"];
  var money = function (n) { return "₹" + Math.round(n).toLocaleString("en-IN"); };
  var fix = function (n) { return (Math.round(n * 10) / 10).toLocaleString("en-IN"); };
  var num = function (id) { var v = parseFloat($("rt-" + id).value); return isFinite(v) && v > 0 ? v : 0; };
  var labelOf = function (id) { return $("rt-" + id).parentNode.firstChild; };

  function state() {
    var f = { fuel: $("rt-fuel").value, round: $("rt-round").checked ? 1 : 0 };
    F.forEach(function (k) { var v = $("rt-" + k).value; if (v !== "") f[k] = v; });
    return f;
  }
  function load(s) {
    if (!s || typeof s !== "object") return;
    if (["petrol", "diesel", "cng"].indexOf(s.fuel) >= 0) $("rt-fuel").value = s.fuel;
    if (s.round != null) $("rt-round").checked = !!s.round;
    F.forEach(function (k) { $("rt-" + k).value = s[k] != null ? String(s[k]).slice(0, 12) : ""; });
  }
  function link() { return location.href.split("#")[0] + "#plan=" + encodeURIComponent(JSON.stringify(state())); }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state())); } catch (err) {}
    $("rt-wa").href = "https://wa.me/?text=" + encodeURIComponent("Our road trip fuel plan on CarryPick: " + link());
  }

  function calc() {
    var cng = $("rt-fuel").value === "cng", unit = cng ? "kg" : "litres";
    labelOf("mileage").nodeValue = cng ? "Mileage (km per kg)" : "Mileage (km per litre)";
    labelOf("fuelp").nodeValue = cng ? "CNG price, per kg" : "Fuel price, per litre";
    var trips = $("rt-round").checked ? 2 : 1;
    var km = num("km") * trips, mil = num("mileage"), people = Math.round(num("people")) || 1;
    var out = $("rt-out"), list = $("rt-list");
    list.innerHTML = "";
    if (!km || !mil) { out.textContent = "Type in the distance, mileage and fuel price to see your fuel cost."; return; }
    var fuel = km / mil, fuelCost = fuel * num("fuelp"), tolls = num("tolls") * trips, parking = num("parking");
    var total = fuelCost + tolls + parking;
    var rows = [["Distance driven", fix(km) + " km" + (trips === 2 ? " (there and back)" : "")],
      ["Fuel needed", fix(fuel) + " " + unit]];
    if (fuelCost) rows.push(["Fuel cost", money(fuelCost)]);
    if (tolls) rows.push(["Tolls" + (trips === 2 ? " (both ways)" : ""), money(tolls)]);
    if (parking) rows.push(["Parking", money(parking)]);
    if (total) rows.push(["Cost per km", "₹" + (Math.round(total / km * 100) / 100).toLocaleString("en-IN")]);
    rows.forEach(function (r) {
      var li = document.createElement("li");
      li.appendChild(document.createTextNode(r[0] + ": "));
      var b = document.createElement("strong"); b.textContent = r[1]; li.appendChild(b);
      list.appendChild(li);
    });
    out.textContent = total ? "Total: " + money(total) + (people > 1 ? " · " + money(total / people) + " per person (" + people + " people)" : "")
      : "Fuel needed: " + fix(fuel) + " " + unit + ". Add the fuel price to see the cost.";
  }

  form.addEventListener("input", function () { calc(); save(); });
  form.addEventListener("change", function () { calc(); save(); });
  $("rt-copy").addEventListener("click", function () {
    var url = link(), btn = this;
    try { history.replaceState(null, "", url); } catch (err) {}
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { btn.textContent = "Link copied"; }, function () {});
  });
  $("rt-reset").addEventListener("click", function () {
    load({ fuel: "petrol", round: 1 });
    try { localStorage.removeItem(KEY); history.replaceState(null, "", location.pathname); } catch (err) {}
    calc(); save();
  });

  var start = null, m = location.hash.match(/^#plan=(.+)$/);
  if (m) { try { start = JSON.parse(decodeURIComponent(m[1])); } catch (err) {} }
  if (!start) { try { start = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (err) {} }
  load(start);
  form.hidden = false;
  calc(); save();
})();
