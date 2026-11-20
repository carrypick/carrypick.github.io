"""More free tools, kept out of build.py so it stays small:

- tools/shoe-size.html               <- data/shoe_sizes.json (Bata India and Campus charts), static/shoe-size.js
- tools/power-bank-flight-check.html <- data/power_banks.json (airline rules read on official pages), static/power-bank.js

build.py calls register(B) where it lists TOOLS (home cards, tool pills), then build_all(B, ...) with the other tools.
B is the build module itself, so this file uses its helpers (page, card, faq_block ...).
The pages work without JS: every chart is a plain table, and the scripts only highlight a row and fill the result box.
"""

import json
from html import escape as e

from common import ROOT

SHOE_FILE = ROOT / "data" / "shoe_sizes.json"
SHOE_PATH = "tools/shoe-size.html"
SHOE_UPDATED = "2026-11-20"
POWER_FILE = ROOT / "data" / "power_banks.json"
POWER_PATH = "tools/power-bank-flight-check.html"
POWER_SIZES = (5000, 10000, 20000, 26800, 30000, 40000, 50000)  # mAh rows in the no-JS table

# Category pages that link to a tool, under the "Before you buy" tip: category slug -> (tool path, link text).
CATEGORY_TOOLS = {"shoes": (SHOE_PATH, "Not sure of your size? Use our shoe size converter")}


def register(B):
    if SHOE_FILE.exists():
        B.TOOLS.append((SHOE_PATH, "Shoe size converter", "Free tool", "Shoe size chart: India to US, EU and cm",
                        "Measure your foot in cm, or pick the size you know, and see it in India/UK, US and EU sizes.",
                        "Find my size", "shoe", "shoes", ""))
    if POWER_FILE.exists():
        B.TOOLS.append((POWER_PATH, "Power bank flight checker", "Free tool", "Is my power bank allowed on the flight?",
                        "Type the mAh on your power bank and see its watt-hours, and if IndiGo, Air India and Akasa Air let it on board.",
                        "Check my power bank", "shield", "travel-gear", ""))


def category_link(B, slug, p):
    """A line for the category page that points to its tool, or ""."""
    tool = CATEGORY_TOOLS.get(slug)
    if not tool or not any(t[0] == tool[0] for t in B.TOOLS):
        return ""
    return f'<p class="cat-tool"><a href="{p}{tool[0]}">{e(tool[1])} &rarr;</a></p>'


def build_all(B, cfg, deals, pages, lastmod):
    if SHOE_FILE.exists():
        build_shoe_size(B, cfg, deals, pages, lastmod)
    if POWER_FILE.exists():
        build_power_bank(B, cfg, deals, pages, lastmod)


def _finish(B, cfg, pages, lastmod, path, seo, desc, crumb, body, faq, updated):
    faq_html, faq_schema = B.faq_block(faq)
    body = body.replace("{faq}", faq_html)
    crumbs = B.crumbs_schema(cfg, [("Home", ""), (crumb, path)])
    pages.append(B.write(path, B.page(cfg, seo, desc, body, 1, path,
                                      [B.tool_article(cfg, seo, desc, path, updated, updated), crumbs, faq_schema], og_type="article")))
    lastmod[path] = updated


def _head(B, title, crumb, sub, tint, glyph):
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>{e(crumb)}</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">{e(sub)}</p>"""
    return B.page_head(tint, f'<div class="media media-tile tint-{tint}">{B.icon(glyph, "icon media-icon")}</div>', inner, "../")


def possessive(label):
    return label + "'" if label.endswith("s") else label + "'s"  # Kids', Men's, Women's


def uk_label(row):
    return row["uk"] + (" (kids)" if row.get("kids") else "")


def cm_text(B, row):
    lo, hi = row["cm"]
    return "%s–%s cm" % (B.num(lo), B.num(hi))


def build_shoe_size(B, cfg, deals, pages, lastmod):
    data = json.loads(SHOE_FILE.read_text(encoding="utf-8"))
    path = SHOE_PATH
    groups = {g["slug"]: g for g in data["groups"]}
    men, women, kids = groups["men"], groups["women"], groups["kids"]

    def find(group, uk=None, eu=None, cm=None):
        for r in group["rows"]:
            if (uk and r["uk"] == uk and not r.get("kids")) or (eu and r["eu"] == eu) or (cm and r["cm"][1] >= cm):
                return r
        raise SystemExit("Error: shoe size chart has no row for %s" % (uk or eu or cm))

    m8, w40, m26, k5 = find(men, uk="8"), find(women, eu="40"), find(men, cm=26), next(r for r in kids["rows"] if r["age"].startswith("4.5"))
    m6, w6 = find(men, uk="6"), find(women, uk="6")

    tables = []
    for g in data["groups"]:
        age_head = "<th>Age (about)</th>" if g["slug"] == "kids" else ""
        rows = "".join(
            f'<tr data-uk="{e(r["uk"])}" data-kids="{1 if r.get("kids") else 0}" data-us="{e(r["us"])}" data-eu="{e(r["eu"])}" '
            f'data-lo="{r["cm"][0]}" data-hi="{r["cm"][1]}"><th scope="row">{e(uk_label(r))}</th><td>{e(r["us"])}</td><td>{e(r["eu"])}</td>'
            f'<td>{cm_text(B, r)}</td>' + (f'<td>{e(r["age"])} years</td>' if g["slug"] == "kids" else "") + "</tr>"
            for r in g["rows"])
        tables.append(f"""<h3 id="chart-{g["slug"]}">{e(possessive(g["label"]))} shoe size chart ({e(g["brand"])})</h3>
<div class="table-wrap"><table class="compare ss-table" id="ss-t-{g["slug"]}" data-group="{g["slug"]}" data-label="{e(possessive(g["label"]))}"><thead><tr><th>India / UK</th><th>US</th><th>EU</th><th>Foot length</th>{age_head}</tr></thead><tbody>{rows}</tbody></table></div>""")

    shoes = [d for d in deals if d["category"] == "shoes"]
    cards = "".join(B.card(cfg, d, "../").replace('<article class="card"', '<article class="card" data-for="%s"' % e(
        d.get("specs", {}).get("For", "").lower()), 1) for d in shoes)
    picks_html = (f"""<h2 id="picks">Our shoe picks</h2>
<p id="ss-picks-note">Travel shoes, sandals and flip-flops for men and women. Each Amazon page has the brand's own size chart: check it before you order.</p>
<div class="grid" id="ss-picks">{cards}</div>""" if shoes else "")
    src = " and ".join(f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])}</a>' for s in data["sources"])
    checked = B.fmt_date(data["checked"])
    title = "Shoe size chart for India: India/UK to US, EU and cm"
    seo = "Shoe size chart India: UK to US, EU and cm for men, women and kids"
    desc = ("Free shoe size converter for India. Measure your foot in cm or pick your size, and see the India/UK, US and EU size "
            "for men, women and kids, from Bata India's and Campus's size charts.")
    body = f"""{_head(B, title, "Shoe size converter", "A free tool. Updated " + B.fmt_date(SHOE_UPDATED), "shoes", "shoe")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>India and UK sizes are the same number.</strong> An India 8 is a UK 8.</li>
<li>On Bata India's chart, a men's UK {m8["uk"]} is a US {m8["us"]} and an EU {m8["eu"]}, for a foot of {cm_text(B, m8)}.</li>
<li>Your foot length in cm is the surest way to pick a size. Sizes vary by brand, so check the brand's own chart too.</li>
</ul></div>
<h2>Step 1: measure your foot</h2>
<ol>
<li>Put a sheet of paper on the floor, against a wall.</li>
<li>Stand on it with your heel touching the wall, wearing the socks you'll wear with the shoes.</li>
<li>Ask someone to mark the tip of your longest toe. (It isn't always the big toe.)</li>
<li>Measure from the wall to the mark with a ruler, in cm. Do both feet and use the longer one.</li>
<li>Measure in the evening, when feet are at their largest.</li>
</ol>
<h2>Step 2: find your size</h2>
<form class="checker" id="ss" onsubmit="return false">
<div class="checker-fields"><label>Shoes for<select id="ss-who"><option value="men">Men</option><option value="women">Women</option><option value="kids">Kids</option></select></label>
<label>Foot length (cm)<input id="ss-cm" type="number" min="10" max="35" step="0.1" inputmode="decimal" placeholder="e.g. 26"></label>
<label hidden data-js>Or, a size I know<select id="ss-sys"><option value="uk">India / UK</option><option value="us">US</option><option value="eu">EU</option></select></label>
<label hidden data-js>Size<select id="ss-size"><option value="">Choose…</option></select></label></div>
<p class="checker-total" id="ss-out" aria-live="polite">Type your foot length in cm, or pick a size you know, to see it in every size system.</p>
<div id="ss-result" hidden>
<div class="table-wrap"><table class="compare snug"><tbody>
<tr><th scope="row">India / UK</th><td id="ss-r-uk"></td></tr>
<tr><th scope="row">US</th><td id="ss-r-us"></td></tr>
<tr><th scope="row">EU</th><td id="ss-r-eu"></td></tr>
<tr><th scope="row">Foot length</th><td id="ss-r-cm"></td></tr>
</tbody></table></div>
<p class="hint" id="ss-r-note"></p>
<p id="ss-r-links"><a href="#picks">See our shoe picks</a> &middot; <a href="../category/shoes.html">All shoes and sandals</a> &middot; <a href="../guides/travel-shoes-guide.html">Which shoes to take on a trip</a></p>
</div>
</form>
<h2>Shoe size charts</h2>
<p>Men's and women's sizes are from Bata India's size guide. Kids' sizes are from Campus's kids size chart. Foot length is the length of your foot, not of the shoe.</p>
{"".join(tables)}
<p class="checked">Checked on {checked} on {src}. Sizes vary by brand: sports brands often use a different US size for the same UK size, and some shoes run small or wide. The size chart on each product page is the one to trust.</p>
<p>Kids' sizes go up from 7 to 13, then start again at 1. Leave a little growing room: if your child's foot is between two sizes, take the bigger one.</p>
{picks_html}
<p>More help: <a href="../guides/travel-shoes-guide.html">which shoes to take on a trip</a> and <a href="../category/shoes.html">all our shoes and sandals</a>.</p>
{{faq}}
{B.tool_pills("../", path)}
</article></div>
<script src="../assets/shoe-size.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("Is Indian shoe size the same as UK size?", "Yes. Shoes in India are sold in UK sizes, so an India 8 is the same as a UK 8."),
        ("What is UK %s in US and EU size?" % m8["uk"],
         "On Bata India's chart, a men's UK %s is a US %s and an EU %s, for a foot of %s. Other brands can give a different US size, so check the brand's own chart."
         % (m8["uk"], m8["us"], m8["eu"], cm_text(B, m8))),
        ("What is size %s in India for women?" % w40["eu"],
         "On Bata India's women's chart, EU %s is an India/UK %s and a US %s, for a foot of %s." % (w40["eu"], w40["uk"], w40["us"], cm_text(B, w40))),
        ("What shoe size is a 26 cm foot?",
         "For men, about an India/UK %s (EU %s) on Bata India's chart, which covers feet of %s." % (m26["uk"], m26["eu"], cm_text(B, m26))),
        ("How do I measure my foot size in cm at home?",
         "Stand on a sheet of paper with your heel against a wall, mark the tip of your longest toe, and measure from the wall to the mark in cm. Measure both feet in the evening and use the longer one."),
        ("Are men's and women's shoe sizes the same?",
         "On Bata India's chart, the same UK number fits the same foot length for men and women, but the EU number is different: a men's UK %s is an EU %s, a women's UK %s is an EU %s."
         % (m6["uk"], m6["eu"], w6["uk"], w6["eu"])),
        ("What shoe size does a 5 year old wear in India?",
         "Often about a UK %s kids' size on Campus's chart (ages %s, foot %s). Children grow fast, so measure the foot rather than going by age."
         % (k5["uk"], k5["age"], cm_text(B, k5))),
    ]
    _finish(B, cfg, pages, lastmod, path, seo, desc, "Shoe size converter", body, faq, SHOE_UPDATED)


def power_verdict(wh, airlines):
    """Same rule as static/power-bank.js: ("yes"|"close"|"no", headline)."""
    if wh <= min(a["max_wh"] for a in airlines):
        return "yes", "Allowed in your cabin bag"
    if wh <= max(a["max_wh"] for a in airlines):
        return "close", "Needs airline approval"
    return "no", "Not allowed on Indian flights"


def build_power_bank(B, cfg, deals, pages, lastmod):
    data = json.loads(POWER_FILE.read_text(encoding="utf-8"))
    path = POWER_PATH
    airlines = data["airlines"]
    volt = data["voltage"]
    checked = B.fmt_date(data["checked"])
    low, high = min(a["max_wh"] for a in airlines), max(a["max_wh"] for a in airlines)
    by_low = " and ".join(a["name"] for a in airlines if a["max_wh"] == low)
    by_high = " and ".join(a["name"] for a in airlines if a["max_wh"] == high)

    def mah_for(wh):
        return int(round(wh * 1000 / volt, -2))

    def yes_no(ok):
        return '<span class="fit fit-yes">Yes</span>' if ok else '<span class="fit fit-no">No</span>'

    head_cells = "".join("<th>%s</th>" % e(a["name"]) for a in airlines)
    size_rows = "".join(
        f'<tr><th scope="row">{m:,} mAh</th><td>{B.num(m * volt / 1000)} Wh</td>'
        + "".join("<td>%s</td>" % yes_no(m * volt / 1000 <= a["max_wh"]) for a in airlines) + "</tr>"
        for m in POWER_SIZES)
    airline_rows = "".join(
        f'<tr><th scope="row">{e(a["name"])}</th><td>Up to {a["max_wh"]} Wh</td>'
        f'<td>{e(a["rule"])} <a class="src" href="{e(a["source"])}" target="_blank" rel="noopener">Source</a></td></tr>'
        for a in airlines)
    on_board = "".join(f'<li><strong>{e(r["text"])}</strong> <span class="muted">{e(r["who"])}</span></li>' for r in data["on_board"])
    sources = ", ".join(f'<a href="{e(a["source"])}" target="_blank" rel="noopener">{e(a["source_label"])}</a>' for a in airlines)
    picks = [d for d in deals if "power bank" in d["title"].lower()]
    if picks:
        more_links = '<a href="#picks">Power banks we picked</a> &middot; <a href="../baggage/can-i-carry/power-bank.html">Power bank rules in full</a>'
    else:
        more_links = '<a href="../baggage/can-i-carry/power-bank.html">Power bank rules in full</a> &middot; <a href="../baggage/can-i-carry.html">What else can I carry?</a>'
    picks_html = ""
    if picks:
        picks_html = '<h2 id="picks">Power banks we picked</h2><div class="grid">%s</div>' % "".join(B.card(cfg, d, "../") for d in picks)
    title = "Is my power bank allowed on the flight? mAh to Wh checker"
    seo = "Power bank allowed in flight? mAh to Wh checker for IndiGo, Air India, Akasa"
    desc = ("Type your power bank's mAh and see its watt-hours (Wh) and whether IndiGo, Air India and Akasa Air allow it in the cabin. "
            "Power banks are never allowed in check-in bags. Rules checked on %s." % checked)
    body = f"""{_head(B, title, "Power bank flight checker", "A free tool. Rules checked on " + checked, "travel-gear", "shield")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Power banks go in your cabin bag only, never in check-in.</strong> Every Indian airline here says so.</li>
<li>Up to {low} Wh (about {mah_for(low):,} mAh) is fine on all three airlines. {by_high} takes up to {high} Wh; {by_low} stop at {low} Wh.</li>
<li>You can't use your power bank or charge it during the flight, and it can't go in the overhead bin.</li>
</ul></div>
<form class="checker" id="pb" onsubmit="return false" data-volt="{volt}" data-low="{low}" data-high="{high}">
<div class="checker-fields"><label>Capacity (mAh)<input id="pb-mah" type="number" min="100" max="100000" step="100" inputmode="numeric" placeholder="e.g. 20000"></label>
<label>Cell voltage (V)<input id="pb-v" type="number" min="1" max="30" step="0.01" inputmode="decimal" value="{volt}"></label>
<label>Or the Wh on the label<input id="pb-wh" type="number" min="1" max="1000" step="0.1" inputmode="decimal" placeholder="e.g. 74"></label></div>
<p class="hint">The mAh and Wh are printed on the back of the power bank. Most use {volt} V cells; if the label gives another cell voltage, use that.</p>
<p class="checker-total" id="pb-out" aria-live="polite">Type your power bank's mAh to see its watt-hours and whether you can fly with it.</p>
<div id="pb-result" hidden>
<div class="table-wrap"><table class="compare snug" id="pb-airlines"><thead><tr><th>Airline</th><th>Cabin bag</th><th>Check-in</th></tr></thead><tbody>
{"".join(f'<tr data-max="{a["max_wh"]}"><th scope="row">{e(a["name"])}</th><td class="pb-cabin"></td><td><span class="fit fit-no">No</span></td></tr>' for a in airlines)}
</tbody></table></div>
<p class="hint" id="pb-note"></p>
<p>{more_links}</p>
</div>
</form>
<h2>Common power bank sizes</h2>
<p>Watt-hours = mAh x {volt} ÷ 1,000. Cabin bag only, on every airline.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Power bank</th><th>About</th>{head_cells}</tr></thead><tbody>{size_rows}</tbody></table></div>
<h2>The rules by airline</h2>
<p>No airline here allows a power bank in a check-in bag.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Cabin bag</th><th>What the airline says</th></tr></thead><tbody>{airline_rows}</tbody></table></div>
<p class="checked">Checked on {checked} on {sources}. Security staff can still refuse any item, and airlines can change their rules, so check your airline before you fly.</p>
<h2>On the plane</h2>
<ul>{on_board}</ul>
<h2>What "needs airline approval" means</h2>
<p>A power bank over {low} Wh and up to {high} Wh is allowed on {by_high}'s list, but {by_low}'s pages allow only up to {low} Wh. Ask your airline before you fly, or take a smaller one. Over {high} Wh, no airline here takes it.</p>
<p class="checked">Not confirmed: we couldn't find DGCA's circular on in-flight use on DGCA's own website, so that rule is from Akasa Air's page and news reports. Everything else above is from the airlines' own pages, not from BCAS or DGCA circulars.</p>
{picks_html}
<p>More help: <a href="../baggage/can-i-carry/power-bank.html">can I carry a power bank on a flight?</a>, <a href="../baggage/can-i-carry.html">what else you can carry</a> and <a href="../baggage/index.html">baggage rules for Indian airlines</a>.</p>
{{faq}}
{B.tool_pills("../", path)}
</article></div>
<script src="../assets/power-bank.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("Is a 20000 mAh power bank allowed in flight in India?",
         "Yes, in your cabin bag. At %s V it is about %s Wh, under the %s Wh limit of %s and the %s Wh limit of %s."
         % (volt, B.num(20000 * volt / 1000), low, by_low, high, by_high)),
        ("How do I convert mAh to Wh?", "Multiply the mAh by the voltage and divide by 1,000. For a 10,000 mAh power bank with %s V cells: 10,000 x %s ÷ 1,000 = %s Wh."
         % (volt, volt, B.num(10000 * volt / 1000))),
        ("Can I keep a power bank in check-in baggage?", "No. IndiGo, Air India and Akasa Air all ban power banks in check-in bags. Akasa Air says a check-in bag with a power bank in it won't be loaded."),
        ("Can I use a power bank during the flight?", "No. Akasa Air's rules ban using or charging power banks during the flight, and news reports say DGCA has banned it on all Indian flights. Charge your phone before you board."),
        ("What is the biggest power bank allowed on IndiGo?", "IndiGo's list allows power banks up to %s Wh (about %s mAh at %s V), with the power rating printed on it."
         % (high, "{:,}".format(mah_for(high)), volt)),
        ("How many power banks can I carry?", "Air India and Akasa Air allow 2 spare batteries per person, and a power bank counts as one. IndiGo's list doesn't give a number, so keep to two."),
    ]
    _finish(B, cfg, pages, lastmod, path, seo, desc, "Power bank flight checker", body, faq, data["checked"])
