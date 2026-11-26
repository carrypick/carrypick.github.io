// Packing checklist: quantities follow the number of days, up to the item's cap (same rules as pack_qty() in scripts/build.py).
// Ticks are saved in this browser only, one list per trip type.
// On packing/index.html the list carries every preset (data-presets): each item says which trips it belongs to
// (data-trips), and the trip chips (data-preset) or a #weekend / #beach / #train / #wedding link switch the list in place.
(function () {
  var list = document.querySelector(".pack-list");
  var days = document.getElementById("pk-days");
  if (!list || !days) return;
  var presets = (list.getAttribute("data-presets") || "").split(" ").filter(Boolean);
  var key, boxes;
  var rules = { per_day: function (n) { return n; }, per_day_plus_1: function (n) { return n + 1; },
                per_day_plus_2: function (n) { return n + 2; }, per_2_days: function (n) { return n / 2; },
                per_3_days: function (n) { return n / 3; }, six_per_day: function (n) { return 6 * n; } };

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
      var cap = Number(q.getAttribute("data-cap")) || Infinity;
      q.textContent = "× " + Math.min(cap, Math.max(1, value));
    });
  }
  function setup(trip) {
    list.setAttribute("data-trip", trip);
    key = "cp_pack_" + trip;
    if (presets.length) {
      list.querySelectorAll("li[data-trips]").forEach(function (li) {
        li.hidden = (" " + li.getAttribute("data-trips") + " ").indexOf(" " + trip + " ") < 0;
      });
      list.querySelectorAll(".pack-group").forEach(function (g) {
        g.hidden = !g.querySelector("li:not([hidden])");
      });
      document.querySelectorAll(".trip-chip[data-preset]").forEach(function (c) {
        var on = c.getAttribute("data-preset") === trip;
        c.classList.toggle("on", on);
        if (on) c.setAttribute("aria-current", "page"); else c.removeAttribute("aria-current");
      });
    }
    boxes = [].slice.call(list.querySelectorAll("li:not([hidden]) input[type=checkbox]"));
    var ticked = load();
    boxes.forEach(function (b) { b.checked = ticked.indexOf(b.getAttribute("data-id")) >= 0; });
    quantities();
    count();
  }
  function choose(trip, scroll) {
    var chip = document.querySelector('.trip-chip[data-preset="' + trip + '"]');
    if (!chip) return false;
    days.value = chip.getAttribute("data-days") || days.value;
    setup(trip);
    if (scroll) document.getElementById("packer").scrollIntoView({ behavior: "smooth", block: "start" });
    return true;
  }

  list.addEventListener("change", function () { save(); count(); });
  days.addEventListener("input", quantities);
  document.getElementById("pk-clear").addEventListener("click", function () {
    boxes.forEach(function (b) { b.checked = false; });
    save(); count();
  });
  document.getElementById("pk-print").addEventListener("click", function () { window.print(); });
  if (presets.length) {
    document.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest(".trip-chip[data-preset], [data-preset-link]");
      if (!a) return;
      var trip = a.getAttribute("data-preset") || a.getAttribute("data-preset-link");
      if (choose(trip, !!a.getAttribute("data-preset-link"))) {
        ev.preventDefault();
        try { history.replaceState(null, "", trip === "week" ? location.pathname : "#" + trip); } catch (err) { /* old browser */ }
      }
    });
  }
  setup(list.getAttribute("data-trip"));
  // Arriving from an old list (packing/beach.html links to index.html#beach): show that preset, and leave the
  // browser at its advice section, which is where the link points.
  var hash = location.hash.slice(1);
  if (presets.indexOf(hash) > 0) choose(hash, false);
})();
