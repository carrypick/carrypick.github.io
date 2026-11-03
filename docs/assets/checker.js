// Cabin bag checker: same fit rule as size_fit() in scripts/build.py.
(function () {
  var dataEl = document.getElementById("bc-data");
  if (!dataEl) return;
  var data = JSON.parse(dataEl.textContent);
  var $ = function (id) { return document.getElementById(id); };
  var fields = ["bc-l", "bc-w", "bc-h", "bc-kg"].map($);

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
      checks.push({ over: worst, why: num(worst) + " cm over on one side" });
    }
    if (a.total) {
      var total = bag[0] + bag[1] + bag[2];
      checks.push({ over: total - a.total, why: num(total) + " cm in total, " + num(total - a.total) + " cm over" });
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
    $("bc-total").textContent = hasSize ? "Your bag: " + num(v[0] + v[1] + v[2]) + " cm in total (L + W + H)" : "";
    data.airlines.forEach(function (a) {
      var row = document.querySelector('tr[data-slug="' + a.slug + '"]');
      var size = row.querySelector(".r-size");
      var kg = row.querySelector(".r-kg");
      if (!hasSize) size.innerHTML = badge("na", "Enter size");
      else {
        var r = sizeFit(bag, a);
        size.innerHTML = !r ? badge("na", "No limit given")
          : r.ok ? badge("yes", "Fits")
          : (r.over <= 3 ? badge("close", num(r.over) + " cm over") : badge("no", "Too big")) + why(r.why);
      }
      if (!(v[3] > 0)) kg.innerHTML = badge("na", "Enter weight");
      else if (!a.kg) kg.innerHTML = badge("na", "No limit given");
      else kg.innerHTML = v[3] <= a.kg
        ? badge("yes", "OK") + why(num(a.kg - v[3]) + " kg spare")
        : badge("no", "Too heavy") + why(num(v[3] - a.kg) + " kg over");
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
  update();
})();
