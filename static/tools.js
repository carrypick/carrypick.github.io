// Size and weight tools (tools/*.html): watch size by wrist, backpack by laptop size, packed bag weight.
(function () {
  var $ = function (id) { return document.getElementById(id); };
  function round(x) { return Math.round(x * 10) / 10; }

  // Watch size by wrist: the chart rows carry their wrist range, the pick cards their dial size in mm.
  if ($("ws-cm")) {
    var rows = [].slice.call(document.querySelectorAll("#ws-table tr[data-wrist]"));
    var watches = [].slice.call(document.querySelectorAll("#ws-picks [data-mm]"));
    var watchSize = function () {
      var v = parseFloat($("ws-cm").value), cm = $("ws-unit").value === "in" ? v * 2.54 : v;
      rows.forEach(function (r) { r.classList.remove("on"); });
      if (!(cm >= 10 && cm <= 30)) {
        $("ws-out").textContent = "Type your wrist size to see the dial sizes that suit it.";
        watches.forEach(function (c) { c.hidden = false; });
        $("ws-picks-note").textContent = "Sorted from small to large. Type your wrist size above to see the ones that suit it.";
        return;
      }
      var row = rows.filter(function (r) {
        var lim = r.getAttribute("data-wrist").split("-").map(parseFloat);
        return cm >= lim[0] && cm < lim[1];
      })[0];
      row.classList.add("on");
      var mm = row.cells[2].textContent.match(/\d+/g).map(Number);
      $("ws-out").textContent = "A " + round(cm) + " cm wrist suits a dial of about " + mm[0] + "–" + mm[1] + " mm.";
      var shown = 0;
      watches.forEach(function (c) {
        var size = parseFloat(c.getAttribute("data-mm"));
        c.hidden = !(size >= mm[0] - 1 && size <= mm[1] + 1);
        if (!c.hidden) shown++;
      });
      $("ws-picks-note").textContent = shown ? "Our picks in that size:" : "None of our picks is in that size yet. All picks are shown below.";
      if (!shown) watches.forEach(function (c) { c.hidden = false; });
    };
    $("ws-cm").addEventListener("input", watchSize);
    $("ws-unit").addEventListener("change", watchSize);
  }

  // Backpack by laptop size: cards carry the largest laptop size the seller lists (0 = not listed).
  if ($("lb-size")) {
    var bags = [].slice.call(document.querySelectorAll("#lb-picks [data-inch]"));
    bags.forEach(function (c) {
      var inch = parseFloat(c.getAttribute("data-inch"));
      var tag = document.createElement("p");
      tag.className = "fit-tag small muted";
      tag.textContent = inch ? "Laptop: up to " + inch + " inch" : "Laptop size: check listing";
      c.querySelector(".card-body").appendChild(tag);
    });
    $("lb-size").addEventListener("change", function () {
      var want = parseFloat(this.value), fits = 0;
      bags.forEach(function (c) {
        var inch = parseFloat(c.getAttribute("data-inch"));
        c.hidden = want ? !(inch >= want - 0.3) : false;
        if (want && !c.hidden) fits++;
      });
      $("lb-out").textContent = !want ? "Choose your laptop size to see the backpacks that fit it."
        : fits ? fits + (fits === 1 ? " of our backpacks fits" : " of our backpacks fit") + " a " + want + " inch laptop, by the seller's listed size."
        : "None of our picks lists that size yet.";
    });
  }

  // Packed bag weight: every item input carries its typical weight in kg.
  if ($("bw")) {
    var inputs = [].slice.call(document.querySelectorAll("#bw ~ .pack-list input[data-kg], .pack-list input[data-kg]"));
    var weigh = function () {
      var bag = parseFloat($("bw-bag").value), limit = parseFloat($("bw-limit").value), things = 0;
      inputs.forEach(function (i) { things += (parseFloat(i.value) || 0) * parseFloat(i.getAttribute("data-kg")); });
      var total = bag + things, left = limit - total;
      $("bw-out").textContent = "About " + round(total) + " kg in total (bag " + round(bag) + " kg + things " + round(things) + " kg). " +
        (left >= 0 ? "About " + round(left) + " kg left of your " + limit + " kg limit." : "About " + round(-left) + " kg over your " + limit + " kg limit.");
      $("bw-out").classList.toggle("over", left < 0);
    };
    inputs.forEach(function (i) { i.addEventListener("input", weigh); });
    $("bw-bag").addEventListener("change", weigh);
    $("bw-limit").addEventListener("change", weigh);
    $("bw-clear").addEventListener("click", function () { inputs.forEach(function (i) { i.value = 0; }); weigh(); });
    weigh();
  }
})();
