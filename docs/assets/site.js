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
