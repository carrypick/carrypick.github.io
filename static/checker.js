// Cabin bag checker: same fit rule as size_fit() in scripts/build.py.
(function () {
  var dataEl = document.getElementById("bc-data");
  if (!dataEl) return;
  var data = JSON.parse(dataEl.textContent);
  var $ = function (id) { return document.getElementById(id); };
  var fields = ["bc-l", "bc-w", "bc-h", "bc-kg"].map($);
  // The Hindi checker passes its own words in data.t; {n}, {total} and {over} are filled in below.
  var T = Object.assign({
    total: "Your bag: {total} cm in total (L + W + H)", size: "Enter size", weight: "Enter weight", none: "No limit given",
    fits: "Fits", over: "{n} cm over", big: "Too big", side: "{n} cm over on one side", sum: "{total} cm in total, {over} cm over",
    ok: "OK", spare: "{n} kg spare", heavy: "Too heavy", kgOver: "{n} kg over"
  }, data.t || {});
  function say(key, n, total) {
    return T[key].replace("{n}", n).replace("{over}", n).replace("{total}", total);
  }

  function num(x) { return String(Math.round(x * 10) / 10); }
  function badge(state, text) {
    return '<span class="fit fit-' + state + '">' + text + "</span>";
  }
  function why(text) { return text ? '<span class="why">' + text + "</span>" : ""; }

  function sizeFit(bag, a) {
    var checks = [];
    if (a.dims) {
      var lim = a.dims.slice().sort(function (x, y) { return y - x; });
      var worst = -Infinity;
      bag.forEach(function (b, i) { worst = Math.max(worst, b - lim[i]); });
      checks.push({ over: worst, why: say("side", num(worst)) });
    }
    if (a.total) {
      var total = bag[0] + bag[1] + bag[2];
      checks.push({ over: total - a.total, why: say("sum", num(total - a.total), num(total)) });
    }
    if (!checks.length) return null;
    var fails = checks.filter(function (c) { return c.over > 0; });
    var ok = a.either ? fails.length < checks.length : fails.length === 0;
    if (ok) return { ok: true, why: "", over: 0 };
    return {
      ok: false,
      why: fails.map(function (c) { return c.why; }).join("; "),
      over: Math.max.apply(null, fails.map(function (c) { return c.over; }))
    };
  }

  function update() {
    var v = fields.map(function (f) { return parseFloat(f.value); });
    var hasSize = v[0] > 0 && v[1] > 0 && v[2] > 0;
    var bag = hasSize ? v.slice(0, 3).sort(function (x, y) { return y - x; }) : null;
    $("bc-total").textContent = hasSize ? say("total", "", num(v[0] + v[1] + v[2])) : "";
    data.airlines.forEach(function (a) {
      var row = document.querySelector('tr[data-slug="' + a.slug + '"]');
      var size = row.querySelector(".r-size");
      var kg = row.querySelector(".r-kg");
      if (!hasSize) size.innerHTML = badge("na", T.size);
      else {
        var r = sizeFit(bag, a);
        size.innerHTML = !r ? badge("na", T.none)
          : r.ok ? badge("yes", T.fits)
          : (r.over <= 3 ? badge("close", say("over", num(r.over))) : badge("no", T.big)) + why(r.why);
      }
      if (!(v[3] > 0)) kg.innerHTML = badge("na", T.weight);
      else if (!a.kg) kg.innerHTML = badge("na", T.none);
      else kg.innerHTML = v[3] <= a.kg
        ? badge("yes", T.ok) + why(say("spare", num(a.kg - v[3])))
        : badge("no", T.heavy) + why(say("kgOver", num(v[3] - a.kg)));
    });
  }

  $("bc-pick").addEventListener("change", function () {
    var pick = data.picks[this.value];
    if (!pick) return;
    fields[0].value = pick.dims[0];
    fields[1].value = pick.dims[1];
    fields[2].value = pick.dims[2];
    fields[3].value = "";
    update();
    fields[3].focus();
  });
  fields.forEach(function (f) { f.addEventListener("input", update); });
  // Links from a pick page (?bag=ASIN) open with that bag's size filled in.
  var bag = new URLSearchParams(window.location.search).get("bag");
  var index = data.picks.findIndex(function (p) { return p.asin === bag; });
  if (index >= 0) {
    $("bc-pick").value = String(index);
    $("bc-pick").dispatchEvent(new Event("change"));
  }
  // Links from the luggage size chart (?l=55&w=35&h=25, in cm) open with that size filled in.
  var params = new URLSearchParams(window.location.search);
  ["l", "w", "h"].forEach(function (k, i) {
    var v = parseFloat(params.get(k));
    if (v > 0) fields[i].value = v;
  });
  update();
})();
