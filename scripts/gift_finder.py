"""Gift finder quiz (tools/gift-finder.html, static/gift-finder.js).

data/gift_finder.json maps each answer (who, occasion, an optional size word) to picks from our gift guides
and links to those guides. It never holds prices: "small", "nice" and "big" say how much of a gift a pick is.
The page works without JavaScript: it then shows who -> guide links and a few top picks for each person.
build.py calls register(B) where it lists TOOLS, and build(B, ...) after the guides, so guide links can be checked.
"""
import json
import re
import sys
import urllib.parse
from html import escape as e

from common import ROOT

FILE = ROOT / "data" / "gift_finder.json"
PATH = "tools/gift-finder.html"
UPDATED = "2026-11-20"
SHOW = 6         # pick cards in a quiz result
NOJS_PICKS = 3   # pick links per person in the no-JS list
GIFT_ICON = ('<rect x="4" y="9" width="16" height="11" rx="1.5"/><path d="M3 9h18M12 9v11"/>'
             '<path d="M12 9c-1.5-3-5-4-5.5-2S9 9 12 9zM12 9c1.5-3 5-4 5.5-2S15 9 12 9z"/>')


def register(B):
    if not FILE.exists():
        return
    B.ICONS.setdefault("gift", GIFT_ICON)
    # First on the home page's tools list: gifts are our season until Christmas.
    B.TOOLS.insert(0, (PATH, "Gift finder quiz", "Free tool", "Gift finder: what gift should I give?",
                       "Tell us who it's for and the occasion, and see gift ideas from our Christmas, Secret Santa, farewell and wedding guides.",
                       "Find a gift", "gift", "watches", "gift-box"))


def results(data, who, occ, size=""):
    """Same rule as static/gift-finder.js: (asins, guides, filled). filled is True when the size had too few matches."""
    w = next(x for x in data["who"] if x["slug"] == who)
    o = next(x for x in data["occasions"] if x["slug"] == occ)
    pair = data["pairs"].get(who + "+" + occ, {})
    occ_picks = [] if who in o.get("not_for", []) else o["picks"]
    order = []

    def add(asins):
        order.extend(a for a in asins if a not in order)

    add(pair.get("picks", []))
    if o.get("lead") and occ_picks:
        add(occ_picks)
        add(w["picks"])
    else:
        add(w["picks"][:4])
        add(occ_picks[:2])
        add(w["picks"])
    filled = False
    if size:
        match = [a for a in order if data["size_of"][a] == size]
        filled = len(match) < 3
        order = match + [a for a in order if a not in match] if filled else match
    guides = []
    for href, label in pair.get("guides", []) + o["guides"] + w["guides"]:
        if href.split("#")[0] not in (g[0].split("#")[0] for g in guides):  # one link per guide page
            guides.append([href, label])
    return order[:SHOW], guides[:3], filled


def check(B, data, deals_by_asin):
    """Stop the build on a typo, a missing pick or a guide link (or #anchor) that isn't on the site."""
    sizes = {s["slug"] for s in data["sizes"]}
    for a, s in data["size_of"].items():
        if a not in deals_by_asin:
            sys.exit("Error: gift finder size_of has %s, which is not in data/deals.json" % a)
        if s not in sizes:
            sys.exit("Error: gift finder size_of %s: unknown size %s" % (a, s))
    whos = {w["slug"] for w in data["who"]}
    occs = {o["slug"] for o in data["occasions"]}
    rows = [("who " + w["slug"], w) for w in data["who"]] + [("occasion " + o["slug"], o) for o in data["occasions"]]
    for key, pair in data["pairs"].items():
        who, _, occ = key.partition("+")
        if who not in whos or occ not in occs:
            sys.exit("Error: gift finder pair %s: unknown who or occasion" % key)
        rows.append(("pair " + key, pair))
    for where, row in rows:
        for a in row.get("picks", []):
            if a not in data["size_of"]:
                sys.exit("Error: gift finder %s uses %s, which has no size in size_of (or isn't a pick)" % (where, a))
        for href, _ in row.get("guides", []):
            path, _, anchor = href.partition("#")
            page = B.DOCS / path
            if not page.exists():
                sys.exit("Error: gift finder %s links to %s, which isn't built" % (where, path))
            if anchor and ('id="%s"' % anchor) not in page.read_text(encoding="utf-8"):
                sys.exit("Error: gift finder %s links to #%s, which isn't on %s" % (where, anchor, path))
    for w in data["who"]:
        if w.get("occasion") and w["occasion"] not in occs:
            sys.exit("Error: gift finder who %s: unknown occasion %s" % (w["slug"], w["occasion"]))
        for o in data["occasions"]:
            if len(results(data, w["slug"], o["slug"])[0]) < 4:
                sys.exit("Error: gift finder %s + %s shows fewer than 4 picks" % (w["slug"], o["slug"]))
    if re.search(r"(₹|\bRs\.?\s?|\bINR\s?)\d|\bratings?\b|\bout of 5\b|\d stars?\b|★|\bprice|\bcheap|\bbudget|\bunder \d",
                 json.dumps(data, ensure_ascii=False), re.I):
        sys.exit("Error: data/gift_finder.json mentions a price, budget or rating. Use the size words only.")


def build(B, cfg, deals_by_asin, pages, lastmod):
    if not FILE.exists():
        return
    data = json.loads(FILE.read_text(encoding="utf-8"))
    check(B, data, deals_by_asin)
    deal = deals_by_asin

    def name(asin, short):
        if asin not in deal:
            sys.exit("Error: gift finder FAQ names %s, which is not in data/deals.json" % asin)
        return short

    def g(href):
        return "../" + href

    payload = {
        "who": [{k: v for k, v in w.items() if k != "line"} | {"guides": [[g(h), t] for h, t in w["guides"]]} for w in data["who"]],
        "occasions": [o | {"guides": [[g(h), t] for h, t in o["guides"]]} for o in data["occasions"]],
        "pairs": {k: p | {"guides": [[g(h), t] for h, t in p.get("guides", [])]} for k, p in data["pairs"].items()},
        "sizes": data["sizes"], "size_of": data["size_of"], "show": SHOW,
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pool = "".join(B.card(cfg, deal[a], "../").replace('<article class="card"', '<article class="card" data-asin="%s"' % a, 1)
                   for a in data["size_of"])

    def opts(rows, q):
        return "".join(f'<button type="button" class="gf-opt" data-q="{q}" data-v="{r["slug"]}">{e(r["label"])}'
                       + (f'<small>{e(r["hint"])}</small>' if r.get("hint") else "") + "</button>" for r in rows)

    url = B.abs_url(cfg, PATH)
    wa = "https://wa.me/?text=" + urllib.parse.quote(url, safe="")

    # Without JavaScript: who -> guide links and the top picks for that person.
    rows = []
    for w in data["who"]:
        links = " &middot; ".join(f'<a href="{e(g(h))}">{e(t)}</a>' for h, t in w["guides"])
        picks = ", ".join(f'<a href="../picks/{a}.html">{e(deal[a]["title"])}</a>' for a in w["picks"][:NOJS_PICKS])
        rows.append(f"""<div class="gf-row" id="for-{w["slug"]}"><h3>For {e(w["for"])}{" (Secret Santa)" if w.get("occasion") == "secret-santa" else ""}</h3>
<p>{e(w["line"])}</p>
<p><strong>Read:</strong> {links}</p>
<p class="small"><strong>Top picks:</strong> {picks}</p></div>""")
    top = ["B0C3LRF94X", "B0F13ZFVVX", "B00NIWHQVI", "B018VZBTLY", "B08LKXV22C", "B0BS3M2XQV"]
    top_grid = "".join(B.card(cfg, deal[a], "../") for a in top if a in deal)

    title = "Gift finder quiz: what gift should I give?"
    seo = "Gift finder quiz India: gift ideas for men, women, kids, boss and colleagues"
    desc = ("Free gift finder quiz: pick who the gift is for (colleague, boss, wife, husband, kids, parents, a traveller or Secret Santa) "
            "and the occasion, and see matching gift ideas for Christmas, farewell, New Year, weddings and birthdays.")
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>Gift finder</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">A free tool. Answer 2 or 3 quick questions. Updated {B.fmt_date(UPDATED)}</p>"""
    head = B.page_head("watches", f'<div class="media media-tile tint-watches">{B.icon("gift", "icon media-icon")}</div>', inner, "../")  # no head photo: the quiz stays near the top on phones
    faq = [
        ("What is a good Christmas gift for men?",
         "A watch he'll wear every day, like the %s or the %s, a leather wallet gift set from %s, or a sling bag. "
         "For a man who travels, a weekender duffle or a toiletry bag." % (name("B07H3K85H5", "Timex Classics"), name("B018VZBTLY", "Titan Classique"),
                                                                           name("B0C3LRF94X", "WildHorn"))),
        ("What are good gift ideas for women?",
         "A dressy watch such as the %s, a sling or tote bag from %s or Lavie, or a zip-around wallet. "
         "For a woman who travels, a light crossbody bag or packing cubes." % (name("B08LKXV22C", "Titan Raga"), name("B0BQWF3TJK", "Zouk"))),
        ("What is a good Secret Santa gift for coworkers?",
         "Something anyone can use at work: a %s steel bottle, a cable and charger organiser, a wallet and pen gift set for men, "
         "or a zip-around wallet for women. Skip jokes and anything too personal." % name("B00NIWHQVI", "Milton")),
        ("What should I give a colleague as a farewell gift?",
         "A wallet gift set, a passport holder for someone moving abroad, or a laptop backpack for a new job. "
         "For a boss or senior colleague, a team gift such as a %s watch." % name("B018VZBTLY", "Titan")),
        ("What gift can I give my parents?",
         "A pair watch set like %s or Sonata Bandhan, warm thermal sets for winter, or comfortable walking shoes for dad."
         % name("B07PY6CQYV", "Titan Bandhan")),
        ("What gift should I give for a marriage?",
         "Something the couple will use together: a couple watch set, a set of 3 trolley bags for the new home, "
         "or a cabin trolley and weekender bag for the honeymoon. Check the couple's list first if they have one."),
        ("What do small token, nice gift and big gift mean?",
         "They say how much of a gift you want, not a price. A small token is a desk gift or Secret Santa, a nice gift suits a friend or family, "
         "and a big gift is for a partner, parents or a gift from the whole team. We don't show prices: check them on Amazon.in."),
    ]
    faq_html, faq_schema = B.faq_block(faq)
    body = f"""{head}
<div class="wrap"><article class="guide">
<p class="pm-nojs" id="gf-nojs">Turn on JavaScript for the quick quiz, or pick the person below to see our gift guides and top picks.</p>
<section class="checker gf" id="gf" hidden>
<p class="gf-step muted small" id="gf-step">Question 1 of 3</p>
<fieldset class="gf-q" id="gf-q-who"><legend>Who is the gift for?</legend><div class="gf-opts">{opts(data["who"], "who")}</div></fieldset>
<fieldset class="gf-q" id="gf-q-occ" hidden><legend>What's the occasion?</legend><div class="gf-opts">{opts(data["occasions"], "occ")}</div></fieldset>
<fieldset class="gf-q" id="gf-q-size" hidden><legend>How big a gift? <span class="muted">Optional</span></legend><div class="gf-opts gf-opts-1">{opts(data["sizes"], "size")}
<button type="button" class="gf-opt gf-skip" data-q="size" data-v="">Skip: show me everything</button></div></fieldset>
<p class="gf-nav" id="gf-nav" hidden><button type="button" class="link-btn" id="gf-back">&larr; Back</button></p>
</section>
<section id="gf-result" hidden>
<h2 id="gf-title" tabindex="-1">Gift ideas</h2>
<p class="muted small"><span id="gf-answers"></span> &middot; <button type="button" class="link-btn" id="gf-change">Change answers</button></p>
<p class="hint" id="gf-note" hidden></p>
<div class="grid" id="gf-grid" aria-live="polite"></div>
<div class="next-step gf-guides"><h2>Read the full guide</h2><ul id="gf-guides"></ul></div>
<p class="pm-actions"><button type="button" class="btn pm-btn2" id="gf-again">Start again</button> <a class="btn btn-whatsapp" href="{e(wa)}" target="_blank" rel="noopener">Share on WhatsApp</a></p>
</section>
<template id="gf-pool">{pool}</template>
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Not sure what to give?</strong> A watch, a good bag or useful travel gear suits most people and gets used every day.</li>
<li>For a colleague or Secret Santa, keep it useful and not personal: a steel bottle, a wallet set or a cable organiser.</li>
<li>For a boss, give one bigger gift from the whole team. For parents, a pair watch set.</li>
</ul></div>
<h2 id="by-person">Gift ideas by person</h2>
{"".join(rows)}
<h2>Our most-given gift picks</h2>
<div class="grid">{top_grid}</div>
{faq_html}
{B.tool_pills("../", PATH)}
</article></div>
<script type="application/json" id="gf-data">{blob}</script>
<script src="../assets/gift-finder.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    crumbs = B.crumbs_schema(cfg, [("Home", ""), ("Gift finder", PATH)])
    app = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Gift finder quiz", "url": url,
           "applicationCategory": "LifestyleApplication", "operatingSystem": "Any", "description": desc}
    pages.append(B.write(PATH, B.page(cfg, seo, desc, body, 1, PATH,
                                      [B.tool_article(cfg, seo, desc, PATH, UPDATED, UPDATED), crumbs, faq_schema, app],
                                      og_type="article", photo="gift-box")))
    lastmod[PATH] = UPDATED
