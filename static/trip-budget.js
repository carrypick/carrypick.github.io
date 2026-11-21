// Trip budget calculator + split the bill (tools/trip-budget-calculator.html).
// Every amount is typed in by the reader; we never fill in prices. Inputs are kept in localStorage
// and can travel in the link (#plan=...), so friends open the same plan.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var form = $("tb"), sp = $("sp");
  if (!form || !sp) return;
  var KEY = "cp-trip-budget";
  var F = ["people", "nights", "travel", "hotel", "rooms", "food", "local", "activities", "visa", "shopping", "buffer"];
  var PARTS = [["travel", "Travel"], ["stay", "Hotel"], ["food", "Food"], ["local", "Local transport"], ["activities", "Activities"],
    ["visa", "Visa or permits"], ["shopping", "Shopping"], ["buffer", "Buffer"]];
  var friends = [], exps = [];
  var CUR = { INR: ["₹", "en-IN", 0], USD: ["$", "en-US", 0], EUR: ["€", "en-IE", 0], GBP: ["£", "en-GB", 0], AED: ["AED ", "en-AE", 0],
    SGD: ["S$", "en-SG", 0], THB: ["฿", "en-US", 0], JPY: ["¥", "ja-JP", 0], AUD: ["A$", "en-AU", 0] };
  var cur = "INR"; // only the symbol and number format change: no conversion, no rates
  var money = function (n) { var c = CUR[cur]; return c[0] + Math.round(n).toLocaleString(c[1]); };
  var num = function (id) { var v = parseFloat($("tb-" + id).value); return isFinite(v) && v > 0 ? v : 0; };
  var esc = function (s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; };

  function state() {
    var f = {};
    F.forEach(function (k) { var v = $("tb-" + k).value; if (v !== "") f[k] = v; });
    return { f: f, p: friends, e: exps, c: cur };
  }
  function load(s) {
    if (!s || typeof s !== "object") return;
    var f = s.f || {};
    if (typeof s.c === "string" && CUR[s.c]) { cur = s.c; $("tb-cur").value = cur; }
    F.forEach(function (k) { $("tb-" + k).value = f[k] != null ? String(f[k]).slice(0, 12) : ""; });
    friends = Array.isArray(s.p) ? s.p.filter(function (x) { return typeof x === "string"; }).slice(0, 30).map(function (x) { return x.slice(0, 30); }) : [];
    exps = Array.isArray(s.e) ? s.e.filter(function (x) {
      return x && typeof x.by === "number" && x.by < friends.length && isFinite(x.amt);
    }).slice(0, 200).map(function (x) {
      var forList = Array.isArray(x.for) ? x.for.filter(function (i) { return typeof i === "number" && i < friends.length; }) : [];
      return { by: x.by, what: String(x.what || "").slice(0, 40), amt: +x.amt, for: forList };
    }) : [];
  }
  function link() {
    return location.href.split("#")[0] + "#plan=" + encodeURIComponent(JSON.stringify(state()));
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state())); localStorage.setItem(KEY + "-cur", cur); } catch (err) {}
    $("tb-wa").href = "https://wa.me/?text=" + encodeURIComponent("Our trip budget on CarryPick: " + link());
  }

  function calc() {
    var people = Math.round(num("people")), nights = Math.round(num("nights"));
    var days = nights + 1, rooms = num("rooms") || (people ? 1 : 0);
    var v = {
      travel: num("travel") * people, stay: num("hotel") * rooms * nights, food: num("food") * people * days,
      local: num("local") * days, activities: num("activities"), visa: num("visa") * people, shopping: num("shopping")
    };
    var sub = 0; for (var k in v) sub += v[k];
    v.buffer = sub * Math.min(num("buffer"), 100) / 100;
    var total = sub + v.buffer;
    var out = $("tb-out"), bar = $("tb-bar"), leg = $("tb-legend");
    if (!total) {
      out.textContent = "Type in your people, nights and amounts to see your total.";
      bar.hidden = true; leg.innerHTML = ""; return;
    }
    var bits = ["Total: " + money(total)];
    if (people) bits.push(money(total / people) + " per person");
    if (nights) bits.push(money(total / days) + " per day (" + days + " days)");
    out.textContent = bits.join(" · ");
    bar.innerHTML = ""; leg.innerHTML = "";
    PARTS.forEach(function (p, i) {
      var amt = v[p[0]]; if (!amt) return;
      var pct = amt / total * 100;
      var s = document.createElement("span");
      s.className = "tc-seg tc-c" + i; s.style.width = pct + "%"; s.title = p[1];
      bar.appendChild(s);
      var li = document.createElement("li");
      li.innerHTML = '<i class="tc-dot tc-c' + i + '"></i>' + esc(p[1]) + ": <strong>" + money(amt) + "</strong> (" + Math.round(pct) + "%)";
      leg.appendChild(li);
    });
    bar.hidden = false;
  }

  // ---------- split the bill ----------
  function renderSplit() {
    var fl = $("sp-friends"), payer = $("sp-payer"), forBox = $("sp-for");
    fl.innerHTML = ""; payer.innerHTML = ""; forBox.innerHTML = "";
    friends.forEach(function (n, i) {
      var li = document.createElement("li");
      li.innerHTML = esc(n) + ' <button type="button" aria-label="Remove ' + esc(n) + '" data-rm="' + i + '">×</button>';
      fl.appendChild(li);
      var o = document.createElement("option"); o.value = i; o.textContent = n; payer.appendChild(o);
      var l = document.createElement("label"); l.className = "pm-pill";
      l.innerHTML = '<input type="checkbox" value="' + i + '" checked> ' + esc(n);
      forBox.appendChild(l);
    });
    $("sp-for-box").hidden = friends.length < 2;
    var el = $("sp-exp"); el.innerHTML = "";
    exps.forEach(function (x, i) {
      var li = document.createElement("li");
      var who = x.for.length && x.for.length < friends.length ? " (for " + x.for.map(function (j) { return friends[j]; }).join(", ") + ")" : "";
      li.innerHTML = "<span>" + esc(friends[x.by]) + " paid <strong>" + money(x.amt) + "</strong>" + (x.what ? " for " + esc(x.what) : "") + esc(who) +
        '</span> <button type="button" aria-label="Remove payment" data-rx="' + i + '">×</button>';
      el.appendChild(li);
    });
    settle();
  }
  function settle() {
    var out = $("sp-out");
    if (friends.length < 2 || !exps.length) {
      out.innerHTML = friends.length < 2 ? '<p class="hint">Add at least two friends to split the bill.</p>' : '<p class="hint">Add a payment to see who owes whom.</p>';
      return;
    }
    var bal = friends.map(function () { return 0; }), spent = 0;
    exps.forEach(function (x) {
      var who = x.for.length ? x.for : friends.map(function (_, i) { return i; });
      bal[x.by] += x.amt; spent += x.amt;
      who.forEach(function (j) { bal[j] -= x.amt / who.length; });
    });
    var cred = [], debt = [];
    bal.forEach(function (b, i) { if (b > 0.5) cred.push([i, b]); else if (b < -0.5) debt.push([i, -b]); });
    cred.sort(function (a, b) { return b[1] - a[1]; }); debt.sort(function (a, b) { return b[1] - a[1]; });
    var moves = [], c = 0, d = 0;
    while (c < cred.length && d < debt.length) {
      var amt = Math.min(cred[c][1], debt[d][1]);
      moves.push(esc(friends[debt[d][0]]) + " pays " + esc(friends[cred[c][0]]) + " <strong>" + money(amt) + "</strong>");
      cred[c][1] -= amt; debt[d][1] -= amt;
      if (cred[c][1] < 0.5) c++;
      if (debt[d][1] < 0.5) d++;
    }
    var html = "<p><strong>Spent together: " + money(spent) + "</strong></p>";
    html += moves.length ? "<h3>Settle up</h3><ul class=\"tc-settle\"><li>" + moves.join("</li><li>") + "</li></ul>" : "<p>Everyone is square. Nobody owes anything.</p>";
    out.innerHTML = html;
  }

  // ---------- events ----------
  F.forEach(function (k) { $("tb-" + k).addEventListener("input", function () { calc(); save(); }); });
  function addFriend() {
    var n = $("sp-name").value.trim().slice(0, 30);
    if (!n || friends.length >= 30) return;
    friends.push(n); $("sp-name").value = ""; $("sp-name").focus();
    renderSplit(); save();
  }
  $("sp-add-f").addEventListener("click", addFriend);
  $("sp-name").addEventListener("keydown", function (ev) { if (ev.key === "Enter") { ev.preventDefault(); addFriend(); } });
  $("sp-add-e").addEventListener("click", function () {
    var amt = parseFloat($("sp-amt").value), by = parseInt($("sp-payer").value, 10);
    if (!(amt > 0) || isNaN(by)) { $("sp-amt").focus(); return; }
    var forList = [];
    Array.prototype.forEach.call($("sp-for").querySelectorAll("input"), function (c) { if (c.checked) forList.push(+c.value); });
    if (!forList.length) return;
    if (forList.length === friends.length) forList = [];
    exps.push({ by: by, what: $("sp-what").value.trim().slice(0, 40), amt: amt, for: forList });
    $("sp-amt").value = ""; $("sp-what").value = "";
    renderSplit(); save();
  });
  sp.addEventListener("click", function (ev) {
    var t = ev.target;
    if (t.hasAttribute("data-rm")) {
      var i = +t.getAttribute("data-rm");
      friends.splice(i, 1);
      exps = exps.filter(function (x) { return x.by !== i; }).map(function (x) {
        x.by = x.by > i ? x.by - 1 : x.by;
        x.for = x.for.filter(function (j) { return j !== i; }).map(function (j) { return j > i ? j - 1 : j; });
        return x;
      });
      renderSplit(); save();
    } else if (t.hasAttribute("data-rx")) {
      exps.splice(+t.getAttribute("data-rx"), 1); renderSplit(); save();
    }
  });
  $("tb-copy").addEventListener("click", function () {
    var url = link(), btn = this;
    try { history.replaceState(null, "", url); } catch (err) {}
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(function () { btn.textContent = "Link copied"; }, function () {});
  });
  $("tb-reset").addEventListener("click", function () {
    load({ f: {}, p: [], e: [], c: cur });
    try { localStorage.removeItem(KEY); history.replaceState(null, "", location.pathname); } catch (err) {}
    calc(); renderSplit(); save();
  });

  // ---------- start: the link wins over what this browser saved ----------
  var start = null, m = location.hash.match(/^#plan=(.+)$/);
  if (m) { try { start = JSON.parse(decodeURIComponent(m[1])); } catch (err) {} }
  if (!start) { try { start = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (err) {} }
  if (!start) { try { var sc = localStorage.getItem(KEY + "-cur"); if (sc && CUR[sc]) start = { c: sc }; } catch (err) {} }
  load(start);
  $("tb-print").hidden = true;
  $("tb-cur").addEventListener("change", function () { cur = CUR[this.value] ? this.value : "INR"; calc(); renderSplit(); save(); });
  form.hidden = false; sp.hidden = false;
  calc(); renderSplit(); save();
})();
