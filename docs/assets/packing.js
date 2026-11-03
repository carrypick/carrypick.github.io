// Packing checklist: quantities follow the number of days (same rules as pack_qty() in scripts/build.py).
// Ticks are saved in this browser only, one list per trip type.
(function () {
  var list = document.querySelector(".pack-list");
  var days = document.getElementById("pk-days");
  if (!list || !days) return;
  var key = "cp_pack_" + list.getAttribute("data-trip");
  var boxes = [].slice.call(list.querySelectorAll("input[type=checkbox]"));
  var rules = { per_day: function (n) { return n; }, per_day_plus_1: function (n) { return n + 1; },
                per_2_days: function (n) { return n / 2; }, per_3_days: function (n) { return n / 3; } };

  function load() { try { return JSON.parse(localStorage.getItem(key) || "[]"); } catch (err) { return []; } }
  function save() {
    var ids = boxes.filter(function (b) { return b.checked; }).map(function (b) { return b.getAttribute("data-id"); });
    try { localStorage.setItem(key, JSON.stringify(ids)); } catch (err) { /* private mode: ticks last until reload */ }
  }
  function count() {
    var done = boxes.filter(function (b) { return b.checked; }).length;
    document.getElementById("pk-count").textContent = done + " of " + boxes.length + " packed";
  }
  function quantities() {
    var n = Math.min(30, Math.max(1, parseInt(days.value, 10) || 1));
    list.querySelectorAll(".pk-qty").forEach(function (q) {
      var rule = q.getAttribute("data-qty");
      var value = /^\d+$/.test(rule) ? Number(rule) : Math.ceil(rules[rule](n));
      q.textContent = "× " + Math.max(1, value);
    });
  }

  var ticked = load();
  boxes.forEach(function (b) { b.checked = ticked.indexOf(b.getAttribute("data-id")) >= 0; });
  list.addEventListener("change", function () { save(); count(); });
  days.addEventListener("input", quantities);
  document.getElementById("pk-clear").addEventListener("click", function () {
    boxes.forEach(function (b) { b.checked = false; });
    save(); count();
  });
  document.getElementById("pk-print").addEventListener("click", function () { window.print(); });
  quantities();
  count();
})();
