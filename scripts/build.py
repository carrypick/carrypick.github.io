"""Build the static website into docs/ from data/ and content/.

Run:  python3 scripts/build.py
Amazon rules built in: disclosure on every page, no prices, no ratings,
no product images, no auto-redirects, buy links marked as paid.
Free stock photos (data/photos.json) only illustrate guides, categories and
the home page; pick pages and product cards never show them. Instead each pick
shows our own drawing, made from its listed size and details (scripts/pick_art.py).
"""

import json
import re
import shutil
import sys
import urllib.parse
from datetime import date, datetime, timedelta
from html import escape as e

import diagrams
import hindi_pages
import pick_art
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
COUPONS_FILE = ROOT / "data" / "coupons.json"  # tested shop coupons (VIP's CK15); the morning task updates "checked" and "status"
EXTRA_BAGGAGE_FILE = ROOT / "data" / "extra_baggage.json"  # excess baggage fees by airline (domestic)
CARRY_DIR = ROOT / "content" / "carry"  # one page per flight item; front matter 'item' names its row in flight_items.json
CUSTOMS_DIR = ROOT / "content" / "customs"  # Indian customs rules for passengers: index.md is the hub, the rest are item pages
HINDI_FILE = ROOT / "data" / "hindi.json"
STATIC_DIR = ROOT / "static"
PHOTO_DIR = STATIC_DIR / "photos"
HERO_PHOTO = "traveller-sunset"
BAGGAGE_PHOTO = "airport-terminal"
DEAL_HOURS = 24  # how long a "Deal spotted" badge shows (site.js hides it after this, and must match)
PHOTOS = {}    # filled by build() from data/photos.json
DIAGRAMS = {}  # filled by build() from scripts/diagrams.py
PICK_ART = {}  # ASIN -> (svg, alt), our drawing of each pick, filled by build() from scripts/pick_art.py
PICK_ART_DIR = STATIC_DIR / "picks"  # share images of the drawings, made by scripts/make_pick_images.py
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


def and_list(names):
    """["A", "B", "C"] -> "A, B and C"."""
    names = list(names)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


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
    if cfg.get("pinterest_url"):
        links.append('<li><a href="%s" target="_blank" rel="noopener">Pinterest</a></li>' % e(cfg["pinterest_url"]))
    return "".join(links)


# ---------- page shell ----------

def abs_url(cfg, path=""):
    return cfg["base_url"].rstrip("/") + "/" + path


def org_schema(cfg):
    same_as = [u for u in (telegram_url(cfg), cfg.get("whatsapp_channel"), cfg.get("pinterest_url")) if u]
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


def page(cfg, title, description, body, depth, path, schema=None, og_type="website", photo=None, robots="max-image-preview:large", lang="en",
         share_image=None):
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
        og = abs_url(cfg, share_image[0]) if share_image else (photo_og(cfg, photo) if photo in PHOTOS else None)
        if og:
            head_extra += ('<meta property="og:image" content="%s">\n<meta property="og:image:width" content="1200">\n'
                           '<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">'
                           % e(og))
            if share_image:
                head_extra += '\n<meta property="og:image:alt" content="%s">' % e(share_image[1])
        else:
            head_extra += '<meta property="og:image" content="%s/assets/logo.png">' % e(base)
    if cfg.get("google_site_verification"):
        head_extra += '\n<meta name="google-site-verification" content="%s">' % e(cfg["google_site_verification"])
    if cfg.get("pinterest_site_verification"):
        head_extra += '\n<meta name="p:domain_verify" content="%s">' % e(cfg["pinterest_site_verification"])
    if cfg.get("base_url"):
        head_extra += '\n<link rel="alternate" type="application/atom+xml" title="%s guides" href="%s/feed.xml">' % (e(cfg["site_name"]), e(cfg["base_url"].rstrip("/")))
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


def pick_img(deal, p, eager=False):
    """Our own drawing of a pick (never a product photo). Width and height stop the layout from jumping."""
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<img src="{p}assets/picks/{deal["asin"]}.svg" width="{pick_art.W}" height="{pick_art.H}" '
            f'alt="{e(PICK_ART[deal["asin"]][1])}" {load}>')


def share_image(asin):
    """The 1200 x 630 share image of a pick's drawing, if scripts/make_pick_images.py has made one."""
    found = sorted(PICK_ART_DIR.glob(asin + "-*.jpg")) if PICK_ART_DIR.exists() else []
    return ("assets/picks/" + found[-1].name, PICK_ART[asin][1]) if found else None


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
    if info.get("commons"):  # Wikimedia Commons photos need the author, the licence and the file page
        return (f'Photo: <a href="{e(info["profile"])}" target="_blank" rel="noopener">{e(info["credit"])}</a>, '
                f'<a href="{e(info["license_url"])}" target="_blank" rel="noopener">{e(info["license"])}</a>, via '
                f'<a href="{e(info["page"])}" target="_blank" rel="noopener">Wikimedia Commons</a>')
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
  <a class="card-media" href="{href}" tabindex="-1" aria-hidden="true"><span class="art tint-{deal['category']}">{pick_img(deal, p)}</span>{badge}{deal_badge(deal)}</a>
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
  <a class="art inline-art tint-{deal['category']}" href="{p}picks/{deal['asin']}.html" tabindex="-1" aria-hidden="true">{pick_img(deal, p)}</a>
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


TOP_PICKS_TITLE = "Our picks for this size"


def top_picks(cfg, rows, p, title=TOP_PICKS_TITLE, more=""):
    """A short list near the top of a page: one pick per need, a one-line reason each and the Amazon button.
    rows: (deal, label, reason). more: optional HTML for a link under the list."""
    if not rows:
        return ""
    items = "".join(f"""<li class="tp">
  <a class="tp-art art tint-{d['category']}" href="{p}picks/{d['asin']}.html" tabindex="-1" aria-hidden="true">{pick_img(d, p)}</a>
  <div class="tp-body">
    <p class="tp-label">{e(label)}</p>
    <h3 class="tp-title"><a href="{p}picks/{d['asin']}.html">{e(d['title'])}</a></h3>
    <p class="tp-why">{e(reason)}</p>
    <div class="tp-buy">{buy_button(cfg, d)}</div>
  </div>
</li>""" for d, label, reason in rows)
    more_html = f'<p class="tp-more">{more}</p>' if more else ""
    return f'<section class="top-picks"><h2>{e(title)}</h2><ul class="tp-list">{items}</ul>{more_html}</section>'


def next_step(links, title="Next step", text=""):
    """A box at the end of a page that says where to go next. links: (href, label)."""
    items = "".join(f'<li><a href="{e(href)}">{e(label)} {icon("arrow", "icon icon-sm")}</a></li>' for href, label in links)
    text_html = f"<p>{text}</p>" if text else ""
    return f'<aside class="next-step"><h2>{e(title)}</h2>{text_html}<ul>{items}</ul></aside>'


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


def booking_box(cfg, place, hindi=False):
    """Hand-placed hotel links (EarnKaro). Trip guides only, never next to Amazon picks."""
    label = "{name} पर {place} के होटल देखें" if hindi else "Search {place} on {name}"
    note = ("कीमत और कमरे बुकिंग साइट पर दिखते हैं। हमने हर होटल की जाँच नहीं की है, इसलिए पहले हाल के रिव्यू पढ़ें।" if hindi else
            "Prices and rooms are shown on the booking site. We have not checked each hotel, so read recent reviews first.")
    links = "".join(f'<div class="book-row"><a class="btn btn-amazon" href="{e(url)}" {BUY_ATTRS}>{e(label.format(name=name, place=place))}</a><span class="paid">Paid link</span></div>'
                    for name, url in cfg["booking_partners"].items())
    return f'<div class="cta-box">{links}<p>{note}</p></div>'


def shop_box(cfg, shop):
    """Hand-placed link to a shop's own site (EarnKaro). Only on pages with no Amazon picks."""
    return (f'<div class="cta-box"><div class="book-row"><a class="btn btn-amazon" href="{e(cfg["shop_partners"][shop])}" {BUY_ATTRS}>Visit {e(shop)}</a>'
            f'<span class="paid">Paid link</span></div><p>Prices and stock are shown on the shop\'s own site. We have not tested these products.</p></div>')


def anchor(text):
    """An id for a heading, so other pages and our pick boxes can link straight to a section."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text).replace("**", "")
    return re.sub(r"[^a-z0-9\u0900-\u0963\u0966-\u097f]+", "-", text.lower()).strip("-")  # Devanagari kept for Hindi headings


def flight_box(cfg, place=None, scope="domestic", hindi=False):
    """Hand-placed flight links (EarnKaro): Cleartrip for any airline, plus airlines that pay only on international
    bookings. Trip guides and the international baggage hub only, never next to Amazon picks."""
    partners = [(name, f["url"]) for name, f in cfg["flight_partners"].items() if scope in f["scope"]]
    if hindi:
        label = "{name} पर {place} की फ़्लाइट देखें" if place else "{name} पर फ़्लाइट देखें"
        note = "किराया और सीटें बुकिंग साइट पर दिखती हैं। पैसे देने से पहले देखें कि आपके किराए में कितना सामान शामिल है।"
    else:
        label = "Compare flights to {place} on {name}" if place else "Check fares on {name}"
        note = ("Fares and seats are shown on the booking site. Before you pay, check how much baggage your fare includes."
                if scope == "domestic" else
                "Cleartrip shows fares from many airlines. The other links go to the airline's own website. "
                "Before you pay, check how much baggage your fare includes.")
    links = "".join(f'<div class="book-row"><a class="btn btn-amazon" href="{e(url)}" {BUY_ATTRS}>{e(label.format(name=name, place=place))}</a><span class="paid">Paid link</span></div>'
                    for name, url in partners)
    return f'<div class="cta-box">{links}<p>{note}</p></div>'


def load_coupons():
    """data/coupons.json: shop name -> code, discount, status ("working" or "ended"), checked (last test date),
    brands and brands_checked. Pages never write a code themselves; they use the tokens below, so an ended code
    disappears everywhere when the morning task sets its status to "ended"."""
    if not COUPONS_FILE.exists():
        return {}
    coupons = json.loads(COUPONS_FILE.read_text(encoding="utf-8"))
    coupons.pop("_note", None)
    for shop, c in coupons.items():
        if c.get("status") not in ("working", "ended") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", c.get("checked", "")):
            sys.exit("Error: data/coupons.json: %s needs status working or ended, and checked YYYY-MM-DD" % shop)
    return coupons


def coupon_text(coupons, kind, shop):
    """Inline coupon text for {{coupon-<kind>:<shop>}} tokens."""
    if shop not in coupons:
        sys.exit("Error: {{coupon-%s:%s}} names a shop that is not in data/coupons.json" % (kind, shop))
    c = coupons[shop]
    ok = c["status"] == "working"
    checked = fmt_date(c["checked"])
    texts = {
        "checked": checked,
        "short": ("%s for %s off" % (c["code"], c["discount"])) if ok else "no working code right now",
        "line": ("Code **%s** took %s off in %s's cart when we last checked, on %s. Coupons can end at any time, so check the discount before you pay."
                 % (c["code"], c["discount"], c.get("cart", shop), checked)) if ok else
                ("We have no working code right now. The last code we tested stopped working when we checked on %s." % checked),
        "brands": ("When we tested %s on %s, it took %s off %s bags on %s's website." % (c["code"], fmt_date(c["brands_checked"]), c["discount"], c["brands"], c.get("cart", shop)))
                  if ok else "We have no working code right now.",
    }
    if kind not in texts:
        sys.exit("Error: unknown coupon token {{coupon-%s:%s}}" % (kind, shop))
    return texts[kind]


def coupon_box(coupons, shop):
    """[[coupon:<shop>]]: the code, when we last tested it, and that it may end. Only on pages with no Amazon picks."""
    if shop not in coupons:
        sys.exit("Error: [[coupon:%s]] names a shop that is not in data/coupons.json" % shop)
    c = coupons[shop]
    if c["status"] != "working":
        return (f'<div class="cta-box coupon-box"><p><strong>No working code right now.</strong> The last code we tested '
                f'stopped working when we checked on {fmt_date(c["checked"])}.</p></div>')
    return (f'<div class="cta-box coupon-box"><p class="coupon-line"><span class="coupon-code notranslate">{e(c["code"])}</span>'
            f'<span><strong>{e(c["discount"])} off</strong> in {e(c.get("cart", shop))}\'s cart</span></p>'
            f'<p>Checked on <strong>{fmt_date(c["checked"])}</strong>: we added a bag to an empty cart on {e(c.get("cart", shop))}\'s website and typed the code. '
            f'We never place an order, and we empty the cart afterwards. Coupons can end at any time, so check the discount before you pay.</p></div>')


def render_markdown(md, cfg, deals_by_asin, p, source):
    if "[[shop:" in md and ("[[pick:" in md or "[[compare:" in md or "[[top:" in md):
        sys.exit("Error: %s mixes a [[shop:]] link with Amazon picks. Keep other shops' links away from Amazon picks." % source)
    if "[[coupon:" in md and ("[[pick:" in md or "[[compare:" in md or "[[top:" in md):
        sys.exit("Error: %s mixes a coupon with Amazon picks. Coupon text must never sit on a page with Amazon picks." % source)
    out, para, items, list_tag, rows = [], [], [], None, []
    tops, top_head = [], None  # [[toppicks:Title|More link text|#anchor]] then one [[top:ASIN|Label|Reason]] line per pick

    def flush():
        nonlocal para, items, list_tag, rows, tops, top_head
        if tops:
            title, more_text, more_href = (list(top_head or []) + ["", "", ""])[:3]
            more = '<a href="%s">%s</a>' % (e(more_href), e(more_text)) if more_text and more_href else ""
            out.append(top_picks(cfg, tops, p, title or TOP_PICKS_TITLE, more))
            tops, top_head = [], None
        if rows:
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows if not re.fullmatch(r"[\s|:-]+", r)]
            head = "".join("<th>%s</th>" % md_inline(c, p) for c in cells[0])
            body = "".join("<tr>%s</tr>" % "".join(("<th scope=\"row\">%s</th>" if i == 0 else "<td>%s</td>") % md_inline(c, p)
                                                    for i, c in enumerate(r)) for r in cells[1:])
            out.append('<div class="table-wrap"><table class="compare snug"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body))
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
        shop = re.fullmatch(r"\[\[shop:([^\]]+)\]\]", line)
        fly = re.fullmatch(r"\[\[fly:([^\]]+)\]\]", line)
        coupon = re.fullmatch(r"\[\[coupon:([^\]]+)\]\]", line)
        toppicks = re.fullmatch(r"\[\[toppicks:([^\]]+)\]\]", line)
        top = re.fullmatch(r"\[\[top:([A-Z0-9]{10})\|([^|\]]+)\|([^\]]+)\]\]", line)
        nxt = re.fullmatch(r"\[\[next:([^\]]+)\]\]", line)
        ul = re.match(r"^- (.+)", line)
        ol = re.match(r"^\d+\. (.+)", line)
        if not line:
            flush()
        elif line.startswith("|"):
            if para or items:
                flush()
            rows.append(line)
        elif shop:
            flush()
            out.append(shop_box(cfg, shop.group(1)))
        elif fly:
            flush()
            where = fly.group(1)
            out.append(flight_box(cfg, None if where == "flights" else where, "domestic", source.startswith("trips-hi")))
        elif coupon:
            flush()
            out.append(coupon_box(load_coupons(), coupon.group(1)))
        elif toppicks:
            flush()
            top_head = [x.strip() for x in toppicks.group(1).split("|")]
        elif top:
            if para or items or rows:
                flush()
            deal = deals_by_asin.get(top.group(1))
            if deal is None:
                sys.exit("Error: %s uses [[top:%s]] but that ASIN is not in data/deals.json" % (source, top.group(1)))
            tops.append((deal, top.group(2).strip(), top.group(3).strip()))
        elif nxt:
            flush()
            links = [x.split("=", 1) for x in nxt.group(1).split("|")]
            if any(len(x) != 2 for x in links):
                sys.exit("Error: %s has a [[next:]] link without path=Label" % source)
            out.append(next_step([(h.strip(), t.strip()) for h, t in links]))
        elif diagram:
            flush()
            out.append(diagram_figure(diagram.group(1), p))
        elif booking:
            flush()
            out.append(booking_box(cfg, booking.group(1), source.startswith("trips-hi")))
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
            out.append('<h2 id="%s">%s</h2>' % (anchor(line[3:]), md_inline(line[3:], p)))
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
        coupons = load_coupons()
        for shop, c in coupons.items():
            if re.search(r"\b%s\b" % re.escape(c["code"]), text):
                sys.exit("Error: %s writes the code %s. Use {{coupon-line:%s}} or [[coupon:%s]] so it updates from data/coupons.json." % (path.name, c["code"], shop, shop))
        if "{{coupon-" in text or "[[coupon:" in text:
            if any(tag in meta["body"] for tag in ("[[pick:", "[[compare:", "[[top:")):
                sys.exit("Error: %s has coupon text and Amazon picks. Keep coupons off pages with Amazon picks." % path.name)
            used = set(re.findall(r"\{\{coupon-[a-z]+:([^}]+)\}\}", text)) | set(re.findall(r"\[\[coupon:([^\]]+)\]\]", text))
            for key in ("title", "seo_title", "description", "body"):
                if key in meta:
                    meta[key] = re.sub(r"\{\{coupon-([a-z]+):([^}]+)\}\}", lambda m: coupon_text(coupons, m.group(1), m.group(2)), meta[key])
            meta["updated"] = max([meta["updated"]] + [coupons[s_]["checked"] for s_ in used if s_ in coupons])
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
        glance_html = ('<div class="answer"><h2>%s at a glance</h2><div class="table-wrap"><table class="compare snug glance"><tbody>%s</tbody></table></div></div>'
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
        glance_html = ('<div class="answer"><h2>%s एक नज़र में</h2><div class="table-wrap"><table class="compare snug glance"><tbody>%s</tbody></table></div></div>'
                       % (e(t.get("place", t["title"])), "".join('<tr><th scope="row">%s</th><td>%s</td></tr>' % (e(k.strip()), md_inline(v.strip(), p))
                                                                  for k, v in glance))) if glance else ""
        inner = f"""<nav class="crumbs"><a href="{p}index.html">होम</a><span>/</span><a href="{p}trips/index.html">Trip guides</a><span>/</span>{e(t.get("place", t["title"]))}</nav>
      <h1>{e(t['title'])}</h1>
      <p class="muted small">{hi_date(t['updated'])} को अपडेट किया गया</p>{hindi_pages.hinglish_line(t)}"""
        art = f'<div class="media media-tile tint-travel-gear">{icon("pin", "icon media-icon")}</div>'
        hindi_pages.check_twin(sys.modules[__name__], t, TRIPS_DIR, "content/trips-hi/%s.md" % t["slug"])
        body = f"""{page_head("travel-gear", art, inner, p, t.get("photo"))}
<div class="wrap"><article class="guide">
{glance_html}
{content}
{hindi_pages.tool_links(sys.modules[__name__], path, p)}
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


def possessive(name):
    """'Thai Airways' -> "Thai Airways'", 'IndiGo' -> "IndiGo's"."""
    return name + ("'" if name.endswith("s") else "'s")


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


def litres(deal):
    m = re.search(r"(\d+(?:\.\d+)?)\s*L\b", deal.get("specs", {}).get("Capacity", ""))
    return float(m.group(1)) if m else 0


def airline_top_rows(name, cabins, picks):
    """Up to three of our picks that fit every cabin limit in `cabins` by listed size: a trolley, the backpack
    with the most litres and the lightest backpack. Each gets a short reason from its listed size and weight."""
    fits = [(d, dims, kg) for d, dims, kg in picks if all(size_fit(dims, c)[0] for c in cabins)]
    limit = min((c["kg"] for c in cabins if c.get("kg")), default=None)
    size = lambda dims: " x ".join(num(x) for x in sorted(dims, reverse=True))
    kgs = lambda kg: "%g" % kg
    whose = name + ("'" if name.endswith("s") else "'s")
    left = lambda kg: (", so about %s kg of the %s kg limit is left for your things" % (num(round(limit - kg, 1)), num(limit))
                       if kg is not None and limit and limit > kg else "")
    rows, used = [], set()
    trolley = next(((d, dims, kg) for d, dims, kg in fits if d["category"] == "luggage"), None)
    if trolley:
        d, dims, kg = trolley
        rows.append((d, "Cabin trolley", "Listed at %s cm, within %s limit. %s kg empty%s." % (size(dims), whose, kgs(kg), left(kg))
                     if kg is not None else "Listed at %s cm, within %s limit." % (size(dims), whose)))
        used.add(d["asin"])
    bags = [x for x in fits if x[0]["category"] == "backpacks" and x[0]["asin"] not in used]
    roomy = max(bags, key=lambda x: (litres(x[0]), -(x[2] or 9)), default=None)
    if roomy and litres(roomy[0]):
        d, dims, kg = roomy
        rows.append((d, "Most room in a backpack", "%s litres, the biggest of our backpacks that fit %s by listed size (%s cm)." % (
            num(litres(d)), name, size(dims))))
        used.add(d["asin"])
    light = min((x for x in bags if x[2] is not None and x[0]["asin"] not in used), key=lambda x: x[2], default=None)
    if light:
        d, dims, kg = light
        rows.append((d, "Lightest backpack", "Only %s kg empty%s. Listed at %s cm." % (kgs(kg), left(kg), size(dims))))
    return rows


def load_airlines(path=AIRLINES_FILE):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for a in data["airlines"]:
        missing = [k for k in ("slug", "name", "official_url", "cabin", "checkin", "sources") if not a.get(k)]
        if missing:
            sys.exit("Error: airline %s is missing %s" % (a.get("slug", "?"), ", ".join(missing)))
    return data


# Where the international airlines fly from India, by their "region" field (hub lead and descriptions).
INTL_REGIONS = [("Gulf", "the Gulf", "the Gulf (Dubai, Doha, Abu Dhabi, Sharjah, Jeddah, Muscat, Bahrain, Kuwait)"),
                ("Asia", "Asia", "South-East and East Asia (Singapore, Bangkok, Kuala Lumpur, Vietnam, Hong Kong)"),
                ("Europe", "Europe", "Europe and the UK (London, Frankfurt, Munich, Istanbul)")]


def intl_where(airlines, long=False):
    """'the Gulf and Asia' (or the long form with cities) for the regions these airlines cover."""
    parts = [(lng if long else short) for key, short, lng in INTL_REGIONS if any(a.get("region") == key for a in airlines)]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def intl_checked(intl):
    """(first, last) date any international airline was checked; an airline's own 'checked' wins over the file's."""
    dates = [a.get("checked", intl["checked"]) for a in intl["airlines"]]
    return min(dates), max(dates)


def build_intl_hub(cfg, intl, picks, pages, lastmod, head, disclaimer, checker_cta, scale_link):
    """baggage/international.html: economy baggage on international flights from India (data/airlines_intl.json)."""
    airlines = intl["airlines"]
    first, checked = intl_checked(intl)
    when = ("Checked on " + fmt_date(checked)) if first == checked else ("Checked between %s and %s" % (fmt_date(first), fmt_date(checked)))
    slugs = {a["slug"] for a in airlines}
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
        ("What is the maximum weight of one checked bag?", "32 kg on every airline here, even if your total allowance is higher. On Saudia and Kuwait Airways economy, each piece is 23 kg."
         + (" Thai Airways economy bags are 23 kg each too." if "thai-airways" in slugs else "")),
    ]
    if "thai-airways" in slugs:
        faq.insert(1, ("How much baggage can I take from India to Bangkok?",
                       "On Thai Airways, one 23 kg bag on Saver and Standard fares and two 23 kg bags on Flexi and Full Flex, plus a 7 kg cabin bag. "
                       "IndiGo gives 20 kg to Bangkok and Phuket on regular fares (25 kg on UpFront)."))
    if {"british-airways", "lufthansa"} <= slugs:
        faq.insert(1, ("How much baggage can I take from India to the UK or Europe?",
                       "In Economy, British Airways and Lufthansa each include one checked bag of up to 23 kg (none on BA's Basic or Lufthansa's Light fares), "
                       "plus a cabin bag and a small personal item. Heavier bags, up to 32 kg, cost extra."))
    if "vietjet" in slugs:
        faq.insert(2, ("Does Vietjet include checked baggage from India?",
                       "Not on Eco fares: you get only 7 kg of cabin baggage and buy checked bags separately, cheapest with your ticket. "
                       "Deluxe includes 20 kg and SkyBoss 30 kg."))
    faq_html, faq_schema = faq_block(faq)
    trip_lists = [(slug, place) for slug, place in (("thailand", "Thailand"), ("dubai", "Dubai"), ("bali", "Bali"))
                  if (ARTICLES_DIR / ("%s-packing-list.md" % slug)).exists()]
    packing_abroad = ("<p>Packing for the trip? See our packing lists for %s.</p>" % and_list(
        ['<a href="../guides/%s-packing-list.html">%s</a>' % (slug, place) for slug, place in trip_lists])) if trip_lists else ""
    title = "Baggage rules for international flights from India"
    seo = "International baggage allowance from India %s: Emirates, Qatar, Thai, IndiGo, Air India" % checked[:4]
    desc = ("Cabin bag size and checked baggage by fare for %d airlines on flights from India to %s, "
            "including Emirates, Qatar Airways, Saudia, IndiGo and Air India. Checked against official websites, %s." % (
                len(airlines), intl_where(airlines), fmt_date(checked)))
    pieces = "Kuwait Airways counts pieces (2 x 23 kg on Economy)" + (
        ", and so does Thai Airways since March 2026 (one or two 23 kg bags)" if "thai-airways" in slugs else "") + (
        ". British Airways and Lufthansa give Economy one 23 kg bag" if {"british-airways", "lufthansa"} <= slugs else "")
    no_bag = (["Etihad Basic", "flydubai Lite", "Air Arabia Basic", "IndiGo Lite", "Kuwait Airways Zero Bag"] + (["Vietjet Eco"] if "vietjet" in slugs else [])
              + (["British Airways Basic"] if "british-airways" in slugs else []) + (["Lufthansa Economy Light"] if "lufthansa" in slugs else []))
    body = f"""{head(title, '<a href="index.html">Baggage rules</a><span>/</span>International', when + " against each airline's official website &middot; economy, India routes", BAGGAGE_PHOTO)}
<div class="wrap"><article class="guide">
<p class="lead">Economy baggage on flights between India and {e(intl_where(airlines, long=True))}, in one place. Tap an airline for the full rules, infant allowance and tips.</p>
{checker_cta}
<h2>Cabin and checked baggage at a glance</h2>
<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Cabin bag</th><th>Cabin size limit</th><th>Extra small bag</th><th>Checked baggage (economy)</th></tr></thead><tbody>{rows}</tbody></table></div>
{disclaimer}
<p>Still choosing a flight? Compare fares, then check the baggage your fare includes before you pay:</p>
{flight_box(cfg, None, "international") if cfg.get("flight_partners") else ""}
<h2>Rules that catch travellers out</h2>
<ul>
<li><strong>32 kg per bag.</strong> Even with a 35 or 40 kg allowance, no single bag can weigh more than 32 kg. Split heavy luggage into two bags.</li>
<li><strong>Weight or pieces?</strong> Most airlines here count your total kg. {pieces}. Saudia's economy bags are 23 kg each. Some airlines also limit the number of bags: IndiGo 2, Air Arabia 2, flydubai 3.</li>
<li><strong>Bags need a flat side.</strong> Qatar Airways and Gulf Air refuse round bags and bundles tied with rope or wrapped in blankets. Emirates and flydubai ask you to repack odd-shaped items in a box, and Muscat airport charges extra for them.</li>
<li><strong>Power banks stay in the cabin.</strong> Most of these airlines don't allow using or charging power banks on board, and Qatar Airways bans charging them. Never pack one in a checked bag.</li>
<li><strong>Cheap fares may have no checked bag.</strong> {", ".join(no_bag[:-1])} and {no_bag[-1]} include only a cabin bag. Buying extra baggage online before you fly is much cheaper than at the airport.</li>
<li><strong>Medicines into the UAE.</strong> Controlled medicines need approval from the UAE health ministry before you travel. Carry the prescription.{(' See <a href="customs/uae-dubai.html">what you can carry from India to Dubai</a>.') if (CUSTOMS_DIR / "uae-dubai.md").exists() else ''}</li>
<li><strong>Keep gold, cash and documents with you.</strong> flydubai says not to pack money, jewellery or precious metals in checked bags.</li>
</ul>
{('<p><strong>Flying back into India?</strong> Indian Customs allows goods worth ₹75,000 per person duty free since February 2026, plus 2 litres of alcohol. '
  'Gold, iPhones and cash have their own limits: see our <a href="customs.html">Indian customs rules</a>.</p>') if CUSTOMS_DIR.exists() else ''}
<h2>Do our cabin picks fit?</h2>
<p>Based on the size listed on Amazon. Gulf Air's and Qatar Airways' limits are the hardest to meet, so a backpack is often the safest cabin bag.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Our pick</th>{matrix_head}</tr></thead><tbody>{matrix_rows}</tbody></table></div>
<p>Weigh your packed bags at home with a {scale_link}, and try our <a href="../tools/bag-weight.html">bag weight calculator</a>.</p>
{faq_html}
<p>Buying a check-in bag for this trip? See <a href="../guides/trolley-bag-size-for-international-travel.html">which trolley size fits a 23 kg bag and the 158 cm limit</a>.</p>
{packing_abroad}
<h2>Flying within India?</h2>
<p>Domestic allowances are smaller: usually a 7 kg cabin bag and 15 kg of check-in baggage. See our <a href="index.html">baggage rules for Indian airlines</a>.</p>
{tool_pills("../", "baggage/international.html")}
</article></div>
{telegram_band(cfg, "../")}"""
    path = "baggage/international.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("International", path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, [tool_article(cfg, seo, desc, path, intl["checked"], checked), crumbs, faq_schema],
                                  og_type="article", photo=BAGGAGE_PHOTO)))
    lastmod[path] = checked


def extra_section(a, extra_by_slug):
    """Short 'Extra baggage charges' block on a domestic airline page, linking to its fees page."""
    x = extra_by_slug.get(a["slug"])
    if not x or a.get("scope") == "international":
        return ""
    summary = prepaid_summary(x)
    return (f'<h2>Extra baggage charges</h2><ul>'
            f'<li><strong>Prepaid online:</strong> {e(summary) if summary else "not listed (Air India says up to 20% less than the airport rate)"}.</li>'
            f'<li><strong>At the airport:</strong> {e(x["airport_text"])}.</li>'
            f'<li><strong>Extra bag:</strong> {e(x.get("piece_short", "see the fees page"))}.</li>'
            f'<li><strong>Cabin bag over 7 kg:</strong> {e(x.get("cabin_short", "see the fees page"))}.</li></ul>'
            f'<p>See every slab and rule on <a href="extra-baggage-charges/{x["slug"]}.html">{e(a["name"])} extra baggage charges</a>.</p>')


def build_baggage(cfg, deals, data, pages, lastmod, intl=None, extra=None):
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

    def article_schema(title, desc, path, photo=None, modified=None):
        image = photo_og(cfg, photo) if photo in PHOTOS else abs_url(cfg, "assets/logo.png")
        return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
                "datePublished": min(data.get("published", checked), modified or checked), "dateModified": modified or checked, "inLanguage": "en-IN",
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
    join_names = lambda names: names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    hub_rows = []
    for d, dims, kg in picks:
        names = [a["name"] for a in airlines if size_fit(dims, a["cabin"])[0]]
        if d["category"] == "luggage" and names:
            hub_rows.append((len(names), d, "Cabin trolley for " + join_names(names), "Listed at %s cm%s." % (
                " x ".join(num(x) for x in sorted(dims, reverse=True)), (", %g kg empty" % kg) if kg is not None else "")))
    hub_rows = [r[1:] for r in sorted(hub_rows, key=lambda r: -r[0])]
    hub_rows += [(d, "Backpack that fits all %d airlines" % len(airlines), why)
                 for d, label, why in airline_top_rows("all %d airlines" % len(airlines), [a["cabin"] for a in airlines], picks)
                 if label == "Most room in a backpack"]
    hub_picks = top_picks(cfg, hub_rows, "../", "Cabin bags that fit by their listed size",
                          '<a href="#our-picks-fit">See all our picks against each airline</a>')
    body = f"""{head(title, "Baggage rules", "Checked on " + fmt_date(checked) + " against each airline's official website", BAGGAGE_PHOTO)}
<div class="wrap"><article class="guide">
<p class="lead">Domestic economy limits for India's main airlines, in one place. Tap an airline for the full rules, fare types and tips.</p>
{('<p>Flying abroad? See the <a href="international.html">international baggage rules</a> for Emirates, Qatar Airways, Thai Airways, Singapore Airlines, IndiGo, Air India and more, on flights from India.</p>') if intl_airlines else ''}
{('<p>Flying back into India? See the <a href="customs.html">Indian customs rules</a>: the ₹75,000 duty-free allowance, gold, alcohol and cash limits.</p>') if CUSTOMS_DIR.exists() else ''}
{checker_cta}
<h2>Cabin and check-in baggage at a glance</h2>
<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Cabin bag</th><th>Cabin size limit</th><th>Extra small bag</th><th>Free check-in (domestic)</th></tr></thead><tbody>{rows}</tbody></table></div>
{disclaimer}
{hub_picks}
<h2>Cabin bag limits side by side</h2>
{limits_fig}
<h2 id="our-picks-fit">Do our cabin picks fit?</h2>
<p>Many "55 cm" cabin trolleys are a little bigger than the limits once you add up all three sides. A backpack is often the safest cabin bag. Here's how our picks compare, using the size listed on Amazon.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Our pick</th>{matrix_head}</tr></thead><tbody>{matrix_rows}</tbody></table></div>
<h2>How to avoid extra baggage charges</h2>
<ul>
<li><strong>Measure with wheels and handles.</strong> Airlines measure the whole bag, not just the shell.</li>
<li><strong>Weigh it at home.</strong> A {scale_link} costs less than one excess-baggage fee.</li>
<li><strong>Remember the bag's own weight.</strong> A hard cabin trolley often weighs 2.5–3 kg of your 7 kg.</li>
<li><strong>Check your fare.</strong> Some cheap fares include cabin baggage only.</li>
</ul>
{('<p>Already over the limit? Compare <a href="extra-baggage-charges.html">extra baggage charges by airline</a>: prepaid slabs, the airport rate per kg and fees for heavy cabin bags.</p>') if extra else ''}
{next_step([("../guides/cabin-luggage-guide.html#our-cabin-bag-picks", "Cabin trolleys we picked, and the airlines each one fits"),
            ("luggage-size-chart.html", "Trolley bag sizes in cm and inches"),
            ("../guides/luggage-size-guide.html", "What size luggage you need for your trip"),
            ("checker.html", "Check your own bag against every airline")], "Shop by size")}
{tool_pills("../", "baggage/index.html")}
</article></div>
{telegram_band(cfg, "../")}"""
    path = "baggage/index.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), (title, path)])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path, [article_schema(seo, desc, path, BAGGAGE_PHOTO), crumbs],
                                  og_type="article", photo=BAGGAGE_PHOTO)))
    lastmod[path] = checked

    # One page per airline
    extra_by_slug = {x["slug"]: x for x in extra["airlines"]} if extra else {}
    for a in airlines + intl_airlines:
        abroad = a.get("scope") == "international"
        a_checked = a.get("checked") or (intl["checked"] if abroad else checked)
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
        fees = extra_by_slug.get(a["slug"]) if not abroad else None
        if fees:
            summary = prepaid_summary(fees)
            faq.append(("What are %s extra baggage charges?" % a["name"],
                        "On domestic flights, %s charges %s at the airport%s. An extra bag costs %s." % (
                            a["name"], fees["airport_text"], (". Online, before you fly: " + summary) if summary else "", fees.get("piece_short", "extra"))))
        if abroad and a.get("infant"):
            faq.append(("How much baggage does an infant get on %s?" % a["name"], a["infant"]))
        excess = a.get("excess") if abroad else None
        if excess:
            faq.append(("What are %s extra baggage charges from India?" % a["name"], excess["summary"] + "."))
        if a.get("personal"):
            faq.insert(2, ("Can I carry a laptop bag or handbag too?", a["personal"]["summary"] + "."))
        faq_html = "".join("<h3>%s</h3><p>%s</p>" % (e(q), e(ans)) for q, ans in faq)
        weight_note = (('The "weight" column shows what\'s left of the %s kg limit after the bag itself.' % num(cabin["kg"])) if cabin.get("kg")
                       else e(a["name"]) + " gives no weight limit for cabin bags, so the weight column shows no figure.")
        if abroad:
            nm = a.get("page_name", a["name"])
            title = "%s baggage allowance from India: cabin bag and checked baggage" % nm
            seo = a.get("seo_title") or "%s baggage allowance from India %s: cabin bag size and kg by fare" % (nm, year)
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
        body = f"""{head(title, crumb_html, "Checked on " + fmt_date(a_checked) + " against " + e(possessive(a["name"])) + " official website &middot; " + scope_text)}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Cabin bag:</strong> {e(cabin['summary'])}.</li>
<li><strong>Size limit:</strong> {e(size_limit_text(cabin))}.</li>
{('<li><strong>Extra small bag:</strong> ' + e(a['personal']['summary']) + '.</li>') if a.get('personal') else ''}
<li><strong>{"Checked baggage" if abroad else "Free check-in"}:</strong> {e(a['checkin_summary'])}.</li>
</ul></div>
{top_picks(cfg, airline_top_rows(a["name"], [cabin], picks), "../", "Cabin bags that fit " + a["name"],
           '<a href="#our-picks-fit">See all our picks checked against this limit</a>')}
{checker_cta}
<h2>Cabin baggage</h2>
<p>{e(cabin.get('detail', cabin['summary'] + '.'))}</p>
{diagram_figure("cabin-limits-" + a["slug"], "../") if "cabin-limits-" + a["slug"] in DIAGRAMS else ""}
<h2>{"Checked baggage on India flights" if abroad else "Check-in baggage (domestic)"}</h2>
<table class="specs">{checkin_rows}</table>
{('<p>' + e(a['checkin_note']) + '</p>') if a.get('checkin_note') else ''}
{('<h2>Infants</h2><p>' + e(a['infant']) + '</p>') if abroad and a.get('infant') else ''}
{extra_section(a, extra_by_slug)}
{('<h2>Extra baggage charges</h2><p>' + e(excess['summary']) + '.</p><ul>' + "".join("<li>%s</li>" % e(x) for x in excess.get("points", [])) + '</ul>') if excess else ''}
{('<h2>Good to know</h2><ul>' + notes + '</ul>') if notes else ''}
<h2 id="our-picks-fit">Do our cabin picks fit {e(a['name'])}?</h2>
<p>Based on the size listed on Amazon. {weight_note}</p>
{fit_table(cfg, a, picks, "../")}
<p>Weigh your packed bag at home with a {scale_link} before you leave.</p>
<section class="faq"><h2>Questions</h2>{faq_html}</section>
<h2>Source</h2>
<p>Official {e(a['name'])} pages: {sources}</p>
{disclaimer}
<h2>Other airlines</h2>
{others(a['slug'], intl_airlines if abroad else airlines)}
{('<p>Flying within India? See the <a href="index.html">baggage rules for Indian airlines</a>.</p>') if abroad else ''}
{next_step([("../guides/cabin-luggage-guide.html#our-cabin-bag-picks", "Cabin trolleys we picked, and the airlines each one fits"),
            ("luggage-size-chart.html", "Trolley bag sizes in cm and inches"),
            ("checker.html", "Check your own bag against " + possessive(a["name"]) + " limit")]
           + ([] if abroad or a["slug"] not in extra_by_slug else [(extra_path(a["slug"])[len("baggage/"):], a["name"] + " extra baggage charges")]),
           "Shop by size", "Need a bag that fits " + e(a["name"]) + "? Start with the cabin size, then add a check-in bag for longer trips.")}
{tool_pills("../", "")}
</article></div>
{telegram_band(cfg, "../")}"""
        path = "baggage/%s.html" % a["slug"]
        crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html")]
                               + ([("International", "baggage/international.html")] if abroad else []) + [(a["name"], path)])
        faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}
        pages.append(write(path, page(cfg, seo, desc, body, 1, path, [article_schema(seo, desc, path, modified=a_checked), crumbs, faq_schema],
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
{top_picks(cfg, hub_rows, "../", "Bag too big? These fit by their listed size", '<a href="index.html#our-picks-fit">See all our picks against each airline</a>')}
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


# ---------- extra baggage charges (data/extra_baggage.json) ----------

EXTRA_PATH = "baggage/extra-baggage-charges.html"


def rupees(n):
    return "₹{:,}".format(int(n))


def load_extra_baggage(airlines):
    """Fees by airline, joined to airlines.json for the name and the baggage rules page."""
    if not EXTRA_BAGGAGE_FILE.exists() or not airlines:
        return None
    data = json.loads(EXTRA_BAGGAGE_FILE.read_text(encoding="utf-8"))
    names = {a["slug"]: a for a in airlines["airlines"]}
    for x in data["airlines"]:
        missing = [k for k in ("slug", "airport_per_kg", "airport_text", "piece_text", "cabin_text", "sources") if not x.get(k)]
        if missing or x["slug"] not in names:
            sys.exit("Error: extra baggage entry %s is missing %s or isn't in airlines.json" % (x.get("slug", "?"), ", ".join(missing)))
        x["name"] = names[x["slug"]]["name"]
        x["prepaid_map"] = dict(x["prepaid"] or [])
    return data


def airport_cost(x, kg):
    """What kg extra costs at the airport counter, as text ('up to' and 'plus tax' when the airline says so)."""
    text = rupees(x["airport_per_kg"] * kg)
    if x.get("airport_upto"):
        text = "up to " + text
    if x.get("airport_tax"):
        text += " + tax"
    return text


def extra_path(slug):
    return "baggage/extra-baggage-charges/%s.html" % slug


def prepaid_summary(x):
    """'3 kg ₹2,250, 5 kg ₹3,750 and 10 kg ₹7,500 (about ₹750 per kg)', or None when the airline lists no prepaid prices."""
    if not x["prepaid"]:
        return None
    first = [(kg, price) for kg, price in x["prepaid"] if kg in (3, 5, 10)] or x["prepaid"][:3]
    parts = ["%d kg %s" % (kg, rupees(price)) for kg, price in first]
    rates = sorted(price / kg for kg, price in x["prepaid"])
    rate = rupees(round(rates[0])) if round(rates[0]) == round(rates[-1]) else "%s to %s" % (rupees(round(rates[0])), rupees(round(rates[-1])))
    return "%s and %s (about %s per kg)" % (", ".join(parts[:-1]), parts[-1], rate)


def build_extra_airlines(cfg, deals_by_asin, extra, pages, lastmod):
    """One page per airline: baggage/extra-baggage-charges/<slug>.html."""
    checked = extra["checked"]
    year = checked[:4]
    p = "../../"
    scale = deals_by_asin.get("B07Q822CWX")
    scale_link = f'<a href="{p}picks/{scale["asin"]}.html">luggage scale</a>' if scale else "luggage scale"
    disclaimer = ('<p class="checked">Fees change often and can depend on your fare and route. The price shown when you pay is final, '
                  "so always check your booking and the airline's official website before you fly.</p>")
    for x in extra["airlines"]:
        name, path = x["name"], extra_path(x["slug"])
        summary = prepaid_summary(x)
        if x["prepaid"]:
            rows = []
            for kg, price in x["prepaid"]:
                saving = x["airport_per_kg"] * kg - price
                save = (("up to " if x.get("airport_upto") else "") + rupees(saving)) if saving > 0 else "–"
                rows.append(f'<tr><th scope="row">{kg} kg</th><td>{rupees(price)}</td><td>{e(airport_cost(x, kg))}</td><td>{e(save)}</td></tr>')
            table = ('<div class="table-wrap"><table class="compare snug"><thead><tr><th>Extra weight</th><th>Online</th><th>At the airport</th>'
                     f'<th>You save</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
            table_head = "%s prepaid excess baggage (domestic)" % name
        else:
            rows = "".join(f'<tr><th scope="row">{kg} kg</th><td>{e(airport_cost(x, kg))}</td></tr>' for kg in (3, 5, 10, 15))
            table = ('<div class="table-wrap"><table class="compare snug"><thead><tr><th>Extra weight</th><th>At the airport</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table></div>')
            table_head = "%s excess baggage at the airport (domestic)" % name
        notes = "".join("<li>%s</li>" % e(n) for n in x.get("notes", []))
        five = x["prepaid_map"].get(5)
        faq = [
            ("What are %s extra baggage charges per kg?" % name,
             "At the airport, %s charges %s on domestic flights. " % (name, x["airport_text"])
             + ("Bought online before you fly: %s." % summary if summary else x["prepaid_note"])),
            ("How much is 5 kg extra baggage on %s?" % name,
             ("%s online, or %s at the airport." % (rupees(five), airport_cost(x, 5))) if five else
             ("%s at the airport. %s doesn't list a prepaid price; you see it in Manage Booking after you book." % (airport_cost(x, 5), name))),
            ("What are %s excess baggage charges at the airport?" % name,
             "%s above your free check-in allowance (%s)." % (x["airport_text"][0].upper() + x["airport_text"][1:], x.get("free", "see your ticket"))),
            ("How to add extra baggage in %s?" % name, x["prepaid_note"]),
            ("What if my %s cabin bag is more than 7 kg?" % name, x["cabin_text"]),
            ("Does %s charge for an extra piece of baggage?" % name, x["piece_text"]),
        ]
        faq_html, faq_schema = faq_block(faq)
        others = '<ul class="airline-links">' + "".join(
            f'<li><a href="{o["slug"]}.html">{e(o["name"])}</a></li>' for o in extra["airlines"] if o["slug"] != x["slug"]) + "</ul>"
        title = "%s extra baggage charges: per kg, prepaid and at the airport" % name
        seo = "%s extra baggage charges %s: per kg, prepaid and airport rates" % (name, year)
        desc = ("%s excess baggage charges on domestic flights: %s at the airport%s. Extra bag: %s. Cabin bag over 7 kg: %s. Checked %s." % (
            name, x["airport_text"], ("; online " + summary) if summary else "", x.get("piece_short", "see below"),
            x.get("cabin_short", "see below"), fmt_date(checked)))
        inner = f"""<nav class="crumbs"><a href="{p}index.html">Home</a><span>/</span><a href="../index.html">Baggage rules</a><span>/</span><a href="../extra-baggage-charges.html">Extra baggage charges</a></nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Checked on {fmt_date(checked)} against {e(name)}'s official website &middot; domestic flights</p>"""
        body = f"""{page_head("luggage", media(cfg, "luggage", "media media-tile"), inner, p)}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Free check-in baggage:</strong> {e(x.get("free", "see your ticket"))}.</li>
<li><strong>Prepaid online:</strong> {e(summary) if summary else "not listed by " + e(name) + " (up to 20% less than the airport rate, it says)"}.</li>
<li><strong>At the airport:</strong> {e(x["airport_text"])}.</li>
<li><strong>Extra bag:</strong> {e(x.get("piece_short", "see below"))}.</li>
<li><strong>Cabin bag over 7 kg:</strong> {e(x.get("cabin_short", "see below"))}.</li>
</ul></div>
<h2>{e(table_head)}</h2>
{table}
<p>{e(x["prepaid_note"])}</p>
<h2>Extra bags</h2>
<p>{e(x["piece_text"])}</p>
<h2>Cabin bag over 7 kg</h2>
<p>{e(x["cabin_text"])}</p>
{('<h2>Lite fares</h2><p>' + e(x["lite"]) + '</p>') if x.get("lite") else ''}
{('<h2>Good to know</h2><ul>' + notes + '</ul>') if notes else ''}
<h2>How to pay less</h2>
<ul>
<li><strong>Weigh your bag at home</strong> with a {scale_link}, then buy the smallest slab that covers the extra weight. Prepaid kilos you don't use aren't refunded.</li>
<li><strong>Check the cabin bag size</strong> in our <a href="../checker.html">cabin bag checker</a>: a bag that's too big gets checked in.</li>
<li><strong>Add up your packing list</strong> with the <a href="{p}tools/bag-weight.html">bag weight calculator</a>.</li>
</ul>
<p>Compare {e(name)} with other airlines on our <a href="../extra-baggage-charges.html">extra baggage charges</a> page, and see the free allowance on the <a href="../{x["slug"]}.html">{e(name)} baggage rules</a> page.</p>
{faq_html}
<h2>Source</h2>
<p>Official {e(name)} pages, read on {fmt_date(checked)}: {sources_html(x["sources"])}</p>
{disclaimer}
<h2>Extra baggage charges on other airlines</h2>
{others}
{tool_pills(p, "")}
</article></div>
{telegram_band(cfg, p)}"""
        crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Extra baggage charges", EXTRA_PATH), (name, path)])
        pages.append(write(path, page(cfg, seo, desc, body, 2, path,
                                      [tool_article(cfg, seo, desc, path, extra.get("published", checked), checked), crumbs, faq_schema],
                                      og_type="article")))
        lastmod[path] = checked


def build_extra_baggage(cfg, deals_by_asin, extra, pages, lastmod):
    """Hub page comparing excess baggage fees on domestic flights."""
    checked = extra["checked"]
    year = checked[:4]
    rows_all = extra["airlines"]
    with_prepaid = [x for x in rows_all if x["prepaid"]]
    per_kg = sorted(price / kg for x in with_prepaid for kg, price in x["prepaid"])
    airport = sorted(x["airport_per_kg"] for x in rows_all)
    pre_lo, pre_hi = rupees(round(per_kg[0])), rupees(round(per_kg[-1]))
    air_lo, air_hi = rupees(airport[0]), rupees(airport[-1])
    p = "../"
    scale = deals_by_asin.get("B07Q822CWX")
    scale_link = f'<a href="../picks/{scale["asin"]}.html">luggage scale</a>' if scale else "luggage scale"

    slabs = (3, 5, 10, 15)
    pre_rows = []
    for x in rows_all:
        if x["prepaid"]:
            cells = "".join("<td>%s</td>" % (rupees(x["prepaid_map"][kg]) if kg in x["prepaid_map"] else "–") for kg in slabs)
        else:
            cells = '<td colspan="%d">Not listed (Air India says up to 20%% less than the airport rate)</td>' % len(slabs)
        pre_rows.append(f'<tr><th scope="row"><a href="extra-baggage-charges/{x["slug"]}.html">{e(x["name"])}</a></th>{cells}</tr>')
    air_rows = "".join(f'<tr><th scope="row">{e(x["name"])}</th><td>{e(x["airport_text"])}</td><td>{e(x.get("piece_short", "–"))}</td>'
                       f'<td>{e(x.get("cabin_short", "–"))}</td></tr>' for x in rows_all)
    five_rows = []
    for x in rows_all:
        online = x["prepaid_map"].get(5)
        at_airport = airport_cost(x, 5)
        if online:
            saving = x["airport_per_kg"] * 5 - online
            save = ("up to " if x.get("airport_upto") else "") + rupees(saving)
            five_rows.append(f'<tr><th scope="row">{e(x["name"])}</th><td>{rupees(online)}</td><td>{e(at_airport)}</td><td>{e(save)}</td></tr>')
        else:
            five_rows.append(f'<tr><th scope="row">{e(x["name"])}</th><td>Not listed</td><td>{e(at_airport)}</td><td>Up to 20%</td></tr>')
    # Is the smallest prepaid slab worth it for 1-2 kg? Worked out from each airline's own figures.
    small = [x for x in with_prepaid if min(x["prepaid_map"]) == 3]
    two_kg_cheaper = all(x["airport_per_kg"] * 2 < x["prepaid_map"][3] for x in small)
    indigo = next((x for x in rows_all if x["slug"] == "indigo"), None)
    two_kg_line = ""
    if two_kg_cheaper and indigo:
        two_kg_line = (f'<li><strong>Only 1 or 2 kg over?</strong> The smallest slab online is 3 kg. On IndiGo, 2 kg at the airport costs '
                       f'{rupees(indigo["airport_per_kg"] * 2)}, less than the 3 kg slab at {rupees(indigo["prepaid_map"][3])}. '
                       'The same is true on the other airlines with a 3 kg slab.</li>')

    faq = [
        ("What are extra baggage charges per kg on domestic flights in India?",
         "At the airport counter, IndiGo, Air India, Air India Express, Akasa Air and SpiceJet charge %s to %s per kg above your free check-in allowance, "
         "which is usually 15 kg. Bought online before you fly, it works out to about %s to %s per kg, sold in slabs such as 3, 5 and 10 kg." % (air_lo, air_hi, pre_lo, pre_hi)),
    ]
    if indigo:
        faq.append(("What are IndiGo extra baggage charges per kg?",
                    "%s at the airport. Bought online, IndiGo charges %s for 3 kg, %s for 5 kg and %s for 10 kg, which is %s per kg." % (
                        indigo["airport_text"], rupees(indigo["prepaid_map"][3]), rupees(indigo["prepaid_map"][5]),
                        rupees(indigo["prepaid_map"][10]), rupees(indigo["prepaid_map"][5] // 5))))
    faq += [
        ("What are Air India extra baggage charges for domestic flights?",
         "₹800 per kg plus tax at the airport. Air India says paying ahead online saves up to 20%, but it doesn't list prepaid prices: you see them in Manage Booking."),
        ("Can I buy extra baggage at the airport?",
         "Yes. You pay at the check-in counter at the airport rate, which costs more per kg than buying online before you fly. Online purchase usually closes 2 or 3 hours before departure."),
        ("What happens if my cabin bag is more than 7 kg?",
         "It depends on the airline. Air India lets you carry up to 12 kg for ₹3,000. Air India Express sells 3 or 5 kg more (Xtra Carry-On), and SpiceJet charges ₹700 per kg ahead or ₹750 at the airport, up to 5 kg more. "
         "IndiGo and Akasa Air list no fee for a heavier cabin bag, so expect to check it in."),
        ("Does an extra bag include extra weight?",
         "No. A second bag costs about ₹950 to ₹1,000 on IndiGo, Air India Express, Akasa Air and SpiceJet, and that fee buys no weight. Every kg over your free allowance is still charged."),
        ("Is prepaid excess baggage refundable?",
         "Not for kilos you don't use: if you buy 5 kg and carry 3 kg extra, there's no refund. Airlines do refund it if they cancel the flight, and some refund it when you cancel the whole booking in time."),
    ]
    faq_html, faq_schema = faq_block(faq)
    sources = "".join(f'<li><strong>{e(x["name"])}:</strong> {sources_html(x["sources"])}</li>' for x in rows_all)
    pick_box = inline_pick(cfg, scale, p) if scale else ""
    guides = [("cabin-luggage-guide", "how to pick a cabin trolley"), ("polycarbonate-vs-polypropylene-luggage", "polycarbonate vs polypropylene luggage"),
              ("trolley-bag-capacity-kg-litres", "trolley bag capacity in kg and litres")]
    guide_links = ", ".join(f'<a href="../guides/{slug}.html">{text}</a>' for slug, text in guides if (ARTICLES_DIR / (slug + ".md")).exists())

    title = "Extra baggage charges on domestic flights in India"
    seo = "Extra baggage charges per kg %s: IndiGo, Air India, Akasa, SpiceJet" % year
    desc = ("Excess baggage charges on IndiGo, Air India, Air India Express, Akasa Air and SpiceJet domestic flights: prepaid slabs, "
            "airport rate per kg, extra bags and cabin bags over 7 kg. Checked %s." % fmt_date(checked))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Baggage rules</a><span>/</span>Extra baggage charges</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Checked on {fmt_date(checked)} against each airline's official website &middot; domestic flights</p>"""
    body = f"""{page_head("luggage", media(cfg, "luggage", "media media-tile"), inner, p, "bathroom-scale")}
<div class="wrap"><article class="guide">
<p class="lead">Over your free baggage allowance? Here's what India's main airlines charge for extra kilos, extra bags and heavy cabin bags on domestic flights, and how to pay less.</p>
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>At the airport:</strong> {air_lo} to {air_hi} per kg over your free check-in allowance (usually 15 kg).</li>
<li><strong>Online, before you fly:</strong> about {pre_lo} to {pre_hi} per kg, sold in slabs such as 3, 5 and 10 kg.</li>
<li><strong>An extra bag:</strong> about ₹950 to ₹1,000, and it includes no extra weight.</li>
<li><strong>Cabin bag over 7 kg:</strong> the rules differ a lot by airline. See the table below.</li>
</ul></div>
<h2>Extra baggage charges by airline</h2>
<p>Full details for each airline: every prepaid slab, extra bags, heavy cabin bags and Lite fares.</p>
<ul class="airline-links">{"".join(f'<li><a href="extra-baggage-charges/{x["slug"]}.html">{e(x["name"])}</a></li>' for x in rows_all)}</ul>
<h2>Prepaid extra baggage (bought online)</h2>
<p>The price for each slab of extra check-in weight, bought online after booking.</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Airline</th>{"".join("<th>%d kg</th>" % kg for kg in slabs)}</tr></thead><tbody>{"".join(pre_rows)}</tbody></table></div>
<h2>At the airport, extra bags and heavy cabin bags</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Airline</th><th>At the airport</th><th>Extra bag</th><th>Cabin bag over 7 kg</th></tr></thead><tbody>{air_rows}</tbody></table></div>
<p class="checked">Checked on {fmt_date(checked)}. Fees change often and can depend on your fare and route. The price shown when you pay is final, so always check your booking and the airline's website before you fly.</p>
<h2>Airport or online: what 5 kg extra costs</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Airline</th><th>Online</th><th>At the airport</th><th>You save</th></tr></thead><tbody>{"".join(five_rows)}</tbody></table></div>
<p>Buying online is cheaper on every airline here, but only by about ₹50 to ₹100 per kg. The bigger saving comes from not paying for kilos you don't need:</p>
<ul>
<li><strong>Prepaid kilos aren't refunded.</strong> Buy 5 kg, carry 3 kg extra, and the other 2 kg are lost.</li>
{two_kg_line}
<li><strong>Buy the slab after you weigh.</strong> Pack, weigh the bag at home, then buy the smallest slab that covers it.</li>
<li><strong>The online window closes early:</strong> 2 hours before departure on IndiGo, Air India, Air India Express and Akasa Air, 3 hours on SpiceJet.</li>
</ul>
<h2>How to avoid extra baggage charges</h2>
<ul>
<li><strong>Weigh your bags at home.</strong> A {scale_link} costs less than a few kilos at the airport. Most check-in bags are allowed 15 kg, and most cabin bags 7 kg.</li>
<li><strong>Choose a lighter bag.</strong> An empty trolley typically weighs about 2.5 kg in cabin size and 3.4 to 4.3 kg in medium and large sizes, all taken from your allowance. See typical weights in our <a href="luggage-size-chart.html">trolley bag size chart</a>.</li>
<li><strong>Add it up before you pack.</strong> Our <a href="../tools/bag-weight.html">bag weight calculator</a> shows if you'll stay under 7 kg and 15 kg.</li>
<li><strong>Make sure the cabin bag fits.</strong> A cabin bag that's too big gets checked in and counts towards your check-in weight. Try the <a href="checker.html">cabin bag checker</a>.</li>
<li><strong>Wear the heavy things.</strong> Put on your jacket and heaviest shoes for the flight.</li>
<li><strong>Check your fare.</strong> IndiGo Lite and Air India Express Xpress Lite fares include no check-in bag at all.</li>
<li><strong>Travelling together?</strong> SpiceJet lets passengers on one booking combine their check-in baggage. Other airlines count each passenger's allowance separately, so check your ticket.</li>
<li><strong>Keep every bag under 32 kg.</strong> No airline here takes a heavier single bag, even if you pay.</li>
</ul>
{pick_box}
<p>More help: {guide_links}.</p>
{faq_html}
<h2>Sources</h2>
<p>Official airline pages, read on {fmt_date(checked)}:</p>
<ul>{sources}</ul>
<p>See also the free baggage allowance for each airline on our <a href="index.html">baggage rules for Indian airlines</a> page.</p>
{tool_pills("../", EXTRA_PATH)}
</article></div>
{telegram_band(cfg, "../")}"""
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Extra baggage charges", EXTRA_PATH)])
    pages.append(write(EXTRA_PATH, page(cfg, seo, desc, body, 1, EXTRA_PATH,
                                        [tool_article(cfg, seo, desc, EXTRA_PATH, extra.get("published", checked), checked), crumbs, faq_schema],
                                        og_type="article", photo="bathroom-scale")))
    lastmod[EXTRA_PATH] = checked
    build_extra_airlines(cfg, deals_by_asin, extra, pages, lastmod)


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
    ac3 = {"dims_cm": size["ac3_dims_cm"]}
    ac3_text = " x ".join(num(x) for x in size["ac3_dims_cm"])
    ac3_rows = []
    for d in deals:
        dims = parse_dims(d.get("specs", {}).get("Size"))
        if d["category"] == "luggage" and dims and "duffle" not in d["title"].lower() and size_fit(dims, ac3)[0]:
            kg = parse_kg(d.get("specs", {}).get("Weight"))
            ac3_rows.append((kg if kg is not None else 99, d, "Fits AC 3-tier and Chair Car",
                             "Listed at %s cm, inside the %s cm limit%s." % (" x ".join(num(x) for x in sorted(dims, reverse=True)), ac3_text,
                                                                            (". %g kg empty" % kg) if kg is not None else "")))
    ac3_html = top_picks(cfg, [r[1:] for r in sorted(ac3_rows, key=lambda r: r[0])][:3], "../",
                         "Suitcases that fit the AC 3-tier limit", '<a href="#our-suitcases-fit">See all our suitcases against both limits</a>')
    bags_html = ""
    if bag_rows:
        heads = "".join("<th>%s<span class=why>%s cm</span></th>" % (e(label), " x ".join(num(x) for x in lim)) for label, lim in limits)
        bags_html = ('<h2 id="our-suitcases-fit">Do our suitcases fit in the compartment?</h2><p>The limit is for trunks, suitcases and boxes. Based on the size listed on Amazon. '
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
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Class</th><th>Free allowance</th><th>Maximum, with charges</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>{e(data["allowance_note"])}</p>
<h2>Size limit for suitcases and trunks</h2>
<p>{e(size["text"])}</p>
{ac3_html}
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


def load_carry_pages(data):
    """content/carry/*.md, in the order of the big table. Each page's answers and rule come from its row in
    data/flight_items.json (front matter 'item'), so a rule is written in one place only."""
    if not CARRY_DIR.exists():
        return []
    order = {it["item"]: i for i, it in enumerate(it for g in data["groups"] for it in g["items"])}
    items = {it["item"]: it for g in data["groups"] for it in g["items"]}
    out = []
    for a in load_articles(CARRY_DIR):
        it = items.get(a.get("item"))
        if not it:
            sys.exit("Error: content/carry/%s.md names item %r, which is not in data/flight_items.json" % (a["slug"], a.get("item")))
        missing = [k for k in ("cabin_short", "checked_short") if not it.get(k)]
        if missing:
            sys.exit("Error: flight item %r has a page but no %s in data/flight_items.json" % (it["item"], ", ".join(missing)))
        if any(tag in a["body"] for tag in ("[[shop:", "[[book:", "[[fly:", "[[coupon:")):
            sys.exit("Error: content/carry/%s.md links to another shop. These pages carry Amazon picks only." % a["slug"])
        out.append((a, it))
    return sorted(out, key=lambda x: order[x[1]["item"]])


def build_carry_items(cfg, data, carry, deals_by_asin, pages, lastmod):
    """One page per item, e.g. baggage/can-i-carry/power-bank.html: the direct answers, the rule and its source
    from data/flight_items.json, then the explanation, FAQ and links from content/carry/<slug>.md."""
    count = sum(len(g["items"]) for g in data["groups"])
    p = "../../"
    for a, it in carry:
        path = "baggage/can-i-carry/%s.html" % a["slug"]
        checked = it.get("rechecked", data["checked"])
        rows = ""
        for where, label in (("cabin", "Cabin bag"), ("checked", "Check-in bag")):
            state, word = ANSWER[it[where]]
            rows += f'<tr><th scope="row">{label}</th><td><span class="fit fit-{state}">{word}</span> {e(it[where + "_short"])}</td></tr>'
        sources = [s.split("=", 1) for s in a.get("sources", "").split(" | ") if "=" in s]
        related = [r.split("=", 1) for r in a.get("related", "").split(" | ") if "=" in r]
        others = "".join(f'<li><a href="{b["slug"]}.html">{e(jt["item"])}</a></li>' for b, jt in carry if b["slug"] != a["slug"])
        content = render_markdown(a["body"], cfg, deals_by_asin, p, "carry/%s.md" % a["slug"])
        inner = f"""<nav class="crumbs"><a href="{p}index.html">Home</a><span>/</span><a href="../index.html">Baggage rules</a><span>/</span><a href="../can-i-carry.html">Can I carry it?</a><span>/</span>{e(it["item"])}</nav>
      <h1>{e(a["title"])}</h1>
      <p class="muted small">Checked on {fmt_date(checked)} against {e(a.get("checked_against", "official airline and airport pages"))}</p>"""
        body = f"""{page_head("watches", f'<div class="media media-tile tint-watches">{icon("shield", "icon media-icon")}</div>', inner, p)}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2>
<div class="table-wrap"><table class="compare snug"><tbody>{rows}</tbody></table></div>
<p class="checked">Checking more than one thing? See all {count} items on our <a href="../can-i-carry.html">Can I carry it on a flight?</a> list.</p></div>
<h2>The rule</h2>
<p>{e(it["rule"])} <a class="src" href="{e(it["source"])}" target="_blank" rel="noopener">Source</a></p>
<p class="checked">Checked on {fmt_date(checked)}. Security staff can still refuse any item, and airlines can be stricter or change their rules, so check your airline before you fly.</p>
{content}
<h2>Sources</h2>
<p>{sources_html([{"label": label, "url": url} for label, url in sources])}</p>
<h2>More items people ask about</h2>
<ul class="airline-links">{others}<li><a href="../can-i-carry.html">All {count} items</a></li></ul>
{('<h2>Related guides</h2><ul class="airline-links">%s</ul>' % "".join(f'<li><a href="{p}{e(u)}">{e(label)}</a></li>' for u, label in related)) if related else ""}
</article></div>
{telegram_band(cfg, p)}"""
        seo = a.get("seo_title", a["title"])
        crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Can I carry it?", "baggage/can-i-carry.html"),
                                     (it["item"], path)])
        updated = max(a["updated"], checked)
        schema = [tool_article(cfg, seo, a["description"], path, a["date"], updated), crumbs]
        faq = md_faq(a["body"])
        if faq:
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]})
        pages.append(write(path, page(cfg, seo, a["description"], body, 2, path, schema, og_type="article")))
        lastmod[path] = updated


def build_can_i_carry(cfg, deals_by_asin, pages, lastmod):
    data = json.loads(FLIGHT_ITEMS_FILE.read_text(encoding="utf-8"))
    checked = data["checked"]
    carry = load_carry_pages(data)
    page_of = {it["item"]: a["slug"] for a, it in carry}
    groups = []
    for group in data["groups"]:
        rows = []
        for it in group["items"]:
            cells = ""
            for where in ("cabin", "checked"):
                state, label = ANSWER[it[where]]
                cells += f'<td><span class="fit fit-{state}">{label}</span></td>'
            words = " ".join([it["item"]] + it.get("also", []))
            name = e(it["item"])
            if it["item"] in page_of:
                name = f'<a href="can-i-carry/{page_of[it["item"]]}.html">{name}</a>'
            rows.append(f'<tr data-words="{e(words.lower())}"><th scope="row">{name}</th>{cells}'
                        f'<td>{e(it["rule"])} <a class="src" href="{e(it["source"])}" target="_blank" rel="noopener">Source</a></td></tr>')
        groups.append(f'<tbody data-group><tr class="group-row"><th colspan="4" scope="colgroup">{e(group["name"])}</th></tr>{"".join(rows)}</tbody>')
    count = sum(len(g["items"]) for g in data["groups"])
    most_asked = ""
    if carry:
        links = "".join(f'<li><a href="can-i-carry/{a["slug"]}.html">{e(it["item"])}</a></li>' for a, it in carry)
        most_asked = (f'<h2>Most asked items, in detail</h2><p>How much you can take, the rule on each airline and how to pack it:</p>'
                      f'<ul class="airline-links">{links}</ul>')
    faq_html, faq_schema = faq_block([(f["q"], f["a"]) for f in data["faq"]])
    title = "Can I carry it on a flight? Cabin and check-in rules in India"
    seo = "Can I carry it on a flight in India? Cabin and check-in item list %s" % checked[:4]
    desc = ("Search %d items, from power banks and perfume to pickles and dry coconut, and see if they can go in your "
            "cabin bag or check-in baggage on flights in India. Checked %s." % (count, fmt_date(checked)))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Baggage rules</a><span>/</span>Can I carry it?</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Checked on {fmt_date(checked)} against BCAS, DGCA and airline pages</p>"""
    own_pages = (" The %d items people ask about most also have their own page, with the rules airline by airline and how to pack them."
                 % len(carry)) if carry else ""
    lead = (f'<p class="lead">Search {count} things people pack, from power banks and perfume to pickle and dry coconut. '
            f'Each row shows whether it can go in your cabin bag, your check-in bag or neither on flights within India, '
            f'with the rule and a link to the official page it comes from.{own_pages}</p>')
    customs_tip = ('<aside class="tip">' + icon("plane", "icon tip-icon") + '<div><strong>Flying into India from abroad?</strong>'
                   '<p>The airline rules are only half of it. See how much alcohol, gold and cash Indian Customs lets you bring in duty free, '
                   'in our <a href="customs.html">customs rules for passengers</a>.</p></div></aside>') if CUSTOMS_DIR.exists() else ""
    body = f"""{page_head("watches", f'<div class="media media-tile tint-watches">{icon("shield", "icon media-icon")}</div>', inner, "../")}
<div class="wrap"><article class="guide guide-wide">
{lead}
<div class="answer"><h2>The rules most people get wrong</h2><ul>{"".join("<li>%s</li>" % e(x) for x in data["key_rules"])}</ul></div>
<form class="checker" onsubmit="return false"><label>Search an item<input id="carry-q" type="search" placeholder="power bank, perfume, pickle…" autocomplete="off"></label>
<p class="hint" id="carry-count" aria-live="polite" data-all="{{n}} items" data-some="{{shown}} of {{n}} items">{count} items</p></form>
<div class="table-wrap"><table class="compare carry-table" id="carry-table"><thead><tr><th>Item</th><th>Cabin bag</th><th>Check-in</th><th>Rule</th></tr></thead>{"".join(groups)}</table></div>
<p class="hint" id="carry-none" hidden>No match. Try another word, or check the airline's own list.</p>
<p class="checked">"With limits" means it's allowed only in the way the rule says. "Not listed" means the official pages we checked don't say. Security staff can still refuse any item, and airlines can be stricter, so check your airline before you fly.</p>
{most_asked}
<aside class="tip">{icon("ruler", "icon tip-icon")}<div><strong>Packing your cabin bag?</strong><p>Check its size with the <a href="checker.html">cabin bag checker</a>, and use a <a href="../packing/index.html">packing checklist</a>.</p></div></aside>
{customs_tip}
{faq_html}
<h2>Sources</h2>
<p>{sources_html(data["sources"])}</p>
{tool_pills("../", "baggage/can-i-carry.html")}
</article></div>
<script src="../assets/carry.js" defer></script>
{telegram_band(cfg, "../")}"""
    path = "baggage/can-i-carry.html"
    crumbs = crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Can I carry it?", path)])
    modified = max([checked] + [it.get("rechecked", checked) for g in data["groups"] for it in g["items"]])
    pages.append(write(path, page(cfg, seo, desc, body, 1, path,
                                  [tool_article(cfg, seo, desc, path, checked, modified), crumbs, faq_schema], og_type="article")))
    lastmod[path] = modified
    build_carry_items(cfg, data, carry, deals_by_asin, pages, lastmod)


# ---------- Indian customs rules for passengers (content/customs/*.md) ----------

CUSTOMS_PATH = "baggage/customs.html"
NOT_ADVICE = ("This page explains the rules in simple words. It is not legal advice. Customs officers make the final decision, "
              "and rules and duty rates can change, so check with Indian Customs (CBIC) or the Customs help desk at the airport if you're unsure.")


def customs_path(a):
    return CUSTOMS_PATH if a["slug"] == "index" else "baggage/customs/%s.html" % a["slug"]


def load_customs():
    """content/customs/index.md is the hub (baggage/customs.html); every other file is baggage/customs/<slug>.html.
    Front matter: title, seo_title, description, date, checked, quick ("line | line"), sources ("Label=URL | ..."),
    optional nav (short name for links), order, related ("path=Label | ...") and not_advice (for another country's rules)."""
    if not CUSTOMS_DIR.exists():
        return []
    found = load_articles(CUSTOMS_DIR)
    for a in found:
        missing = [k for k in ("checked", "quick", "sources") if not a.get(k)]
        if missing:
            sys.exit("Error: content/customs/%s.md is missing %s" % (a["slug"], ", ".join(missing)))
        if any(tag in a["body"] for tag in ("[[shop:", "[[book:", "[[fly:", "[[coupon:")):
            sys.exit("Error: content/customs/%s.md links to another shop. These pages carry Amazon picks only." % a["slug"])
        a["updated"] = max(a["updated"], a["checked"])
    if not any(a["slug"] == "index" for a in found):
        sys.exit("Error: content/customs/ needs an index.md for the hub page")
    return sorted(found, key=lambda a: (a["slug"] != "index", int(a.get("order", 99))))


def build_customs(cfg, deals_by_asin, customs, pages, lastmod):
    hub = customs[0]
    subs = customs[1:]
    for a in customs:
        is_hub = a is hub
        path = customs_path(a)
        p = "../" if is_hub else "../../"
        here = "" if is_hub else "../"  # from this page to baggage/
        quick = "".join("<li>%s</li>" % md_inline(q.strip(), p) for q in a["quick"].split(" | ") if q.strip())
        sources = [{"label": s.split("=", 1)[0].strip(), "url": s.split("=", 1)[1].strip()} for s in a["sources"].split(" | ") if "=" in s]
        related = [r.split("=", 1) for r in a.get("related", "").split(" | ") if "=" in r]
        content = render_markdown(a["body"], cfg, deals_by_asin, p, "customs/%s.md" % a["slug"])
        not_advice = a.get("not_advice", NOT_ADVICE)
        crumb = (f'<a href="{p}index.html">Home</a><span>/</span><a href="{here}index.html">Baggage rules</a><span>/</span>'
                 + ("Customs rules" if is_hub else f'<a href="../customs.html">Customs rules</a><span>/</span>{e(a.get("nav", a["title"]))}'))
        inner = f"""<nav class="crumbs">{crumb}</nav>
      <h1>{e(a["title"])}</h1>
      <p class="muted small">Checked on {fmt_date(a["checked"])} against {e(a.get("checked_against", "the Baggage Rules, 2026 and other official CBIC documents"))}</p>"""
        art = f'<div class="media media-tile tint-travel-gear">{icon("globe", "icon media-icon")}</div>'
        links = [(customs_path(b), b.get("nav", b["title"])) for b in customs if b is not a]
        others = "".join(f'<li><a href="{p}{e(u)}">{e(label)}</a></li>' for u, label in links)
        body = f"""{page_head("travel-gear", art, inner, p, a.get("photo"))}
<div class="wrap"><article class="guide">
{('<p class="lead">' + md_inline(a["lead"], p) + '</p>') if a.get("lead") else ""}
<div class="answer"><h2>Quick answer</h2><ul>{quick}</ul></div>
<p class="checked">{not_advice}</p>
{content}
<h2>Sources</h2>
<p>Official documents, read on {fmt_date(a["checked"])}:</p>
<ul>{"".join("<li>%s</li>" % sources_html([s]) for s in sources)}</ul>
<p class="checked">Checked on {fmt_date(a["checked"])}. {not_advice}</p>
{(f'<h2>{"Customs rules by item" if is_hub else "More customs rules"}</h2><ul class="airline-links">{others}</ul>') if others else ""}
{('<h2>Related guides</h2><ul class="airline-links">%s</ul>' % "".join(f'<li><a href="{p}{e(u.strip())}">{e(label.strip())}</a></li>' for u, label in related)) if related else ""}
{tool_pills(p, path)}
</article></div>
{telegram_band(cfg, p)}"""
        seo = a.get("seo_title", a["title"])
        trail = [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Customs rules", CUSTOMS_PATH)]
        if not is_hub:
            trail.append((a.get("nav", a["title"]), path))
        schema = [tool_article(cfg, seo, a["description"], path, a["date"], a["updated"]), crumbs_schema(cfg, trail)]
        faq = md_faq(a["body"])
        if faq:
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]})
        pages.append(write(path, page(cfg, seo, a["description"], body, 1 if is_hub else 2, path, schema,
                                      og_type="article", photo=a.get("photo"))))
        lastmod[path] = a["updated"]


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
        return hindi_pages.tool_links(sys.modules[__name__], current, "../")

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
    # Hindi readers get a short table: the 5 cabin trolleys and 3 backpacks that fit the most airlines
    # (all 30-odd English product names would otherwise fill the page). The checker link in fit_more covers the rest.
    scored = sorted(((sum(1 for a in airlines["airlines"] if size_fit(dims, a["cabin"])[0]), sum(dims), d, dims)
                     for d, dims, kg in cabin_picks(deals)), key=lambda x: (-x[0], x[1]))
    shown = ([x for x in scored if "trolley" in x[2]["title"].lower()][:5]
             + [x for x in scored if x[2]["category"] == "backpacks"][:3])
    matrix_head = "".join("<th>%s</th>" % e(a["name"]) for a in airlines["airlines"])
    matrix_rows = "".join(
        f'<tr><th scope="row"><a href="../picks/{d["asin"]}.html">{e(d["title"])}</a><span class="why">{num(sum(dims))} cm</span></th>'
        + "".join("<td>%s</td>" % badge(*size_fit(dims, a["cabin"])[::2]) for a in airlines["airlines"]) + "</tr>"
        for fits, total, d, dims in shown)
    fit_more = ("<p class=\"checked\">%s</p>" % (t["fit_more"] % len(scored))) if t.get("fit_more") and len(scored) > len(shown) else ""
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
{fit_more}
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
    hi_pages = hindi_pages.carry_links(sys.modules[__name__])
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
            name = f'<a href="{hi_pages[it["item"]]}">{e(h["name"])}</a>' if it["item"] in hi_pages else e(h["name"])
            rows.append(f'<tr data-words="{e(words.lower())}"><th scope="row">{name}<span class="why" lang="en">{e(it["item"])}</span></th>{cells}'
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
{('<h2>सबसे ज़्यादा पूछी जाने वाली चीज़ें, विस्तार से</h2><p>कितना ले जा सकते हैं, हर एयरलाइन का नियम और पैक कैसे करें:</p><ul class="airline-links">'
  + "".join(f'<li><a href="{href}">{e(t["items"].get(item, {}).get("name", item))}</a></li>' for item, href in hi_pages.items()) + '</ul>') if hi_pages else ""}
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
    ac3 = {"dims_cm": size["ac3_dims_cm"]}
    ac3_text = " x ".join(num(x) for x in size["ac3_dims_cm"])
    ac3_rows = []
    for d in deals:
        dims = parse_dims(d.get("specs", {}).get("Size"))
        if d["category"] == "luggage" and dims and "duffle" not in d["title"].lower() and size_fit(dims, ac3)[0]:
            kg = parse_kg(d.get("specs", {}).get("Weight"))
            ac3_rows.append((kg if kg is not None else 99, d, "Fits AC 3-tier and Chair Car",
                             "Listed at %s cm, inside the %s cm limit%s." % (" x ".join(num(x) for x in sorted(dims, reverse=True)), ac3_text,
                                                                            (". %g kg empty" % kg) if kg is not None else "")))
    ac3_html = top_picks(cfg, [r[1:] for r in sorted(ac3_rows, key=lambda r: r[0])][:3], "../",
                         "Suitcases that fit the AC 3-tier limit", '<a href="#our-suitcases-fit">See all our suitcases against both limits</a>')
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
# Heights Indian brands list in cm (people search "77 cm luggage in inches", "55 cm bag in inches")
CM_ROWS = [(55, "Cabin"), (56, "Cabin"), (65, "Medium"), (66, "Medium"), (68, "Medium"), (69, "Medium"),
           (75, "Large"), (76, "Large"), (77, "Large"), (78, "Large"), (79, "Large")]
# From guides/trolley-bag-capacity-kg-litres: keep the two in step
CAPACITY_ROWS = [("Cabin", "About 55 cm", "39 L", "2.5 kg", "6–12 kg"), ("Medium", "65–69 cm", "69 L", "3.4 kg", "10–21 kg"),
                 ("Large", "75–80 cm", "108 L", "4.3 kg", "16–32 kg")]
# Size chart rows that link to a guide for that size (paths from baggage/)
SIZE_GUIDES = {20: "../guides/20-inch-trolley-bag-size.html", 22: "../guides/22-inch-trolley-bag-size.html",
               24: "../guides/24-inch-trolley-bag-size.html", 26: "../guides/26-inch-trolley-bag-size.html",
               28: "../guides/28-inch-trolley-bag-size.html", 30: "../guides/32-inch-trolley-bag-size.html#what-about-30-inch", 32: "../guides/32-inch-trolley-bag-size.html"}
CAPACITY_GUIDES = {"Cabin": "../guides/cabin-luggage-guide.html", "Medium": "../guides/24-inch-trolley-bag-size.html",
                   "Large": "../guides/28-inch-trolley-bag-size.html"}
# One pick per size near the top of the size chart. Keep the reasons true to each pick's listed specs in data/deals.json.
SIZE_CHART_PICKS = [
    ("B097JLKP8X", "Cabin size, for IndiGo", "Listed at 55 x 35 x 25 cm, within the cabin limit of IndiGo, Akasa Air and SpiceJet's Boeing planes. 2.7 kg empty."),
    ("B0F5HGLC5Q", "Cabin size, for Air India", "Only 20 cm deep, so by its listed size it fits Air India's 55 x 40 x 20 cm limit. 2.2 kg empty."),
    ("B0GNSKLF5Z", "Medium, 65–69 cm", "The lightest medium trolley we found, at 2.52 kg, so more of a 15 kg fare is left for your things."),
    ("B0GX5VFHMS", "Large, 75–80 cm", "Listed at 152 cm in total, inside the 158 cm check-in limit that most large trolleys go over."),
]


SIZE_CHART_UPDATED = "2026-11-15"  # bump when the size chart's facts change; the Hindi chart (scripts/hindi_pages.py) warns until it matches


def build_size_chart(cfg, deals_by_asin, airlines, pages, lastmod, intl=None):
    """Inches/cm and kg/lb chart for luggage, with airline limits converted (baggage/luggage-size-chart.html)."""
    path = "baggage/luggage-size-chart.html"
    updated = SIZE_CHART_UPDATED
    cm = lambda inches: num(round(inches * 2.54, 1))
    inch = lambda c: num(round(c / 2.54, 1))
    lb = lambda kg: num(round(kg * 2.20462, 1))
    size_rows = "".join(f'<tr><th scope="row">' + (f'<a href="{SIZE_GUIDES[i]}">{i} inch</a>' if i in SIZE_GUIDES else f'{i} inch')
                        + f'</th><td>{cm(i)} cm</td><td>{e(kind)}</td><td>{e(trip)}</td></tr>'
                        for i, kind, trip in SIZE_ROWS)
    kg_rows = "".join(f"<tr><th scope=\"row\">{k} kg</th><td>{lb(k)} lb</td></tr>" for k in KG_ROWS)
    cm_rows = "".join(f'<tr><th scope="row">{c} cm</th><td>{inch(c)} in</td><td>{kind}</td></tr>' for c, kind in CM_ROWS)
    capacity_rows = "".join(f'<tr><th scope="row"><a href="{CAPACITY_GUIDES[kind]}">{kind}</a></th><td>{height}</td><td>{litres}</td><td>{empty}</td><td>{clothes}</td></tr>'
                            if kind in CAPACITY_GUIDES else f'<tr><th scope="row">{kind}</th><td>{height}</td><td>{litres}</td><td>{empty}</td><td>{clothes}</td></tr>'
                            for kind, height, litres, empty, clothes in CAPACITY_ROWS)
    air_rows, us_fit = "", []
    us = [22 * 2.54, 14 * 2.54, 9 * 2.54]
    for a in (airlines or {}).get("airlines", []) + [x for x in (intl or {}).get("airlines", []) if x.get("checker", True)]:
        c = a["cabin"]
        if not c.get("dims_cm"):
            continue
        air_rows += (f'<tr><th scope="row"><a href="{a["slug"]}.html">{e(a["name"])}</a></th>'
                     f'<td>{" x ".join(num(x) for x in c["dims_cm"])} cm' + (f'<span class="why">{num(c["total_cm"])} cm in total</span>' if c.get("total_cm") else "") + '</td>'
                     f'<td>{" x ".join(inch(x) for x in c["dims_cm"])} in' + (f'<span class="why">{inch(c["total_cm"])} in in total</span>' if c.get("total_cm") else "") + '</td>'
                     + (f'<td>{num(c["kg"])} kg<span class="why">{lb(c["kg"])} lb</span></td></tr>' if c.get("kg") else '<td>No limit given</td></tr>'))
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
    faq = [("What is the size of a small trolley bag in cm?", "A small trolley usually means a cabin trolley, about 55 cm (%s inches) tall. Many are 36–41 cm wide, but IndiGo's cabin limit is 55 x 35 x 25 cm, so check all three sides before you buy." % inch(55)),
           ("What is the size of a medium trolley bag in cm?", "Most medium trolleys sold in India are 65–69 cm (%s–%s inches) tall and 135–147 cm in total, from the 36 models we read. They listed 45–93 litres, and 69 litres was typical." % (inch(65), inch(69))),
           ("What is 20 inch luggage in cm?", "20 inches is %s cm. That's smaller than the usual 55 cm cabin trolley sold in India, though some brands sell 55 cm bags as \"20 inch\"." % cm(20)),
           ("Is a 24 inch suitcase cabin or check-in?", "Check-in. 24 inches is %s cm, too tall for the 55–56 cm cabin limits of Indian airlines. It's a small medium-size bag, good for 4–6 days." % cm(24)),
           ("How many inches is a 55 cm cabin bag?", "55 cm is %s inches." % inch(55)),
           ("What is 22 x 14 x 9 inches in cm?", us_answer),
           ("How many pounds is 23 kg?", "23 kg is about %s lb. 7 kg, the usual Indian cabin bag limit, is about %s lb." % (lb(23), lb(7)))]
    faq_html, faq_schema = faq_block(faq)
    picks_html = top_picks(cfg, [(deals_by_asin[a], label, why) for a, label, why in SIZE_CHART_PICKS if a in deals_by_asin], "../",
                           "Our picks for each size",
                           'Why we chose them: <a href="../guides/cabin-luggage-guide.html#our-cabin-bag-picks">cabin</a>, '
                           '<a href="../guides/24-inch-trolley-bag-size.html#our-picks">medium</a> and '
                           '<a href="../guides/28-inch-trolley-bag-size.html#our-picks-all-within-158-cm-by-their-listed-size">large</a> picks compared')
    end_html = next_step([("../guides/cabin-luggage-guide.html#our-cabin-bag-picks", "Cabin trolleys that fit IndiGo and Air India"),
                          ("../guides/24-inch-trolley-bag-size.html#our-picks", "Medium check-in trolleys (65–69 cm)"),
                          ("../guides/28-inch-trolley-bag-size.html#our-picks-all-within-158-cm-by-their-listed-size", "Large trolleys within the 158 cm limit"),
                          ("checker.html", "Check your own bag against every airline")],
                         "Found your size? Pick a bag", "See the bags we picked for that size, with each one's listed size, weight and the airlines it fits.")
    size_fig = diagram_figure("luggage-sizes", "../") if "luggage-sizes" in DIAGRAMS else ""
    title = "Trolley bag size chart: cm, inches, litres and kg"
    seo = "Trolley bag sizes in cm and inches: suitcase size chart"
    desc = ("Trolley bag sizes in cm: 20 inch is %s cm, 24 inch %s cm, 28 inch %s cm. Cabin, medium and large suitcase sizes "
            "with litres, kg and airline limits." % (cm(20), cm(24), cm(28)))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Baggage rules</a><span>/</span>Size chart</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">Updated {fmt_date(updated)}</p>"""
    body = f"""{page_head("luggage", f'<div class="media media-tile tint-luggage">{icon("ruler", "icon media-icon")}</div>', inner, "../")}
<div class="wrap"><article class="guide">
<p class="lead">Trolley bags are sold by height. Here is each size in inches and cm, with the trip it suits. Tap a size for its full guide.</p>
<h2>Trolley sizes in inches and cm</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Inches</th><th>cm</th><th>Size</th><th>Trip length</th></tr></thead><tbody>{size_rows}</tbody></table></div>
<p class="small">Sizes are the bag's height. Sellers don't always say whether it includes the wheels, so check the full size on the listing.</p>
{picks_html}
<h2>Indian trolley sizes in cm, in inches</h2>
<p>Indian brands list trolleys by height in cm. Here is each common height in inches.</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Listed height</th><th>Inches</th><th>Size</th></tr></thead><tbody>{cm_rows}</tbody></table></div>
<div class="answer"><h2>Quick answer</h2><ul>{"".join("<li>%s</li>" % e(x) for x in quick)}</ul></div>
<h2>Convert inches, cm, kg and lb</h2>
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
{size_fig}
{('<h2>Cabin bag limits in inches: Indian and international airlines</h2><div class="table-wrap"><table class="compare snug"><thead><tr><th>Airline</th><th>Size limit (cm)</th><th>In inches</th><th>Weight</th></tr></thead><tbody>' + air_rows + '</tbody></table></div><p class="checked">Economy limits: domestic flights for Indian airlines, India routes for international airlines. From our <a href="index.html">baggage rules</a> and <a href="international.html">international baggage</a> pages. Check your ticket before you fly.</p>') if air_rows else ""}
<h2>Size chart in litres and kg</h2>
<p>From 80 trolley models we read on Amazon.in on 6 Nov 2026. The clothes column is our rough estimate, not a test. Your airline ticket is usually the real limit. See <a href="../guides/trolley-bag-capacity-kg-litres.html">trolley bag capacity in kg and litres</a>.</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Size</th><th>Height</th><th>Listed litres (typical)</th><th>Empty bag (typical)</th><th>Clothes it could hold</th></tr></thead><tbody>{capacity_rows}</tbody></table></div>
<h2>Check-in bag size</h2>
<p>Most Indian airlines limit each checked bag to <strong>158 cm in total</strong> (length + width + height), which is about {inch(158)} inches, and <strong>32 kg</strong> (about {lb(32)} lb). Many large trolleys go over that: of the 31 large models we checked on Amazon.in on 6 Nov 2026, <strong>26 were listed over 158 cm</strong>. See <a href="../guides/28-inch-trolley-bag-size.html">the 5 that weren't</a>.</p>
<h2>Kilograms to pounds</h2>
<p>Indian airlines use kg. Foreign airlines, US websites and some luggage scales show pounds.</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>kg</th><th>Pounds (lb)</th></tr></thead><tbody>{kg_rows}</tbody></table></div>
{end_html}
{faq_html}
<p>More help: <a href="../guides/trolley-bag-capacity-kg-litres.html">how many kg each size holds</a>, <a href="../guides/20-inch-trolley-bag-size.html">20 inch</a>, <a href="../guides/22-inch-trolley-bag-size.html">22 inch</a>, <a href="../guides/24-inch-trolley-bag-size.html">24 inch</a>, <a href="../guides/26-inch-trolley-bag-size.html">26 inch</a>, <a href="../guides/28-inch-trolley-bag-size.html">28 inch</a> and <a href="../guides/32-inch-trolley-bag-size.html">32 inch</a> trolleys in detail, <a href="../guides/trolley-bag-size-for-international-travel.html">a bag for international flights</a>, <a href="../guides/luggage-size-guide.html">what size luggage you need</a> and <a href="../guides/cabin-luggage-guide.html">how to pick a cabin trolley</a>.</p>
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
# Picks under the bag weight calculator. Keep the reasons true to each pick's listed specs in data/deals.json.
WEIGHT_PICKS = [
    ("B07Q822CWX", "Weigh it at home", "A hand-held luggage scale: hook the bag on and lift. It reads up to 50 kg in 0.1 kg steps, and the battery is included."),
    ("B0F5HGLC5Q", "Light cabin trolley", "2.2 kg empty, so about 4.8 kg of a 7 kg cabin limit is left for your things. Fits Air India by its listed size."),
    ("B0GNSKLF5Z", "Light medium trolley", "2.52 kg empty, the lightest medium trolley we found, so about 12.5 kg of a 15 kg fare is left for your things."),
]
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
    by_asin = {d["asin"]: d for d in deals}
    weight_rows = [(by_asin[a], label, why) for a, label, why in WEIGHT_PICKS if a in by_asin]
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
{top_picks(cfg, weight_rows, "../", "Over the limit? Weigh it, or start with a lighter bag")}
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


# Destination packing lists (guides) linked from the matching checklist, when the guide exists.
PACKING_GUIDES = {"abroad": (("dubai", "Dubai"), ("thailand", "Thailand"), ("bali", "Bali")),
                  "beach": (("goa", "Goa"), ("andaman", "Andaman"), ("thailand", "Thailand"), ("bali", "Bali"))}


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
        lists = [(s_, place) for s_, place in PACKING_GUIDES.get(slug, ()) if (ARTICLES_DIR / ("%s-packing-list.md" % s_)).exists()]
        if lists:
            going_html += '<p class="small">Want the full list, with what to wear and why? Read our packing lists for %s.</p>' % and_list(
                f'<a href="../guides/{s_}-packing-list.html">{place}</a>' for s_, place in lists)
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
        # Amazon's Linking Requirements: no prices and no ratings (stars or rating counts) outside the API.
        text = json.dumps([d.get(k) for k in ("title", "note", "highlights", "best_for", "skip_if")], ensure_ascii=False)
        if re.search(r"(₹|\bRs\.?\s?|\bINR\s?)\d|\bratings\b|\bout of 5\b|\d stars?\b|★", text, re.I):
            sys.exit("Error: deal %s mentions a price or Amazon ratings. Leave those to Amazon.in." % d["asin"])
    deals_by_asin = {d["asin"]: d for d in deals}
    articles = load_articles()
    articles_by_slug = {a["slug"]: a for a in articles}
    trips = load_articles(TRIPS_DIR) if TRIPS_DIR.exists() else []
    # A trip with an unexpired "feature_until: YYYY-MM-DD" goes first, then "priority: 1" trips, then the rest by date
    trips.sort(key=lambda t: (t.get("feature_until", "") < date.today().isoformat(), -int(t.get("priority", 0))))

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
    indigo = next((a["cabin"]["dims_cm"] for a in airlines["airlines"] if a["slug"] == "indigo"), None) if airlines else None
    PICK_ART.update(pick_art.build_all(deals, indigo or (55, 35, 25)))
    (DOCS / "assets" / "picks").mkdir(exist_ok=True)
    for asin, (svg, alt) in PICK_ART.items():
        (DOCS / "assets" / "picks" / (asin + ".svg")).write_text(svg, encoding="utf-8")
    if airlines:
        TOOLS.append(("baggage/index.html", "Airline baggage rules", "IndiGo &middot; Air India &middot; Akasa &middot; SpiceJet",
                      "Baggage rules for Indian airlines", "Cabin bag size and weight, and free check-in baggage, all in one place.",
                      "See the rules", "plane", "travel-gear", BAGGAGE_PHOTO))
        TOOLS.append(("baggage/checker.html", "Cabin bag checker", "Free tool", "Will my bag fit? Cabin bag checker",
                      "Type your bag's size and weight and see which airlines accept it as a cabin bag.", "Check your bag", "ruler", "luggage", "plane-cabin"))
    extra = load_extra_baggage(airlines)
    if extra:
        TOOLS.append((EXTRA_PATH, "Extra baggage charges", "IndiGo &middot; Air India &middot; Akasa &middot; SpiceJet",
                      "Extra baggage charges by airline", "Prepaid slabs, the airport rate per kg, extra bags and cabin bags over 7 kg, side by side.",
                      "Compare charges", "suitcase", "luggage", ""))
    if intl_airlines:
        TOOLS.append(("baggage/international.html", "International baggage rules", "Emirates &middot; Qatar &middot; Saudia &middot; Singapore",
                      "Baggage rules for international flights", "Cabin bag size and checked kg by fare for %d airlines flying from India to %s." % (
                          len(intl_airlines["airlines"]), intl_where(intl_airlines["airlines"])),
                      "See the rules", "plane", "luggage", "plane-window"))
    TOOLS.append(("baggage/luggage-size-chart.html", "Luggage size chart", "Inches &middot; cm &middot; kg &middot; lb",
                  "Luggage size chart: inches to cm", "20, 24 or 28 inch? Trolley sizes in cm, airline cabin limits in inches, and kg to pounds.",
                  "See the chart", "ruler", "travel-gear", "tape-measure"))
    if FLIGHT_ITEMS_FILE.exists():
        TOOLS.append(("baggage/can-i-carry.html", "Can I carry it on a flight?", "Free tool", "Can I carry it on a flight?",
                      "Power banks, perfume, pickles, dry coconut: see what goes in your cabin bag and what goes in check-in.",
                      "Search items", "shield", "watches", "baggage-belt"))
    customs = load_customs()
    if customs:
        TOOLS.append((CUSTOMS_PATH, "Indian customs rules", "Duty free &middot; gold &middot; alcohol &middot; cash",
                      "Customs rules for flying into India", "The ₹75,000 duty-free allowance, gold, alcohol, iPhones and cash: what you can bring without paying duty.",
                      "See the rules", "globe", "travel-gear", ""))
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
    if HINDI_PAGES:
        hindi_pages.register(sys.modules[__name__], extra)  # Hindi size chart, item pages and extra baggage pages
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
    # Seasonal guides with an unexpired feature_until go first on the home page: the season that ends soonest first
    # (Christmas pages before New Year ones), then "priority: 1" guides, then newest first
    today = date.today().isoformat()

    def home_key(a):
        until = a.get("feature_until", "")
        live = until >= today
        return (not live, until if live else "", -int(a.get("priority", 0)))

    home_guides = sorted(articles, key=home_key)
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
{('<section class="wrap section">' + section_head("Buying guides", '<a class="see-all" href="guides/index.html">All guides ' + icon("arrow", "icon icon-sm") + '</a>') + guide_cards(cfg, home_guides[:3], "") + '</section>') if articles else ''}
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
            fit_html = f"""<section class="pick-fit"><h2>Will it fit as a cabin bag?</h2>
<p>Its listed size is {" x ".join(num(x) for x in dims)} cm, {num(sum(dims))} cm in total. Here's how that compares with each airline's cabin limit.</p>
<table class="specs">{fit_rows}</table>
<p class="small"><a href="../baggage/checker.html?bag={d['asin']}">Open it in the cabin bag checker</a> to add its packed weight. Always check your airline before you fly.</p></section>"""
        body = f"""<div class="wrap">
<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="../category/{d['category']}.html">{e(cat['name'])}</a></nav>
<article class="pick">
  <div class="pick-top">
    {brand}
    <h1>{e(d['title'])}</h1>
    {note}
    {best}
    <div class="cta-box">
      {deal_badge(d, "deal-note")}
      {buy_button(cfg, d, "Check today's price on Amazon", big=True)}
      <p>Prices and stock change often. Amazon.in shows the latest price and real photos.</p>
    </div>
  </div>
  {fit_html}
  <figure class="pick-media pick-art"><div class="art tint-{d['category']}">{pick_img(d, "../", eager=True)}</div>
    <figcaption>Our drawing, made from the listed size, colour and details. It is not a photo of the product: Amazon.in shows the real photos.</figcaption></figure>
  <div class="pick-info">
    <h2>Key features</h2>
    <ul class="features">{features}</ul>
    {specs_html}
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
        pages.append(write(path, page(cfg, d["title"], desc, body, 1, path, [crumbs], share_image=share_image(d["asin"]))))
        lastmod[path] = d["added_at"][:10]

    # When Amazon changes a listing we move the pick to the new ASIN ("old_asins" in deals.json). The old address
    # keeps a plain page with a link to the new one: no auto-redirect, kept out of the sitemap and search results.
    for d in deals:
        for old in d.get("old_asins", []):
            path = "picks/%s.html" % old
            body = (f'<div class="wrap"><article class="prose"><h1>This pick has moved</h1>'
                    f'<p>Amazon changed the listing we linked to, so this pick now has a new page:</p>'
                    f'<p><a href="{d["asin"]}.html">{e(d["title"])}</a></p></article></div>')
            write(path, page(cfg, "This pick has moved", "This pick now has a new page: %s." % d["title"], body, 1, path,
                             robots="noindex"))

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
        build_baggage(cfg, deals, airlines, pages, lastmod, intl_airlines, extra)
    if extra:
        build_extra_baggage(cfg, deals_by_asin, extra, pages, lastmod)
    if PACKING_FILE.exists():
        build_packing(cfg, deals_by_asin, pages, lastmod, trips)
    if RAILWAYS_FILE.exists():
        build_railways(cfg, deals, pages, lastmod)
    if FLIGHT_ITEMS_FILE.exists():
        build_can_i_carry(cfg, deals_by_asin, pages, lastmod)
    if customs:
        build_customs(cfg, deals_by_asin, customs, pages, lastmod)
    build_size_chart(cfg, deals_by_asin, airlines, pages, lastmod, intl_airlines)
    build_tools(cfg, deals, pages, lastmod)
    if trips:
        build_trips(cfg, trips, deals_by_asin, pages, lastmod)
    if trips_hi:
        build_trips_hi(cfg, trips_hi, deals_by_asin, pages, lastmod)
    if HINDI_PAGES:
        build_hindi(cfg, deals, airlines, pages, lastmod)
        hindi_pages.build_all(sys.modules[__name__], cfg, deals, deals_by_asin, airlines, intl_airlines, extra, pages, lastmod)

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
    photo_credits = ("<h2>Photos, drawings and diagrams</h2>\n<p>Each pick has a simple drawing that we make ourselves from its listed "
                     "size, colour and details, drawn to scale where the listing gives a size. It is not a photo of the product, so check "
                     "the real photos on Amazon.in before you buy. Our diagrams are drawn by us too.</p>")
    if PHOTOS:
        photo_credits += ("\n<p>The photos on our home, category and guide pages are free stock photos that set the scene. "
                          "They are not photos of the products we pick.</p>\n<ul>%s</ul>"
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
<p>Our trip guides also have hotel links to {and_list(list(cfg["booking_partners"]))}, and flight links to {and_list([n for n, f in cfg["flight_partners"].items() if "domestic" in f["scope"]])}. Our <a href="baggage/international.html">international baggage page</a> has flight links to {and_list([n for n, f in cfg["flight_partners"].items() if "international" in f["scope"]])}. Our <a href="guides/vip-bags-guide.html">VIP bags guide</a> and <a href="guides/vip-bags-coupon-code.html">VIP coupon page</a> have links to VIP's own store. These go through EarnKaro, an affiliate service. If you book or buy through one, we may earn a commission, and you pay the same price. Amazon is not part of these links.</p>
<p>The VIP coupon page shows a code that EarnKaro lists for VIP's store. We test it in VIP's cart without placing an order, and show the date of our last check.</p>
<p>Links that earn us a commission are marked "Paid link". Commissions help us keep this site free. They do not change which products we pick.</p>"""),
        "privacy.html": ("Privacy policy", f"""<h1>Privacy policy</h1>
<p>{name} does not ask for your name, email or any personal details, and this site sets no cookies of its own, except one that remembers your language if you choose Google Translate (see below).</p>
<ul>
<li>This site is hosted on GitHub Pages. GitHub may keep basic server logs, such as IP addresses, for security. See GitHub's privacy statement.</li>
<li>Fonts are loaded from Google Fonts, which may log your IP address. See Google's privacy policy.</li>
<li>If you pick a language in the language menu other than English or our own Hindi pages, the page loads Google Translate, which sends the page text to Google to translate it. A cookie called "googtrans" then remembers your choice on this site. Pick English in the menu to remove it.</li>
<li>When you click a link to Amazon.in, Amazon may set cookies to track the referral. See Amazon.in's privacy notice.</li>
<li>When you click a hotel or flight link in a trip guide, a flight link on our international baggage page, or a shop link on our VIP bags guide or VIP coupon page, it goes through EarnKaro's link services (bitli.in and linkredirect.in) to that site. These services and that site may set cookies and log your visit to track the referral. See their privacy policies.</li>
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
        "privacy.html": "%s asks for no personal details and sets no cookies of its own. What GitHub, Google Fonts, Amazon and our hotel, flight and shop link partners may log when you visit." % cfg["site_name"],
        "contact.html": "Questions, corrections or ideas for %s? Reach us on Telegram or WhatsApp." % cfg["site_name"],
    }
    for path, (title, text) in info.items():
        body = f'<div class="wrap"><article class="prose">{text}</article></div>'
        pages.append(write(path, page(cfg, title, info_desc.get(path, title + " - " + cfg["site_name"]), body, 0, path,
                                      robots="noindex" if path == "404.html" else "max-image-preview:large")))

    if HINDI_PAGES:
        hindi_pages.check_links(sys.modules[__name__], [p for p in pages if p.startswith("hi/")])

    # Sitemap and robots (only once we know the live address)
    if cfg["base_url"]:
        base = cfg["base_url"].rstrip("/") + "/"
        def images(path):
            """Our photos and diagrams on a page, listed for Google Images."""
            text = (DOCS / path).read_text(encoding="utf-8")
            found = sorted(set(re.findall(r'assets/photos/[a-z0-9-]+-1600\.webp|assets/diagrams/[a-z0-9-]+\.svg', text)))
            if path.startswith("picks/"):
                found.append("assets/picks/%s.svg" % path[6:-5])  # only its own drawing, not the cards below
            return "".join("<image:image><image:loc>%s</image:loc></image:image>" % e(base + f) for f in found)

        urls = "".join("<url><loc>%s</loc>%s%s</url>" % (e(base + ("" if p == "index.html" else p)),
                                                         "<lastmod>%s</lastmod>" % lastmod[p] if p in lastmod else "", images(p))
                       for p in pages if p != "404.html")
        (DOCS / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">%s</urlset>\n' % urls,
            encoding="utf-8",
        )
        # Atom feed of the guides: readers can follow it, and Google accepts it as a second sitemap.
        entries = sorted([("guides/%s.html" % a["slug"], a) for a in articles] + [("trips/%s.html" % t["slug"], t) for t in trips],
                         key=lambda x: x[1]["updated"], reverse=True)
        (DOCS / "feed.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>%s guides</title><id>%s</id>'
            '<link rel="self" href="%sfeed.xml"/><link href="%s"/><updated>%sT00:00:00+05:30</updated><author><name>%s</name></author>%s</feed>\n'
            % (e(cfg["site_name"]), e(base), e(base), e(base), entries[0][1]["updated"], e(cfg["site_name"]),
               "".join('<entry><title>%s</title><id>%s</id><link href="%s"/><updated>%sT00:00:00+05:30</updated><summary>%s</summary></entry>'
                       % (e(x["title"]), e(base + path), e(base + path), x["updated"], e(x["description"])) for path, x in entries)),
            encoding="utf-8",
        )
        (DOCS / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\nSitemap: %sfeed.xml\n" % (base, base), encoding="utf-8")
        if cfg.get("indexnow_key"):
            # Public key file that proves to IndexNow (Bing and others) that we own this site; see scripts/indexnow.py.
            (DOCS / (cfg["indexnow_key"] + ".txt")).write_text(cfg["indexnow_key"], encoding="utf-8")

    # Self-check: Amazon requires the disclosure everywhere, and no page may auto-redirect.
    moved = {old for d in deals for old in d.get("old_asins", [])}
    codes = [c["code"] for c in load_coupons().values()]
    for html_file in DOCS.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        if DISCLOSURE not in text:
            sys.exit("Error: disclosure missing on %s" % html_file)
        if "amazon.in/" in text and any(re.search(r"\b%s\b" % re.escape(code), text) for code in codes):
            sys.exit("Error: %s shows a coupon code and Amazon links. Keep coupon text (titles and descriptions too) off pages with Amazon links." % html_file)
        if re.search(r'http-equiv="refresh"|location\.(href|replace)', text, re.I):
            sys.exit("Error: auto-redirect found on %s" % html_file)
        if html_file.parent.name == "picks" and "assets/photos/" in text:
            sys.exit("Error: a stock photo is on pick page %s, where it could pass as the product" % html_file)
        if (html_file.parent.name == "picks" and html_file.stem not in moved
                and 'src="../assets/picks/%s.svg"' % html_file.stem not in text):
            sys.exit("Error: pick page %s doesn't show its drawing" % html_file)
    # Our drawings may only be our own vector shapes: no embedded or linked pictures, and always the note.
    for svg_file in (DOCS / "assets" / "picks").glob("*.svg"):
        text = svg_file.read_text(encoding="utf-8")
        if re.search(r"<image|<foreignObject|href=|data:", text) or pick_art.NOTE not in text:
            sys.exit("Error: %s must be our own drawing with the note '%s'" % (svg_file, pick_art.NOTE))

    print("Built %d pages (%d picks, %d guides) into docs/" % (len(pages), len(deals), len(articles)))


if __name__ == "__main__":
    build()
