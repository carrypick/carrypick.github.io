// Embed view of the cabin bag checker and the power bank flight checker (backlink kit, plan A9, 28 Nov 2026).
// The same URL with ?embed=1 shows only the checker and a "Tool by CarryPick" credit (rel="nofollow"), for bloggers
// who paste our iframe code. No new page: the canonical stays the tool page, and this view is set to noindex.
// The header, menus, footer, our picks and every other link are removed from the page, not just hidden.
(function () {
  var params;
  try { params = new URLSearchParams(window.location.search); } catch (err) { return; }
  if (params.get("embed") !== "1") return;
  var root = document.documentElement;
  root.classList.add("cp-embed");
  var robots = document.querySelector('meta[name="robots"]');
  if (robots) robots.setAttribute("content", "noindex, follow");

  // keep: what the embed shows; drop: parts of it that point at our picks or other pages
  var VIEWS = [
    { test: "#bag-checker", keep: ["#bag-checker", "#bc-results"], drop: ["#bc-pick"] },
    { test: "#pb", keep: ["#pb"], drop: ['a[href="#picks"]'] }
  ];

  document.addEventListener("DOMContentLoaded", function () {
    var view = VIEWS.filter(function (v) { return document.querySelector(v.test); })[0];
    if (!view) return;
    var canonical = document.querySelector('link[rel="canonical"]');
    var toolUrl = canonical ? canonical.href : window.location.href.split("?")[0];
    var box = document.createElement("div");
    box.className = "cp-embed-box";
    var h1 = document.querySelector("main h1");
    if (h1) {
      var title = document.createElement("p");
      title.className = "cp-embed-title";
      title.textContent = h1.textContent;
      box.appendChild(title);
    }
    view.drop.forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) (el.closest("label, p") || el).remove();
    });
    view.keep.forEach(function (sel) {
      var el = document.querySelector(sel);
      if (!el) return;
      var block = el.closest(".table-wrap") || el;
      var next = block.nextElementSibling;
      box.appendChild(block);
      if (next && next.classList.contains("checked")) box.appendChild(next);
    });
    // Plain text instead of links inside the tool: the only link in the embed is the brand credit.
    box.querySelectorAll("a").forEach(function (a) {
      a.replaceWith(document.createTextNode(a.textContent));
    });
    var credit = document.createElement("p");
    credit.className = "cp-credit";
    var link = document.createElement("a");
    link.href = toolUrl;
    link.target = "_blank";
    link.rel = "nofollow noopener";
    link.textContent = "Tool by CarryPick";
    credit.appendChild(link);
    box.appendChild(credit);
    Array.prototype.slice.call(document.body.children).forEach(function (child) {
      if (child.tagName !== "SCRIPT") child.remove();
    });
    document.body.appendChild(box);
  });
})();
