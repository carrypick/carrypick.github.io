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


def fmt_date(value):
    d = datetime.fromisoformat(value) if "T" in value else datetime.strptime(value, "%Y-%m-%d")
    return "%d %s" % (d.day, d.strftime("%b %Y"))


def telegram_url(cfg):
    channel = cfg["telegram_channel"].lstrip("@")
    return "https://t.me/" + channel if channel else ""


# ---------- page shell ----------

def page(cfg, title, description, body, depth, path):
    p = "../" * depth
    name = e(cfg["site_name"])
    full_title = e(title) + " | " + name if title else name + " | " + e(cfg["tagline"])
    canonical = ""
    if cfg["base_url"]:
        base = cfg["base_url"].rstrip("/")
        url = base + "/" + path
        canonical = '<link rel="canonical" href="%s">\n<meta property="og:url" content="%s">' % (e(url), e(url))
        canonical += '\n<meta property="og:image" content="%s/assets/logo.png">' % e(base)
    cats = "".join(
        '<a href="%scategory/%s.html">%s</a>' % (p, slug, e(c["name"])) for slug, c in cfg["categories"].items()
    )
    contact = '<a href="%scontact.html">Contact</a>' % p
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
{canonical}
<link rel="stylesheet" href="{p}assets/style.css">
<link rel="icon" type="image/png" href="{p}assets/logo.png">
</head>
<body>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand" href="{p}index.html">{name}</a>
    <nav class="main-nav"><a href="{p}guides/index.html">Guides</a><a href="{p}about.html">About</a></nav>
  </div>
  <p class="disclosure-bar wrap">We may earn a commission when you buy through links on this site. {DISCLOSURE}</p>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <nav class="footer-cats">{cats}</nav>
    <nav class="footer-legal"><a href="{p}disclosure.html">Affiliate disclosure</a><a href="{p}privacy.html">Privacy</a>{contact}</nav>
    <p class="muted small">{DISCLOSURE} Prices and availability are shown only on Amazon.in and can change at any time.</p>
    <p class="muted small">&copy; {date.today().year} {name}</p>
  </div>
</footer>
</body>
</html>
"""


# ---------- building blocks ----------

def buy_button(cfg, deal, label="Check price on Amazon", big=False):
    cls = "btn btn-big" if big else "btn"
    href = e(amazon_link(deal["asin"], cfg["amazon_tag"]))
    return f'<a class="{cls}" href="{href}" {BUY_ATTRS}>{label}</a><span class="paid">Paid link</span>'


def tile(cfg, category, big=False):
    emoji = cfg["categories"][category]["emoji"]
    cls = "tile tile-big" if big else "tile"
    return f'<div class="{cls} tile-{category}" aria-hidden="true">{emoji}</div>'


def card(cfg, deal, p):
    cat = cfg["categories"][deal["category"]]
    return f"""<article class="card">
  <a class="card-link" href="{p}picks/{deal['asin']}.html">
    {tile(cfg, deal['category'])}
    <div class="card-body">
      <p class="eyebrow">{e(cat['name'])}</p>
      <h3>{e(deal['title'])}</h3>
      <p class="muted">{e(deal['highlights'][0])}</p>
    </div>
  </a>
  <div class="card-actions">{buy_button(cfg, deal)}</div>
</article>"""


def grid(cfg, deals, p):
    return '<div class="grid">' + "\n".join(card(cfg, d, p) for d in deals) + "</div>"


def inline_pick(cfg, deal, p):
    items = "".join("<li>%s</li>" % e(h) for h in deal["highlights"][:3])
    return f"""<aside class="inline-pick">
  {tile(cfg, deal['category'])}
  <div>
    <h4><a href="{p}picks/{deal['asin']}.html">{e(deal['title'])}</a></h4>
    <ul>{items}</ul>
    <div class="card-actions">{buy_button(cfg, deal)}</div>
  </div>
</aside>"""


def telegram_box(cfg):
    url = telegram_url(cfg)
    if not url:
        return ""
    return f"""<section class="telegram-box">
  <h2>Get new picks on Telegram</h2>
  <p>We post a few hand-picked bags, luggage and watches every day. No spam.</p>
  <a class="btn btn-telegram" href="{e(url)}" target="_blank" rel="noopener">Join our Telegram channel</a>
</section>"""


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
        articles.append(meta)
    return sorted(articles, key=lambda a: a["date"], reverse=True)


def guide_list(articles, p):
    rows = "".join(
        f"""<li><a href="{p}guides/{a['slug']}.html"><strong>{e(a['title'])}</strong>
<span class="muted">{e(a['description'])}</span></a></li>"""
        for a in articles
    )
    return f'<ul class="guide-list">{rows}</ul>'


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

    if DOCS.exists():
        for child in DOCS.iterdir():
            if child.name in KEEP_IN_DOCS:
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    DOCS.mkdir(exist_ok=True)
    shutil.copytree(STATIC_DIR, DOCS / "assets")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    pages = []

    # Home
    chips = "".join(
        f'<a class="chip" href="category/{slug}.html">{c["emoji"]} {e(c["name"])}</a>'
        for slug, c in cfg["categories"].items()
    )
    picks_html = grid(cfg, deals[:12], "") if deals else '<p class="muted">New picks are coming soon.</p>'
    guides_html = guide_list(articles[:3], "") if articles else ""
    body = f"""<section class="hero">
  <h1>{e(cfg['tagline'])}</h1>
  <p class="lead">We check the size, material, warranty and real-world use, so you can buy the right bag or watch the first time.</p>
  <nav class="chips">{chips}</nav>
</section>
<section><h2>Latest picks</h2>{picks_html}</section>
{('<section><h2>Buying guides</h2>' + guides_html + '<p><a href="guides/index.html">All guides &rarr;</a></p></section>') if guides_html else ''}
{telegram_box(cfg)}"""
    pages.append(write("index.html", page(cfg, "", cfg["tagline"], body, 0, "")))

    # Pick pages
    for d in deals:
        cat = cfg["categories"][d["category"]]
        more = [x for x in deals if x["category"] == d["category"] and x["asin"] != d["asin"]][:4]
        features = "".join("<li>%s</li>" % e(h) for h in d["highlights"])
        note = f'<p class="lead">{e(d["note"])}</p>' if d.get("note") else ""
        more_html = f"<section><h2>More {e(cat['name'])}</h2>{grid(cfg, more, '../')}</section>" if more else ""
        body = f"""<nav class="crumbs"><a href="../index.html">Home</a> &rsaquo; <a href="../category/{d['category']}.html">{e(cat['name'])}</a></nav>
<article class="pick">
  {tile(cfg, d['category'], big=True)}
  <div>
    <h1>{e(d['title'])}</h1>
    {note}
    <h2>Key features</h2>
    <ul class="features">{features}</ul>
    <div class="cta">
      {buy_button(cfg, d, "Check today's price on Amazon", big=True)}
      <p class="muted small">Prices and stock change often. Amazon.in shows the latest price.</p>
    </div>
    <p class="muted small">Added {fmt_date(d['added_at'])}</p>
  </div>
</article>
{telegram_box(cfg)}
{more_html}"""
        desc = d["note"] if d.get("note") else d["highlights"][0]
        pages.append(write("picks/%s.html" % d["asin"], page(cfg, d["title"], desc, body, 1, "picks/%s.html" % d["asin"])))

    # Category pages
    for slug, cat in cfg["categories"].items():
        items = [d for d in deals if d["category"] == slug]
        related = [a for a in articles if a.get("category") == slug]
        items_html = grid(cfg, items, "../") if items else '<p class="muted">New picks are coming soon.</p>'
        related_html = "<section><h2>Guides</h2>%s</section>" % guide_list(related, "../") if related else ""
        body = f"""<nav class="crumbs"><a href="../index.html">Home</a> &rsaquo; {e(cat['name'])}</nav>
<h1>{cat['emoji']} {e(cat['name'])}</h1>
{items_html}
{related_html}"""
        desc = "Hand-picked %s from Amazon India." % cat["name"].lower()
        pages.append(write("category/%s.html" % slug, page(cfg, cat["name"], desc, body, 1, "category/%s.html" % slug)))

    # Guides
    body = '<h1>Buying guides</h1>' + (guide_list(articles, "../") if articles else '<p class="muted">Coming soon.</p>')
    pages.append(write("guides/index.html", page(cfg, "Buying guides", "Simple buying guides for bags, luggage and watches.", body, 1, "guides/index.html")))
    for a in articles:
        content = render_markdown(a["body"], cfg, deals_by_asin, "../", a["slug"] + ".md")
        body = f"""<nav class="crumbs"><a href="../index.html">Home</a> &rsaquo; <a href="index.html">Guides</a></nav>
<article class="guide">
  <h1>{e(a['title'])}</h1>
  <p class="muted small">Updated {fmt_date(a['date'])}</p>
  {content}
</article>
{telegram_box(cfg)}"""
        pages.append(write("guides/%s.html" % a["slug"], page(cfg, a["title"], a["description"], body, 1, "guides/%s.html" % a["slug"])))

    # Info pages
    name = e(cfg["site_name"])
    tg = telegram_url(cfg)
    contact_lines = []
    if tg:
        contact_lines.append(f'<li>Telegram: <a href="{e(tg)}" target="_blank" rel="noopener">{e(cfg["telegram_channel"])}</a></li>')
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
<li>When you click a link to Amazon.in, Amazon may set cookies to track the referral. See Amazon.in's privacy notice.</li>
<li>If you join our Telegram channel, Telegram's privacy policy applies.</li>
</ul>
<p>Questions? See our <a href="contact.html">contact page</a>.</p>"""),
        "contact.html": ("Contact", f"<h1>Contact</h1>\n<p>Have a question or found a mistake? Reach us here:</p>\n{contact_html}"),
        "404.html": ("Page not found", '<h1>Page not found</h1><p>This page has moved or no longer exists. <a href="index.html">Go to the home page</a>.</p>'),
    }
    for path, (title, body) in info.items():
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
