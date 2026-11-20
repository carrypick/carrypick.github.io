"""Clothing size converter (tools/clothing-size.html), kept out of build.py:

- data/clothing_sizes.json: body-measurement size charts copied from Marks & Spencer India, Libas and Levi's India,
  with M&S's own UK/US/EU table for women. Each chart keeps its brand's numbers; we never merge two brands into one row.
- static/clothing-size.js: the instant converter. It reads the sizes from the tables on the page.
- docs/assets/diagrams/measure-body.svg: our own drawing of where to measure chest, waist, hips and height.

build.py calls register(B) where it lists TOOLS, and build_all(B, ...) with the other tools.
The page works without JS: every chart is a plain table and the form stays hidden.
"""

import json
from html import escape as e

import diagrams
import more_tools
from common import ROOT

DATA_FILE = ROOT / "data" / "clothing_sizes.json"
PATH = "tools/clothing-size.html"
UPDATED = "2026-11-20"
MEASURE_LABELS = {"chest": "Chest", "bust": "Bust", "waist": "Waist", "hips": "Hips", "height": "Height"}
WHO = (("men", "Men"), ("women", "Women"), ("kids", "Kids"))
WHO_HEAD = {"men": "Men's size charts", "women": "Women's size charts", "kids": "Kids' size chart by age"}


def register(B):
    if not DATA_FILE.exists():
        return
    B.TOOLS.append((PATH, "Clothing size converter", "Free tool", "Clothing size chart: UK, US and EU to Indian size",
                    "Measure your chest, waist or hips, or pick the size you know, and see it in UK, US, EU and letter sizes.",
                    "Find my size", "jacket", "clothing", ""))
    more_tools.CATEGORY_TOOLS.setdefault("clothing", (PATH, "Not sure of your size? Use our clothing size converter"))


# ---------- the drawing ----------

def measure_body():
    t = diagrams.text
    body = ('<circle cx="200" cy="58" r="26" class="body line" stroke-width="1.8"/>'
            '<rect x="189" y="82" width="22" height="18" class="body line" stroke-width="1.8"/>'
            '<path d="M138 118 Q124 122 120 140 L110 250 Q109 262 118 262 L126 262 L138 160 Z" class="side line" stroke-width="1.8" stroke-linejoin="round"/>'
            '<path d="M262 118 Q276 122 280 140 L290 250 Q291 262 282 262 L274 262 L262 160 Z" class="side line" stroke-width="1.8" stroke-linejoin="round"/>'
            '<path d="M150 104 Q200 94 250 104 L262 118 L256 170 Q238 200 236 212 Q252 240 252 268 L244 400 L208 400 L202 300 '
            'L198 300 L192 400 L156 400 L148 268 Q148 240 164 212 Q162 200 144 170 L138 118 Z" class="body line" stroke-width="1.8" stroke-linejoin="round"/>')
    tapes = ""
    for y, rx, name, how in ((150, 60, "Chest or bust", "Round the fullest part"),
                             (212, 37, "Waist", "Round the narrowest part"),
                             (264, 53, "Hips", "Round the widest part")):
        tapes += ('<ellipse cx="200" cy="%d" rx="%d" ry="7" fill="none" class="dim" stroke-width="3"/>' % (y, rx)
                  + '<line x1="%d" y1="%d" x2="312" y2="%d" class="dim" stroke-width="1.5" stroke-dasharray="4 4"/>' % (200 + rx, y, y)
                  + t(320, y - 2, name, "ink", 18, "start", 700) + t(320, y + 19, how, "muted", 15, "start"))
    height = ('<line x1="30" y1="400" x2="300" y2="400" class="line" stroke-width="2"/>'
              + diagrams.dim_line(60, 34, 60, 398)
              + '<text x="44" y="216" class="dimtext" font-size="16" font-weight="700" text-anchor="middle" '
                'transform="rotate(-90 44 216)">Height (kids)</text>')
    return diagrams.svg(520, 425, "Where to measure: chest or bust, waist, hips and height", body + tapes + height
                        + t(260, 418, "Keep the tape level and snug, not tight.", "muted", 14))


# ---------- the tables ----------

def to_cm(chart, v):
    return v if chart["unit"] == "cm" else v * 2.54


def span(v):
    """A value from the data file as (lo, hi), or None."""
    if v is None:
        return None
    return (v[0], v[1]) if isinstance(v, list) else (v, v)


def half(x):
    return round(x * 2) / 2


def cell(B, chart, v):
    s = span(v)
    if not s:
        return "–"
    lo, hi = s
    if chart["unit"] == "cm":
        main = B.num(lo) + ("" if lo == hi else "–" + B.num(hi)) + " cm"
        other = B.num(half(lo / 2.54)) + ("" if lo == hi else "–" + B.num(half(hi / 2.54))) + " in"
    else:
        main = B.num(lo) + ("" if lo == hi else "–" + B.num(hi)) + " in"
        other = str(round(lo * 2.54)) + ("" if lo == hi else "–" + str(round(hi * 2.54))) + " cm"
    return f'{main}<br><span class="muted small">{other}</span>'


def table_html(B, chart, sources):
    heads = "".join("<th>%s</th>" % MEASURE_LABELS[m] for m in chart["measures"])
    heads += "".join('<th class="x">%s</th>' % e(c) for c in chart["cols"])
    rows = []
    for r in chart["rows"]:
        attrs = "".join(' data-m-%s="%s,%s"' % (m, round(to_cm(chart, span(r[m])[0]), 2), round(to_cm(chart, span(r[m])[1]), 2))
                        for m in chart["measures"] if span(r.get(m)))
        tds = "".join("<td>%s</td>" % cell(B, chart, r.get(m)) for m in chart["measures"])
        tds += "".join('<td class="x">%s</td>' % e(r.get(c) or "–") for c in chart["cols"])
        rows.append(f'<tr{attrs}><th scope="row">{e(r["size"])}</th>{tds}</tr>')
    src = sources[chart["source"]]
    note = ""
    if chart.get("cols_source"):
        cs = sources[chart["cols_source"]]
        note = (f' US and EU sizes from <a href="{e(cs["url"])}" target="_blank" rel="noopener">{e(cs["label"])}</a>, '
                "which gives them in pairs.")
    say = f' data-say="{e(chart["say"])}"' if chart.get("say") else ""
    unit_note = "Inches are worked out from the cm." if chart["unit"] == "cm" else "Libas gives inches; cm are worked out."
    return f"""<h3 id="chart-{chart["id"]}">{e(chart["title"])}</h3>
<div class="table-wrap"><table class="compare cs-table" id="cs-t-{chart["id"]}" data-chart="{chart["id"]}" data-title="{e(chart["title"])}" data-head="{e(chart["size_head"])}"{say}>
<thead><tr><th>{e(chart["size_head"])}</th>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="hint small">Body measurements, from <a href="{e(chart["url"])}" target="_blank" rel="noopener">{e(src["brand"])}'s size guide</a>.{note} {unit_note}</p>"""


# ---------- the page ----------

def build_all(B, cfg, deals, pages, lastmod):
    if not DATA_FILE.exists():
        return
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    charts = {c["id"]: c for c in data["charts"]}
    sources = {s["id"]: s for s in data["sources"]}
    for g in data["garments"]:
        for cid in g["charts"]:
            if cid not in charts:
                raise SystemExit("Error: clothing garment %s uses unknown chart %s" % (g["slug"], cid))
            missing = [m for m in g["measures"] if m not in charts[cid]["measures"]]
            if missing:
                raise SystemExit("Error: clothing chart %s has no %s" % (cid, ", ".join(missing)))

    svg = measure_body()
    B.DIAGRAMS["measure-body"] = (svg, "Drawing: where to put the tape for chest or bust, waist and hips, and how to measure a child's height",
                                  "Measure your body, not your clothes: round the fullest part of the chest or bust, the narrowest part of the waist and the widest part of the hips.")
    (B.DOCS / "assets" / "diagrams" / "measure-body.svg").write_text(svg, encoding="utf-8")

    def row(cid, size):
        return next(r for r in charts[cid]["rows"] if r["size"] == size)

    def cm(cid, size, m):
        lo, hi = span(row(cid, size)[m])
        return B.num(lo) + ("" if lo == hi else "–" + B.num(hi)) + " cm"

    uk10, uk12 = row("ms-women-tops", "UK 10"), row("ms-women-tops", "UK 12")
    f38, lib_m = row("ms-men-formal", "38"), row("libas-kurta", "M")
    xl, xl_t = row("ms-men-tops", "XL"), row("ms-men-trousers", "XL")
    lev32 = row("levis-men-jeans", "32")
    w28, w30 = row("only-women-jeans", "28"), row("only-women-jeans", "30")
    m_trousers = next(r for r in charts["ms-men-trousers"]["rows"] if span(r["waist"])[0] <= lev32["waist"] <= span(r["waist"])[1])
    boy5 = row("ms-boys", "5–6 years")

    tables = []
    for who, label in WHO:
        gs = [g for g in data["garments"] if g["who"] == who]
        seen, parts = set(), []
        for g in gs:
            for cid in g["charts"]:
                if cid not in seen:
                    seen.add(cid)
                    parts.append(table_html(B, charts[cid], sources))
        tables.append(f'<h2 id="{who}">{e(WHO_HEAD[who])}</h2>' + "".join(parts))

    garments_js = json.dumps([{"slug": g["slug"], "who": g["who"], "label": g["label"], "measures": g["measures"], "charts": g["charts"]}
                              for g in data["garments"]], ensure_ascii=False, separators=(",", ":"))
    who_opts = "".join(f'<option value="{w}">{l}</option>' for w, l in WHO)
    inputs = "".join(f'<label data-m="{m}" hidden>{MEASURE_LABELS[m]}<input id="cs-{m}" type="number" min="1" max="250" step="0.5" inputmode="decimal" placeholder="e.g. {ph}"></label>'
                     for m, ph in (("chest", "96"), ("bust", "88"), ("waist", "80"), ("hips", "98"), ("height", "116")))

    clothes = [d for d in deals if d["category"] == "clothing"]
    cards = "".join(B.card(cfg, d, "../").replace('<article class="card"', '<article class="card" data-for="%s"' % e(
        d.get("specs", {}).get("For", "").lower()), 1) for d in clothes)
    picks_html = (f"""<h2 id="picks">Our clothing picks for trips</h2>
<p id="cs-picks-note">Thermals, jackets and rain wear for men and women. Each Amazon page has the brand's own size chart: check it before you order.</p>
<div class="grid" id="cs-picks">{cards}</div>""" if clothes else "")

    checked = B.fmt_date(data["checked"])
    src_links = ", ".join(f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])}</a>' for s in data["sources"])
    title = "Size chart for men, women and kids in India: UK, US and EU to Indian size"
    seo = "Clothing size chart India: UK, US, EU to Indian size for men, women, kids"
    desc = ("Free clothing size converter for India. Enter your chest, bust, waist or hips in cm or inches, or pick a size, "
            "and see UK, US, EU and letter sizes (XS to XXL) for men, women and kids, from M&S India, ONLY India, Libas and Levi's India charts.")
    body = f"""{more_tools._head(B, title, "Clothing size converter", "A free tool. Updated " + B.fmt_date(UPDATED), "clothing", "jacket")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>India has no single size system.</strong> Stores like Marks &amp; Spencer India sell UK sizes, and Indian brands use letters (S, M, L) and inches (a 38 kurta, a 32 jeans).</li>
<li>On M&amp;S's charts, a women's UK {uk10["size"][3:]} fits a {cm("ms-women-tops", "UK 10", "bust")} bust. It is size {uk10["Letter"]}, and M&amp;S lists it with US {uk10["US"]} and EU {uk10["EU"]}.</li>
<li>Go by your body in cm or inches, not by the letter. Sizes vary by brand, so check the brand's own chart too.</li>
</ul></div>
<h2>Step 1: measure yourself</h2>
{B.diagram_figure("measure-body", "../")}
<ol>
<li><strong>Chest or bust:</strong> wear a thin top, and put the tape round the fullest part, under the arms. Keep it level across your back.</li>
<li><strong>Waist:</strong> round the narrowest part of your body, usually just above the navel. Breathe out normally; don't pull in your stomach.</li>
<li><strong>Hips:</strong> stand with your feet together and put the tape round the widest part of your bottom.</li>
<li><strong>Kids:</strong> measure height without shoes, standing against a wall, and the chest round the fullest part.</li>
<li>Keep the tape snug, not tight. No tape? Use a string, then lay it on a ruler.</li>
</ol>
<h2>Step 2: find your size</h2>
<form class="checker" id="cs" onsubmit="return false" data-garments='{e(garments_js)}' hidden data-js>
<div class="checker-fields"><label>Clothes for<select id="cs-who">{who_opts}</select></label>
<label>What<select id="cs-garment"></select></label>
<label>Units<select id="cs-unit"><option value="cm">cm</option><option value="in">inches</option></select></label>
{inputs}
<label>Or, a size I know<select id="cs-size"><option value="">Choose…</option></select></label></div>
<p class="checker-total" id="cs-out" aria-live="polite">Type your measurement, or pick a size you know, to see it on each brand's chart.</p>
<div id="cs-result" hidden>
<ul id="cs-r-list"></ul>
<p class="hint" id="cs-r-note"></p>
<p id="cs-r-links"><a href="#picks">See our clothing picks</a> &middot; <a href="../category/clothing.html">All clothing and winter wear</a> &middot; <a href="shoe-size.html">Shoe size converter</a></p>
</div>
</form>
<h2>Size charts</h2>
<p>All the charts below are body measurements: the size that fits a body of that chest, waist or hip. Each chart keeps its brand's own numbers, and we name the brand on every chart. Where brands differ, we show both.</p>
{"".join(tables)}
<p class="checked">Checked on {checked} on {src_links}. Sizes vary by brand and by fit (slim, regular, relaxed), so the size chart on the product page is the one to trust.</p>
<h2>UK, US and EU sizes for women</h2>
<p>M&amp;S's own table gives UK, US and EU sizes in pairs: UK 8–10 is US 4–6 and EU 36–38 (Small), and UK 12–14 is US 8–10 and EU 40–42 (Medium). Up to UK 26, M&amp;S's US number is 4 less than the UK one and the EU number is 28 more. Other brands can differ, and M&amp;S gives no US or EU sizes for trousers.</p>
<h2>Women's jeans sizes 26, 28, 30, 32</h2>
<p>Women's jeans in India are often sold by number. On ONLY India's chart, a size {w28["size"]} jeans is an {w28["Letter"]}, a UK {w28["UK"]} and a US {w28["US"]}, for a {B.num(w28["waist"])} cm waist and {B.num(w28["hips"])} cm hips. A size {w30["size"]} is an {w30["Letter"]} (UK {w30["UK"]}, US {w30["US"]}), for a {B.num(w30["waist"])} cm waist and {B.num(w30["hips"])} cm hips. ONLY gives the same numbers to each pair of sizes (25 and 26, 27 and 28, and so on), so either size of a pair fits the same body. ONLY's product pages also list each size's own garment measurements under Size Details.</p>
<p>Brands differ: ONLY's UK 10 jeans are for a {cm("only-women-jeans", "30", "waist")} waist, but M&amp;S's UK 10 trousers are for a {cm("ms-women-bottoms", "UK 10", "waist")} waist. Use the chart of the brand you buy.</p>
<h2>Men's shirt sizes 38, 39, 40, 42</h2>
<p>Formal shirts in India are often sold by collar size in cm. On M&amp;S India's chart, a {f38["size"]} collar is a {f38["Letter"]} with a {cm("ms-men-formal", "38", "chest")} chest, and a 42 collar is an L. T-shirts and casual shirts go by letter: an M fits a {cm("ms-men-tops", "M", "chest")} chest on M&amp;S's chart.</p>
<p>Kids' clothes are sold by age, but children of the same age differ a lot. Go by height first: if your child is between two sizes, take the bigger one.</p>
{picks_html}
<p>More help: our <a href="shoe-size.html">shoe size converter</a> (India/UK, US, EU and cm), <a href="../guides/winter-clothes-for-hill-trips.html">winter clothes for hill trips</a> and <a href="../category/clothing.html">all our clothing picks</a>.</p>
{{faq}}
{B.tool_pills("../", PATH)}
</article></div>
<script src="../assets/clothing-size.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("Is a 38 size shirt M or L?",
         "On Marks & Spencer India's formal shirt chart, a 38 collar is an %s, for a chest of %s. A 41 or 42 collar is an L. Indian brands use the same collar numbers, but which letter they call it can differ, so check the brand's chart."
         % (f38["Letter"], cm("ms-men-formal", "38", "chest"))),
        ("What is XL size in number for men?",
         "On M&S India's charts, an XL shirt or T-shirt fits a %s chest (about 44–46 in), and XL trousers fit a %s waist (about 39–41 in)."
         % (cm("ms-men-tops", "XL", "chest"), cm("ms-men-trousers", "XL", "waist"))),
        ("Is 32 size jeans L or XL?",
         "Usually neither. On Levi's India's 511 chart, size 32 is for a waist of %s cm (about 33.5 in). On M&S India's trouser chart, that waist is a %s (%s)."
         % (B.num(lev32["waist"]), m_trousers["size"], cm("ms-men-trousers", m_trousers["size"], "waist"))),
        ("How do I convert UK size to Indian size for clothes?",
         "Many stores in India, like Marks & Spencer India, sell clothes in UK sizes, so a UK 12 is the same size here. On M&S's chart a women's UK 12 is a Medium, for a %s bust."
         % cm("ms-women-tops", "UK 12", "bust")),
        ("What is 28 size jeans for women?",
         "On ONLY India's chart, size 28 jeans are an %s, a UK %s and a US %s, for a waist of %s cm (about %s in) and hips of %s cm."
         % (w28["Letter"], w28["UK"], w28["US"], B.num(w28["waist"]), B.num(half(w28["waist"] / 2.54)), B.num(w28["hips"]))),
        ("What is size 30 jeans for women in US and UK size?",
         "On ONLY India's chart, size 30 is a UK %s and a US %s (%s), for a %s cm waist and %s cm hips."
         % (w30["UK"], w30["US"], w30["Letter"], B.num(w30["waist"]), B.num(w30["hips"]))),
        ("What is US size to Indian size for women's clothes?",
         "On M&S's table, US 4–6 is UK 8–10 and EU 36–38 (Small), and US 8–10 is UK 12–14 and EU 40–42 (Medium). Sizes in India are usually given as UK sizes or letters."),
        ("What does kurti size 38 mean?",
         "On Libas's kurta chart, the 38 is the bust in inches: size %s fits a %s in bust, %s in waist and %s in hips." % (lib_m["size"], lib_m["bust"], lib_m["waist"], lib_m["hips"])),
        ("What size is a 5 year old in India?",
         "On M&S India's boys' chart, 5–6 years is for a height of %s cm and a chest of %s cm. Measure your child's height, because children of the same age differ a lot."
         % (B.num(boy5["height"]), B.num(boy5["chest"]))),
        ("How do I measure my chest, waist and hips?",
         "Use a soft tape. Chest or bust: round the fullest part, under the arms. Waist: round the narrowest part, above the navel. Hips: round the widest part of the bottom, feet together. Keep the tape level and snug, not tight."),
    ]
    more_tools._finish(B, cfg, pages, lastmod, PATH, seo, desc, "Clothing size converter", body, faq, UPDATED)
