// Long weekends planner: hide table rows by month and leave days. Every plan is worked out at build time by
// scripts/long_weekends.py; each row says its month (data-month), the leave it needs with and without restricted
// holidays (data-leave, data-leave-rh) and whether it is worth showing in each view (data-plain, data-rh).
// Links like long-weekends-2027.html#month=3 or #leave=1 open with that filter chosen.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("lw"), table = $("lw-table");
  if (!form || !table) return;
  var month = $("lw-month"), leave = $("lw-leave"), rh = $("lw-rh"), count = $("lw-count"), none = $("lw-none");
  var rows = table.tBodies[0].rows;

  function show() {
    var m = month.value, n = +leave.value, useRh = rh.checked, shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], d = r.dataset;
      var ok = (useRh ? d.rh === "1" && +d.leaveRh <= n : d.plain === "1" && +d.leave <= n) && (m === "all" || d.month === m);
      r.hidden = !ok;
      if (ok) shown++;
    }
    count.textContent = shown ? "Showing " + shown + " long weekend" + (shown === 1 ? "" : "s") + "." : "";
    none.hidden = shown > 0;
  }

  var h = location.hash.replace("#", "").split("&");
  h.forEach(function (kv) {
    var p = kv.split("=");
    if (p[0] === "month" && month.querySelector('option[value="' + p[1] + '"]')) month.value = p[1];
    if (p[0] === "leave" && /^[0-3]$/.test(p[1])) leave.value = p[1];
    if (p[0] === "rh") rh.checked = p[1] === "1";
  });
  [month, leave, rh].forEach(function (el) { el.addEventListener("change", show); });
  form.hidden = false;
  var nojs = $("lw-nojs");
  if (nojs) nojs.hidden = true;
  show();
})();
