"""Packing list maker (tools/packing-list-maker.html, static/pack-maker.js).

The list comes from data/packing.json, the same file as the ready-made checklists on /packing/:
each item's "maker" conditions decide when it shows, and "qty"/"cap" set the count.
The page works without JavaScript: it then shows the 8 ready lists and the FAQ.
"""
import json
import sys
from html import escape as e

PATH = "tools/packing-list-maker.html"
UPDATED = "2026-11-20"
KEYS = {"type", "who", "by", "where", "season", "min_days"}


def check(data, m, deals_by_asin):
    """Stop the build when the maker data has a typo, so a bad rule never ships."""
    mk = data["maker"]
    allowed = {"type": {t["slug"] for t in mk["types"]}, "who": {w["slug"] for w in mk["who"]},
               "by": {b["slug"] for b in mk["by"]}, "where": {"india", "abroad"},
               "season": set(mk["seasons"].values())}

    def conds(where, sets):
        if not isinstance(sets, list) or not sets:
            sys.exit("Error: packing maker rule for %s must be a list of condition sets" % where)
        for c in sets:
            for k, v in c.items():
                if k not in KEYS:
                    sys.exit("Error: packing maker rule for %s has unknown key %s" % (where, k))
                if k == "min_days":
                    if not isinstance(v, int):
                        sys.exit("Error: packing maker rule for %s: min_days must be a number" % where)
                elif not set(v) <= allowed[k]:
                    sys.exit("Error: packing maker rule for %s: unknown %s %s" % (where, k, sorted(set(v) - allowed[k])))

    ids = set()
    for g in data["groups"]:
        for item in g["items"]:
            if item["id"] in ids:
                sys.exit("Error: packing item id %s is used twice" % item["id"])
            ids.add(item["id"])
            if "maker" not in item:
                sys.exit("Error: packing item %s has no maker rule (use [{}] for always)" % item["id"])
            conds(item["id"], item["maker"])
            if item.get("cap") is not None and not isinstance(item["cap"], int):
                sys.exit("Error: packing item %s: cap must be a number" % item["id"])
    for kind in ("notes", "guides", "shop"):
        for i, row in enumerate(mk[kind]):
            conds("%s %d" % (kind, i + 1), row["maker"])
    for t in mk["types"]:
        if t["list"] not in {x["slug"] for x in data["trips"]}:
            sys.exit("Error: packing maker type %s points to unknown list %s" % (t["slug"], t["list"]))


def build(m, cfg, deals_by_asin, pages, lastmod):
    data = json.loads(m.PACKING_FILE.read_text(encoding="utf-8"))
    check(data, m, deals_by_asin)
    mk = data["maker"]
    trips = data["trips"]
    list_path = {t["slug"]: "packing/" + ("index.html" if t["slug"] == "week" else t["slug"] + ".html") for t in trips}

    def exists(path):
        return (m.DOCS / path).exists()

    def item_json(item):
        out = {"id": item["id"], "name": item["name"], "when": item["maker"]}
        if item.get("qty") is not None:
            out["qty"] = item["qty"]
        if item.get("cap") is not None:
            out["cap"] = item["cap"]
        if item.get("pick") and item["pick"] in deals_by_asin:
            out["href"], out["more"] = "../picks/%s.html" % item["pick"], "Our pick"
        elif item.get("link") and exists(item["link"]):
            out["href"], out["more"] = "../" + item["link"], "See more"
        return out

    guides = []
    for row in mk["guides"]:
        links = [["../" + href, label] for href, label in row["links"] if exists(href)]
        if links:
            guides.append({"when": row["maker"], "links": links})
    cats = cfg["categories"]
    shop = [{"when": row["maker"], "links": [["../category/%s.html" % c, cats[c]["name"]] for c in row["cats"]
                                             if c in cats and exists("category/%s.html" % c)]} for row in mk["shop"]]
    payload = {
        "groups": [{"name": g["name"], "items": [item_json(i) for i in g["items"]]} for g in data["groups"]],
        "types": [{"slug": t["slug"], "label": t["label"], "list": "../" + list_path[t["list"]],
                   "list_label": next(x["label"] for x in trips if x["slug"] == t["list"]),
                   "where": t.get("where")} for t in mk["types"]],
        "seasons": mk["seasons"], "notes": [{"when": n["maker"], "html": n["text"]} for n in mk["notes"]],
        "guides": guides, "shop": [s for s in shop if s["links"]],
        "url": m.abs_url(cfg, PATH),
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
              "November", "December"]
    type_opts = "".join(f'<option value="{t["slug"]}">{e(t["label"])}</option>' for t in mk["types"])
    month_opts = "".join(f'<option value="{i + 1}">{mo}</option>' for i, mo in enumerate(months))
    who_boxes = "".join(f'<label class="pm-pill"><input type="checkbox" name="who" value="{w["slug"]}"'
                        f'{" checked" if w["slug"] in ("men", "women") else ""}> <span>{e(w["label"])}</span></label>' for w in mk["who"])
    by_radios = "".join(f'<label class="pm-pill"><input type="radio" name="by" value="{b["slug"]}"'
                        f'{" checked" if b["slug"] == "flight" else ""}> <span>{e(b["label"])}</span></label>' for b in mk["by"])
    where_radios = "".join(f'<label class="pm-pill"><input type="radio" name="where" value="{w}"'
                           f'{" checked" if w == "india" else ""}> <span>{lab}</span></label>'
                           for w, lab in (("india", "In India"), ("abroad", "Abroad")))
    ready = "".join(f'<li><a href="../{list_path[t["slug"]]}">{e(t["title"])}</a></li>' for t in trips)
    n_items = sum(len(g["items"]) for g in data["groups"])

    title = "Packing list maker: make a travel packing list for your trip"
    seo = "Packing list maker: free travel packing list generator for India"
    desc = ("Free packing list maker: choose beach, hills, city, abroad, pilgrimage, work or wedding, the days, month, "
            "who is going (men, women, kids, baby) and flight, train or road. Get a printable checklist to tick, copy or share on WhatsApp.")
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>Packing list maker</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">A free tool. Updated {m.fmt_date(UPDATED)}</p>"""
    head = m.page_head("travel-gear", f'<div class="media media-tile tint-travel-gear">{m.icon("check", "icon media-icon")}</div>', inner, "../")
    faq = [
        ("How do I make a packing list for a trip?", "Choose the kind of trip, how many days, the month, who is going and how you travel. The maker builds a list "
         "from about %d common items, with counts for your number of days, and you tick things off as you pack." % n_items),
        ("How many clothes should I pack for a 7-day trip?", "About one top a day plus one spare (8), one pair of trousers or jeans for every 3 days (3), "
         "one set of underwear a day plus one (8) and 7 pairs of socks. For longer trips, pack for about a week and wash clothes there."),
        ("What should I pack for a baby or kids?", "For a baby: about 6 diapers a day, wipes, one set of clothes a day plus 2 spare, food or formula, "
         "a blanket and their medicines. For kids: clothes for each day plus 2 spare, their ID, medicines, a bottle, snacks and something to keep them busy."),
        ("Can I take a power bank on a flight in India?", "Yes, but only in your cabin bag, never in check-in. Keep it with you, not in the overhead bin, "
         "and don't use it during the flight. Many airlines allow up to 2 power banks of 100 Wh or less."),
        ("Are my ticks saved?", "Yes, on this device only, in your browser. Nothing is sent to us. Clear them with the Clear ticks button."),
        ("Can I print the list or send it to my family?", "Yes. Use Print for a paper list, Copy list to paste it anywhere, or Share on WhatsApp "
         "to send the list as text. It has only the items, not your name or details."),
    ]
    faq_html, faq_schema = m.faq_block(faq)
    body = f"""{head}
<div class="wrap"><article class="guide">
<p class="pm-nojs" id="pm-nojs">Turn on JavaScript to make a list for your own trip, or open one of the ready-made lists below.</p>
<form class="checker pm-form" id="pm" onsubmit="return false" hidden>
<div class="pm-fields">
<label>Kind of trip<select id="pm-type">{type_opts}</select></label>
<label>How many days?<input id="pm-days" type="number" inputmode="numeric" min="1" max="30" value="5"></label>
<label>Month<select id="pm-month">{month_opts}</select></label>
</div>
<fieldset class="pm-set"><legend>Who is going? <span class="muted">Tick all that apply</span></legend><div class="pm-pills">{who_boxes}</div></fieldset>
<fieldset class="pm-set"><legend>Travelling by</legend><div class="pm-pills">{by_radios}</div></fieldset>
<fieldset class="pm-set"><legend>Where</legend><div class="pm-pills">{where_radios}</div></fieldset>
</form>
<div id="pm-out" hidden>
<h2 id="pm-title">Your packing list</h2>
<p class="checker-total"><span id="pm-count" aria-live="polite"></span></p>
<p class="pm-actions"><button type="button" class="btn pm-btn" id="pm-print">Print</button> <button type="button" class="btn pm-btn2" id="pm-copy">Copy list</button> <a class="btn btn-whatsapp" id="pm-wa" href="https://wa.me/" target="_blank" rel="noopener">Share on WhatsApp</a> <button type="button" class="link-btn" id="pm-clear">Clear ticks</button></p>
<p class="hint small muted" id="pm-copied" aria-live="polite"></p>
<div class="pm-notes" id="pm-notes"></div>
<div class="pack-list" id="pm-list"></div>
<p class="checked">Counts are a guide for each person. Your ticks stay in this browser only.</p>
<div class="pm-noprint" id="pm-after"></div>
</div>
<div class="pm-noprint">
<p>Going to the snow? Read our full packing lists for <a href="../guides/manali-packing-list.html">Manali</a>, <a href="../guides/kashmir-packing-list.html">Kashmir</a> and <a href="../guides/snow-trip-packing-list.html">any snow trip</a>. Going to Rajasthan, Kerala or Rishikesh? See our <a href="../guides/rajasthan-packing-list.html">Rajasthan</a>, <a href="../guides/kerala-packing-list.html">Kerala</a> and <a href="../guides/rishikesh-packing-list.html">Rishikesh</a> packing lists. Going on the Char Dham Yatra? See the <a href="../guides/kedarnath-packing-list.html">Kedarnath packing list</a>. Going to Ladakh? See the <a href="../guides/ladakh-packing-list.html">Ladakh packing list</a>. Travelling with kids in the summer holidays? See the <a href="../guides/summer-vacation-packing-list-for-kids.html">summer vacation packing list for kids</a>.</p>
<p>Not sure which clothes to take? Pick your place and month in the <a href="what-to-wear.html">what-to-wear helper</a>. Plan the money too with our <a href="trip-budget-calculator.html">trip budget calculator</a>. Travelling with a baby? See the <a href="../guides/travelling-with-baby-checklist.html">baby travel checklist</a> and the airline rules for <a href="../guides/flying-with-baby-or-toddler.html">flying with a baby or toddler</a>. Packing for yourself as a woman? See <a href="../guides/travel-essentials-for-women.html">travel essentials for women</a> and <a href="../guides/solo-female-travel-india.html">solo female travel in India</a>.</p>
<div class="answer"><h2>Quick answer</h2><ul>
<li>Pack one top a day plus one spare, trousers for every 3 days, and underwear for each day plus one.</li>
<li>Staying more than a week? Pack for about 7 days and wash clothes there: the maker caps the counts.</li>
<li>Flying? Power banks go in your cabin bag only, and cabin liquids must be 100 ml or less each, in one clear 1-litre bag.</li>
</ul></div>
<section class="pm-ready"><h2>Ready-made packing lists</h2>
<p>Prefer a list that's ready to go? Each one has quantities for your number of days, and you can tick things off as you pack.</p>
<ul>{ready}</ul></section>
{faq_html}
{m.tool_pills("../", PATH)}
</div>
</article></div>
<script type="application/json" id="pm-data">{blob}</script>
<script src="../assets/pack-maker.js" defer></script>
{m.telegram_band(cfg, "../")}"""
    crumbs = m.crumbs_schema(cfg, [("Home", ""), ("Packing list maker", PATH)])
    # No WebApplication schema: Google reads it as a software app and flags it for missing offers and ratings.
    pages.append(m.write(PATH, m.page(cfg, seo, desc, body, 1, PATH,
                                      [m.tool_article(cfg, seo, desc, PATH, UPDATED, UPDATED), crumbs, faq_schema],
                                      og_type="article", photo="packed-suitcase")))
    lastmod[PATH] = UPDATED
