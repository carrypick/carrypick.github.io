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

// Language menu. English and our own Hindi pages are plain links. Other languages use Google Translate:
// its script loads only after a visitor picks one, and then on each page while Google's "googtrans" cookie holds that choice.
(function () {
  var menu = document.querySelector(".lang-menu");
  if (!menu) return;
  var pageLang = (document.documentElement.lang || "en").slice(0, 2);
  function chosen() {
    var m = document.cookie.match(/(?:^|; )googtrans=\/[^/;]*\/([^;]+)/);
    return m && m[1] !== pageLang ? decodeURIComponent(m[1]) : null;
  }
  function save(value) {
    var host = location.hostname;
    ["", "; domain=" + host, "; domain=." + host.split(".").slice(-2).join(".")].forEach(function (domain) {
      document.cookie = "googtrans=" + (value ? value + "; path=/" : "; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT") + domain;
    });
  }
  menu.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-lang]");
    if (ev.target.closest("[data-gt-reset]")) { save(null); return; }
    if (!btn) return;
    var lang = btn.getAttribute("data-lang");
    if (lang === pageLang) {
      if (chosen()) { save(null); location.reload(); } else { menu.open = false; }
      return;
    }
    save("/" + pageLang + "/" + lang);
    location.reload();
  });
  document.addEventListener("click", function (ev) {
    if (menu.open && !menu.contains(ev.target)) menu.open = false;
  });
  var lang = chosen();
  if (!lang) return;
  // Show which language is on, and a bar to go back (it replaces Google's own banner, which the CSS hides).
  menu.querySelectorAll(".lang-grid .on").forEach(function (el) { el.classList.remove("on"); el.removeAttribute("aria-current"); });
  var picked = menu.querySelector('[data-lang="' + lang + '"]');
  if (picked) { picked.classList.add("on"); picked.setAttribute("aria-current", "true"); }
  menu.querySelector(".lang-code").textContent = lang.toUpperCase();
  var bar = document.createElement("div");
  bar.className = "gt-notice notranslate";
  bar.innerHTML = '<span class="wrap">Translated by Google Translate. Machine translation may have mistakes. ' +
    '<button type="button" class="link-btn" data-lang="' + pageLang + '">Show original</button></span>';
  bar.addEventListener("click", function (ev) { if (ev.target.closest("[data-lang]")) { save(null); location.reload(); } });
  var header = document.querySelector(".site-header");
  header.parentNode.insertBefore(bar, header.nextSibling);
  var holder = document.createElement("div");
  holder.id = "gt-el";
  holder.hidden = true;
  document.body.appendChild(holder);
  window.cpTranslateInit = function () {
    new google.translate.TranslateElement({ pageLanguage: pageLang, autoDisplay: false }, "gt-el");
  };
  var script = document.createElement("script");
  script.src = "https://translate.google.com/translate_a/element.js?cb=cpTranslateInit";
  document.head.appendChild(script);
})();
