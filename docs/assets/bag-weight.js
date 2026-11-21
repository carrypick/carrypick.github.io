// Excess baggage calculator (tools/bag-weight.html). Data comes from #bw-data, built from data/airlines.json,
// data/airlines_intl.json and data/extra_baggage.json by scripts/bag_weight.py. Nothing here invents a number:
// when a fare's allowance depends on the route, the traveller types the figure on their ticket.
(function () {
  var form = document.getElementById("bw"), raw = document.getElementById("bw-data");
  if (!form || !raw) return;
  var data = JSON.parse(raw.textContent), $ = function (id) { return document.getElementById(id); };
  var route = $("bw-route"), airline = $("bw-airline"), fare = $("bw-fare"), out = $("bw-out");
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  form.hidden = false;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function r1(x) { return Math.round(x * 10) / 10; }
  function kg(x) { return r1(x) + " kg"; }
  function rs(n) { return "₹" + Math.round(n).toLocaleString("en-IN"); }
  function date(iso) { var p = iso.split("-"); return +p[2] + " " + MONTHS[+p[1] - 1] + " " + p[0]; }
  function poss(n) { return esc(n) + (/s$/.test(n) ? "'" : "'s"); }
  function val(el) { var v = parseFloat(el.value); return isNaN(v) || v < 0 ? null : v; }
  function current() { for (var i = 0; i < data.length; i++) if (data[i].slug === airline.value) return data[i]; return data[0]; }
  function link(href, text, ext) { return '<a href="' + esc(href) + '"' + (ext ? ' target="_blank" rel="noopener"' : "") + ">" + esc(text) + "</a>"; }
  function chip(ok, text) { return '<span class="fit ' + (ok === null ? "fit-na" : ok ? "fit-yes" : "fit-no") + '">' + esc(text) + "</span>"; }
  function row(label, status, detail) { return "<tr><th scope=\"row\">" + esc(label) + "</th><td>" + status + (detail ? '<span class="why">' + detail + "</span>" : "") + "</td></tr>"; }

  function fillAirlines() {
    var keep = airline.value;
    airline.innerHTML = airline.getAttribute("data-" + route.value);
    if ([].some.call(airline.options, function (o) { return o.value === keep; })) airline.value = keep;
    fillFares();
  }
  function fillFares() {
    var a = current();
    fare.innerHTML = a.fares.map(function (f, i) { return '<option value="' + i + '">' + esc(f.fare) + " (" + esc(f.text.length > 40 ? f.text.slice(0, 38) + "…" : f.text) + ")</option>"; }).join("");
    var first = a.fares.findIndex(function (f) { return !f.rule || f.rule.kg !== 0; });
    fare.value = String(first < 0 ? 0 : first);
    calc();
  }

  function calc() {
    var a = current(), f = a.fares[+fare.value] || a.fares[0], rule = f.rule;
    var own = val($("bw-own"));
    $("bw-own-wrap").hidden = !!rule;
    if (!rule && own !== null) rule = { kg: own, note: "" };
    $("bw-allow").innerHTML = "<strong>" + esc(a.name) + ", " + esc(f.fare) + ":</strong> checked " + esc(f.text) +
      ". Cabin: " + esc(a.cabin_text) + "." + (rule ? "" : " This fare's allowance depends on your route, so type the kg shown on your ticket.");

    var cabin = val($("bw-cabin")), personal = val($("bw-personal"));
    var bags = [].map.call(document.querySelectorAll(".bw-bag"), val);
    var entered = bags.map(function (b, i) { return { w: b, n: i + 1 }; }).filter(function (b) { return b.w !== null && b.w > 0; });
    if (cabin === null && personal === null && !entered.length) {
      out.innerHTML = '<p class="checker-total">Type what your bags weigh to see if they are within the allowance.</p>';
      return;
    }
    var rows = [], fees = [], fixes = [], fx = a.fees, cabinOver = 0, cabinRoom = null, checkedOver = 0, checkedRoom = null;

    // Cabin bag and personal item
    var cLimit = a.cabin_kg;
    if (a.personal_shared) {
      var both = (cabin || 0) + (personal || 0);
      if (cabin !== null || personal !== null) {
        var lbl = personal === null ? "Cabin bag" : cabin === null ? "Personal item" : "Cabin bag + personal item";
        if (cLimit) {
          cabinOver = Math.max(0, both - cLimit); cabinRoom = Math.max(0, cLimit - both);
          rows.push(row(lbl, chip(!cabinOver, cabinOver ? "Over by " + kg(cabinOver) : "OK"),
            kg(both) + " of " + kg(cLimit) + " allowed. " + esc(a.name) + " counts any personal item inside this one cabin limit."));
        } else rows.push(row(lbl, chip(null, "No kg limit in our data"), esc(a.cabin_text)));
      }
    } else {
      if (cabin !== null) {
        if (cLimit) {
          cabinOver = Math.max(0, cabin - cLimit); cabinRoom = Math.max(0, cLimit - cabin);
          rows.push(row("Cabin bag", chip(!cabinOver, cabinOver ? "Over by " + kg(cabinOver) : "OK"), kg(cabin) + " of " + kg(cLimit) + " allowed."));
        } else rows.push(row("Cabin bag", chip(null, "No kg limit in our data"), esc(a.cabin_text) + ". Check the airline's page."));
      }
      if (personal !== null) {
        if (a.personal_kg) {
          var pOver = Math.max(0, personal - a.personal_kg);
          rows.push(row("Personal item", chip(!pOver, pOver ? "Over by " + kg(pOver) : "OK"), kg(personal) + " of " + kg(a.personal_kg) + " allowed."));
          if (pOver) cabinOver += pOver;
          else if (cabinOver) fixes.push("Your personal item has " + kg(a.personal_kg - personal) + " of room: move small heavy things like a charger or a book there.");
        } else rows.push(row("Personal item", chip(null, "No kg limit stated"), esc(a.personal_text || "Not stated")));
      }
    }

    // Checked bags
    var sum = entered.reduce(function (t, b) { return t + b.w; }, 0);
    if (entered.length) {
      if (!rule) rows.push(row("Checked bags", chip(null, "Type your allowance"), "Total " + kg(sum) + ". " + esc(f.text)));
      else if (rule.kg === 0) {
        checkedOver = sum;
        rows.push(row("Checked bags", chip(false, "No free checked bag"), "This fare includes no checked bag, so all " + kg(sum) + " must be paid for."));
        if (fx && fx.lite) fees.push(esc(fx.lite));
      } else if (rule.per_bag && a.scope === "international") {
        var room = 0;
        entered.forEach(function (b, i) {
          var over = Math.max(0, b.w - rule.per_bag), extra = i >= rule.pieces;
          if (!extra) room += Math.max(0, rule.per_bag - b.w);
          rows.push(row("Checked bag " + b.n, extra ? chip(false, "Extra bag") : chip(!over, over ? "Over by " + kg(over) : "OK"),
            extra ? "Your fare includes " + rule.pieces + (rule.pieces === 1 ? " bag" : " bags") + ": this one is charged as an extra bag." : kg(b.w) + " of " + kg(rule.per_bag) + " per bag."));
          if (over && !extra) checkedOver += over;
        });
        checkedRoom = room;
        if (checkedOver && room > 0) fixes.push("Another of your bags has " + kg(room) + " of room: move weight into it, as each bag is weighed on its own.");
      } else {
        var total = rule.kg != null ? rule.kg : rule.per_bag;
        checkedOver = Math.max(0, sum - total); checkedRoom = Math.max(0, total - sum);
        rows.push(row(entered.length > 1 ? "Checked bags (total)" : "Checked bag", chip(!checkedOver, checkedOver ? "Over by " + kg(checkedOver) : "OK"),
          kg(sum) + " of " + kg(total) + " allowed" + (rule.note ? " (" + esc(rule.note) + ")" : "") + "."));
        if (rule.pieces && entered.length > rule.pieces) {
          rows.push(row("Number of bags", chip(false, entered.length + " bags, " + rule.pieces + " included"), fx ? esc(fx.piece_text) : "Extra bags cost extra. See the airline's page."));
        }
      }
      if (a.max_bag) entered.forEach(function (b) {
        if (b.w > a.max_bag) rows.push(row("Checked bag " + b.n, chip(false, "Over " + a.max_bag + " kg"),
          poss(a.name) + " rules say no single bag may weigh more than " + a.max_bag + " kg. Split it into two bags."));
      });
    }

    // Fees from our data
    if (checkedOver > 0 && rule && rule.kg !== 0) {
      if (fx) {
        var airport = fx.airport_per_kg * checkedOver;
        fees.push("<strong>At the airport:</strong> " + esc(fx.airport_text) + " × " + kg(checkedOver) + " = " + (fx.upto ? "up to " : "") + rs(airport) + (fx.tax ? " + tax" : "") + ".");
        var slab = null;
        fx.prepaid.forEach(function (s) { if (s[0] >= checkedOver && (!slab || s[0] < slab[0])) slab = s; });
        if (slab) {
          fees.push("<strong>Pre-booked online:</strong> the " + slab[0] + " kg pack costs " + rs(slab[1]) + ". " + esc(fx.prepaid_note));
          if (slab[1] < airport) fixes.push("Pre-book the " + slab[0] + " kg pack online: " + rs(slab[1]) + " instead of about " + rs(airport) + " at the counter.");
        } else if (fx.prepaid.length) fees.push("<strong>Pre-booked online:</strong> you're over the biggest pack (" + fx.prepaid[fx.prepaid.length - 1][0] + " kg). " + esc(fx.prepaid_note));
        else fees.push("<strong>Pre-booked online:</strong> " + esc(fx.prepaid_note));
      }
    }
    if (cabinOver > 0 && fx) fees.push("<strong>Heavy cabin bag:</strong> " + esc(fx.cabin_text));
    var needFee = checkedOver > 0 || cabinOver > 0 || (rule && rule.pieces && entered.length > rule.pieces);
    if (needFee && !fx) {
      if (a.excess) fees.push(esc(a.excess.summary) + "." + (a.excess.points.length ? "<ul>" + a.excess.points.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul>" : ""));
      else fees.push("We don't have " + poss(a.name) + " excess baggage fees yet. Its official page shows them: " + link(a.official, a.name + " baggage page", true) + ".");
    }

    // Fixes
    if (checkedOver > 0 && cabinRoom > 0) fixes.unshift("Your cabin bag has " + kg(cabinRoom) + " of room: move up to " + kg(Math.min(cabinRoom, checkedOver)) +
      " of heavy things like shoes or books into it, within its size limit. Liquids over 100 ml must stay in the checked bag.");
    if (cabinOver > 0 && checkedRoom > 0) fixes.unshift("Your checked baggage has " + kg(checkedRoom) + " of room: move up to " + kg(Math.min(checkedRoom, cabinOver)) +
      " from the cabin bag into it. Keep medicines, documents, power banks and valuables with you.");
    if (cabinOver > 0 && !entered.length) fixes.push("Over in the cabin? A heavy cabin bag is usually checked in, where it counts towards your checked allowance.");
    if (checkedOver > 0 || cabinOver > 0) fixes.push("Wear your heaviest jacket and shoes on the flight instead of packing them.");

    var html = '<div class="table-wrap"><table class="result-table"><tbody>' + rows.join("") + "</tbody></table></div>";
    var anyOver = checkedOver > 0 || cabinOver > 0 || rows.join("").indexOf("fit-no") > -1;
    html = '<p class="checker-total ' + (anyOver ? "over" : "") + '">' + (anyOver ? "Some of your baggage is over the allowance." : rows.join("").indexOf("fit-yes") > -1 ? "Your bags are within the allowance." : "") + "</p>" + html;
    if (fees.length) html += "<h3>What " + esc(a.name) + " charges</h3><ul><li>" + fees.join("</li><li>") + "</li></ul>";
    if (fixes.length) html += "<h3>How to fix it</h3><ul><li>" + fixes.join("</li><li>") + "</li></ul>";
    var src = a.sources.slice(0, 2).map(function (s) { return link(s.url, s.label, true); });
    if (fx) src = src.concat(fx.sources.slice(0, 1).map(function (s) { return link(s.url, s.label, true); }));
    html += '<p class="checked">Source: ' + poss(a.name) + " official pages (" + src.join(", ") + "), checked " + date(fx ? fx.checked : a.checked) +
      ". See our " + link("../" + a.page, a.name + " baggage rules") + (fx ? " and " + link("../" + fx.page, a.name + " extra baggage charges") : "") +
      ". " + esc(a.note) + "</p>";
    out.innerHTML = html;
  }

  route.addEventListener("change", fillAirlines);
  airline.addEventListener("change", fillFares);
  fare.addEventListener("change", calc);
  form.addEventListener("input", function (ev) { if (ev.target.tagName === "INPUT") calc(); });
  $("bw-add").addEventListener("click", function () {
    var n = document.querySelectorAll(".bw-bag").length + 1;
    if (n > 6) return;
    var l = document.createElement("label");
    l.innerHTML = "Checked bag " + n + '<input class="bw-bag" type="number" min="0" max="60" step="0.1" inputmode="decimal">';
    $("bw-bags").appendChild(l);
    l.querySelector("input").focus();
  });
  $("bw-clear").addEventListener("click", function () { [].forEach.call(form.querySelectorAll("input"), function (i) { i.value = ""; }); calc(); });
  fillAirlines();
})();
