"""Build the static website into docs/ from data/ and content/.

Run:  python3 scripts/build.py
Amazon rules built in: disclosure on every page, no prices, no ratings,
no product images, no auto-redirects, buy links marked as paid.
Free stock photos (data/photos.json) only illustrate guides, categories and
the home page; pick pages and product cards never show them.
"""

import json
import re
import shutil
import sys
import urllib.parse
from datetime import date, datetime, timedelta
from html import escape as e

import diagrams
from common import IST, ROOT, amazon_link, load_config, load_deals

DOCS = ROOT / "docs"
ARTICLES_DIR = ROOT / "content" / "articles"
TRIPS_DIR = ROOT / "content" / "trips"
TRIPS_HI_DIR = ROOT / "content" / "trips-hi"  # Hindi versions, same file names as content/trips
AIRLINES_FILE = ROOT / "data" / "airlines.json"
INTL_AIRLINES_FILE = ROOT / "data" / "airlines_intl.json"
PHOTOS_FILE = ROOT / "data" / "photos.json"
RAILWAYS_FILE = ROOT / "data" / "railways.json"
FLIGHT_ITEMS_FILE = ROOT / "data" / "flight_items.json"
HINDI_FILE = ROOT / "data" / "hindi.json"
STATIC_DIR = ROOT / "static"
PHOTO_DIR = STATIC_DIR / "photos"
HERO_PHOTO = "traveller-sunset"
BAGGAGE_PHOTO = "airport-terminal"
DEAL_HOURS = 24  # how long a "Deal spotted" badge shows (site.js hides it after this, and must match)
PHOTOS = {}    # filled by build() from data/photos.json
DIAGRAMS = {}  # filled by build() from scripts/diagrams.py
TOOLS = []     # travel tool pages, filled by build(): (path, short name, eyebrow, title, text, link text, icon, tint, photo)
HINDI_PAGES = {}  # English path -> its Hindi version, filled by build() when data/hindi.json exists
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
KEEP_IN_DOCS = {"CNAME"}
BUY_ATTRS = 'rel="sponsored nofollow noopener" target="_blank"'
FONTS = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
HINDI_FONT = "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700&display=swap"
HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]

# Simple line icons (24x24, drawn with currentColor) so the site has no copied product images.
ICONS = {
    "backpack": '<path d="M9 6.5V5a3 3 0 0 1 6 0v1.5"/><rect x="5" y="6.5" width="14" height="14.5" rx="4"/>'
                '<rect x="8.5" y="13" width="7" height="5" rx="1.5"/><path d="M9.5 6.5v3M14.5 6.5v3"/>',
    "suitcase": '<rect x="6" y="6" width="12" height="13" rx="2.5"/><path d="M10 6V3.5h4V6"/>'
                '<path d="M10 9.5v6M14 9.5v6"/><circle cx="9" cy="21" r="1"/><circle cx="15" cy="21" r="1"/>',
    "watch": '<circle cx="12" cy="12" r="5.5"/><path d="M12 9.5V12l1.8 1.2"/>'
             '<path d="M9.3 7.1 9.9 3h4.2l.6 4.1M9.3 16.9l.6 4.1h4.2l.6-4.1"/>',
    "plane": '<path d="M21 15.5v-2L13.5 9V4.5a1.5 1.5 0 0 0-3 0V9L3 13.5v2l7.5-2.5v4.6l-2 1.4V21l3.5-1 3.5 1v-2l-2-1.4V13z"/>',
    "check": '<path d="M5 12.5l4.2 4.2L19 7"/>',
    "train": '<rect x="5.5" y="3" width="13" height="14" rx="3"/><path d="M5.5 10.5h13M9 17l-2.5 4M15 17l2.5 4"/>'
             '<circle cx="9" cy="13.8" r=".9"/><circle cx="15" cy="13.8" r=".9"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "ruler": '<rect x="2.5" y="8" width="19" height="8" rx="1.5"/><path d="M6.5 8v3M10.5 8v4M14.5 8v3M18.5 8v4"/>',
    "pin": '<path d="M12 21s-6-5.4-6-10a6 6 0 0 1 12 0c0 4.6-6 10-6 10z"/><circle cx="12" cy="11" r="2.2"/>',
    "send": '<path d="M21 4 3 11l6.5 2.5L19 7l-7 8.2V20l3.2-3.6L19 19.5z"/>',
    "link": '<path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1"/><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    "chat": '<path d="M20.5 11.5a8.5 8.5 0 0 1-12.6 7.4L3.5 20l1.2-4.2A8.5 8.5 0 1 1 20.5 11.5z"/>',
    "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5"/>',
    "tag": '<path d="M3.5 12.2V4.5a1 1 0 0 1 1-1h7.7l8.3 8.3-8.7 8.7z"/><circle cx="8" cy="8" r="1.6"/>',
    "jacket": '<path d="M9 3.5 5 6 3 14l3 1 1-3v9h10v-9l1 3 3-1-2-8-4-2.5"/><path d="M9 3.5 12 6l3-2.5M12 6v15"/>',
    "shoe": '<path d="M3 8c1.5 1 3 1 4.5 0l5.2 5c1 1 2.4 1.5 3.8 1.5h3.2A1.8 1.8 0 0 1 21.5 16.3v1.7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>'
            '<path d="M3 15.5h18.3M9.8 10.3 8.3 11.8M12 12.5l-1.5 1.5"/>',
    "handbag": '<path d="M5.5 9h13l1.5 11.5a.5.5 0 0 1-.5.5h-15a.5.5 0 0 1-.5-.5z"/><path d="M8.5 12V7a3.5 3.5 0 0 1 7 0v5"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1.1 1 1.8V16h5v-.3c0-.7.4-1.4 1-1.8A6 6 0 0 0 12 3z"/>',
}


def icon(name, cls="icon"):
    return ('<svg class="%s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % (cls, ICONS[name]))


def fmt_date(value):
    d = datetime.fromisoformat(value) if "T" in value else datetime.strptime(value, "%Y-%m-%d")
    return "%d %s" % (d.day, d.strftime("%b %Y"))


def hi_date(value):
    d = datetime.strptime(value[:10], "%Y-%m-%d")
    return "%d %s %d" % (d.day, HI_MONTHS[d.month - 1], d.year)


def telegram_url(cfg):
    channel = cfg["telegram_channel"].lstrip("@")
    return "https://t.me/" + channel if channel else ""


def follow_links(cfg):
    links = []
    if telegram_url(cfg):
        links.append('<li><a href="%s" target="_blank" rel="noopener">Telegram channel</a></li>' % e(telegram_url(cfg)))
    if cfg.get("whatsapp_channel"):
        links.append('<li><a href="%s" target="_blank" rel="noopener">WhatsApp channel</a></li>' % e(cfg["whatsapp_channel"]))
    return "".join(links)


# ---------- page shell ----------

def abs_url(cfg, path=""):
    return cfg["base_url"].rstrip("/") + "/" + path


def org_schema(cfg):
    same_as = [u for u in (telegram_url(cfg), cfg.get("whatsapp_channel")) if u]
    return {"@type": "Organization", "name": cfg["site_name"], "url": abs_url(cfg),
            "logo": abs_url(cfg, "assets/logo.png"), "sameAs": same_as}


def crumbs_schema(cfg, items):
    """items: (name, path) pairs from Home down to the current page."""
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i, "name": name, "item": abs_url(cfg, path)}
        for i, (name, path) in enumerate(items, 1)]}


def schema_tags(cfg, schema):
    if not (schema and cfg["base_url"]):
        return ""
    return "".join('\n<script type="application/ld+json">%s</script>'
                   % json.dumps(s, ensure_ascii=False).replace("</", "<\\/") for s in schema)


def clip(text, limit=158):
    """Shorten a meta description at a word boundary, so search results don't cut it mid-word."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:-–") + "…"


def lang_pair(path):
    """(English path, Hindi path) when this page has a version in the other language."""
    return next(((en, hi) for en, hi in HINDI_PAGES.items() if path in (en, hi)), None)


# Languages offered through Google Translate in the header menu (code, name in that language, name in English).
GT_LANGS = [("bn", "বাংলা", "Bengali"), ("mr", "मराठी", "Marathi"), ("ta", "தமிழ்", "Tamil"), ("te", "తెలుగు", "Telugu"),
            ("kn", "ಕನ್ನಡ", "Kannada"), ("gu", "ગુજરાતી", "Gujarati"), ("ml", "മലയാളം", "Malayalam"), ("pa", "ਪੰਜਾਬੀ", "Punjabi"),
            ("ru", "Русский", "Russian"), ("de", "Deutsch", "German"), ("fr", "Français", "French"), ("es", "Español", "Spanish")]


def language_menu(path, p, lang):
    """Header language menu: our own English and Hindi pages where both exist; Google Translate for the rest.
    Google's script loads only after a visitor picks one of those languages (static/site.js)."""
    pair = lang_pair(path)
    if lang == "hi":
        en = f'<a href="{p}{pair[0]}" lang="en" data-gt-reset>English</a>'
        hi = '<span class="on" lang="hi" aria-current="true">हिंदी</span>'
    else:
        en = '<button type="button" class="on" data-lang="en" lang="en" aria-current="true">English</button>'
        hi = (f'<a href="{p}{pair[1]}" lang="hi" data-gt-reset>हिंदी</a>' if pair
              else '<button type="button" data-lang="hi" lang="hi" title="Hindi, by Google Translate">हिंदी <small lang="en">Google</small></button>')
    others = "".join(f'<button type="button" data-lang="{c}" lang="{c}" title="{name}">{native}</button>' for c, native, name in GT_LANGS)
    return f"""<details class="lang-menu notranslate">
      <summary aria-label="Choose language">{icon("globe", "icon icon-sm")}<span class="lang-code">{"हिं" if lang == "hi" else "EN"}</span></summary>
      <div class="lang-panel">
        <p class="lang-head">Language</p>
        <div class="lang-grid">{en}{hi}</div>
        <p class="lang-head">Translate with Google</p>
        <div class="lang-grid">{others}</div>
        <p class="lang-note">{"हिंदी पेज हमने ख़ुद लिखे हैं। " if lang == "hi" else ""}Other languages are machine translations by Google and may have mistakes. Google Translate loads only after you pick a language.</p>
      </div>
    </details>"""


def share_bar(cfg, path, title, lang="en"):
    """WhatsApp, Telegram and copy-link buttons, so readers can pass a guide, tool or pick on to friends and family."""
    if not cfg["base_url"]:
        return ""
    url = abs_url(cfg, "" if path == "index.html" else path)
    text = urllib.parse.quote(title + " " + url)
    hi = lang == "hi"
    return f"""<div class="wrap share">
  <p class="share-head">{"यह पेज शेयर करें" if hi else "Share this page"}</p>
  <div class="share-row">
    <a class="share-btn share-wa" href="https://wa.me/?text={text}" target="_blank" rel="noopener">{icon("chat", "icon icon-sm")}<span>WhatsApp</span></a>
    <a class="share-btn share-tg" href="https://t.me/share/url?url={urllib.parse.quote(url)}&amp;text={urllib.parse.quote(title)}" target="_blank" rel="noopener">{icon("send", "icon icon-sm")}<span>Telegram</span></a>
    <button type="button" class="share-btn" data-share-copy="{e(url)}" data-done="{"कॉपी हो गया" if hi else "Link copied"}">{icon("link", "icon icon-sm")}<span>{"लिंक कॉपी करें" if hi else "Copy link"}</span></button>
  </div>
</div>"""


def page(cfg, title, description, body, depth, path, schema=None, og_type="website", photo=None, robots="max-image-preview:large", lang="en"):
    p = "../" * depth
    if og_type == "article" or path.startswith("picks/"):
        # Share buttons go just above the Telegram/WhatsApp band at the end of guides, tools, trips and picks.
        bar = share_bar(cfg, path, title or cfg["site_name"], lang)
        band = '<section class="band">'
        body = body.replace(band, bar + "\n" + band, 1) if band in body else body + bar
    name = e(cfg["site_name"])
    description = clip(description)
    if not title:
        full_title = e(cfg.get("home_title") or cfg["site_name"] + " | " + cfg["tagline"])
    else:
        # Long titles skip the brand so search results show the words that matter.
        full_title = e(title) + " | " + name if len(title) <= 50 else e(title)
    head_extra = ""
    if cfg["base_url"]:
        base = cfg["base_url"].rstrip("/")
        url = base + "/" + path
        head_extra = '<link rel="canonical" href="%s">\n<meta property="og:url" content="%s">\n' % (e(url), e(url))
        pair = lang_pair(path)
        if pair:
            head_extra += "".join('<link rel="alternate" hreflang="%s" href="%s">\n' % (code, e(base + "/" + target))
                                  for code, target in (("en-IN", pair[0]), ("hi-IN", pair[1]), ("x-default", pair[0])))
        if photo in PHOTOS:
            head_extra += ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n'
                           '<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">'
                           % e(photo_og(cfg, photo)))
        else:
            head_extra += '<meta property="og:image" content="%s/assets/logo.png">' % e(base)
    if cfg.get("google_site_verification"):
        head_extra += '\n<meta name="google-site-verification" content="%s">' % e(cfg["google_site_verification"])
    nav = "".join(
        '<a href="%scategory/%s.html">%s</a>' % (p, slug, e(c["name"].split(" &")[0]))
        for slug, c in cfg["categories"].items()
    )
    tg = telegram_url(cfg)
    tg_btn = ('<a class="nav-cta" href="%s" target="_blank" rel="noopener">%s<span>Telegram</span></a>'
              % (e(tg), icon("send", "icon icon-sm"))) if tg else ""
    html_lang, og_locale = ("hi-IN", "hi_IN") if lang == "hi" else ("en-IN", "en_IN")
    hindi_font = '\n<link rel="stylesheet" href="%s">' % HINDI_FONT if lang == "hi" else ""
    foot_cats = "".join(
        '<li><a href="%scategory/%s.html">%s</a></li>' % (p, slug, e(c["name"])) for slug, c in cfg["categories"].items()
    )
    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{e(description)}">
<meta property="og:title" content="{e(title or cfg['site_name'])}">
<meta property="og:description" content="{e(description)}">
<meta property="og:site_name" content="{name}">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="{og_locale}">
<meta name="robots" content="{robots}">
{head_extra}{schema_tags(cfg, schema)}
<link rel="icon" type="image/png" href="{p}assets/logo.png">
<link rel="apple-touch-icon" href="{p}assets/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">{hindi_font}
<link rel="stylesheet" href="{p}assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand notranslate" href="{p}index.html"><img src="{p}assets/logo.png" alt="" width="34" height="34"><span>{name}</span></a>
    <nav class="main-nav">{nav}<a class="nav-keep" href="{p}baggage/index.html">Baggage<span class="nav-long"> rules</span></a>{('<a class="nav-keep" href="%strips/index.html">Trips</a>' % p) if TRIPS_DIR.exists() else ""}<a class="nav-keep" href="{p}guides/index.html">Guides</a></nav>
    {tg_btn}
    {language_menu(path, p, lang)}
  </div>
</header>
<p class="disclosure-bar"><span class="wrap">We may earn a commission when you buy through links on this site. <span class="notranslate">{DISCLOSURE}</span></span></p>
<script>window.CARRYPICK_TAGS = {json.dumps(cfg.get("channel_tags", {}))};</script>
<script src="{p}assets/site.js" defer></script>
<main>
{body}
</main>
<footer class="site-footer">
  <div class="wrap footer-grid">
    <div class="footer-brand">
      <a class="brand brand-light" href="{p}index.html"><img src="{p}assets/logo.png" alt="" width="34" height="34"><span>{name}</span></a>
      <p>{e(cfg['tagline'])}. We read the details, so you buy the right thing the first time.</p>
    </div>
    <div><h4>Categories</h4><ul>{foot_cats}</ul></div>
    <div><h4>CarryPick</h4><ul>
      <li><a href="{p}guides/index.html">Buying guides</a></li>
      {('<li><a href="%strips/index.html">Trip guides</a></li>' % p) if TRIPS_DIR.exists() else ""}
      {"".join('<li><a href="%s%s">%s</a></li>' % (p, t[0], e(t[1])) for t in TOOLS)}
      <li><a href="{p}about.html">About us</a></li>
      <li><a href="{p}contact.html">Contact</a></li>
      {follow_links(cfg)}
    </ul></div>
    <div><h4>Legal</h4><ul>
      <li><a href="{p}disclosure.html">Affiliate disclosure</a></li>
      <li><a href="{p}privacy.html">Privacy policy</a></li>
    </ul></div>
  </div>
  <div class="wrap footer-bottom">
    <p><span class="notranslate">{DISCLOSURE}</span> Prices and availability are shown only on Amazon.in and can change at any time.</p>
    <p>&copy; {date.today().year} {name}</p>
  </div>
</footer>
</body>
</html>
"""


# ---------- building blocks ----------

def buy_button(cfg, deal, label="Check price on Amazon", big=False):
    cls = "btn btn-amazon btn-big" if big else "btn btn-amazon"
    href = e(amazon_link(deal["asin"], cfg["amazon_tag"]))
    return f'<a class="{cls}" href="{href}" {BUY_ATTRS}>{label}</a><span class="paid">Paid link</span>'


def fresh_deal(deal):
    """The time Amazon showed a deal label for this pick, if that was less than DEAL_HOURS ago."""
    if not deal.get("deal_seen_at"):
        return None
    seen = datetime.fromisoformat(deal["deal_seen_at"])
    return seen if datetime.now(IST) - seen < timedelta(hours=DEAL_HOURS) else None


def deal_badge(deal, cls="deal-badge"):
    """Empty and hidden in the HTML: site.js writes "Deal spotted <time>" and removes it after DEAL_HOURS,
    so no expired deal claim stays on the page. Never a price or % off."""
    seen = fresh_deal(deal)
    return f'<span class="{cls}" data-deal-seen="{seen.isoformat()}" hidden></span>' if seen else ""


def media(cfg, category, cls="media"):
    return f'<div class="{cls} tint-{category}">{icon(cfg["categories"][category]["icon"], "icon media-icon")}</div>'


# ---------- stock photos and our own diagrams ----------

def webp_size(path):
    """Width and height of a WebP file, read from its header."""
    data = path.read_bytes()[:30]
    kind = data[12:16]
    if kind == b"VP8 ":
        return int.from_bytes(data[26:28], "little") & 0x3FFF, int.from_bytes(data[28:30], "little") & 0x3FFF
    if kind == b"VP8L":
        b = data[21:25]
        return 1 + (((b[1] & 0x3F) << 8) | b[0]), 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
    if kind == b"VP8X":
        return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
    sys.exit("Error: %s is not a WebP file this script can read" % path.name)


def load_photos():
    if not PHOTOS_FILE.exists():
        return {}
    photos = json.loads(PHOTOS_FILE.read_text(encoding="utf-8"))["photos"]
    for slot, info in photos.items():
        big = PHOTO_DIR / ("%s-1600.webp" % slot)
        if not big.exists():
            sys.exit("Error: photo %s is missing. Run: python3 scripts/fetch_photos.py" % slot)
        info["size"] = webp_size(big)
    return photos


def photo_og(cfg, slot):
    return abs_url(cfg, "assets/photos/%s-og.jpg" % slot)


def photo_img(slot, p, sizes, eager=False, alt=None):
    info = PHOTOS[slot]
    base = "%sassets/photos/%s" % (p, slot)
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    # "focus" in data/photos.json (e.g. "50% 80%") keeps the subject in view when a card crops the photo.
    focus = f' style="object-position: {e(info["focus"])}"' if info.get("focus") else ""
    return (f'<img src="{base}-800.webp" srcset="{base}-800.webp 800w, {base}-1600.webp 1600w" sizes="{sizes}" '
            f'width="{info["size"][0]}" height="{info["size"][1]}" alt="{e(info["alt"] if alt is None else alt)}"{focus} {load}>')


def photo_credit(slot):
    info = PHOTOS[slot]
    return (f'Photo: <a href="{e(info["profile"])}" target="_blank" rel="noopener">{e(info["credit"])}</a> on '
            f'<a href="https://unsplash.com/photos/{e(info["unsplash"])}" target="_blank" rel="noopener">Unsplash</a>')


def photo_figure(slot, p, sizes, cls="photo", eager=False):
    return f'<figure class="{cls}">{photo_img(slot, p, sizes, eager)}<figcaption>{photo_credit(slot)}</figcaption></figure>'


def diagram_figure(name, p):
    if name not in DIAGRAMS:
        sys.exit("Error: unknown diagram %s (see scripts/diagrams.py)" % name)
    svg, alt, caption = DIAGRAMS[name]
    w, h = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg).groups()
    return (f'<figure class="diagram"><img src="{p}assets/diagrams/{name}.svg" width="{w}" height="{h}" '
            f'alt="{e(alt)}" loading="lazy" decoding="async"><figcaption>{e(caption)}</figcaption></figure>')


def page_head(tint, art, inner, p, photo=None):
    """Top of category, guide and baggage pages: a photo on the right when there is one, else the icon tile."""
    if photo in PHOTOS:
        figure = photo_figure(photo, p, "(min-width: 760px) 440px, 100vw", "photo head-photo", eager=True)
        return f"""<section class="page-head tint-{tint}">
  <div class="wrap page-head-grid">
    <div>
      {inner}
    </div>
    {figure}
  </div>
</section>"""
    return f"""<section class="page-head tint-{tint}">
  <div class="wrap page-head-row">
    {art}
    <div>
      {inner}
    </div>
  </div>
</section>"""


def chips(tags, cls="chip-tag"):
    return "".join('<span class="%s">%s</span>' % (cls, e(t)) for t in tags)


def card(cfg, deal, p, deal_only=False):
    href = f"{p}picks/{deal['asin']}.html"
    badge = f'<span class="badge">Best for {e(deal["best_for"][0])}</span>' if deal.get("best_for") else ""
    brand = f'<p class="brand-name">{e(deal["brand"])}</p>' if deal.get("brand") else ""
    feats = "".join("<li>%s%s</li>" % (icon("check", "icon icon-check"), e(h)) for h in deal["highlights"][:2])
    hide = f' data-deal-seen="{fresh_deal(deal).isoformat()}" hidden' if deal_only else ""
    return f"""<article class="card"{hide}>
  <a class="card-media" href="{href}" tabindex="-1" aria-hidden="true">{media(cfg, deal['category'])}{badge}{deal_badge(deal)}</a>
  <div class="card-body">
    {brand}
    <h3><a href="{href}">{e(deal['title'])}</a></h3>
    <ul class="mini-features">{feats}</ul>
  </div>
  <div class="card-foot">{buy_button(cfg, deal)}</div>
</article>"""


def grid(cfg, deals, p):
    return '<div class="grid">' + "\n".join(card(cfg, d, p) for d in deals) + "</div>"


def inline_pick(cfg, deal, p):
    items = "".join("<li>%s%s</li>" % (icon("check", "icon icon-check"), e(h)) for h in deal["highlights"][:3])
    brand = f'<p class="brand-name">{e(deal["brand"])}</p>' if deal.get("brand") else ""
    return f"""<aside class="inline-pick">
  {media(cfg, deal['category'], 'media media-sm')}
  <div class="inline-body">
    {deal_badge(deal, "deal-badge deal-inline")}
    {brand}
    <h4><a href="{p}picks/{deal['asin']}.html">{e(deal['title'])}</a></h4>
    <ul class="mini-features">{items}</ul>
    <div class="card-foot">{buy_button(cfg, deal)}</div>
  </div>
</aside>"""


def compare_table(cfg, deals, p):
    keys = []
    for d in deals:
        for k in d.get("specs", {}):
            if k not in keys:
                keys.append(k)
    head = "".join("<th>%s</th>" % e(k) for k in keys)
    rows = []
    for d in deals:
        cells = "".join("<td>%s</td>" % e(d.get("specs", {}).get(k, "–")) for k in keys)
        link = e(amazon_link(d["asin"], cfg["amazon_tag"]))
        rows.append(f'<tr><th scope="row"><a href="{p}picks/{d["asin"]}.html">{e(d["title"])}</a></th>{cells}'
                    f'<td><a class="table-buy" href="{link}" {BUY_ATTRS}>Check price</a><span class="paid">Paid link</span></td></tr>')
    return (f'<div class="table-wrap"><table class="compare"><thead><tr><th>Product</th>{head}<th></th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def telegram_band(cfg, p):
    url = telegram_url(cfg)
    if not url:
        return ""
    wa = cfg.get("whatsapp_channel")
    wa_btn = (f'<a class="btn btn-whatsapp" href="{e(wa)}" target="_blank" rel="noopener">{icon("chat", "icon icon-sm")} Follow on WhatsApp</a>'
              if wa else "")
    return f"""<section class="band">
  <div class="wrap band-row">
    <img src="{p}assets/logo.png" alt="" width="72" height="72">
    <div>
      <h2>New picks every day on Telegram{' and WhatsApp' if wa else ''}</h2>
      <p>Hand-picked bags, luggage, watches and travel essentials on sale, plus quick buying tips. No spam.</p>
    </div>
    <div class="band-ctas">
      <a class="btn btn-light" href="{e(url)}" target="_blank" rel="noopener">{icon("send", "icon icon-sm")} Join on Telegram</a>
      {wa_btn}
    </div>
  </div>
</section>"""


def tip_box(cfg, slug, p, articles_by_slug):
    cat = cfg["categories"][slug]
    guide = articles_by_slug.get(cat.get("guide"))
    link = f' <a href="{p}guides/{guide["slug"]}.html">Read the full guide &rarr;</a>' if guide else ""
    return f'<aside class="tip">{icon("bulb", "icon tip-icon")}<div><strong>Before you buy</strong><p>{e(cat["tip"])}{link}</p></div></aside>'


def section_head(title, link_html=""):
    return f'<div class="section-head"><h2>{e(title)}</h2>{link_html}</div>'


# ---------- markdown (small subset) for guides ----------

def md_inline(text, p):
    text = e(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: '<a href="%s">%s</a>' % (m.group(2).replace('"', "%22"), m.group(1)),
        text,
    )


def booking_box(cfg, place):
    """Hand-placed hotel links (EarnKaro). Trip guides only, never next to Amazon picks."""
    links = "".join(f'<a class="btn" href="{e(url)}" {BUY_ATTRS}>Search {e(place)} on {e(name)}</a><span class="paid">Paid link</span> '
                    for name, url in cfg["booking_partners"].items())
    return f'<div class="cta-box">{links}<p>Prices and rooms are shown on the booking site. We have not checked each hotel, so read recent reviews first.</p></div>'


def render_markdown(md, cfg, deals_by_asin, p, source):
    out, para, items, list_tag, rows = [], [], [], None, []

    def flush():
        nonlocal para, items, list_tag, rows
        if rows:
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows if not re.fullmatch(r"[\s|:-]+", r)]
            head = "".join("<th>%s</th>" % md_inline(c, p) for c in cells[0])
            body = "".join("<tr>%s</tr>" % "".join(("<th scope=\"row\">%s</th>" if i == 0 else "<td>%s</td>") % md_inline(c, p)
                                                    for i, c in enumerate(r)) for r in cells[1:])
            out.append('<div class="table-wrap"><table class="compare"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body))
            rows = []
        if para:
            out.append("<p>%s</p>" % md_inline(" ".join(para), p))
            para = []
        if items:
            out.append("<%s>%s</%s>" % (list_tag, "".join("<li>%s</li>" % md_inline(i, p) for i in items), list_tag))
            items, list_tag = [], None

    for raw in md.splitlines():
        line = raw.strip()
        pick = re.fullmatch(r"\[\[pick:([A-Z0-9]{10})\]\]", line)
        compare = re.fullmatch(r"\[\[compare:([A-Z0-9,]+)\]\]", line)
        diagram = re.fullmatch(r"\[\[diagram:([a-z0-9-]+)\]\]", line)
        booking = re.fullmatch(r"\[\[book:([^\]]+)\]\]", line)
        ul = re.match(r"^- (.+)", line)
        ol = re.match(r"^\d+\. (.+)", line)
        if not line:
            flush()
        elif line.startswith("|"):
            if para or items:
                flush()
            rows.append(line)
        elif diagram:
            flush()
            out.append(diagram_figure(diagram.group(1), p))
        elif booking:
            flush()
            out.append(booking_box(cfg, booking.group(1)))
        elif compare:
            flush()
            asins = compare.group(1).split(",")
            missing = [a for a in asins if a not in deals_by_asin]
            if missing:
                sys.exit("Error: %s compares unknown ASINs %s" % (source, ", ".join(missing)))
            out.append(compare_table(cfg, [deals_by_asin[a] for a in asins], p))
        elif pick:
            flush()
            deal = deals_by_asin.get(pick.group(1))
            if deal is None:
                sys.exit("Error: %s uses [[pick:%s]] but that ASIN is not in data/deals.json" % (source, pick.group(1)))
            out.append(inline_pick(cfg, deal, p))
        elif line.startswith("### "):
            flush()
            out.append("<h3>%s</h3>" % md_inline(line[4:], p))
        elif line.startswith("## "):
            flush()
            out.append("<h2>%s</h2>" % md_inline(line[3:], p))
        elif ul or ol:
            tag = "ul" if ul else "ol"
            if para or (list_tag and list_tag != tag):
                flush()
            list_tag = tag
            items.append((ul or ol).group(1))
        else:
            if items:
                flush()
            para.append(line)
    flush()
    return "\n".join(out)


def md_faq(md):
    """Questions and answers from a '## Questions' section (### question, then the answer paragraph), for FAQPage data."""
    section = re.search(r"^## Questions\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    if not section:
        return []
    plain = lambda t: re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t).replace("**", "")
    return [(q.strip(), plain(" ".join(a.split())))
            for q, a in re.findall(r"^### (.+?)\n(.*?)(?=^### |\Z)", section.group(1), re.S | re.M) if a.strip()]


def load_articles(directory=ARTICLES_DIR):
    articles = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        if not match:
            sys.exit("Error: %s is missing the --- front matter block" % path.name)
        meta = dict(line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line)
        meta.update(slug=path.stem, body=match.group(2))
        meta.setdefault("updated", meta["date"])
        meta["minutes"] = max(1, round(len(re.sub(r"\[\[pick:\w+\]\]", "", meta["body"]).split()) / 200))
        articles.append(meta)
    return sorted(articles, key=lambda a: a["date"], reverse=True)


def guide_cards(cfg, articles, p):
    cards = []
    for a in articles:
        cat = a.get("category")
        if a.get("photo") in PHOTOS:
            art = '<div class="guide-art guide-photo">%s</div>' % photo_img(a["photo"], p, "(min-width: 700px) 360px, 100vw", alt="")
        else:
            glyph = icon(cfg["categories"][cat]["icon"] if cat in cfg["categories"] else "book", "icon guide-icon")
            art = f'<div class="guide-art tint-{e(cat or "none")}">{glyph}</div>'
        cards.append(f"""<a class="guide-card" href="{p}guides/{a['slug']}.html">
  {art}
  <div class="guide-body">
    <p class="eyebrow">Buying guide &middot; {a['minutes']} min read</p>
    <h3>{e(a['title'])}</h3>
    <p>{e(a['description'])}</p>
    <span class="more">Read guide {icon("arrow", "icon icon-sm")}</span>
  </div>
</a>""")
    return '<div class="guide-grid">%s</div>' % "".join(cards)


def trip_cards(trips, p):
    cards = []
    for t in trips:
        art = ('<div class="guide-art guide-photo">%s</div>' % photo_img(t["photo"], p, "(min-width: 700px) 360px, 100vw", alt="")
               if t.get("photo") in PHOTOS else f'<div class="guide-art tint-travel-gear">{icon("pin", "icon guide-icon")}</div>')
        best = " &middot; Best: %s" % e(t["best"]) if t.get("best") else ""
        cards.append(f"""<a class="guide-card" href="{p}trips/{t['slug']}.html">
  {art}
  <div class="guide-body">
    <p class="eyebrow">Trip guide{best}</p>
    <h3>{e(t['title'])}</h3>
    <p>{e(t['description'])}</p>
    <span class="more">Plan your trip {icon("arrow", "icon icon-sm")}</span>
  </div>
</a>""")
    return '<div class="guide-grid">%s</div>' % "".join(cards)


def build_trips(cfg, trips, deals_by_asin, pages, lastmod):
    """Destination trip guides from content/trips/*.md (front matter: place, best, glance "Label=Value | ...", packing)."""
    for t in trips:
        if t.get("photo") and t["photo"] not in PHOTOS:
            sys.exit("Error: trip %s uses photo %s, which is not in data/photos.json" % (t["slug"], t["photo"]))
        content = render_markdown(t["body"], cfg, deals_by_asin, "../", "trips/%s.md" % t["slug"])
        glance = [part.split("=", 1) for part in t.get("glance", "").split(" | ") if "=" in part]
        glance_html = ('<div class="answer"><h2>%s at a glance</h2><div class="table-wrap"><table class="compare glance"><tbody>%s</tbody></table></div></div>'
                       % (e(t.get("place", t["title"])), "".join('<tr><th scope="row">%s</th><td>%s</td></tr>' % (e(k.strip()), md_inline(v.strip(), "../"))
                                                                  for k, v in glance))) if glance else ""
        pack = t.get("packing")
        pack_file = "index.html" if pack == "week" else "%s.html" % pack
        pack_link = (f'our <a href="../packing/{pack_file}">packing checklist</a>' if pack and (DOCS / "packing" / pack_file).exists()
                     else 'our <a href="../packing/index.html">packing checklists</a>')
        tip = (f'<aside class="tip">{icon("check", "icon tip-icon")}<div><strong>Packing for {e(t.get("place", "your trip"))}?</strong>'
               f'<p>Tick things off with {pack_link}, check <a href="../baggage/can-i-carry.html">what you can carry on the flight</a>, '
               f'and see the <a href="../baggage/index.html">airline baggage rules</a>.</p></div></aside>')
        inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Trip guides</a><span>/</span>{e(t.get("place", t["title"]))}</nav>
      <h1>{e(t['title'])}</h1>
      <p class="muted small">Updated {fmt_date(t['updated'])} &middot; {t['minutes']} min read</p>"""
        art = f'<div class="media media-tile tint-travel-gear">{icon("pin", "icon media-icon")}</div>'
        body = f"""{page_head("travel-gear", art, inner, "../", t.get("photo"))}
<div class="wrap"><article class="guide">
{glance_html}
{content}
{tip}
{tool_pills("../", "")}
</article></div>
{telegram_band(cfg, "../")}"""
        path = "trips/%s.html" % t["slug"]
        image = photo_og(cfg, t["photo"]) if t.get("photo") in PHOTOS else abs_url(cfg, "assets/logo.png")
        article = {"@context": "https://schema.org", "@type": "Article", "headline": t.get("seo_title", t["title"]),
                   "description": t["description"], "datePublished": t["date"], "dateModified": t["updated"],
                   "inLanguage": "en-IN", "image": image, "about": {"@type": "TouristDestination", "name": t.get("place", t["title"])},
                   "mainEntityOfPage": abs_url(cfg, path), "author": org_schema(cfg), "publisher": org_schema(cfg)}
        crumbs = crumbs_schema(cfg, [("Home", ""), ("Trip guides", "trips/index.html"), (t.get("place", t["title"]), path)])
        schema = [article, crumbs]
        faq = md_faq(t["body"])
        if faq:
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
        pages.append(write(path, page(cfg, t.get("seo_title", t["title"]), t["description"], body, 1, path, schema,
                                      og_type="article", photo=t.get("photo"))))
        lastmod[path] = t["updated"]

    places = ", ".join(t.get("place", t["title"]) for t in trips if t.get("hub_title") != "no")
    inner = """<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>Trip guides</nav>
      <h1>Trip guides for India</h1>
      <p class="muted small">When to go, how to get there, local rules and what to pack</p>"""
    body = f"""{page_head("travel-gear", f'<div class="media media-tile tint-travel-gear">{icon("pin", "icon media-icon")}</div>', inner, "../")}
<div class="wrap section">{trip_cards(trips, "../")}</div>
{telegram_band(cfg, "../")}"""
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Trip guides", "trips/index.html")])
    pages.append(write("trips/index.html", page(cfg, "Trip guides for India: %s" % places,
                                                "Plan a trip to %s: best time, weather, getting there, getting around, local rules and packing lists." % places,
                                                body, 1, "trips/index.html", [crumbs])))
    lastmod["trips/index.html"] = max(t["updated"] for t in trips)


def build_trips_hi(cfg, trips_hi, deals_by_asin, pages, lastmod):
    """Hindi trip guides from content/trips-hi/<slug>.md -> hi/trips/<slug>.html, paired with trips/<slug>.html."""
    for t in trips_hi:
        path = "hi/trips/%s.html" % t["slug"]
        p = "../../"
        content = render_markdown(t["body"], cfg, deals_by_asin, p, "trips-hi/%s.md" % t["slug"])
        glance = [part.split("=", 1) for part in t.get("glance", "").split(" | ") if "=" in part]
        glance_html = ('<div class="answer"><h2>%s एक नज़र में</h2><div class="table-wrap"><table class="compare glance"><tbody>%s</tbody></table></div></div>'
                       % (e(t.get("place", t["title"])), "".join('<tr><th scope="row">%s</th><td>%s</td></tr>' % (e(k.strip()), md_inline(v.strip(), p))
                                                                  for k, v in glance))) if glance else ""
        inner = f"""<nav class="crumbs"><a href="{p}index.html">होम</a><span>/</span><a href="{p}trips/index.html">Trip guides</a><span>/</span>{e(t.get("place", t["title"]))}</nav>
      <h1>{e(t['title'])}</h1>
      <p class="muted small">{hi_date(t['updated'])} को अपडेट किया गया</p>"""
        art = f'<div class="media media-tile tint-travel-gear">{icon("pin", "icon media-icon")}</div>'
        body = f"""{page_head("travel-gear", art, inner, p, t.get("photo"))}
<div class="wrap"><article class="guide">
{glance_html}
{content}
<p class="checked">हम Amazon Associate हैं और योग्य ख़रीदारी पर कमीशन कमाते हैं। आपके लिए क़ीमत वही रहती है।</p>
</article></div>
{telegram_band(cfg, p)}"""
        image = photo_og(cfg, t["photo"]) if t.get("photo") in PHOTOS else abs_url(cfg, "assets/logo.png")
        article = {"@context": "https://schema.org", "@type": "Article", "headline": t.get("seo_title", t["title"]),
                   "description": t["description"], "datePublished": t["date"], "dateModified": t["updated"],
                   "inLanguage": "hi-IN", "image": image, "about": {"@type": "TouristDestination", "name": t.get("place", t["title"])},
                   "mainEntityOfPage": abs_url(cfg, path), "author": org_schema(cfg), "publisher": org_schema(cfg)}
        crumbs = crumbs_schema(cfg, [("होम", ""), ("Trip guides", "trips/index.html"), (t.get("place", t["title"]), path)])
        schema = [article, crumbs]
        faq = md_faq(t["body"].replace("## सवाल-जवाब", "## Questions"))
        if faq:
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
        pages.append(write(path, page(cfg, t.get("seo_title", t["title"]), t["description"], body, 2, path, schema,
                                      og_type="article", photo=t.get("photo"), lang="hi")))
        lastmod[path] = t["updated"]


# ---------- baggage rules and bag checker ----------

def parse_dims(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)", text or "")
    return [float(x) for x in m.groups()] if m else None


def parse_kg(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g)\b", text or "")
    if not m:
        return None
    return float(m.group(1)) / (1000 if m.group(2) == "g" else 1)


def num(x):
    return ("%.1f" % x).rstrip("0").rstrip(".")


def size_limit_text(cabin):
    parts = []
    if cabin.get("dims_cm"):
        parts.append(" x ".join(num(x) for x in cabin["dims_cm"]) + " cm")
    if cabin.get("total_cm"):
        parts.append("%s cm in total (L + W + H)" % num(cabin["total_cm"]))
    return " or ".join(parts) if cabin.get("either") else ", and ".join(parts)


def short_limit_text(cabin):
    parts = []
    if cabin.get("dims_cm"):
        parts.append(" x ".join(num(x) for x in cabin["dims_cm"]) + " cm")
    if cabin.get("total_cm"):
        parts.append("%s cm total" % num(cabin["total_cm"]))
    if cabin.get("kg"):
        parts.append("%s kg" % num(cabin["kg"]))
    return " · ".join(parts)


def size_fit(dims, cabin):
    """Same rule as static/checker.js: a bag fits if it passes every limit the airline gives
    (or any one of them when the airline says either is fine). Sides are compared largest to largest.
    Returns (fits, reason, cm over)."""
    bag = sorted(dims, reverse=True)
    checks = []
    if cabin.get("dims_cm"):
        over = max(b - l for b, l in zip(bag, sorted(cabin["dims_cm"], reverse=True)))
        checks.append((over, "%s cm over on one side" % num(over)))
    if cabin.get("total_cm"):
        over = sum(bag) - cabin["total_cm"]
        checks.append((over, "%s cm in total, %s cm over" % (num(sum(bag)), num(over))))
    if not checks:
        return None, "No size limit given", 0
    fails = [(over, why) for over, why in checks if over > 0]
    ok = len(fails) < len(checks) if cabin.get("either") else not fails
    if ok:
        return True, "", 0
    return False, "; ".join(why for over, why in fails), max(over for over, why in fails)


def fit_badge(ok, over=0):
    if ok is None:
        return '<span class="fit fit-na">Check listing</span>'
    if ok:
        return '<span class="fit fit-yes">Fits</span>'
    if over <= 3:
        return '<span class="fit fit-close">%s cm over</span>' % num(over)
    return '<span class="fit fit-no">Too big</span>'


def cabin_picks(deals):
    picks = []
    for d in deals:
        dims = parse_dims(d.get("specs", {}).get("Size"))
        if d["category"] in ("luggage", "backpacks") and dims and sum(dims) <= 130:
            picks.append((d, dims, parse_kg(d.get("specs", {}).get("Weight"))))
    return picks


def fit_table(cfg, airline, picks, p):
    rows = []
    for d, dims, kg in picks:
        ok, why, over = size_fit(dims, airline["cabin"])
        left = ""
        if kg is not None and airline["cabin"].get("kg"):
            spare = airline["cabin"]["kg"] - kg
            left = "about %s kg left for your things" % num(spare) if spare > 0 else "the bag alone is over the limit"
        link = e(amazon_link(d["asin"], cfg["amazon_tag"]))
        rows.append(f"""<tr><th scope="row"><a href="{p}picks/{d['asin']}.html">{e(d['title'])}</a></th>
<td>{" x ".join(num(x) for x in dims)} cm<span class="why">{num(sum(dims))} cm in total</span></td>
<td>{fit_badge(ok, over)}{('<span class="why">' + e(why) + '</span>') if why else ''}</td>
<td>{e(left) or '–'}</td>
<td><a class="table-buy" href="{link}" {BUY_ATTRS}>Check price</a><span class="paid">Paid link</span></td></tr>""")
    return ('<div class="table-wrap"><table class="compare"><thead><tr><th>Our pick</th><th>Listed size</th>'
            f'<th>Fits {e(airline["name"])}?</th><th>Weight</th><th></th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def load_airlines(path=AIRLINES_FILE):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for a in data["airlines"]:
        missing = [k for k in ("slug", "name", "official_url", "cabin", "checkin", "sources") if not a.get(k)]
        if missing:
            sys.exit("Error: airline %s is missing %s" % (a.get("slug", "?"), ", ".join(missing)))
    return data


def build_intl_hub(cfg, intl, picks, pages, lastmod, head, disclaimer, checker_cta, scale_link):
    """baggage/international.html: economy baggage on international flights from India (data/airlines_intl.json)."""
    airlines, checked = intl["airlines"], intl["checked"]
    names = [a["name"] for a in airlines]
    rows = "".join(f"""<tr><th scope="row"><a href="{a['slug']}.html">{e(a['name'])}</a><span class="why">{e(a.get('hub', ''))}</span></th>
<td>{e(a['cabin']['summary'])}</td><td>{e(size_limit_text(a['cabin']))}</td>
<td>{e(a['personal']['summary']) if a.get('personal') else '–'}</td><td>{e(a['checkin_summary'])}</td></tr>""" for a in airlines)
    matrix_head = "".join("<th>%s</th>" % e(a["name"]) for a in airlines)
    matrix_rows = "".join(
        f'<tr><th scope="row"><a href="../picks/{d["asin"]}.html">{e(d["title"])}</a><span class="why">{num(sum(dims))} cm in total</span></th>'
        + "".join("<td>%s</td>" % fit_badge(*size_fit(dims, a["cabin"])[::2]) for a in airlines) + "</tr>"
        for d, dims, kg in picks)
    faq = [
        ("How many kg can I take from India to Dubai?", "It depends on the airline and fare: Emirates gives 20–35 kg, IndiGo 30 kg on regular fares, Air India 25–35 kg, and flydubai 20–30 kg (none on Lite). All allow a 7 kg cabin bag."),
        ("Which airline has the smallest cabin bag limit?", "Gulf Air: 6 kg and 45 x 40 x 30 cm. Qatar Airways is also strict at 50 x 37 x 25 cm. Most 55 cm trolleys sold in India are too big for both."),
        ("Can I carry a bag tied with rope or a cloth bundle?", "Usually not. Qatar Airways and Gulf Air refuse bags tied with rope or wrapped in blankets, and Dubai, Sharjah, Bahrain and Muscat airports have similar rules. Pack things in a suitcase or a sealed box."),
        ("Can I use a power bank on Emirates?", "No. Since 1 October 2025 Emirates doesn't allow using or charging power banks on board. You can still carry one under 100 Wh in your cabin bag, never in checked baggage. Most other airlines here have similar rules."),
        ("What is the maximum weight of one checked bag?", "32 kg on every airline here, even if your total allowance is higher. On Saudia and Kuwait Airways economy, each piece is 23 kg."),
    ]
    faq_html, faq_schema = faq_block(faq)
    title = "Baggage rules for international flights from India"
    seo = "International baggage allowance from India %s: Emirates, Qatar, Saudia, IndiGo, Air India" % checked[:4]
    desc = ("Cabin bag size and checked baggage by fare for %d airlines on flights from India to the Gulf and Singapore, "
            "including Emirates, Qatar Airways, Saudia, IndiGo and Air India. Checked against official websites, %s." % (len(airlines), fmt_date(checked)))
    body = f"""{head(title, '<a href="index.html">Baggage rules</a><span>/</span>International', "Checked on " + fmt_date(checked) + " against each airline's official website &middot; economy, India routes", BAGGAGE_PHOTO)}
<div class="wrap"><article class="guide">
<p class="lead">Economy baggage on flights between India and the Gulf (Dubai, Doha, Abu Dhabi, Sharjah, Jeddah, Muscat, Bahrain, Kuwait) and Singapore, in one place. Tap an airline for the full rules, infant allowance and tips.</p>
{checker_cta}
<h2>Cabin and checked baggage at a glance</h2>
<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Cabin bag</th><th>Cabin size limit</th><th>Extra small bag</th><th>Checked baggage (economy)</th></tr></thead><tbody>{rows}</tbody></table></div>
{disclaimer}
<h2>Rules that catch travellers out</h2>
<ul>
<li><strong>32 kg per bag.</strong> Even with a 35 or 40 kg allowance, no single bag can weigh more than 32 kg. Split heavy luggage into two bags.</li>
<li><strong>Weight or pieces?</strong> Most airlines here count your total kg. Kuwait Airways counts pieces (2 x 23 kg on Economy), and Saudia's economy bags are 23 kg each. Some airlines also limit the number of bags: IndiGo 2, Air Arabia 2, flydubai 3.</li>
<li><strong>Bags need a flat side.</strong> Qatar Airways and Gulf Air refuse round bags and bundles tied with rope or wrapped in blankets. Emirates and flydubai ask you to repack odd-shaped items in a box, and Muscat airport charges extra for them.</li>
<li><strong>Power banks stay in the cabin.</strong> Most of these airlines don't allow using or charging power banks on board, and Qatar Airways bans charging them. Never pack one in a checked bag.</li>
<li><strong>Cheap fares may have no checked bag.</strong> Etihad Basic, flydubai Lite, Air Arabia Basic, IndiGo Lite and Kuwait Airways Zero Bag include only a cabin bag. Buying extra baggage online before you fly is much cheaper than at the airport.</li>
<li><strong>Medicines into the UAE.</strong> Controlled medicines need approval from the UAE health ministry before you travel. Carry the prescription.</li>
<li><strong>Keep gold, cash and documents with you.</strong> flydubai says not to pack money, jewellery or precious metals in checked bags.</li>
</ul>
<h2>Do our cabin picks fit?</h2>
<p>Based on the size listed on Amazon. Gulf Air's and Qatar Airways' limits are the hardest to meet, so a backpack is often the safest cabin bag.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Our pick</th>{matrix_head}</tr></thead><tbody>{matrix_rows}</tbody></table></div>
<p>Weigh your packed bags at home with a {scale_link}, and try our <a href="../tools/bag-weight.html">bag weight calculator</a>.</p>
{faq_html}
<h2>Flying within India?</h2>
<p>Domestic allowances are smaller: usually a 7 kg cabin bag and 15 kg of check-in baggage. See our <a href="index.html">baggage rules for Indian airlines</a>.</p>
{tool_pills("../", "baggage/international.html")}
</article></div>
{telegram_band(cfg, "../")}"""
    path = "baggage/international.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Gulf airlines", path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, [tool_article(cfg, seo, desc, path, checked, checked), crumbs, faq_schema],
                                  og_type="article", photo=BAGGAGE_PHOTO)))
    lastmod[path] = checked


def build_baggage(cfg, deals, data, pages, lastmod, intl=None):
    """Indian airlines (data) get the hub table; international airlines (intl) get their own hub. All get a page and checker rows."""
    airlines = data["airlines"]
    intl_airlines = intl["airlines"] if intl else []
    checked = data["checked"]
    year = checked[:4]
    picks = cabin_picks(deals)
    scale = next((d for d in deals if "scale" in d["title"].lower()), None)
    scale_link = f'<a href="../picks/{scale["asin"]}.html">luggage scale</a>' if scale else "luggage scale"
    disclaimer = ('<p class="checked">Rules change often and can depend on your fare, route and aircraft. '
                  'Always check your ticket and the airline\'s official website before you fly.</p>')
    checker_cta = (f'<aside class="tip">{icon("ruler", "icon tip-icon")}<div><strong>Will your bag fit?</strong>'
                   '<p>Type your bag\'s size into our <a href="checker.html">cabin bag checker</a> and see every airline at once.</p></div></aside>')
    others = lambda current, group: '<ul class="airline-links">' + "".join(
        f'<li><a href="{a["slug"]}.html">{e(a["name"])}</a></li>' for a in group if a["slug"] != current) + "</ul>"

    def head(title, crumb_html, sub, photo=None, extra=""):
        inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>{crumb_html}</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">{sub}</p>{extra}"""
        return page_head("luggage", media(cfg, "luggage", "media media-tile"), inner, "../", photo)

    def article_schema(title, desc, path, photo=None):
        image = photo_og(cfg, photo) if photo in PHOTOS else abs_url(cfg, "assets/logo.png")
        return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
                "datePublished": data.get("published", checked), "dateModified": checked, "inLanguage": "en-IN",
                "image": image, "mainEntityOfPage": abs_url(cfg, path),
                "author": org_schema(cfg), "publisher": org_schema(cfg)}

    # Hub page
    rows = "".join(f"""<tr><th scope="row"><a href="{a['slug']}.html">{e(a['name'])}</a></th>
<td>{e(a['cabin']['summary'])}</td><td>{e(size_limit_text(a['cabin']))}</td>
<td>{e(a['personal']['summary']) if a.get('personal') else '–'}</td><td>{e(a['checkin_summary'])}</td></tr>""" for a in airlines)
    matrix_head = "".join("<th>%s</th>" % e(a["name"]) for a in airlines)
    matrix_rows = "".join(
        f'<tr><th scope="row"><a href="../picks/{d["asin"]}.html">{e(d["title"])}</a><span class="why">{num(sum(dims))} cm in total</span></th>'
        + "".join("<td>%s</td>" % fit_badge(*size_fit(dims, a["cabin"])[::2]) for a in airlines) + "</tr>"
        for d, dims, kg in picks)
    title = "Baggage rules for Indian airlines"
    seo = "Baggage rules for Indian airlines %s: cabin and check-in limits" % year
    desc = ("Cabin bag size and weight, extra small bag and free check-in baggage for IndiGo, Air India, "
            "Air India Express, Akasa Air and SpiceJet domestic flights, checked against official websites.")
    limits_fig = diagram_figure("cabin-limits", "../") if "cabin-limits" in DIAGRAMS else ""
    body = f"""{head(title, "Baggage rules", "Checked on " + fmt_date(checked) + " against each airline's official website", BAGGAGE_PHOTO)}
<div class="wrap"><article class="guide">
<p class="lead">Domestic economy limits for India's main airlines, in one place. Tap an airline for the full rules, fare types and tips.</p>
{('<p>Flying abroad? See the <a href="international.html">international baggage rules</a> for Emirates, Qatar Airways, Saudia, Singapore Airlines, IndiGo and Air India and more, on flights from India.</p>') if intl_airlines else ''}
{checker_cta}
<h2>Cabin and check-in baggage at a glance</h2>
<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Cabin bag</th><th>Cabin size limit</th><th>Extra small bag</th><th>Free check-in (domestic)</th></tr></thead><tbody>{rows}</tbody></table></div>
{disclaimer}
<h2>Cabin bag limits side by side</h2>
{limits_fig}
<h2>Do our cabin picks fit?</h2>
<p>Many "55 cm" cabin trolleys are a little bigger than the limits once you add up all three sides. A backpack is often the safest cabin bag. Here's how our picks compare, using the size listed on Amazon.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Our pick</th>{matrix_head}</tr></thead><tbody>{matrix_rows}</tbody></table></div>
<h2>How to avoid extra baggage charges</h2>
<ul>
<li><strong>Measure with wheels and handles.</strong> Airlines measure the whole bag, not just the shell.</li>
<li><strong>Weigh it at home.</strong> A {scale_link} costs less than one excess-baggage fee.</li>
<li><strong>Remember the bag's own weight.</strong> A hard cabin trolley often weighs 2.5–3 kg of your 7 kg.</li>
<li><strong>Check your fare.</strong> Some cheap fares include cabin baggage only.</li>
</ul>
<p>More help: <a href="../guides/cabin-luggage-guide.html">how to pick a cabin trolley</a> and <a href="../guides/luggage-size-guide.html">what size luggage you need</a>.</p>
{tool_pills("../", "baggage/index.html")}
</article></div>
{telegram_band(cfg, "../")}"""
    path = "baggage/index.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), (title, path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, [article_schema(seo, desc, path, BAGGAGE_PHOTO), crumbs],
                                  og_type="article", photo=BAGGAGE_PHOTO)))
    lastmod[path] = checked

    # One page per airline
    for a in airlines + intl_airlines:
        abroad = a.get("scope") == "international"
        a_checked = intl["checked"] if abroad else checked
        cabin = a["cabin"]
        checkin_rows = "".join("<tr><th scope=\"row\">%s</th><td>%s</td></tr>" % (e(c["fare"]), e(c["allowance"])) for c in a["checkin"])
        notes = "".join("<li>%s</li>" % e(n) for n in a.get("notes", []))
        sources = " ".join(f'<a href="{e(src["url"])}" target="_blank" rel="noopener">{e(src["label"])}</a>' for src in a["sources"])
        faq = [
            ("How much cabin baggage is allowed on %s?" % a["name"], cabin["summary"] + "."),
            ("What is the %s cabin bag size limit?" % a["name"],
             "The limit is %s. Measure the bag with its wheels and handles." % size_limit_text(cabin)),
            (("How much checked baggage do I get on %s from India?" if abroad else "How much free check-in baggage do I get on %s domestic flights?") % a["name"],
             a["checkin_summary"] + ". It depends on your fare type, so check your ticket."),
        ]
        if abroad and a.get("infant"):
            faq.append(("How much baggage does an infant get on %s?" % a["name"], a["infant"]))
        if a.get("personal"):
            faq.insert(2, ("Can I carry a laptop bag or handbag too?", a["personal"]["summary"] + "."))
        faq_html = "".join("<h3>%s</h3><p>%s</p>" % (e(q), e(ans)) for q, ans in faq)
        if abroad:
            nm = a.get("page_name", a["name"])
            title = "%s baggage allowance from India: cabin bag and checked baggage" % nm
            seo = "%s baggage allowance from India %s: cabin bag size and kg by fare" % (nm, year)
            desc = "%s economy baggage on India flights: %s, %s. Checked baggage: %s. Checked %s." % (
                nm, cabin["summary"], size_limit_text(cabin), a["checkin_summary"], fmt_date(a_checked))
            crumb_html = '<a href="index.html">Baggage rules</a><span>/</span><a href="international.html">International</a>'
            scope_text = "economy on India routes"
        else:
            title = "%s baggage rules: cabin bag size, weight and check-in" % a["name"]
            seo = "%s baggage rules %s: cabin bag size, weight and check-in" % (a["name"], year)
            desc = "%s domestic baggage rules: %s, %s. Free check-in: %s. Checked %s." % (
                a["name"], cabin["summary"], size_limit_text(cabin), a["checkin_summary"], fmt_date(a_checked))
            crumb_html = '<a href="index.html">Baggage rules</a>'
            scope_text = "domestic economy"
        body = f"""{head(title, crumb_html, "Checked on " + fmt_date(a_checked) + " against " + e(a["name"]) + "'s official website &middot; " + scope_text)}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Cabin bag:</strong> {e(cabin['summary'])}.</li>
<li><strong>Size limit:</strong> {e(size_limit_text(cabin))}.</li>
{('<li><strong>Extra small bag:</strong> ' + e(a['personal']['summary']) + '.</li>') if a.get('personal') else ''}
<li><strong>{"Checked baggage" if abroad else "Free check-in"}:</strong> {e(a['checkin_summary'])}.</li>
</ul></div>
{checker_cta}
<h2>Cabin baggage</h2>
<p>{e(cabin.get('detail', cabin['summary'] + '.'))}</p>
{diagram_figure("cabin-limits-" + a["slug"], "../") if "cabin-limits-" + a["slug"] in DIAGRAMS else ""}
<h2>{"Checked baggage on India flights" if abroad else "Check-in baggage (domestic)"}</h2>
<table class="specs">{checkin_rows}</table>
{('<p>' + e(a['checkin_note']) + '</p>') if a.get('checkin_note') else ''}
{('<h2>Infants</h2><p>' + e(a['infant']) + '</p>') if abroad and a.get('infant') else ''}
{('<h2>Good to know</h2><ul>' + notes + '</ul>') if notes else ''}
<h2>Do our cabin picks fit {e(a['name'])}?</h2>
<p>Based on the size listed on Amazon. The "weight" column shows what's left of the {num(cabin['kg']) if cabin.get('kg') else ''} kg limit after the bag itself.</p>
{fit_table(cfg, a, picks, "../")}
<p>Weigh your packed bag at home with a {scale_link} before you leave.</p>
<section class="faq"><h2>Questions</h2>{faq_html}</section>
<h2>Source</h2>
<p>Official {e(a['name'])} pages: {sources}</p>
{disclaimer}
<h2>Other airlines</h2>
{others(a['slug'], intl_airlines if abroad else airlines)}
{('<p>Flying within India? See the <a href="index.html">baggage rules for Indian airlines</a>.</p>') if abroad else ''}
{tool_pills("../", "")}
</article></div>
{telegram_band(cfg, "../")}"""
        path = "baggage/%s.html" % a["slug"]
        crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html")]
                               + ([("International", "baggage/international.html")] if abroad else []) + [(a["name"], path)])
        faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}
        pages.append(write(path, page(cfg, seo, desc, body, 1, path, [article_schema(seo, desc, path), crumbs, faq_schema],
                                      og_type="article")))
        lastmod[path] = a_checked

    if intl_airlines:
        build_intl_hub(cfg, intl, picks, pages, lastmod, head, disclaimer, checker_cta, scale_link)

    # Bag checker
    # Some airlines have a smaller limit on some planes; the checker shows those as extra rows.
    rows_for_checker = []
    for a in airlines + [x for x in intl_airlines if x.get("checker", True)]:
        rows_for_checker.append((a["slug"], a["name"], a["slug"], a["cabin"]))
        for i, v in enumerate(a["cabin"].get("variants", []), 1):
            rows_for_checker.append(("%s-%d" % (a["slug"], i), "%s (%s)" % (a["name"], v["label"]), a["slug"],
                                     dict(a["cabin"], dims_cm=v.get("dims_cm"), total_cm=v.get("total_cm"))))
    js_data = {"airlines": [{"slug": key, "name": name, "kg": c.get("kg"), "dims": c.get("dims_cm"),
                             "total": c.get("total_cm"), "either": bool(c.get("either"))}
                            for key, name, page_slug, c in rows_for_checker],
               "picks": [{"asin": d["asin"], "title": d["title"], "dims": dims, "kg": kg} for d, dims, kg in picks]}
    js_json = json.dumps(js_data).replace("</", "<\\/")
    options = "".join('<option value="%d">%s</option>' % (i, e(d["title"])) for i, (d, dims, kg) in enumerate(picks))
    result_rows = "".join(f'<tr data-slug="{key}"><th scope="row"><a href="{page_slug}.html">{e(name)}</a>'
                          f'<span class="why">{e(short_limit_text(c))}</span></th>'
                          '<td class="r-size"><span class="fit fit-na">Enter size</span></td>'
                          '<td class="r-kg"><span class="fit fit-na">Enter weight</span></td></tr>'
                          for key, name, page_slug, c in rows_for_checker)
    title = "Will my bag fit? Cabin bag checker for Indian and international airlines" if intl_airlines else "Will my bag fit? Cabin bag checker for Indian airlines"
    seo = "Cabin bag size checker: will my bag fit IndiGo, Air India, Akasa or SpiceJet?"
    desc = ("Type your bag's length, width, height and weight to see if it fits the cabin baggage limits of India's main airlines"
            + (", plus Emirates, Qatar Airways, Saudia, Singapore Airlines and other international airlines." if intl_airlines else "."))
    body = f"""{head(title, '<a href="index.html">Baggage rules</a>', "Airline limits checked on " + fmt_date(checked) + " &middot; economy")}
<div class="wrap"><article class="guide">
<form class="checker" id="bag-checker" onsubmit="return false">
  <label>Fill from one of our picks (optional)
    <select id="bc-pick"><option value="">Choose a bag…</option>{options}</select>
  </label>
  <div class="checker-fields">
    <label>Length (cm)<input id="bc-l" type="number" inputmode="decimal" min="0" step="0.5" placeholder="55"></label>
    <label>Width (cm)<input id="bc-w" type="number" inputmode="decimal" min="0" step="0.5" placeholder="35"></label>
    <label>Height (cm)<input id="bc-h" type="number" inputmode="decimal" min="0" step="0.5" placeholder="25"></label>
    <label>Packed weight (kg)<input id="bc-kg" type="number" inputmode="decimal" min="0" step="0.1" placeholder="7"></label>
  </div>
  <p class="checker-total" id="bc-total" aria-live="polite"></p>
  <p class="hint">Measure the whole bag, with wheels and handles. Results update as you type.</p>
</form>
<noscript><p>This checker needs JavaScript. You can still compare the limits on our <a href="index.html">baggage rules page</a>.</p></noscript>
<div class="table-wrap"><table class="result-table" id="bc-results"><thead><tr><th>Airline</th><th>Size</th><th>Weight</th></tr></thead><tbody>{result_rows}</tbody></table></div>
{disclaimer}
<h2>How to measure your bag</h2>
{diagram_figure("measure-bag", "../")}
<h2>How this works</h2>
<ul>
<li>We compare your bag's longest side with the airline's longest allowed side, and so on, because a bag can be turned to fit.</li>
<li>When an airline gives a total size (length + width + height), we add up your three sides.</li>
<li>These are the standard economy limits: domestic flights for Indian airlines, and India routes for international airlines. Your fare, route or aircraft can change them.</li>
</ul>
<p>See the <a href="index.html">full baggage rules for each airline</a>, or read <a href="../guides/cabin-luggage-guide.html">how to pick a cabin trolley</a>.</p>
{tool_pills("../", "baggage/checker.html")}
</article></div>
<script type="application/json" id="bc-data">{js_json}</script>
<script src="../assets/checker.js" defer></script>
{telegram_band(cfg, "../")}"""
    path = "baggage/checker.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Cabin bag checker", path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, [crumbs])))
    lastmod[path] = checked


# ---------- train luggage rules and "can I carry it?" ----------

ANSWER = {"yes": ("yes", "Yes"), "no": ("no", "No"), "conditional": ("close", "With limits"), "unknown": ("na", "Not listed")}


def tool_pills(p, current):
    """Links to our other travel tools, for the end of tool and rules pages."""
    links = "".join(f'<li><a href="{p}{t[0]}">{e(t[1])}</a></li>' for t in TOOLS if t[0] != current)
    return f'<h2>More free travel tools</h2><ul class="airline-links">{links}</ul>' if links else ""


def sources_html(sources):
    return " ".join(f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])}</a>' for s in sources)


def faq_block(faq, heading="Questions"):
    html = "".join("<h3>%s</h3><p>%s</p>" % (e(q), e(a)) for q, a in faq)
    schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    return f'<section class="faq"><h2>{e(heading)}</h2>{html}</section>', schema


def tool_article(cfg, title, desc, path, published, modified, lang="en-IN"):
    return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
            "datePublished": published, "dateModified": modified, "inLanguage": lang,
            "image": abs_url(cfg, "assets/logo.png"), "mainEntityOfPage": abs_url(cfg, path),
            "author": org_schema(cfg), "publisher": org_schema(cfg)}


def build_railways(cfg, deals, pages, lastmod):
    data = json.loads(RAILWAYS_FILE.read_text(encoding="utf-8"))
    checked = data["checked"]
    rows = "".join(f'<tr><th scope="row">{e(c["class"])}</th><td>{num(c["free_kg"])} kg</td>'
                   f'<td>{(num(c["max_kg"]) + " kg") if c.get("max_kg") else "–"}</td></tr>' for c in data["classes"])
    size = data["size"]
    limits = [("Most classes", size["dims_cm"]), ("AC 3-tier and Chair Car", size["ac3_dims_cm"])]
    # The rule covers trunks, suitcases and boxes, so compare our suitcases (not backpacks or soft duffles).
    bag_rows = []
    for d in deals:
        dims = parse_dims(d.get("specs", {}).get("Size"))
        if d["category"] == "luggage" and dims and "duffle" not in d["title"].lower():
            cells = "".join("<td>%s</td>" % fit_badge(*size_fit(dims, {"dims_cm": lim})[::2]) for label, lim in limits)
            bag_rows.append(f'<tr><th scope="row"><a href="../picks/{d["asin"]}.html">{e(d["title"])}</a></th>'
                            f'<td>{" x ".join(num(x) for x in dims)} cm</td>{cells}</tr>')
    bags_html = ""
    if bag_rows:
        heads = "".join("<th>%s<span class=why>%s cm</span></th>" % (e(label), " x ".join(num(x) for x in lim)) for label, lim in limits)
        bags_html = ('<h2>Do our suitcases fit in the compartment?</h2><p>The limit is for trunks, suitcases and boxes. Based on the size listed on Amazon. '
                     'A suitcase can be turned to fit, so we compare its longest side with the longest limit, and so on.</p><div class="table-wrap"><table class="compare">'
                     f'<thead><tr><th>Our pick</th><th>Listed size</th>{heads}</tr></thead><tbody>{"".join(bag_rows)}</tbody></table></div>')
    first, last = data["classes"][0], data["classes"][-1]
    faq = data.get("faq", [])
    faq_html, faq_schema = faq_block([(f["q"], f["a"]) for f in faq]) if faq else ("", None)
    lists = lambda items: "<ul>%s</ul>" % "".join("<li>%s</li>" % e(i) for i in items)
    title = "Indian Railways luggage rules: how much luggage can you carry on a train?"
    seo = "Indian Railways luggage rules %s: free allowance for every class" % checked[:4]
    desc = ("Free luggage allowance on Indian trains: %s kg in %s down to %s kg in %s, the %s cm size limit for suitcases, "
            "excess charges and banned items. Checked %s." % (num(first["free_kg"]), first["class"], num(last["free_kg"]),
                                                               last["class"], " x ".join(num(x) for x in size["dims_cm"]), fmt_date(checked)))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Baggage rules</a><span>/</span>Trains</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Checked on {fmt_date(checked)} against Indian Railways' official pages</p>"""
    body = f"""{page_head("backpacks", f'<div class="media media-tile tint-backpacks">{icon("train", "icon media-icon")}</div>', inner, "../")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>{"".join("<li>%s</li>" % e(x) for x in data["quick"])}</ul></div>
<h2>Free luggage allowance by class</h2>
<div class="table-wrap"><table class="compare"><thead><tr><th>Class</th><th>Free allowance</th><th>Maximum, with charges</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>{e(data["allowance_note"])}</p>
<h2>Size limit for suitcases and trunks</h2>
<p>{e(size["text"])}</p>
{bags_html}
<h2>Carrying extra luggage</h2>
<p>{e(data["excess"])}</p>
<h2>Booking luggage in the luggage van</h2>
<p>{e(data["booking"])}</p>
<h2>What you can't carry</h2>
{lists(data["not_allowed"])}
{('<h2>Good to know</h2>' + lists(data["notes"])) if data.get("notes") else ""}
<aside class="tip">{icon("bulb", "icon tip-icon")}<div><strong>Packing for a train journey?</strong><p>Use our <a href="../packing/train.html">train journey packing list</a>, and lock your bag to the berth with a chain.</p></div></aside>
{faq_html}
<h2>Sources</h2>
<p>Official pages: {sources_html(data["sources"])}</p>
<p class="checked">Rules can change, and staff at stations apply them. Check the Indian Railways or IRCTC website before you travel.</p>
<h2>Flying instead?</h2>
<p>See the <a href="index.html">baggage rules for Indian airlines</a> and the <a href="checker.html">cabin bag checker</a>.</p>
{tool_pills("../", "baggage/train-luggage-rules.html")}
</article></div>
{telegram_band(cfg, "../")}"""
    path = "baggage/train-luggage-rules.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Train luggage rules", path)])
    schema = [tool_article(cfg, seo, desc, path, checked, checked), crumbs] + ([faq_schema] if faq_schema else [])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, schema, og_type="article")))
    lastmod[path] = checked


def build_can_i_carry(cfg, pages, lastmod):
    data = json.loads(FLIGHT_ITEMS_FILE.read_text(encoding="utf-8"))
    checked = data["checked"]
    groups = []
    for group in data["groups"]:
        rows = []
        for it in group["items"]:
            cells = ""
            for where in ("cabin", "checked"):
                state, label = ANSWER[it[where]]
                cells += f'<td><span class="fit fit-{state}">{label}</span></td>'
            words = " ".join([it["item"]] + it.get("also", []))
            rows.append(f'<tr data-words="{e(words.lower())}"><th scope="row">{e(it["item"])}</th>{cells}'
                        f'<td>{e(it["rule"])} <a class="src" href="{e(it["source"])}" target="_blank" rel="noopener">Source</a></td></tr>')
        groups.append(f'<tbody data-group><tr class="group-row"><th colspan="4" scope="colgroup">{e(group["name"])}</th></tr>{"".join(rows)}</tbody>')
    count = sum(len(g["items"]) for g in data["groups"])
    faq_html, faq_schema = faq_block([(f["q"], f["a"]) for f in data["faq"]])
    title = "Can I carry it on a flight? Cabin and check-in rules in India"
    seo = "Can I carry it on a flight in India? Cabin and check-in item list %s" % checked[:4]
    desc = ("Search %d items, from power banks and perfume to pickles and dry coconut, and see if they can go in your "
            "cabin bag or check-in baggage on flights in India. Checked %s." % (count, fmt_date(checked)))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Baggage rules</a><span>/</span>Can I carry it?</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Checked on {fmt_date(checked)} against BCAS, DGCA and airline pages</p>"""
    body = f"""{page_head("watches", f'<div class="media media-tile tint-watches">{icon("shield", "icon media-icon")}</div>', inner, "../")}
<div class="wrap"><article class="guide guide-wide">
<div class="answer"><h2>The rules most people get wrong</h2><ul>{"".join("<li>%s</li>" % e(x) for x in data["key_rules"])}</ul></div>
<form class="checker" onsubmit="return false"><label>Search an item<input id="carry-q" type="search" placeholder="power bank, perfume, pickle…" autocomplete="off"></label>
<p class="hint" id="carry-count" aria-live="polite" data-all="{{n}} items" data-some="{{shown}} of {{n}} items">{count} items</p></form>
<div class="table-wrap"><table class="compare carry-table" id="carry-table"><thead><tr><th>Item</th><th>Cabin bag</th><th>Check-in</th><th>Rule</th></tr></thead>{"".join(groups)}</table></div>
<p class="hint" id="carry-none" hidden>No match. Try another word, or check the airline's own list.</p>
<p class="checked">"With limits" means it's allowed only in the way the rule says. "Not listed" means the official pages we checked don't say. Security staff can still refuse any item, and airlines can be stricter, so check your airline before you fly.</p>
<aside class="tip">{icon("ruler", "icon tip-icon")}<div><strong>Packing your cabin bag?</strong><p>Check its size with the <a href="checker.html">cabin bag checker</a>, and use a <a href="../packing/index.html">packing checklist</a>.</p></div></aside>
{faq_html}
<h2>Sources</h2>
<p>{sources_html(data["sources"])}</p>
{tool_pills("../", "baggage/can-i-carry.html")}
</article></div>
<script src="../assets/carry.js" defer></script>
{telegram_band(cfg, "../")}"""
    path = "baggage/can-i-carry.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Can I carry it?", path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path,
                                  [tool_article(cfg, seo, desc, path, checked, checked), crumbs, faq_schema], og_type="article")))
    lastmod[path] = checked


# ---------- Hindi versions of the tool pages ----------

HINDI_PATHS = {"baggage/index.html": "hi/flight-baggage-rules.html",
               "baggage/can-i-carry.html": "hi/can-i-carry.html",
               "baggage/train-luggage-rules.html": "hi/train-luggage-rules.html"}


def build_hindi(cfg, deals, airlines, pages, lastmod):
    """Hindi pages for flight baggage, 'can I carry it' and train luggage. The text is in data/hindi.json;
    the rules and numbers come from the same data files as the English pages."""
    hi = json.loads(HINDI_FILE.read_text(encoding="utf-8"))
    L = hi["labels"]
    flight = json.loads(FLIGHT_ITEMS_FILE.read_text(encoding="utf-8"))
    rail = json.loads(RAILWAYS_FILE.read_text(encoding="utf-8"))
    for key, data in (("flight_items", flight), ("railways", rail), ("airlines", airlines)):
        if data["checked"] != hi[key]["checked"]:
            print("Warning: data/hindi.json %s was checked %s, but the English data %s. Update the Hindi text."
                  % (key, hi[key]["checked"], data["checked"]))

    def badge(ok, over=0):
        if ok is None:
            return '<span class="fit fit-na">%s</span>' % L["check"]
        if ok:
            return '<span class="fit fit-yes">%s</span>' % L["fits"]
        if over <= 3:
            return '<span class="fit fit-close">%s</span>' % (L["over"] % num(over))
        return '<span class="fit fit-no">%s</span>' % L["too_big"]

    def head(path, title, crumb, sub, tint, art):
        inner = f"""<nav class="crumbs"><a href="../index.html">{L["home"]}</a><span>/</span>{e(crumb)}</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">{e(sub)}</p>"""
        return page_head(tint, f'<div class="media media-tile tint-{tint}">{art}</div>', inner, "../")

    def pills(current):
        mine = [(path, t["crumb"]) for path, t in ((HINDI_PATHS["baggage/index.html"], hi["airlines"]),
                                                   (HINDI_PATHS["baggage/can-i-carry.html"], hi["flight_items"]),
                                                   (HINDI_PATHS["baggage/train-luggage-rules.html"], hi["railways"]))]
        links = "".join(f'<li><a href="../{path}">{e(name)}</a></li>' for path, name in mine if path != current)
        links += "".join(f'<li><a href="../{t[0]}" lang="en">{e(t[1])} (English)</a></li>' for t in TOOLS if t[0] not in HINDI_PATHS)
        return f'<h2>{L["more_tools"]}</h2><ul class="airline-links">{links}</ul>'

    def finish(path, title, seo, desc, body, checked, crumb, faq_schema):
        crumbs = crumbs_schema(cfg, [(L["home"], ""), (crumb, path)])
        schema = [tool_article(cfg, seo, desc, path, checked, checked, "hi-IN"), crumbs] + ([faq_schema] if faq_schema else [])
        pages.append(write(path, page(cfg, seo, desc, body, 1, path, schema, og_type="article", lang="hi")))
        lastmod[path] = checked

    def faq(items):
        return faq_block([(f["q"], f["a"]) for f in items], L["faq"]) if items else ("", None)

    tail = f'<p class="checked">{L["disclosure"]}</p>'

    # Flight baggage rules (airlines.json)
    t = hi["airlines"]
    path = HINDI_PATHS["baggage/index.html"]
    checked = airlines["checked"]
    rows, details = [], []
    for a in airlines["airlines"]:
        h = t["by_airline"].get(a["slug"])
        if not h:
            print("Warning: no Hindi text for airline %s in data/hindi.json" % a["slug"])
            h = {"personal": a.get("personal", {}).get("summary", "–"), "checkin": a["checkin_summary"], "note": ""}
        c = a["cabin"]
        size = t["size"] % (" x ".join(num(x) for x in c["dims_cm"]), num(c["total_cm"])) if c.get("dims_cm") and c.get("total_cm") else e(size_limit_text(c))
        rows.append(f'<tr><th scope="row"><a href="../baggage/{a["slug"]}.html" lang="en">{e(a["name"])}</a></th>'
                    f'<td>{e(t["cabin"] % num(c["kg"]))}</td><td>{e(size)}</td><td>{e(h["personal"])}</td><td>{e(h["checkin"])}</td></tr>')
        if h.get("note"):
            details.append(f'<h3>{e(a["name"])}</h3><p>{e(h["note"])} <a class="src" href="{e(a["official_url"])}" target="_blank" rel="noopener">{L["sources"]}</a></p>')
    picks = cabin_picks(deals)
    matrix_head = "".join("<th>%s</th>" % e(a["name"]) for a in airlines["airlines"])
    matrix_rows = "".join(
        f'<tr><th scope="row"><a href="../picks/{d["asin"]}.html">{e(d["title"])}</a><span class="why">{num(sum(dims))} cm</span></th>'
        + "".join("<td>%s</td>" % badge(*size_fit(dims, a["cabin"])[::2]) for a in airlines["airlines"]) + "</tr>"
        for d, dims, kg in picks)
    scale = next((d for d in deals if "scale" in d["title"].lower()), None)
    scale_html = f'<a href="../picks/{scale["asin"]}.html">{t["scale"]}</a>' if scale else t["scale"]
    faq_html, faq_schema = faq(t["faq"])
    title, seo = t["title"], t["seo"] % checked[:4]
    desc = t["desc"] % hi_date(checked)
    body = f"""{head(path, title, t["crumb"], L["checked"] % hi_date(checked), "luggage", icon("plane", "icon media-icon"))}
<div class="wrap"><article class="guide">
<p class="lead">{e(t["lead"])}</p>
<aside class="tip">{icon("ruler", "icon tip-icon")}<div>{t["checker"]}</div></aside>
<h2>{e(t["h_table"])}</h2>
<div class="table-wrap"><table class="compare"><thead><tr>{"".join("<th>%s</th>" % e(x) for x in t["head"])}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="checked">{e(t["footer"])}</p>
<h2>{e(t["h_details"])}</h2>
{"".join(details)}
<h2>{e(t["h_fit"])}</h2>
<p>{e(t["fit_intro"])}</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>{e(t["fit_head"])}</th>{matrix_head}</tr></thead><tbody>{matrix_rows}</tbody></table></div>
<h2>{e(t["h_tips"])}</h2>
<ul>{"".join("<li>%s</li>" % x.replace("{scale}", scale_html) for x in t["tips"])}</ul>
{faq_html}
{pills(path)}
{tail}
</article></div>
{telegram_band(cfg, "../")}"""
    finish(path, title, seo, desc, body, checked, t["crumb"], faq_schema)

    # Can I carry it? (flight_items.json)
    t = hi["flight_items"]
    path = HINDI_PATHS["baggage/can-i-carry.html"]
    checked = flight["checked"]
    states = {k: (v[0], L[k]) for k, v in ANSWER.items()}
    groups, count = [], 0
    for group in flight["groups"]:
        rows = []
        for it in group["items"]:
            h = t["items"].get(it["item"])
            if not h:
                print("Warning: no Hindi text for flight item %r in data/hindi.json" % it["item"])
                h = {"name": it["item"], "rule": it["rule"], "words": ""}
            cells = "".join('<td><span class="fit fit-%s">%s</span></td>' % states[it[where]] for where in ("cabin", "checked"))
            words = " ".join([h["name"], h.get("words", ""), it["item"]] + it.get("also", []))
            rows.append(f'<tr data-words="{e(words.lower())}"><th scope="row">{e(h["name"])}<span class="why" lang="en">{e(it["item"])}</span></th>{cells}'
                        f'<td>{e(h["rule"])} <a class="src" href="{e(it["source"])}" target="_blank" rel="noopener">{L["sources"]}</a></td></tr>')
            count += 1
        name = t["groups"].get(group["name"], group["name"])
        groups.append(f'<tbody data-group><tr class="group-row"><th colspan="4" scope="colgroup">{e(name)}</th></tr>{"".join(rows)}</tbody>')
    faq_html, faq_schema = faq(t["faq"])
    title, seo = t["title"], t["seo"]
    desc = t["desc"] % (count, hi_date(checked))
    body = f"""{head(path, title, t["crumb"], L["checked"] % hi_date(checked), "watches", icon("shield", "icon media-icon"))}
<div class="wrap"><article class="guide guide-wide">
<div class="answer"><h2>{e(t["key_title"])}</h2><ul>{"".join("<li>%s</li>" % e(x) for x in t["key_rules"])}</ul></div>
<form class="checker" onsubmit="return false"><label>{e(t["search_label"])}<input id="carry-q" type="search" placeholder="{e(t["placeholder"])}" autocomplete="off"></label>
<p class="hint" id="carry-count" aria-live="polite" data-all="{e(t["count_all"])}" data-some="{e(t["count_some"])}">{e(t["count_all"].replace("{n}", str(count)))}</p></form>
<div class="table-wrap"><table class="compare carry-table" id="carry-table"><thead><tr>{"".join("<th>%s</th>" % e(x) for x in t["head"])}</tr></thead>{"".join(groups)}</table></div>
<p class="hint" id="carry-none" hidden>{e(t["none"])}</p>
<p class="checked">{e(t["legend"])}</p>
{faq_html}
<h2>{L["sources"]}</h2>
<p lang="en">{sources_html(flight["sources"])}</p>
{pills(path)}
{tail}
</article></div>
<script src="../assets/carry.js" defer></script>
{telegram_band(cfg, "../")}"""
    finish(path, title, seo, desc, body, checked, t["crumb"], faq_schema)

    # Train luggage rules (railways.json)
    t = hi["railways"]
    path = HINDI_PATHS["baggage/train-luggage-rules.html"]
    checked = rail["checked"]
    rows = "".join(f'<tr><th scope="row">{e(t["classes"].get(c["class"], c["class"]))}</th><td>{num(c["free_kg"])} kg</td>'
                   f'<td>{(num(c["max_kg"]) + " kg") if c.get("max_kg") else "–"}</td></tr>' for c in rail["classes"])
    size = rail["size"]
    limits = [size["dims_cm"], size["ac3_dims_cm"]]
    bag_rows = []
    for d in deals:
        dims = parse_dims(d.get("specs", {}).get("Size"))
        if d["category"] == "luggage" and dims and "duffle" not in d["title"].lower():
            cells = "".join("<td>%s</td>" % badge(*size_fit(dims, {"dims_cm": lim})[::2]) for lim in limits)
            bag_rows.append(f'<tr><th scope="row"><a href="../picks/{d["asin"]}.html">{e(d["title"])}</a></th>'
                            f'<td>{" x ".join(num(x) for x in dims)} cm</td>{cells}</tr>')
    bags_html = ""
    if bag_rows:
        h0, h1, h2, h3 = t["bags_head"]
        bags_html = (f'<h2>{e(t["h_bags"])}</h2><p>{e(t["bags_intro"])}</p><div class="table-wrap"><table class="compare">'
                     f'<thead><tr><th>{e(h0)}</th><th>{e(h1)}</th><th>{e(h2)}<span class=why>{" x ".join(num(x) for x in limits[0])} cm</span></th>'
                     f'<th>{e(h3)}<span class=why>{" x ".join(num(x) for x in limits[1])} cm</span></th></tr></thead><tbody>{"".join(bag_rows)}</tbody></table></div>')
    lists = lambda items: "<ul>%s</ul>" % "".join("<li>%s</li>" % e(i) for i in items)
    faq_html, faq_schema = faq(t["faq"])
    title, seo = t["title"], t["seo"] % checked[:4]
    desc = t["desc"] % hi_date(checked)
    body = f"""{head(path, title, t["crumb"], L["checked"] % hi_date(checked), "backpacks", icon("train", "icon media-icon"))}
<div class="wrap"><article class="guide">
<div class="answer"><h2>{L["quick"]}</h2><ul>{"".join("<li>%s</li>" % e(x) for x in t["quick"])}</ul></div>
<h2>{e(t["h_allowance"])}</h2>
<div class="table-wrap"><table class="compare"><thead><tr>{"".join("<th>%s</th>" % e(x) for x in t["head"])}</tr></thead><tbody>{rows}</tbody></table></div>
<p>{e(t["allowance_note"])}</p>
<h2>{e(t["h_size"])}</h2>
<p>{e(t["size_text"])}</p>
{bags_html}
<h2>{e(t["h_excess"])}</h2>
<p>{e(t["excess"])}</p>
<h2>{e(t["h_booking"])}</h2>
<p>{e(t["booking"])}</p>
<h2>{e(t["h_not_allowed"])}</h2>
{lists(t["not_allowed"])}
<h2>{e(t["h_notes"])}</h2>
{lists(t["notes"])}
<aside class="tip">{icon("bulb", "icon tip-icon")}<div>{t["tip"]}</div></aside>
{faq_html}
<h2>{L["sources"]}</h2>
<p lang="en">{sources_html(rail["sources"])}</p>
<p class="checked">{e(t["footer"])}</p>
{pills(path)}
{tail}
</article></div>
{telegram_band(cfg, "../")}"""
    finish(path, title, seo, desc, body, checked, t["crumb"], faq_schema)


# ---------- luggage size chart ----------

SIZE_ROWS = [(18, "Small cabin bag", "1–3 days"), (20, "Cabin", "2–4 days"), (22, "Cabin, at the height limit of most Indian airlines", "2–4 days"),
             (24, "Small medium", "4–6 days"), (26, "Medium", "5–8 days"), (28, "Large", "8–12 days"),
             (30, "Large", "10+ days, families"), (32, "Extra large: check the 158 cm limit", "Long trips")]
KG_ROWS = [3, 7, 10, 15, 20, 23, 25, 30, 32]


def build_size_chart(cfg, deals_by_asin, airlines, pages, lastmod, intl=None):
    """Inches/cm and kg/lb chart for luggage, with airline limits converted (baggage/luggage-size-chart.html)."""
    path = "baggage/luggage-size-chart.html"
    updated = "2026-11-06"
    cm = lambda inches: num(round(inches * 2.54, 1))
    inch = lambda c: num(round(c / 2.54, 1))
    lb = lambda kg: num(round(kg * 2.20462, 1))
    size_rows = "".join(f'<tr><th scope="row">{i} inch</th><td>{cm(i)} cm</td><td>{e(kind)}</td><td>{e(trip)}</td></tr>'
                        for i, kind, trip in SIZE_ROWS)
    kg_rows = "".join(f"<tr><th scope=\"row\">{k} kg</th><td>{lb(k)} lb</td></tr>" for k in KG_ROWS)
    air_rows, us_fit = "", []
    us = [22 * 2.54, 14 * 2.54, 9 * 2.54]
    for a in (airlines or {}).get("airlines", []) + [x for x in (intl or {}).get("airlines", []) if x.get("checker", True)]:
        c = a["cabin"]
        if not c.get("dims_cm"):
            continue
        air_rows += (f'<tr><th scope="row"><a href="{a["slug"]}.html">{e(a["name"])}</a></th>'
                     f'<td>{" x ".join(num(x) for x in c["dims_cm"])} cm' + (f'<span class="why">{num(c["total_cm"])} cm in total</span>' if c.get("total_cm") else "") + '</td>'
                     f'<td>{" x ".join(inch(x) for x in c["dims_cm"])} in' + (f'<span class="why">{inch(c["total_cm"])} in in total</span>' if c.get("total_cm") else "") + '</td>'
                     f'<td>{num(c["kg"])} kg<span class="why">{lb(c["kg"])} lb</span></td></tr>')
        if size_fit(us, c)[0] and a.get("scope") != "international":
            us_fit.append(a["name"])
    us_cm = " x ".join(num(round(x, 1)) for x in us)
    us_answer = ("22 x 14 x 9 inches is %s cm, %s cm in total. By size it fits %s, but it's a little over the other Indian airlines' limits."
                 % (us_cm, num(round(sum(us), 1)), " and ".join(us_fit))) if us_fit else (
                 "22 x 14 x 9 inches is %s cm, %s cm in total, a little over the cabin limits of the Indian airlines we track."
                 % (us_cm, num(round(sum(us), 1))))
    indigo = next((a for a in (airlines or {}).get("airlines", []) if a["slug"] == "indigo"), None)
    quick = ["1 inch is 2.54 cm. So a 20-inch bag is %s cm, a 24-inch bag is %s cm and a 28-inch bag is %s cm." % (cm(20), cm(24), cm(28)),
             "Indian brands mostly sell trolleys by height in cm: about 55 cm for cabin, 65–69 cm for medium and 75–79 cm for large.",
             "A 22-inch bag (%s cm) is closest to the usual 55 cm cabin height. A true 20-inch bag is smaller, but some brands sell 55 cm bags as \"20 inch\" and 65 cm bags as \"24 inch\", so check the cm." % cm(22)]
    if indigo:
        quick.append("IndiGo's cabin limit, %s cm, is %s inches." % (" x ".join(num(x) for x in indigo["cabin"]["dims_cm"]),
                                                                     " x ".join(inch(x) for x in indigo["cabin"]["dims_cm"])))
    quick.append("The inch size is only the height. Airlines check length, width and height, wheels and handles included.")
    faq = [("What is 20 inch luggage in cm?", "20 inches is %s cm. That's smaller than the usual 55 cm cabin trolley sold in India, though some brands sell 55 cm bags as \"20 inch\"." % cm(20)),
           ("Is a 24 inch suitcase cabin or check-in?", "Check-in. 24 inches is %s cm, too tall for the 55–56 cm cabin limits of Indian airlines. It's a small medium-size bag, good for 4–6 days." % cm(24)),
           ("How many inches is a 55 cm cabin bag?", "55 cm is %s inches." % inch(55)),
           ("What is 22 x 14 x 9 inches in cm?", us_answer),
           ("How many pounds is 23 kg?", "23 kg is about %s lb. 7 kg, the usual Indian cabin bag limit, is about %s lb." % (lb(23), lb(7)))]
    faq_html, faq_schema = faq_block(faq)
    picks = [deals_by_asin[a] for a in ("B097JLKP8X", "B0F5HGLC5Q", "B0GNSKLF5Z", "B0GX5VFHMS") if a in deals_by_asin]
    picks_html = (f'<h2>Our picks by size</h2><p>Cabin trolleys that fit IndiGo or Air India by their listed size, a light medium check-in bag and a large one within 158 cm.</p>'
                  f'{grid(cfg, picks, "../")}') if picks else ""
    size_fig = diagram_figure("luggage-sizes", "../") if "luggage-sizes" in DIAGRAMS else ""
    title = "Luggage size chart: inches to cm for cabin, medium and large bags"
    seo = "Luggage size chart in inches and cm: 20, 24 and 28 inch trolley sizes"
    desc = ("Trolley bag sizes from 18 to 32 inches in cm, the cabin limits of IndiGo, Air India and other Indian airlines in inches, "
            "and kg to pounds for baggage allowances. Free converter.")
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Baggage rules</a><span>/</span>Size chart</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Updated {fmt_date(updated)}</p>"""
    body = f"""{page_head("luggage", f'<div class="media media-tile tint-luggage">{icon("ruler", "icon media-icon")}</div>', inner, "../")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>{"".join("<li>%s</li>" % e(x) for x in quick)}</ul></div>
<form class="checker" onsubmit="return false">
<div class="checker-fields"><label>Number<input id="cv-n" type="number" min="0" step="any" inputmode="decimal" placeholder="e.g. 22"></label>
<label>From<select id="cv-unit"><option value="in">inches</option><option value="cm">cm</option><option value="kg">kg</option><option value="lb">lb</option></select></label></div>
<p class="checker-total" id="cv-out" aria-live="polite"></p>
<p class="hint">Have your bag's size in inches? Type all three sides below and check it against every airline.</p>
<div class="checker-fields"><label>Length (in)<input id="cv-l" type="number" min="0" step="any" inputmode="decimal"></label>
<label>Width (in)<input id="cv-w" type="number" min="0" step="any" inputmode="decimal"></label>
<label>Height (in)<input id="cv-h" type="number" min="0" step="any" inputmode="decimal"></label></div>
<p class="checker-total" id="cv-bag" aria-live="polite"></p>
<p class="hint"><a id="cv-check" href="checker.html">Open the cabin bag checker</a></p>
</form>
<h2>Trolley sizes in inches and cm</h2>
<p>Sizes are the bag's height. Sellers don't always say whether it includes the wheels, so check the full size on the listing.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Inches</th><th>cm</th><th>Size</th><th>Trip length</th></tr></thead><tbody>{size_rows}</tbody></table></div>
{size_fig}
{('<h2>Cabin bag limits in inches: Indian and international airlines</h2><div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Size limit (cm)</th><th>In inches</th><th>Weight</th></tr></thead><tbody>' + air_rows + '</tbody></table></div><p class="checked">Economy limits: domestic flights for Indian airlines, India routes for international airlines. From our <a href="index.html">baggage rules</a> and <a href="international.html">international baggage</a> pages. Check your ticket before you fly.</p>') if air_rows else ""}
<h2>Check-in bag size</h2>
<p>Most Indian airlines limit each checked bag to <strong>158 cm in total</strong> (length + width + height), which is about {inch(158)} inches, and <strong>32 kg</strong> (about {lb(32)} lb). Many large trolleys go over that: of the 31 large models we checked on Amazon.in on 6 Nov 2026, <strong>26 were listed over 158 cm</strong>. See <a href="../guides/28-inch-trolley-bag-size.html">the 5 that weren't</a>.</p>
<h2>Kilograms to pounds</h2>
<p>Indian airlines use kg. Foreign airlines, US websites and some luggage scales show pounds.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>kg</th><th>Pounds (lb)</th></tr></thead><tbody>{kg_rows}</tbody></table></div>
{picks_html}
{faq_html}
<p>More help: <a href="../guides/20-inch-trolley-bag-size.html">20 inch</a>, <a href="../guides/24-inch-trolley-bag-size.html">24 inch</a> and <a href="../guides/28-inch-trolley-bag-size.html">28 inch</a> trolleys in detail, <a href="../guides/luggage-size-guide.html">what size luggage you need</a> and <a href="../guides/cabin-luggage-guide.html">how to pick a cabin trolley</a>.</p>
{tool_pills("../", path)}
</article></div>
<script src="../assets/sizes.js" defer></script>
{telegram_band(cfg, "../")}"""
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Luggage size chart", path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, [tool_article(cfg, seo, desc, path, updated, updated), crumbs, faq_schema],
                                  og_type="article")))
    lastmod[path] = updated


# ---------- size and weight tools ----------

# Wrist size (cm) -> dial size (mm). A rule of thumb from common watch-fitting advice, not a fixed rule.
WRIST_ROWS = [(0, 15, 28, 36, "Small wrist"), (15, 16.5, 34, 38, "Slim wrist"), (16.5, 18, 38, 42, "Average wrist"),
              (18, 19.5, 40, 44, "Wide wrist"), (19.5, 99, 42, 46, "Very wide wrist")]
# Typical laptop sizes by screen size (width x depth, cm). Real laptops vary by a few cm.
LAPTOP_ROWS = [(13.3, "30–31 x 21–22 cm"), (14, "31–33 x 21–23 cm"), (15.6, "35–36 x 23–25 cm"), (16, "35–36 x 24–26 cm"), (17.3, "39–40 x 26–28 cm")]
# Typical weights (kg) for the bag weight estimator. Real items vary; weigh the bag to be sure.
BAG_ITEMS = [("Clothes", [("T-shirt or top", 0.2), ("Shirt", 0.25), ("Jeans", 0.7), ("Trousers", 0.45), ("Shorts", 0.25),
                          ("Kurta", 0.3), ("Saree", 0.6), ("Salwar suit", 0.5), ("Nightwear set", 0.3), ("Underwear", 0.05),
                          ("Socks (pair)", 0.05), ("Sweater", 0.5), ("Light jacket", 0.6), ("Heavy winter jacket", 1.2), ("Thermal set", 0.3)]),
             ("Shoes", [("Sneakers (pair)", 0.8), ("Formal shoes (pair)", 1.0), ("Sandals or slippers (pair)", 0.3)]),
             ("Bathroom and health", [("Toiletry kit", 1.0), ("Towel", 0.5), ("Medicines kit", 0.3)]),
             ("Electronics", [("Laptop", 1.6), ("Laptop charger", 0.3), ("Phone charger and cables", 0.15), ("Power bank", 0.3), ("Camera", 0.7)]),
             ("Other", [("Book", 0.4), ("Umbrella", 0.4), ("Box of sweets or snacks", 1.0), ("Water bottle (empty)", 0.2)])]
BAG_TYPES = [("Backpack", 0.6), ("Soft cabin trolley", 2.4), ("Hard cabin trolley", 2.7), ("Medium check-in trolley", 3.5), ("Large check-in trolley", 4.5), ("Duffle bag", 1.2)]


def first_number(text):
    m = re.search(r"(\d+(?:\.\d+)?)", text or "")
    return float(m.group(1)) if m else None


def build_tools(cfg, deals, pages, lastmod):
    """Watch size by wrist, backpack by laptop size, and packed bag weight (tools/*.html, static/tools.js)."""
    updated = "2026-11-03"

    def finish(path, title, seo, desc, crumb, body, faq):
        faq_html, faq_schema = faq_block(faq)
        body = body.replace("{faq}", faq_html)
        crumbs = crumbs_schema(cfg, [("Home", ""), (crumb, path)])
        pages.append(write(path, page(cfg, seo, desc, body, 1, path,
                                      [tool_article(cfg, seo, desc, path, updated, updated), crumbs, faq_schema], og_type="article")))
        lastmod[path] = updated

    def head(title, crumb, sub, tint, glyph):
        inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>{e(crumb)}</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">{e(sub)}</p>"""
        return page_head(tint, f'<div class="media media-tile tint-{tint}">{icon(glyph, "icon media-icon")}</div>', inner, "../")

    def tagged(d, attr, value):
        return card(cfg, d, "../").replace('<article class="card"', f'<article class="card" {attr}="{value}"', 1)

    # Watch size by wrist
    path = "tools/watch-size.html"
    watches = []
    for d in deals:
        mm = first_number(d.get("specs", {}).get("Case size"))
        if d["category"] == "watches" and mm and "couple" not in d["title"].lower():
            watches.append((mm, d))
    watches.sort(key=lambda x: x[0])
    rows = "".join(f'<tr data-wrist="{lo}-{hi}"><th scope="row">{e(label)}</th><td>{"Under 15 cm" if lo == 0 else ("Over 19.5 cm" if hi == 99 else "%s–%s cm" % (num(lo), num(hi)))}</td><td>{a}–{b} mm</td></tr>'
                   for lo, hi, a, b, label in WRIST_ROWS)
    cards = "".join(tagged(d, "data-mm", num(mm)) for mm, d in watches)
    title = "Watch size chart: which dial size suits your wrist?"
    seo = "Watch size chart India: which watch dial size suits my wrist?"
    desc = "Measure your wrist in cm and see which watch dial size (in mm) suits it, from 28 mm to 46 mm, with our watch picks in that size."
    body = f"""{head(title, "Watch size by wrist", "A free tool. Updated " + fmt_date(updated), "watches", "watch")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li>Wrap a strip of paper or a string around your wrist bone, mark it, and measure it with a ruler in cm.</li>
<li>Most men's wrists are about 16–18 cm and suit a 38–42 mm dial. Slimmer wrists look better with 34–38 mm.</li>
<li>Bigger isn't always better: the lugs (the ends that hold the strap) shouldn't stick out past your wrist.</li>
</ul></div>
<form class="checker" onsubmit="return false">
<div class="checker-fields"><label>Your wrist size<input id="ws-cm" type="number" min="10" max="30" step="0.5" inputmode="decimal" placeholder="e.g. 17"></label>
<label>Unit<select id="ws-unit"><option value="cm">cm</option><option value="in">inches</option></select></label></div>
<p class="checker-total" id="ws-out" aria-live="polite">Type your wrist size to see the dial sizes that suit it.</p>
</form>
<h2>Wrist size to dial size chart</h2>
<div class="table-wrap"><table class="compare" id="ws-table"><thead><tr><th>Wrist</th><th>Wrist size</th><th>Dial size that suits it</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="checked">A rule of thumb, not a strict rule. A thin case and a leather strap look smaller; a thick steel watch looks bigger. Try one on if you can.</p>
<h2>Our watch picks by dial size</h2>
<p id="ws-picks-note">Sorted from small to large. Type your wrist size above to see the ones that suit it.</p>
<div class="grid" id="ws-picks">{cards}</div>
<p>More help: <a href="../guides/first-analog-watch-guide.html">how to choose your first analog watch</a>.</p>
{{faq}}
{tool_pills("../", path)}
</article></div>
<script src="../assets/tools.js" defer></script>
{telegram_band(cfg, "../")}"""
    finish(path, title, seo, desc, "Watch size by wrist", body, [
        ("How do I measure my wrist for a watch?", "Wrap a strip of paper or a string around your wrist just above the wrist bone, mark where it meets, and measure that length with a ruler in cm."),
        ("What watch size is best for a 17 cm wrist?", "A 17 cm wrist is average. A dial of about 38–42 mm usually suits it."),
        ("Is a 42 mm watch too big?", "Not for an average or wide wrist (about 16.5 cm and up). On a slim wrist under 16 cm, 36–38 mm usually looks better."),
        ("What size watch suits women?", "Most women's watches are 28–36 mm. On a slim wrist, 28–34 mm is a safe choice.")])

    # Backpack by laptop size
    path = "tools/laptop-backpack.html"
    bags = []
    for d in deals:
        if d["category"] != "backpacks":
            continue
        fit = d.get("specs", {}).get("Laptop") or d.get("specs", {}).get("Laptop fit") or ""
        sizes = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*(?:–|-|inch)", fit)]
        bags.append((max(sizes) if sizes else 0, fit, d))
    bags.sort(key=lambda x: -x[0])
    cards = "".join(tagged(d, "data-inch", num(inch) if inch else "0") for inch, fit, d in bags)
    rows = "".join(f'<tr><th scope="row">{num(s)} inch</th><td>{e(dims)}</td></tr>' for s, dims in LAPTOP_ROWS)
    title = "Which backpack fits my laptop? Laptop backpack size guide"
    seo = "Laptop backpack size guide: will a 15.6 or 17 inch laptop fit?"
    desc = "Pick your laptop's screen size (13 to 17 inch) and see which of our laptop backpacks fit it, plus typical laptop sizes in cm."
    body = f"""{head(title, "Backpack for my laptop", "A free tool. Updated " + fmt_date(updated), "backpacks", "backpack")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li>Laptop sizes are the screen measured corner to corner, in inches. A "15.6 inch" laptop is about 36 cm wide.</li>
<li>A bag "for 15.6 inch laptops" fits most 15.6 inch and smaller laptops. For 16 or 17 inch laptops, look for a bag that says 17 inch.</li>
<li>Gaming laptops are often thicker and wider, so check your laptop's width and the bag's sleeve size.</li>
</ul></div>
<form class="checker" onsubmit="return false">
<label>Your laptop's screen size<select id="lb-size"><option value="">Choose…</option><option value="13.3">13 or 13.3 inch</option><option value="14">14 inch</option><option value="15.6">15 or 15.6 inch</option><option value="16">16 inch</option><option value="17.3">17 or 17.3 inch</option></select></label>
<p class="checker-total" id="lb-out" aria-live="polite">Choose your laptop size to see the backpacks that fit it.</p>
</form>
<h2>Our laptop backpacks</h2>
<div class="grid" id="lb-picks">{cards}</div>
<p class="checked">Based on the laptop size each seller lists on Amazon. Bags that don't list a size are shown as "check listing".</p>
<h2>Typical laptop sizes</h2>
<div class="table-wrap"><table class="compare"><thead><tr><th>Screen size</th><th>Typical laptop size (width x depth)</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="checked">Real laptops vary by a few cm. Measure yours, or check its size on the maker's website.</p>
<p>More help: <a href="../guides/laptop-backpack-guide.html">how to choose a laptop backpack</a>.</p>
{{faq}}
{tool_pills("../", path)}
</article></div>
<script src="../assets/tools.js" defer></script>
{telegram_band(cfg, "../")}"""
    finish(path, title, seo, desc, "Backpack for my laptop", body, [
        ("Will a 15.6 inch laptop fit in a 15 inch bag?", "Sometimes, but it can be tight. A bag made for 15.6 inch laptops is the safer choice."),
        ("What size backpack do I need for a 17 inch laptop?", "One that says it fits 17 inch laptops. These bags usually hold 28 litres or more."),
        ("How do I know my laptop's size?", "The size is the screen, measured corner to corner. It's usually in the laptop's name or on the box, or measure the width of the laptop itself in cm.")])

    # Packed bag weight
    path = "tools/bag-weight.html"
    groups = "".join(
        f'<section class="pack-group"><h2>{e(name)}</h2><ul>' + "".join(
            f'<li><label class="bw-item"><span>{e(item)} <small class="muted">about {num(kg)} kg</small></span>'
            f'<input type="number" min="0" max="50" step="1" inputmode="numeric" value="0" data-kg="{kg}" aria-label="How many: {e(item)}"></label></li>'
            for item, kg in items) + "</ul></section>" for name, items in BAG_ITEMS)
    bag_opts = "".join(f'<option value="{kg}">{e(name)} (about {num(kg)} kg empty)</option>' for name, kg in BAG_TYPES)
    scale = next((d for d in deals if "scale" in d["title"].lower()), None)
    scale_html = f'<a href="../picks/{scale["asin"]}.html">luggage scale</a>' if scale else "luggage scale"
    title = "How heavy is my bag? Packed bag weight calculator"
    seo = "Bag weight calculator: will my packed bag be under 7 kg or 15 kg?"
    desc = "Add what you're packing and see roughly how heavy your bag will be, against 7 kg cabin and 15–30 kg check-in limits. Free, no sign-up."
    body = f"""{head(title, "Bag weight calculator", "A free tool. Updated " + fmt_date(updated), "travel-gear", "scale" if "scale" in ICONS else "ruler")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li>Most Indian airlines allow a 7 kg cabin bag and 15 kg of check-in baggage on domestic flights.</li>
<li>The bag counts too: a hard cabin trolley is about 2.5–3 kg empty, which leaves only about 4–4.5 kg for your things.</li>
<li>This tool uses typical weights. To be sure, weigh the packed bag at home with a {scale_html}.</li>
</ul></div>
<form class="checker packer" id="bw" onsubmit="return false">
<div class="checker-fields"><label>Your bag<select id="bw-bag">{bag_opts}</select></label>
<label>Weight limit<select id="bw-limit"><option value="7">7 kg (cabin bag)</option><option value="15">15 kg (domestic check-in)</option><option value="20">20 kg</option><option value="23">23 kg</option><option value="25">25 kg</option><option value="30">30 kg</option></select></label></div>
<p class="checker-total" id="bw-out" aria-live="polite"></p>
<p class="hint"><button type="button" class="link-btn" id="bw-clear">Start again</button></p>
</form>
<div class="pack-list">{groups}</div>
<p class="checked">Typical weights for adult clothes and common items. Real items vary, so leave a little room and weigh the bag before you leave.</p>
<p>More help: <a href="../baggage/index.html">baggage rules for Indian airlines</a>, <a href="../baggage/checker.html">will my bag fit?</a> and <a href="../packing/index.html">packing checklists</a>.</p>
{{faq}}
{tool_pills("../", path)}
</article></div>
<script src="../assets/tools.js" defer></script>
{telegram_band(cfg, "../")}"""
    finish(path, title, seo, desc, "Bag weight calculator", body, [
        ("How much can I pack in a 7 kg cabin bag?", "A hard cabin trolley weighs about 2.5–3 kg empty, so you have about 4–4.5 kg left: roughly clothes for 2–3 days, a toiletry kit and a charger. A light backpack leaves more room."),
        ("How heavy is a laptop?", "Most laptops weigh about 1.2–2 kg, plus about 0.3 kg for the charger."),
        ("How can I check my bag's weight at home?", "Use a small hand-held luggage scale: hook the bag on and lift it. Or weigh yourself on a bathroom scale with and without the bag and subtract.")])


# ---------- packing checklists ----------

PACKING_FILE = ROOT / "data" / "packing.json"
QTY_RULES = {"per_day": lambda n: n, "per_day_plus_1": lambda n: n + 1,
             "per_2_days": lambda n: n / 2, "per_3_days": lambda n: n / 3}


def pack_qty(rule, days):
    """Same rule as qty() in static/packing.js."""
    if rule is None:
        return None
    value = rule if isinstance(rule, (int, float)) else QTY_RULES[rule](days)
    return max(1, -(-value // 1)) if not isinstance(value, int) else max(1, value)


def build_packing(cfg, deals_by_asin, pages, lastmod, trip_guides=()):
    data = json.loads(PACKING_FILE.read_text(encoding="utf-8"))
    trips = data["trips"]
    paths = {t["slug"]: ("index.html" if t["slug"] == "week" else t["slug"] + ".html") for t in trips}
    for group in data["groups"]:
        for item in group["items"]:
            if item.get("pick") and item["pick"] not in deals_by_asin:
                sys.exit("Error: packing item %s links to unknown pick %s" % (item["id"], item["pick"]))
            if item.get("qty") is not None and not isinstance(item["qty"], int) and item["qty"] not in QTY_RULES:
                sys.exit("Error: packing item %s has unknown qty %s" % (item["id"], item["qty"]))
    carry_link = ' See <a href="../baggage/can-i-carry.html">what you can carry on a flight</a>.' if FLIGHT_ITEMS_FILE.exists() else ""
    for trip in trips:
        slug = trip["slug"]
        chips = "".join(
            f'<a class="trip-chip{" on" if t["slug"] == slug else ""}" href="{paths[t["slug"]]}"'
            f'{" aria-current=page" if t["slug"] == slug else ""}>{e(t["label"])}</a>' for t in trips)
        groups_html = []
        count = 0
        for group in data["groups"]:
            rows = []
            for item in group["items"]:
                if item["trips"] != "all" and slug not in item["trips"]:
                    continue
                count += 1
                qty = pack_qty(item.get("qty"), trip["days"])
                more = ""
                if item.get("pick"):
                    more = f' <a class="pk-more" href="../picks/{item["pick"]}.html">Our pick</a>'
                elif item.get("link") and (item["link"] != "baggage/can-i-carry.html" or FLIGHT_ITEMS_FILE.exists()):
                    more = f' <a class="pk-more" href="../{item["link"]}">See more</a>'
                rows.append(f'<li><label><input type="checkbox" data-id="{e(item["id"])}"> <span>{e(item["name"])}</span>'
                            + (f' <b class="pk-qty" data-qty="{e(str(item["qty"]))}">× {num(qty)}</b>' if qty else "")
                            + f'</label>{more}</li>')
            if rows:
                groups_html.append(f'<section class="pack-group"><h2>{e(group["name"])}</h2><ul>{"".join(rows)}</ul></section>')
        going = [g for g in trip_guides if g.get("packing") == slug]
        going_html = ('<p class="small">Planning the trip? Read our %s.</p>' % " and ".join(
            f'<a href="../trips/{g["slug"]}.html">{e(g.get("place", g["title"]))} trip guide</a>' for g in going)) if going else ""
        title = trip["title"]
        desc = "%s %s A free checklist with %d items and quantities for your number of days. Tick things off as you pack." % (
            title + ":", trip["intro"].split(". ")[0] + ".", count)
        inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>{'<a href="index.html">Packing lists</a><span>/</span>' if slug != 'week' else ''}{e(trip['label'])}</nav>
      <h1>{e(title)}</h1>
      <p class="lead">{e(trip['intro'])}</p>"""
        body = f"""{page_head("travel-gear", media(cfg, "travel-gear", "media media-tile"), inner, "../", "packed-suitcase")}
<div class="wrap"><article class="guide">
<nav class="trip-chips" aria-label="Packing lists for other trips">{chips}</nav>
{going_html}
<form class="checker packer" id="packer" onsubmit="return false">
  <label>How many days?<input id="pk-days" type="number" inputmode="numeric" min="1" max="30" value="{trip['days']}"></label>
  <p class="checker-total"><span id="pk-count">{count} things to pack</span></p>
  <p class="hint">Quantities change with the number of days. Your ticks stay on this device only. <button type="button" class="link-btn" id="pk-clear">Clear ticks</button> <button type="button" class="link-btn" id="pk-print">Print</button></p>
</form>
<div class="pack-list" data-trip="{slug}">{"".join(groups_html)}</div>
<h2>Packing tips</h2>
<ul>
<li><strong>Cabin bag first.</strong> Keep medicines, documents, your power bank, laptop and one change of clothes in the bag that stays with you.{carry_link}</li>
<li><strong>Heavy things at the bottom.</strong> Put shoes and heavy items near the wheels so the trolley doesn't tip over.</li>
<li><strong>Roll T-shirts, fold shirts.</strong> Rolling saves space; <a href="../picks/B0C4TV4M2F.html">packing cubes</a> keep everything in order.</li>
<li><strong>Weigh it at home.</strong> Check your airline's limit on our <a href="../baggage/index.html">baggage rules page</a>, or the <a href="../baggage/train-luggage-rules.html">train luggage rules</a> for rail trips.</li>
<li><strong>Pick the right bag size.</strong> Not sure? Read <a href="../guides/luggage-size-guide.html">what size luggage you need</a>.</li>
</ul>
{tool_pills("../", "packing/index.html")}
</article></div>
<script src="../assets/packing.js" defer></script>
{telegram_band(cfg, "../")}"""
        path = "packing/" + paths[slug]
        items = [("Home", "")] + ([("Packing lists", "packing/index.html")] if slug != "week" else []) + [(trip["label"], path)]
        article = {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
                   "datePublished": "2026-11-03", "dateModified": "2026-11-03", "inLanguage": "en-IN",
                   "image": photo_og(cfg, "packed-suitcase") if "packed-suitcase" in PHOTOS else abs_url(cfg, "assets/logo.png"),
                   "mainEntityOfPage": abs_url(cfg, path), "author": org_schema(cfg), "publisher": org_schema(cfg)}
        pages.append(write(path, page(cfg, title, desc, body, 1, path, [article, crumbs_schema(cfg, items)],
                                      og_type="article", photo="packed-suitcase")))
        lastmod[path] = "2026-11-03"


# ---------- pages ----------

def write(path, html):
    target = DOCS / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return path


def build():
    cfg = load_config()
    deals = load_deals()
    for d in deals:
        missing = [k for k in ("asin", "title", "category", "highlights", "added_at") if not d.get(k)]
        if missing:
            sys.exit("Error: deal %s is missing %s" % (d.get("asin", "?"), ", ".join(missing)))
        if d["category"] not in cfg["categories"]:
            sys.exit("Error: deal %s has unknown category %s" % (d["asin"], d["category"]))
    deals_by_asin = {d["asin"]: d for d in deals}
    articles = load_articles()
    articles_by_slug = {a["slug"]: a for a in articles}
    trips = load_articles(TRIPS_DIR) if TRIPS_DIR.exists() else []
    trips.sort(key=lambda t: -int(t.get("priority", 0)))  # "priority: 1" in front matter lists a trip first

    if DOCS.exists():
        for child in DOCS.iterdir():
            if child.name in KEEP_IN_DOCS:
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    DOCS.mkdir(exist_ok=True)
    shutil.copytree(STATIC_DIR, DOCS / "assets")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    pages = []
    lastmod = {}
    tg = telegram_url(cfg)

    PHOTOS.update(load_photos())
    for slot in [c.get("photo") for c in cfg["categories"].values()] + [a.get("photo") for a in articles]:
        if slot and slot not in PHOTOS:
            sys.exit("Error: photo %s is used but not listed in data/photos.json" % slot)
    airlines = load_airlines()
    intl_airlines = load_airlines(INTL_AIRLINES_FILE) if airlines else None
    DIAGRAMS.update(diagrams.build_all(airlines["airlines"] if airlines else [],
                                       fmt_date(airlines["checked"]) if airlines else ""))
    (DOCS / "assets" / "diagrams").mkdir()
    for name, (svg, alt, caption) in DIAGRAMS.items():
        (DOCS / "assets" / "diagrams" / (name + ".svg")).write_text(svg, encoding="utf-8")
    if airlines:
        TOOLS.append(("baggage/index.html", "Airline baggage rules", "IndiGo &middot; Air India &middot; Akasa &middot; SpiceJet",
                      "Baggage rules for Indian airlines", "Cabin bag size and weight, and free check-in baggage, all in one place.",
                      "See the rules", "plane", "travel-gear", BAGGAGE_PHOTO))
        TOOLS.append(("baggage/checker.html", "Cabin bag checker", "Free tool", "Will my bag fit? Cabin bag checker",
                      "Type your bag's size and weight and see which airlines accept it as a cabin bag.", "Check your bag", "ruler", "luggage", "plane-cabin"))
    if intl_airlines:
        TOOLS.append(("baggage/international.html", "International baggage rules", "Emirates &middot; Qatar &middot; Saudia &middot; Singapore",
                      "Baggage rules for international flights", "Cabin bag size and checked kg by fare for 12 airlines flying from India to the Gulf and Singapore.",
                      "See the rules", "plane", "luggage", "plane-window"))
    TOOLS.append(("baggage/luggage-size-chart.html", "Luggage size chart", "Inches &middot; cm &middot; kg &middot; lb",
                  "Luggage size chart: inches to cm", "20, 24 or 28 inch? Trolley sizes in cm, airline cabin limits in inches, and kg to pounds.",
                  "See the chart", "ruler", "travel-gear", "tape-measure"))
    if FLIGHT_ITEMS_FILE.exists():
        TOOLS.append(("baggage/can-i-carry.html", "Can I carry it on a flight?", "Free tool", "Can I carry it on a flight?",
                      "Power banks, perfume, pickles, dry coconut: see what goes in your cabin bag and what goes in check-in.",
                      "Search items", "shield", "watches", "baggage-belt"))
    if RAILWAYS_FILE.exists():
        TOOLS.append(("baggage/train-luggage-rules.html", "Train luggage rules", "Indian Railways",
                      "How much luggage can you carry on a train?", "Free luggage allowance for every class, size limits and charges.",
                      "See train rules", "train", "backpacks", "train-engine"))
    if HINDI_FILE.exists() and airlines and FLIGHT_ITEMS_FILE.exists() and RAILWAYS_FILE.exists():
        HINDI_PAGES.update(HINDI_PATHS)
    trips_hi = load_articles(TRIPS_HI_DIR) if TRIPS_HI_DIR.exists() else []
    for t in trips_hi:
        if (TRIPS_DIR / (t["slug"] + ".md")).exists():
            HINDI_PAGES["trips/%s.html" % t["slug"]] = "hi/trips/%s.html" % t["slug"]
    TOOLS.append(("tools/bag-weight.html", "Bag weight calculator", "Free tool", "How heavy is my bag?",
                  "Add what you're packing and see if your bag stays under 7 kg or 15 kg.", "Weigh it", "check", "luggage", "bathroom-scale"))
    TOOLS.append(("tools/laptop-backpack.html", "Backpack for my laptop", "Free tool", "Which backpack fits my laptop?",
                  "Pick your laptop size, from 13 to 17 inch, and see the backpacks that fit it.", "Find a backpack", "backpack", "backpacks", "backpack-field"))
    TOOLS.append(("tools/watch-size.html", "Watch size by wrist", "Free tool", "Which watch size suits my wrist?",
                  "Measure your wrist and see the dial sizes, in mm, that look right on it.", "Find my size", "watch", "watches", "watch-wrist"))
    if PACKING_FILE.exists():
        TOOLS.append(("packing/index.html", "Packing checklists", "Free checklist", "Packing checklists for every trip",
                      "Weekend, wedding, hills, beach, train or abroad: tick off what to pack, with quantities.",
                      "Start packing", "check", "travel-gear", "packed-suitcase"))

    # Home
    cat_tiles = "".join(
        f"""<a class="cat-tile" href="category/{slug}.html">
  {media(cfg, slug, 'media media-tile')}
  <div><h3>{e(c['name'])}</h3><p>{sum(1 for d in deals if d['category'] == slug)} picks</p></div>
  {icon("arrow", "icon icon-sm tile-arrow")}
</a>"""
        for slug, c in cfg["categories"].items()
    )
    if HERO_PHOTO in PHOTOS:
        hero_art = photo_figure(HERO_PHOTO, "", "(min-width: 760px) 42vw, 100vw", "photo hero-photo", eager=True)
    else:
        hero_art = '<div class="hero-art" aria-hidden="true">%s</div>' % "".join(
            f'<div class="hero-bubble tint-{slug}">{icon(c["icon"], "icon")}</div>' for slug, c in cfg["categories"].items())
    tg_cta = (f'<a class="btn btn-ghost" href="{e(tg)}" target="_blank" rel="noopener">{icon("send", "icon icon-sm")} Join on Telegram</a>'
              if tg else "")
    picks_html = grid(cfg, deals[:8], "") if deals else '<p class="muted">New picks are coming soon.</p>'
    fresh = sorted((d for d in deals if fresh_deal(d)), key=lambda d: d["deal_seen_at"], reverse=True)[:8]
    deals_html = ""
    if fresh:
        cards = "\n".join(card(cfg, d, "", deal_only=True) for d in fresh)
        deals_html = f"""<section class="wrap section" id="deals" data-deal-section hidden>
  {section_head("Deals spotted today")}
  <p class="muted small deal-intro">Amazon.in showed a deal on these picks in the last 24 hours. Deals can end at any time, so check today's price on Amazon.</p>
  <div class="grid">{cards}</div>
</section>"""
    baggage_promo = ""
    if TOOLS:
        cards = []
        for path, short, eyebrow, title, text, more, glyph, tint, slot in TOOLS:
            if slot in PHOTOS:
                art = '<div class="guide-art guide-photo">%s</div>' % photo_img(slot, "", "(min-width: 700px) 360px, 100vw", alt="")
            else:
                art = f'<div class="guide-art tint-{tint}">{icon(glyph, "icon guide-icon")}</div>'
            cards.append(f"""<a class="guide-card" href="{path}">
      {art}
      <div class="guide-body"><p class="eyebrow">{eyebrow}</p>
      <h3>{e(title)}</h3><p>{e(text)}</p>
      <span class="more">{e(more)} {icon("arrow", "icon icon-sm")}</span></div>
    </a>""")
        baggage_promo = f"""<section class="wrap section">
  {section_head("Free travel tools")}
  <div class="guide-grid">
    {"".join(cards)}
  </div>
</section>"""
    body = f"""<section class="hero">
  <div class="wrap hero-row">
    <div class="hero-copy">
      <p class="eyebrow eyebrow-light">Bags &middot; Luggage &middot; Watches &middot; Travel gear</p>
      <h1>Buy the right bag or watch, the first time.</h1>
      <p class="lead">Hand-picked products from Amazon India. We check size, material, weight and warranty, then explain it in simple words.</p>
      <div class="hero-ctas"><a class="btn btn-amazon btn-big" href="#latest">See latest picks</a>{tg_cta}</div>
    </div>
    {hero_art}
  </div>
</section>
<section class="trust">
  <div class="wrap trust-row">
    <div>{icon("ruler")}<p><strong>Details checked</strong>Size, litres, weight, warranty</p></div>
    <div>{icon("shield")}<p><strong>No paid rankings</strong>Brands can't pay to be listed</p></div>
    <div>{icon("pin")}<p><strong>Made for India</strong>College, office, flights and trains</p></div>
  </div>
</section>
<section class="wrap section">
  {section_head("Shop by category")}
  <div class="cat-grid">{cat_tiles}</div>
</section>
{deals_html}
<section class="wrap section" id="latest">
  {section_head("Latest picks")}
  {picks_html}
</section>
<section class="wrap section">
  {section_head("How we pick")}
  <ol class="steps">
    <li><span>1</span><h3>Read every detail</h3><p>We go through size, capacity, material, weight and warranty on Amazon.in.</p></li>
    <li><span>2</span><h3>Match real Indian use</h3><p>College commutes, office days, monsoon rain, domestic flight limits.</p></li>
    <li><span>3</span><h3>Explain it simply</h3><p>Short notes on who each product is best for, so you can decide fast.</p></li>
  </ol>
</section>
{baggage_promo}
{('<section class="wrap section">' + section_head("Trip guides", '<a class="see-all" href="trips/index.html">All trips ' + icon("arrow", "icon icon-sm") + '</a>') + trip_cards(trips[:3], "") + '</section>') if trips else ''}
{('<section class="wrap section">' + section_head("Buying guides", '<a class="see-all" href="guides/index.html">All guides ' + icon("arrow", "icon icon-sm") + '</a>') + guide_cards(cfg, articles[:3], "") + '</section>') if articles else ''}
{telegram_band(cfg, "")}"""
    home_schema = [{"@context": "https://schema.org", "@type": "WebSite", "name": cfg["site_name"],
                    "url": abs_url(cfg), "description": cfg["tagline"], "inLanguage": "en-IN",
                    "publisher": org_schema(cfg)}]
    pages.append(write("index.html", page(cfg, "", cfg.get("home_description", cfg["tagline"]), body, 0, "", home_schema, photo=HERO_PHOTO)))

    # Pick pages
    fit_dims = {d["asin"]: dims for d, dims, kg in cabin_picks(deals)} if airlines else {}
    for d in deals:
        cat = cfg["categories"][d["category"]]
        more = [x for x in deals if x["category"] == d["category"] and x["asin"] != d["asin"]][:4]
        features = "".join("<li>%s%s</li>" % (icon("check", "icon icon-check"), e(h)) for h in d["highlights"])
        note = f'<p class="lead">{e(d["note"])}</p>' if d.get("note") else ""
        brand = f'<p class="brand-name">{e(d["brand"])}</p>' if d.get("brand") else ""
        best = f'<div class="chips"><span class="chips-label">Best for</span>{chips(d["best_for"])}</div>' if d.get("best_for") else ""
        more_html = (f'<section class="wrap section">{section_head("More " + cat["name"])}{grid(cfg, more, "../")}</section>'
                     if more else "")
        specs_html = ""
        if d.get("specs"):
            rows = "".join("<tr><th scope=\"row\">%s</th><td>%s</td></tr>" % (e(k), e(v)) for k, v in d["specs"].items())
            specs_html = f'<h2>Specs</h2><table class="specs">{rows}</table>'
        skip_html = (f'<aside class="skip"><strong>Skip it if</strong><p>{e(d["skip_if"])}</p></aside>'
                     if d.get("skip_if") else "")
        fit_html = ""
        if d["asin"] in fit_dims:
            dims = fit_dims[d["asin"]]
            fit_rows = "".join(
                f'<tr><th scope="row"><a href="../baggage/{a["slug"]}.html">{e(a["name"])}</a>'
                f'<span class="why">{e(short_limit_text(a["cabin"]))}</span></th><td>{fit_badge(*size_fit(dims, a["cabin"])[::2])}</td></tr>'
                for a in airlines["airlines"])
            fit_html = f"""<h2>Will it fit as a cabin bag?</h2>
<p>Its listed size is {" x ".join(num(x) for x in dims)} cm, {num(sum(dims))} cm in total. Here's how that compares with each airline's cabin limit.</p>
<table class="specs">{fit_rows}</table>
<p class="small"><a href="../baggage/checker.html?bag={d['asin']}">Open it in the cabin bag checker</a> to add its packed weight. Always check your airline before you fly.</p>"""
        body = f"""<div class="wrap">
<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="../category/{d['category']}.html">{e(cat['name'])}</a></nav>
<article class="pick">
  <div class="pick-media">{media(cfg, d['category'], 'media media-xl')}{('<p class="media-brand">' + e(d['brand']) + '</p>') if d.get('brand') else ''}</div>
  <div class="pick-info">
    {brand}
    <h1>{e(d['title'])}</h1>
    {note}
    {best}
    <div class="cta-box">
      {deal_badge(d, "deal-note")}
      {buy_button(cfg, d, "Check today's price on Amazon", big=True)}
      <p>Prices and stock change often. Amazon.in shows the latest price.</p>
    </div>
    <h2>Key features</h2>
    <ul class="features">{features}</ul>
    {specs_html}
    {fit_html}
    {skip_html}
    {tip_box(cfg, d['category'], '../', articles_by_slug)}
    <p class="muted small">Added {fmt_date(d['added_at'])}</p>
  </div>
</article>
</div>
{more_html}
{telegram_band(cfg, "../")}"""
        features = "; ".join(h.rstrip(".") for h in d["highlights"][:2])
        desc = clip(" ".join(filter(None, [d.get("note"), "Key features: %s." % features,
                                           "See the specs, who it suits and who should skip it."])))
        path = "picks/%s.html" % d["asin"]
        crumbs = crumbs_schema(cfg, [("Home", ""), (cat["name"], "category/%s.html" % d["category"]), (d["title"], path)])
        pages.append(write(path, page(cfg, d["title"], desc, body, 1, path, [crumbs])))
        lastmod[path] = d["added_at"][:10]

    # Category pages
    for slug, cat in cfg["categories"].items():
        items = [d for d in deals if d["category"] == slug]
        related = [a for a in articles if a.get("category") == slug]
        items_html = grid(cfg, items, "../") if items else '<p class="muted">New picks are coming soon.</p>'
        related_html = (f'<section class="section">{section_head("Guides")}{guide_cards(cfg, related, "../")}</section>'
                        if related else "")
        inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>{e(cat['name'])}</nav>
      <h1>{e(cat['name'])}</h1>
      <p class="lead">{e(cat['intro'])}</p>"""
        body = f"""{page_head(slug, media(cfg, slug, 'media media-tile'), inner, "../", cat.get("photo"))}
<div class="wrap section">
  {tip_box(cfg, slug, '../', articles_by_slug)}
  {items_html}
  {related_html}
</div>
{telegram_band(cfg, "../")}"""
        desc = "Hand-picked %s from Amazon India. %s" % (cat["name"].lower(), cat["intro"])
        path = "category/%s.html" % slug
        crumbs = crumbs_schema(cfg, [("Home", ""), (cat["name"], path)])
        item_list = {"@context": "https://schema.org", "@type": "ItemList", "name": cat["name"], "itemListElement": [
            {"@type": "ListItem", "position": i, "url": abs_url(cfg, "picks/%s.html" % d["asin"]), "name": d["title"]}
            for i, d in enumerate(items, 1)]}
        schema = [crumbs, item_list] if items else [crumbs]
        pages.append(write(path, page(cfg, cat.get("seo_title", cat["name"]), desc, body, 1, path, schema, photo=cat.get("photo"))))

    # Guides
    body = f"""<section class="page-head">
  <div class="wrap"><h1>Buying guides</h1><p class="lead">Simple, honest guides to help you choose bags, luggage, watches and what to pack.</p></div>
</section>
<div class="wrap section">{guide_cards(cfg, articles, "../") if articles else '<p class="muted">Coming soon.</p>'}</div>"""
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Guides", "guides/index.html")])
    pages.append(write("guides/index.html", page(cfg, "Buying guides for bags, luggage, watches and travel essentials", "Simple buying guides for India: cabin bag rules, laptop backpacks, luggage sizes by trip length, your first analog watch and wedding gifts.",
                                                 body, 1, "guides/index.html", [crumbs])))
    for a in articles:
        content = render_markdown(a["body"], cfg, deals_by_asin, "../", a["slug"] + ".md")
        cat = a.get("category")
        art = media(cfg, cat, "media media-tile") if cat in cfg["categories"] else ""
        inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Guides</a></nav>
      <h1>{e(a['title'])}</h1>
      <p class="muted small">Updated {fmt_date(a['updated'])} &middot; {a['minutes']} min read</p>"""
        body = f"""{page_head(e(cat or 'none'), art, inner, "../", a.get("photo"))}
<div class="wrap"><article class="guide">{content}</article></div>
{telegram_band(cfg, "../")}"""
        path = "guides/%s.html" % a["slug"]
        image = photo_og(cfg, a["photo"]) if a.get("photo") in PHOTOS else abs_url(cfg, "assets/logo.png")
        article = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"],
                   "description": a["description"], "datePublished": a["date"], "dateModified": a["updated"],
                   "inLanguage": "en-IN", "image": image,
                   "mainEntityOfPage": abs_url(cfg, path), "author": org_schema(cfg), "publisher": org_schema(cfg)}
        crumbs = crumbs_schema(cfg, [("Home", ""), ("Guides", "guides/index.html"), (a["title"], path)])
        schema = [article, crumbs]
        faq = md_faq(a["body"])
        if faq:
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]})
        pages.append(write(path, page(cfg, a.get("seo_title", a["title"]), a["description"], body, 1, path,
                                      schema, og_type="article", photo=a.get("photo"))))
        lastmod[path] = a["updated"]

    if airlines:
        build_baggage(cfg, deals, airlines, pages, lastmod, intl_airlines)
    if PACKING_FILE.exists():
        build_packing(cfg, deals_by_asin, pages, lastmod, trips)
    if RAILWAYS_FILE.exists():
        build_railways(cfg, deals, pages, lastmod)
    if FLIGHT_ITEMS_FILE.exists():
        build_can_i_carry(cfg, pages, lastmod)
    build_size_chart(cfg, deals_by_asin, airlines, pages, lastmod, intl_airlines)
    build_tools(cfg, deals, pages, lastmod)
    if trips:
        build_trips(cfg, trips, deals_by_asin, pages, lastmod)
    if trips_hi:
        build_trips_hi(cfg, trips_hi, deals_by_asin, pages, lastmod)
    if HINDI_PAGES:
        build_hindi(cfg, deals, airlines, pages, lastmod)

    # Info pages
    name = e(cfg["site_name"])
    contact_lines = []
    if tg:
        contact_lines.append(f'<li>Telegram: <a href="{e(tg)}" target="_blank" rel="noopener">{e(cfg["telegram_channel"])}</a></li>')
    if cfg.get("whatsapp_channel"):
        contact_lines.append(f'<li>WhatsApp channel: <a href="{e(cfg["whatsapp_channel"])}" target="_blank" rel="noopener">CarryPick on WhatsApp</a></li>')
    if cfg["contact_email"]:
        contact_lines.append(f'<li>Email: <a href="mailto:{e(cfg["contact_email"])}">{e(cfg["contact_email"])}</a></li>')
    contact_html = "<ul>%s</ul>" % "".join(contact_lines) if contact_lines else "<p>Contact details are coming soon.</p>"
    photo_credits = ""
    if PHOTOS:
        photo_credits = ("<h2>Photos and diagrams</h2>\n<p>The photos on our home, category and guide pages are free stock photos "
                         "that set the scene. They are not photos of the products we pick. Our diagrams are drawn by us.</p>\n<ul>%s</ul>"
                         % "".join("<li>%s</li>" % photo_credit(slot) for slot in PHOTOS))
    info = {
        "about.html": ("About CarryPick: how we pick products", f"""<h1>About {name}</h1>
<p>{name} is a small team that helps shoppers in India pick good bags, luggage, watches and travel essentials on Amazon.in.</p>
<h2>How we choose products</h2>
<ul>
<li>We read the full product details: size, capacity, material, weight and warranty.</li>
<li>We pick products that suit everyday Indian use, like college, office commutes and domestic flights.</li>
<li>We never accept money from brands to list a product.</li>
</ul>
<p>We don't show prices because they change many times a day. The button on each pick takes you to Amazon.in, where you see the current price.</p>
{photo_credits}"""),
        "disclosure.html": ("Affiliate disclosure", f"""<h1>Affiliate disclosure</h1>
<p><strong>{DISCLOSURE}</strong></p>
<p>{name} is a participant in the Amazon Associates Programme. When you click a "Check price on Amazon" button and buy something, Amazon may pay us a small commission. You pay the same price.</p>
<p>Our trip guides also have hotel links to Agoda and Booking.com. These go through EarnKaro, an affiliate service. If you book through one, we may earn a commission, and you pay the same price. Amazon is not part of these links.</p>
<p>Links that earn us a commission are marked "Paid link". Commissions help us keep this site free. They do not change which products we pick.</p>"""),
        "privacy.html": ("Privacy policy", f"""<h1>Privacy policy</h1>
<p>{name} does not ask for your name, email or any personal details, and this site sets no cookies of its own, except one that remembers your language if you choose Google Translate (see below).</p>
<ul>
<li>This site is hosted on GitHub Pages. GitHub may keep basic server logs, such as IP addresses, for security. See GitHub's privacy statement.</li>
<li>Fonts are loaded from Google Fonts, which may log your IP address. See Google's privacy policy.</li>
<li>If you pick a language in the language menu other than English or our own Hindi pages, the page loads Google Translate, which sends the page text to Google to translate it. A cookie called "googtrans" then remembers your choice on this site. Pick English in the menu to remove it.</li>
<li>When you click a link to Amazon.in, Amazon may set cookies to track the referral. See Amazon.in's privacy notice.</li>
<li>When you click a hotel link in a trip guide, it goes through EarnKaro's link services (bitli.in and linkredirect.in) to the booking site. These services and the booking site may set cookies and log your visit to track the referral. See their privacy policies.</li>
<li>If you join our Telegram channel, Telegram's privacy policy applies.</li>
</ul>
<p>Questions? See our <a href="contact.html">contact page</a>.</p>"""),
        "contact.html": ("Contact", f"<h1>Contact</h1>\n<p>Have a question or found a mistake? Reach us here:</p>\n{contact_html}"),
        "404.html": ("Page not found", '<h1>Page not found</h1><p>This page has moved or no longer exists. <a href="index.html">Go to the home page</a>.</p>'
                     + tool_pills("", "")),
    }
    info_desc = {
        "about.html": "How %s picks bags, luggage, watches and travel essentials for India: we read every detail, match real Indian use and never take money from brands to list a product." % cfg["site_name"],
        "disclosure.html": "%s is an Amazon Associate. How our paid links work, what we earn and why it never changes which products we pick." % cfg["site_name"],
        "privacy.html": "%s asks for no personal details and sets no cookies of its own. What GitHub, Google Fonts, Amazon and our hotel link partners may log when you visit." % cfg["site_name"],
        "contact.html": "Questions, corrections or ideas for %s? Reach us on Telegram or WhatsApp." % cfg["site_name"],
    }
    for path, (title, text) in info.items():
        body = f'<div class="wrap"><article class="prose">{text}</article></div>'
        pages.append(write(path, page(cfg, title, info_desc.get(path, title + " - " + cfg["site_name"]), body, 0, path,
                                      robots="noindex" if path == "404.html" else "max-image-preview:large")))

    # Sitemap and robots (only once we know the live address)
    if cfg["base_url"]:
        base = cfg["base_url"].rstrip("/") + "/"
        def images(path):
            """Our photos and diagrams on a page, listed for Google Images."""
            text = (DOCS / path).read_text(encoding="utf-8")
            found = sorted(set(re.findall(r'assets/photos/[a-z0-9-]+-1600\.webp|assets/diagrams/[a-z0-9-]+\.svg', text)))
            return "".join("<image:image><image:loc>%s</image:loc></image:image>" % e(base + f) for f in found)

        urls = "".join("<url><loc>%s</loc>%s%s</url>" % (e(base + ("" if p == "index.html" else p)),
                                                         "<lastmod>%s</lastmod>" % lastmod[p] if p in lastmod else "", images(p))
                       for p in pages if p != "404.html")
        (DOCS / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">%s</urlset>\n' % urls,
            encoding="utf-8",
        )
        (DOCS / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % base, encoding="utf-8")
        if cfg.get("indexnow_key"):
            # Public key file that proves to IndexNow (Bing and others) that we own this site; see scripts/indexnow.py.
            (DOCS / (cfg["indexnow_key"] + ".txt")).write_text(cfg["indexnow_key"], encoding="utf-8")

    # Self-check: Amazon requires the disclosure everywhere, and no page may auto-redirect.
    for html_file in DOCS.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        if DISCLOSURE not in text:
            sys.exit("Error: disclosure missing on %s" % html_file)
        if re.search(r'http-equiv="refresh"|location\.(href|replace)', text, re.I):
            sys.exit("Error: auto-redirect found on %s" % html_file)
        if html_file.parent.name == "picks" and "assets/photos/" in text:
            sys.exit("Error: a stock photo is on pick page %s, where it could pass as the product" % html_file)

    print("Built %d pages (%d picks, %d guides) into docs/" % (len(pages), len(deals), len(articles)))


if __name__ == "__main__":
    build()
