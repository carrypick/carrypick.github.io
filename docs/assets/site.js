// Use the Telegram or WhatsApp tracking ID when the visitor arrived from that channel
// (post links end in ?src=tg or ?src=wa), so Amazon reports show which channel sells.
// Tags are per channel, never per visitor. Everyone else keeps the default tag.
(function () {
  var tags = window.CARRYPICK_TAGS || {};
  var src = new URLSearchParams(window.location.search).get("src");
  try {
    if (src && tags[src]) sessionStorage.setItem("cp_src", src);
    else src = sessionStorage.getItem("cp_src");
  } catch (err) { /* storage blocked: only this page uses the channel tag */ }
  var tag = src && tags[src];
  if (!tag) return;
  document.querySelectorAll('a[href^="https://www.amazon.in/dp/"]').forEach(function (a) {
    var url = new URL(a.href);
    url.searchParams.set("tag", tag);
    a.href = url.toString();
  });
})();

// "Deal spotted" badges show only for 24 hours after Amazon showed a deal label (DEAL_HOURS in build.py).
// The words are written here, not in the HTML, so an expired deal claim never stays on the page.
(function () {
  var HOURS = 24;
  function when(d) {
    try {
      return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
    } catch (err) { return d.toDateString(); }
  }
  document.querySelectorAll("[data-deal-seen]").forEach(function (el) {
    var seen = new Date(el.getAttribute("data-deal-seen"));
    var left = seen.getTime() + HOURS * 3600 * 1000 - Date.now();
    if (!(left > 0)) return;
    if (el.classList.contains("deal-note")) {
      el.textContent = "We spotted a deal on Amazon.in on " + when(seen) + ". Deals can end at any time, so check today's price.";
    } else if (el.classList.contains("deal-badge")) {
      el.textContent = "Deal spotted " + when(seen);
    }
    el.hidden = false;
    setTimeout(function () { el.hidden = true; }, left);
  });
  document.querySelectorAll("[data-deal-section]").forEach(function (section) {
    if (section.querySelector("[data-deal-seen]:not([hidden])")) section.hidden = false;
  });
})();
