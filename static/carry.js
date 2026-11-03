// "Can I carry it?" search: hides rows that don't match, and groups with no matching rows.
(function () {
  var input = document.getElementById("carry-q");
  var table = document.getElementById("carry-table");
  if (!input || !table) return;
  var rows = [].slice.call(table.querySelectorAll("tr[data-words]"));
  function filter() {
    var words = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    var shown = 0;
    rows.forEach(function (row) {
      var text = row.getAttribute("data-words");
      var ok = words.every(function (w) { return text.indexOf(w) >= 0; });
      row.hidden = !ok;
      if (ok) shown++;
    });
    table.querySelectorAll("tbody[data-group]").forEach(function (g) {
      g.hidden = !g.querySelector("tr[data-words]:not([hidden])");
    });
    document.getElementById("carry-count").textContent = words.length ? shown + " of " + rows.length + " items" : rows.length + " items";
    document.getElementById("carry-none").hidden = shown > 0;
  }
  input.addEventListener("input", filter);
  var q = new URLSearchParams(window.location.search).get("q");
  if (q) { input.value = q; }
  filter();
})();
