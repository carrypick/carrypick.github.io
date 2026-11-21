// Geo-aware buy buttons. Loaded only when config amazon_global.enabled is true (build.py region_switch).
// The HTML always holds the Amazon.in link (tag carrypick-21), so visitors in India and visitors without JS
// see exactly today's buttons. Visitors outside India get the amazon.com link from data-global-href.
// No redirects and no pop-ups: we only change where a button points, and the visitor still clicks it.
// Region: a saved choice from the footer switch, else the browser time zone (Asia/Kolkata = India).
(function () {
  var KEY = "cp_region";

  function guess() {
    try {
      var tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
      if (tz === "Asia/Kolkata" || tz === "Asia/Calcutta") return "in";
      return tz ? "global" : "in";
    } catch (err) { return "in"; }
  }

  function saved() {
    try {
      var r = localStorage.getItem(KEY);
      return r === "in" || r === "global" ? r : null;
    } catch (err) { return null; }
  }

  function apply(region) {
    var abroad = region === "global";
    document.querySelectorAll("a[data-global-href]").forEach(function (a) {
      if (!a.hasAttribute("data-india-href")) {
        // site.js may already have set a Telegram/WhatsApp channel tag on this Amazon.in link: keep it.
        a.setAttribute("data-india-href", a.getAttribute("href"));
        a.setAttribute("data-india-label", a.textContent);
      }
      a.setAttribute("href", abroad ? a.getAttribute("data-global-href") : a.getAttribute("data-india-href"));
      a.textContent = abroad ? a.getAttribute("data-global-label") : a.getAttribute("data-india-label");
    });
    // India-only partner links (EarnKaro hotels, Thrillophilia, Akasa): hide a whole box only when a global
    // box replaces it; a single India-only row inside a box (Akasa) is hidden for visitors abroad.
    document.querySelectorAll('.cta-box[data-region="in"][data-has-global], .book-row[data-region="in"]').forEach(function (el) {
      el.hidden = abroad;
    });
    document.querySelectorAll('[data-region="global"]').forEach(function (el) { el.hidden = !abroad; });
    document.querySelectorAll("[data-set-region]").forEach(function (b) {
      var on = b.getAttribute("data-set-region") === region;
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.style.fontWeight = on ? "700" : "400";
      b.style.textDecoration = on ? "none" : "underline";
    });
  }

  var region = saved() || guess();

  document.querySelectorAll(".region-switch").forEach(function (sw) {
    sw.hidden = false;
    sw.querySelectorAll("button").forEach(function (b) {
      b.style.cssText += "background:none;border:0;padding:0 2px;color:inherit;font:inherit;cursor:pointer;";
      b.addEventListener("click", function () {
        region = b.getAttribute("data-set-region");
        try { localStorage.setItem(KEY, region); } catch (err) { /* storage blocked: choice lasts this page */ }
        apply(region);
      });
    });
  });
  apply(region);
})();
