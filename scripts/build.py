"""Build the static website into docs/ from data/ and content/.

Run:  python3 scripts/build.py
Amazon rules built in: disclosure on every page, no prices, no ratings,
no product images, no auto-redirects, buy links marked as paid.
"""

import re
import shutil
import sys
from datetime import date, datetime
from html import escape as e

from common import ROOT, amazon_link, load_config, load_deals

DOCS = ROOT / "docs"
ARTICLES_DIR = ROOT / "content" / "articles"
STATIC_DIR = ROOT / "static"
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
KEEP_IN_DOCS = {"CNAME"}
BUY_ATTRS = 'rel="sponsored nofollow noopener" target="_blank"'
FONTS = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"

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
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "shield": '<path d="M12 3l7 3v6c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "ruler": '<rect x="2.5" y="8" width="19" height="8" rx="1.5"/><path d="M6.5 8v3M10.5 8v4M14.5 8v3M18.5 8v4"/>',
    "pin": '<path d="M12 21s-6-5.4-6-10a6 6 0 0 1 12 0c0 4.6-6 10-6 10z"/><circle cx="12" cy="11" r="2.2"/>',
    "send": '<path d="M21 4 3 11l6.5 2.5L19 7l-7 8.2V20l3.2-3.6L19 19.5z"/>',
    "chat": '<path d="M20.5 11.5a8.5 8.5 0 0 1-12.6 7.4L3.5 20l1.2-4.2A8.5 8.5 0 1 1 20.5 11.5z"/>',
    "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1.1 1 1.8V16h5v-.3c0-.7.4-1.4 1-1.8A6 6 0 0 0 12 3z"/>',
}


def icon(name, cls="icon"):
    return ('<svg class="%s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>' % (cls, ICONS[name]))


def fmt_date(value):
    d = datetime.fromisoformat(value) if "T" in value else datetime.strptime(value, "%Y-%m-%d")
    return "%d %s" % (d.day, d.strftime("%b %Y"))


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

def page(cfg, title, description, body, depth, path):
    p = "../" * depth
    name = e(cfg["site_name"])
    full_title = e(title) + " | " + name if title else name + " | " + e(cfg["tagline"])
    head_extra = ""
    if cfg["base_url"]:
        base = cfg["base_url"].rstrip("/")
        url = base + "/" + path
        head_extra = ('<link rel="canonical" href="%s">\n<meta property="og:url" content="%s">\n'
                      '<meta property="og:image" content="%s/assets/logo.png">' % (e(url), e(url), e(base)))
    if cfg.get("google_site_verification"):
        head_extra += '\n<meta name="google-site-verification" content="%s">' % e(cfg["google_site_verification"])
    nav = "".join(
        '<a href="%scategory/%s.html">%s</a>' % (p, slug, e(c["name"].split(" &")[0]))
        for slug, c in cfg["categories"].items()
    )
    tg = telegram_url(cfg)
    tg_btn = ('<a class="nav-cta" href="%s" target="_blank" rel="noopener">%s<span>Telegram</span></a>'
              % (e(tg), icon("send", "icon icon-sm"))) if tg else ""
    foot_cats = "".join(
        '<li><a href="%scategory/%s.html">%s</a></li>' % (p, slug, e(c["name"])) for slug, c in cfg["categories"].items()
    )
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{e(description)}">
<meta property="og:title" content="{e(title or cfg['site_name'])}">
<meta property="og:description" content="{e(description)}">
<meta property="og:site_name" content="{name}">
<meta property="og:type" content="website">
{head_extra}
<link rel="icon" type="image/png" href="{p}assets/logo.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{p}assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand" href="{p}index.html"><img src="{p}assets/logo.png" alt="" width="34" height="34"><span>{name}</span></a>
    <nav class="main-nav">{nav}<a href="{p}guides/index.html">Guides</a></nav>
    {tg_btn}
  </div>
</header>
<p class="disclosure-bar"><span class="wrap">We may earn a commission when you buy through links on this site. {DISCLOSURE}</span></p>
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
    <p>{DISCLOSURE} Prices and availability are shown only on Amazon.in and can change at any time.</p>
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


def media(cfg, category, cls="media"):
    return f'<div class="{cls} tint-{category}">{icon(cfg["categories"][category]["icon"], "icon media-icon")}</div>'


def chips(tags, cls="chip-tag"):
    return "".join('<span class="%s">%s</span>' % (cls, e(t)) for t in tags)


def card(cfg, deal, p):
    href = f"{p}picks/{deal['asin']}.html"
    badge = f'<span class="badge">Best for {e(deal["best_for"][0])}</span>' if deal.get("best_for") else ""
    brand = f'<p class="brand-name">{e(deal["brand"])}</p>' if deal.get("brand") else ""
    feats = "".join("<li>%s%s</li>" % (icon("check", "icon icon-check"), e(h)) for h in deal["highlights"][:2])
    return f"""<article class="card">
  <a class="card-media" href="{href}" tabindex="-1" aria-hidden="true">{media(cfg, deal['category'])}{badge}</a>
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
    {brand}
    <h4><a href="{p}picks/{deal['asin']}.html">{e(deal['title'])}</a></h4>
    <ul class="mini-features">{items}</ul>
    <div class="card-foot">{buy_button(cfg, deal)}</div>
  </div>
</aside>"""


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
      <p>Hand-picked bags, luggage and watches on sale, plus quick buying tips. No spam.</p>
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


def render_markdown(md, cfg, deals_by_asin, p, source):
    out, para, items, list_tag = [], [], [], None

    def flush():
        nonlocal para, items, list_tag
        if para:
            out.append("<p>%s</p>" % md_inline(" ".join(para), p))
            para = []
        if items:
            out.append("<%s>%s</%s>" % (list_tag, "".join("<li>%s</li>" % md_inline(i, p) for i in items), list_tag))
            items, list_tag = [], None

    for raw in md.splitlines():
        line = raw.strip()
        pick = re.fullmatch(r"\[\[pick:([A-Z0-9]{10})\]\]", line)
        ul = re.match(r"^- (.+)", line)
        ol = re.match(r"^\d+\. (.+)", line)
        if not line:
            flush()
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


def load_articles():
    articles = []
    for path in sorted(ARTICLES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        if not match:
            sys.exit("Error: %s is missing the --- front matter block" % path.name)
        meta = dict(line.split(": ", 1) for line in match.group(1).splitlines() if ": " in line)
        meta.update(slug=path.stem, body=match.group(2))
        meta["minutes"] = max(1, round(len(re.sub(r"\[\[pick:\w+\]\]", "", meta["body"]).split()) / 200))
        articles.append(meta)
    return sorted(articles, key=lambda a: a["date"], reverse=True)


def guide_cards(cfg, articles, p):
    cards = []
    for a in articles:
        cat = a.get("category")
        art = icon(cfg["categories"][cat]["icon"], "icon guide-icon") if cat in cfg["categories"] else icon("book", "icon guide-icon")
        cards.append(f"""<a class="guide-card" href="{p}guides/{a['slug']}.html">
  <div class="guide-art tint-{e(cat or 'none')}">{art}</div>
  <div class="guide-body">
    <p class="eyebrow">Buying guide &middot; {a['minutes']} min read</p>
    <h3>{e(a['title'])}</h3>
    <p>{e(a['description'])}</p>
    <span class="more">Read guide {icon("arrow", "icon icon-sm")}</span>
  </div>
</a>""")
    return '<div class="guide-grid">%s</div>' % "".join(cards)


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

    if DOCS.exists():
        for child in DOCS.iterdir():
            if child.name in KEEP_IN_DOCS:
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    DOCS.mkdir(exist_ok=True)
    shutil.copytree(STATIC_DIR, DOCS / "assets")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    pages = []
    tg = telegram_url(cfg)

    # Home
    cat_tiles = "".join(
        f"""<a class="cat-tile" href="category/{slug}.html">
  {media(cfg, slug, 'media media-tile')}
  <div><h3>{e(c['name'])}</h3><p>{sum(1 for d in deals if d['category'] == slug)} picks</p></div>
  {icon("arrow", "icon icon-sm tile-arrow")}
</a>"""
        for slug, c in cfg["categories"].items()
    )
    hero_art = "".join(
        f'<div class="hero-bubble tint-{slug}">{icon(c["icon"], "icon")}</div>' for slug, c in cfg["categories"].items()
    )
    tg_cta = (f'<a class="btn btn-ghost" href="{e(tg)}" target="_blank" rel="noopener">{icon("send", "icon icon-sm")} Join on Telegram</a>'
              if tg else "")
    picks_html = grid(cfg, deals[:8], "") if deals else '<p class="muted">New picks are coming soon.</p>'
    body = f"""<section class="hero">
  <div class="wrap hero-row">
    <div class="hero-copy">
      <p class="eyebrow eyebrow-light">Bags &middot; Luggage &middot; Watches &middot; Travel gear</p>
      <h1>Buy the right bag or watch, the first time.</h1>
      <p class="lead">Hand-picked products from Amazon India. We check size, material, weight and warranty, then explain it in simple words.</p>
      <div class="hero-ctas"><a class="btn btn-amazon btn-big" href="#latest">See latest picks</a>{tg_cta}</div>
    </div>
    <div class="hero-art" aria-hidden="true">{hero_art}</div>
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
{('<section class="wrap section">' + section_head("Buying guides", '<a class="see-all" href="guides/index.html">All guides ' + icon("arrow", "icon icon-sm") + '</a>') + guide_cards(cfg, articles[:3], "") + '</section>') if articles else ''}
{telegram_band(cfg, "")}"""
    pages.append(write("index.html", page(cfg, "", cfg["tagline"], body, 0, "")))

    # Pick pages
    for d in deals:
        cat = cfg["categories"][d["category"]]
        more = [x for x in deals if x["category"] == d["category"] and x["asin"] != d["asin"]][:4]
        features = "".join("<li>%s%s</li>" % (icon("check", "icon icon-check"), e(h)) for h in d["highlights"])
        note = f'<p class="lead">{e(d["note"])}</p>' if d.get("note") else ""
        brand = f'<p class="brand-name">{e(d["brand"])}</p>' if d.get("brand") else ""
        best = f'<div class="chips"><span class="chips-label">Best for</span>{chips(d["best_for"])}</div>' if d.get("best_for") else ""
        more_html = (f'<section class="wrap section">{section_head("More " + cat["name"])}{grid(cfg, more, "../")}</section>'
                     if more else "")
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
      {buy_button(cfg, d, "Check today's price on Amazon", big=True)}
      <p>Prices and stock change often. Amazon.in shows the latest price.</p>
    </div>
    <h2>Key features</h2>
    <ul class="features">{features}</ul>
    {tip_box(cfg, d['category'], '../', articles_by_slug)}
    <p class="muted small">Added {fmt_date(d['added_at'])}</p>
  </div>
</article>
</div>
{more_html}
{telegram_band(cfg, "../")}"""
        desc = d["note"] if d.get("note") else d["highlights"][0]
        pages.append(write("picks/%s.html" % d["asin"], page(cfg, d["title"], desc, body, 1, "picks/%s.html" % d["asin"])))

    # Category pages
    for slug, cat in cfg["categories"].items():
        items = [d for d in deals if d["category"] == slug]
        related = [a for a in articles if a.get("category") == slug]
        items_html = grid(cfg, items, "../") if items else '<p class="muted">New picks are coming soon.</p>'
        related_html = (f'<section class="section">{section_head("Guides")}{guide_cards(cfg, related, "../")}</section>'
                        if related else "")
        body = f"""<section class="page-head tint-{slug}">
  <div class="wrap page-head-row">
    {media(cfg, slug, 'media media-tile')}
    <div>
      <nav class="crumbs"><a href="../index.html">Home</a><span>/</span>{e(cat['name'])}</nav>
      <h1>{e(cat['name'])}</h1>
      <p class="lead">{e(cat['intro'])}</p>
    </div>
  </div>
</section>
<div class="wrap section">
  {tip_box(cfg, slug, '../', articles_by_slug)}
  {items_html}
  {related_html}
</div>
{telegram_band(cfg, "../")}"""
        desc = "Hand-picked %s from Amazon India. %s" % (cat["name"].lower(), cat["intro"])
        pages.append(write("category/%s.html" % slug, page(cfg, cat["name"], desc, body, 1, "category/%s.html" % slug)))

    # Guides
    body = f"""<section class="page-head">
  <div class="wrap"><h1>Buying guides</h1><p class="lead">Simple, honest guides to help you choose bags, luggage and watches.</p></div>
</section>
<div class="wrap section">{guide_cards(cfg, articles, "../") if articles else '<p class="muted">Coming soon.</p>'}</div>"""
    pages.append(write("guides/index.html", page(cfg, "Buying guides", "Simple buying guides for bags, luggage and watches.", body, 1, "guides/index.html")))
    for a in articles:
        content = render_markdown(a["body"], cfg, deals_by_asin, "../", a["slug"] + ".md")
        cat = a.get("category")
        art = media(cfg, cat, "media media-tile") if cat in cfg["categories"] else ""
        body = f"""<section class="page-head tint-{e(cat or 'none')}">
  <div class="wrap page-head-row">
    {art}
    <div>
      <nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="index.html">Guides</a></nav>
      <h1>{e(a['title'])}</h1>
      <p class="muted small">Updated {fmt_date(a['date'])} &middot; {a['minutes']} min read</p>
    </div>
  </div>
</section>
<div class="wrap"><article class="guide">{content}</article></div>
{telegram_band(cfg, "../")}"""
        pages.append(write("guides/%s.html" % a["slug"], page(cfg, a["title"], a["description"], body, 1, "guides/%s.html" % a["slug"])))

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
    info = {
        "about.html": ("About us", f"""<h1>About {name}</h1>
<p>{name} is a small team that helps shoppers in India pick good bags, luggage and watches on Amazon.in.</p>
<h2>How we choose products</h2>
<ul>
<li>We read the full product details: size, capacity, material, weight and warranty.</li>
<li>We pick products that suit everyday Indian use, like college, office commutes and domestic flights.</li>
<li>We never accept money from brands to list a product.</li>
</ul>
<p>We don't show prices because they change many times a day. The button on each pick takes you to Amazon.in, where you see the current price.</p>"""),
        "disclosure.html": ("Affiliate disclosure", f"""<h1>Affiliate disclosure</h1>
<p><strong>{DISCLOSURE}</strong></p>
<p>{name} is a participant in the Amazon Associates Programme. When you click a "Check price on Amazon" button and buy something, Amazon may pay us a small commission. You pay the same price.</p>
<p>Links that earn us a commission are marked "Paid link". Commissions help us keep this site free. They do not change which products we pick.</p>"""),
        "privacy.html": ("Privacy policy", f"""<h1>Privacy policy</h1>
<p>{name} does not ask for your name, email or any personal details, and this site does not set its own cookies.</p>
<ul>
<li>This site is hosted on GitHub Pages. GitHub may keep basic server logs, such as IP addresses, for security. See GitHub's privacy statement.</li>
<li>Fonts are loaded from Google Fonts, which may log your IP address. See Google's privacy policy.</li>
<li>When you click a link to Amazon.in, Amazon may set cookies to track the referral. See Amazon.in's privacy notice.</li>
<li>If you join our Telegram channel, Telegram's privacy policy applies.</li>
</ul>
<p>Questions? See our <a href="contact.html">contact page</a>.</p>"""),
        "contact.html": ("Contact", f"<h1>Contact</h1>\n<p>Have a question or found a mistake? Reach us here:</p>\n{contact_html}"),
        "404.html": ("Page not found", '<h1>Page not found</h1><p>This page has moved or no longer exists. <a href="index.html">Go to the home page</a>.</p>'),
    }
    for path, (title, text) in info.items():
        body = f'<div class="wrap"><article class="prose">{text}</article></div>'
        pages.append(write(path, page(cfg, title, title + " - " + cfg["site_name"], body, 0, path)))

    # Sitemap and robots (only once we know the live address)
    if cfg["base_url"]:
        base = cfg["base_url"].rstrip("/") + "/"
        urls = "".join("<url><loc>%s</loc></url>" % e(base + ("" if p == "index.html" else p)) for p in pages if p != "404.html")
        (DOCS / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls,
            encoding="utf-8",
        )
        (DOCS / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % base, encoding="utf-8")

    # Self-check: Amazon requires the disclosure everywhere, and no page may auto-redirect.
    for html_file in DOCS.rglob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        if DISCLOSURE not in text:
            sys.exit("Error: disclosure missing on %s" % html_file)
        if re.search(r'http-equiv="refresh"|location\.(href|replace)', text, re.I):
            sys.exit("Error: auto-redirect found on %s" % html_file)

    print("Built %d pages (%d picks, %d guides) into docs/" % (len(pages), len(deals), len(articles)))


if __name__ == "__main__":
    build()
