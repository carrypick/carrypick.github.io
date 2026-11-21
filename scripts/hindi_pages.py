"""Hindi versions of our most-searched English pages, built from the same data so the two never drift apart.

- hi/trolley-bag-size-chart.html      <- baggage/luggage-size-chart.html (SIZE_ROWS, CM_ROWS, CAPACITY_ROWS, airline limits)
- hi/can-i-carry/<slug>.html          <- baggage/can-i-carry/<slug>.html (text in content/carry-hi/<slug>.md; the answers'
                                         yes/no and the Hindi rule come from data/flight_items.json and data/hindi.json)
- hi/extra-baggage-charges.html (+ one page per airline) <- data/extra_baggage.json (Hindi wording in data/hindi.json "extra_baggage")
- hi/cabin-bag-checker.html           <- baggage/checker.html (same airline rows and picks; static/checker.js takes its Hindi words from the page)
- hi/guides/<slug>.html               <- guides/<slug>.html (text in content/articles-hi/<slug>.md)
Hindi trip guides and guides with `matches: <English updated date>` are checked against the English page (check_twin).

build.py calls register() before any page is written (so the English pages get hreflang tags and the language menu link),
then build_all() at the end. B is the build module itself, so this file uses its helpers (page, top_picks, num ...).
Every Hindi text that repeats an English fact keeps a copy of the English it was written from: when the English changes,
the build prints a warning, so update the Hindi at the same time.
"""

import hashlib
import json
import re
import unicodedata
from html import escape as e

from common import ROOT

CARRY_HI_DIR = ROOT / "content" / "carry-hi"  # same file names as content/carry
SIZE_PATH = "hi/trolley-bag-size-chart.html"
SIZE_CHECKED = "2026-11-15"  # the English size chart's SIZE_CHART_UPDATED when this Hindi page was last matched to it
EXTRA_HUB = "hi/extra-baggage-charges.html"
HI_DISCLOSURE = "हम Amazon Associate हैं और योग्य ख़रीदारी पर कमीशन कमाते हैं। आपके लिए क़ीमत वही रहती है।"

# English row (from build.SIZE_ROWS) -> Hindi
SIZE_ROWS_HI = {
    18: ("Small cabin bag", "1–3 days", "छोटा केबिन बैग", "1–3 दिन"),
    20: ("Cabin", "2–4 days", "केबिन", "2–4 दिन"),
    22: ("Cabin, at the height limit of most Indian airlines", "2–4 days", "केबिन, ज़्यादातर भारतीय एयरलाइनों की ऊँचाई की सीमा पर", "2–4 दिन"),
    24: ("Small medium", "4–6 days", "छोटा मीडियम", "4–6 दिन"),
    26: ("Medium", "5–8 days", "मीडियम", "5–8 दिन"),
    28: ("Large", "8–12 days", "लार्ज (बड़ा)", "8–12 दिन"),
    30: ("Large", "10+ days, families", "लार्ज (बड़ा)", "10 से ज़्यादा दिन, परिवार के लिए"),
    32: ("Extra large: check the 158 cm limit", "Long trips", "बहुत बड़ा: 158 cm की सीमा ज़रूर देखें", "लंबी यात्रा"),
}
KINDS_HI = {"Cabin": "केबिन", "Medium": "मीडियम", "Large": "लार्ज"}
# English capacity row (build.CAPACITY_ROWS) -> Hindi height and clothes text
CAPACITY_HI = {
    ("Cabin", "About 55 cm", "39 L", "2.5 kg", "6–12 kg"): ("लगभग 55 cm", "6–12 kg"),
    ("Medium", "65–69 cm", "69 L", "3.4 kg", "10–21 kg"): ("65–69 cm", "10–21 kg"),
    ("Large", "75–80 cm", "108 L", "4.3 kg", "16–32 kg"): ("75–80 cm", "16–32 kg"),
}
# build.SIZE_CHART_PICKS: ASIN -> (English reason it was written from, Hindi label, Hindi reason)
SIZE_PICKS_HI = {
    "B097JLKP8X": ("Listed at 55 x 35 x 25 cm, within the cabin limit of IndiGo, Akasa Air and SpiceJet's Boeing planes. 2.7 kg empty.",
                   "केबिन साइज, IndiGo के लिए",
                   "लिस्टिंग में साइज 55 x 35 x 25 cm है, यानी IndiGo, Akasa Air और SpiceJet के Boeing विमानों की केबिन सीमा के अंदर। ख़ाली बैग 2.7 kg का।"),
    "B0F5HGLC5Q": ("Only 20 cm deep, so by its listed size it fits Air India's 55 x 40 x 20 cm limit. 2.2 kg empty.",
                   "केबिन साइज, Air India के लिए",
                   "सिर्फ़ 20 cm गहरा, इसलिए लिस्टिंग के साइज के हिसाब से Air India की 55 x 40 x 20 cm सीमा में फिट। ख़ाली बैग 2.2 kg का।"),
    "B0GNSKLF5Z": ("The lightest medium trolley we found, at 2.52 kg, so more of a 15 kg fare is left for your things.",
                   "मीडियम, 65–69 cm",
                   "हमें मिली सबसे हल्की मीडियम ट्रॉली, 2.52 kg की। इसलिए 15 kg वाले टिकट में आपके सामान के लिए ज़्यादा वज़न बचता है।"),
    "B0GX5VFHMS": ("Listed at 152 cm in total, inside the 158 cm check-in limit that most large trolleys go over.",
                   "लार्ज, 75–80 cm",
                   "लिस्टिंग में कुल 152 cm, यानी 158 cm की चेक-इन सीमा के अंदर। ज़्यादातर बड़ी ट्रॉलियाँ इस सीमा से बड़ी होती हैं।"),
}
ANSWER_HI = {"yes": ("yes", "yes"), "no": ("no", "no"), "conditional": ("close", "conditional"), "unknown": ("na", "unknown")}


def nfc(text):
    return unicodedata.normalize("NFC", text)


def warn(text):
    print("Warning (Hindi pages): " + text)


def load_hindi():
    return json.loads((ROOT / "data" / "hindi.json").read_text(encoding="utf-8"))


# ---------- which pages exist ----------

def carry_hi(B):
    """(Hindi article, English article, flight item row) for each content/carry-hi/<slug>.md."""
    if not CARRY_HI_DIR.exists() or not B.FLIGHT_ITEMS_FILE.exists():
        return []
    data = json.loads(B.FLIGHT_ITEMS_FILE.read_text(encoding="utf-8"))
    english = {a["slug"]: (a, it) for a, it in B.load_carry_pages(data)}
    out = []
    for h in B.load_articles(CARRY_HI_DIR):
        if h["slug"] not in english:
            B.sys.exit("Error: content/carry-hi/%s.md has no English page in content/carry" % h["slug"])
        missing = [k for k in ("title", "description", "cabin_short", "checked_short", "rechecked", "checked_against") if not h.get(k)]
        if missing:
            B.sys.exit("Error: content/carry-hi/%s.md is missing %s in its front matter" % (h["slug"], ", ".join(missing)))
        if any(tag in h["body"] for tag in ("[[shop:", "[[book:", "[[fly:", "[[coupon:")):
            B.sys.exit("Error: content/carry-hi/%s.md links to another shop. These pages carry Amazon picks only." % h["slug"])
        a, it = english[h["slug"]]
        if h["rechecked"] != it.get("rechecked", data["checked"]):
            warn("content/carry-hi/%s.md was matched to the rule of %s, but %r was rechecked %s. Update the Hindi page."
                 % (h["slug"], h["rechecked"], it["item"], it.get("rechecked", data["checked"])))
        out.append((h, a, it))
    order = [a["slug"] for a, it in B.load_carry_pages(data)]
    return sorted(out, key=lambda x: order.index(x[0]["slug"]))


def register(B, extra):
    """Pair each Hindi page with its English page (hreflang tags, language menu). Call before any page is written."""
    B.HINDI_PAGES["baggage/luggage-size-chart.html"] = SIZE_PATH
    if "baggage/index.html" in B.HINDI_PAGES:
        B.HINDI_PAGES["baggage/checker.html"] = CHECKER_PATH
    for h in guides_hi(B):
        B.HINDI_PAGES["guides/%s.html" % h["slug"]] = "hi/guides/%s.html" % h["slug"]
    for h, a, it in carry_hi(B):
        B.HINDI_PAGES["baggage/can-i-carry/%s.html" % h["slug"]] = "hi/can-i-carry/%s.html" % h["slug"]
    import hindi_tools
    hindi_tools.register(B)  # Hindi shoe size, power bank and other tool twins
    hi = load_hindi()
    if extra and "extra_baggage" in hi:
        B.HINDI_PAGES[B.EXTRA_PATH] = EXTRA_HUB
        for x in extra["airlines"]:
            if x["slug"] in hi["extra_baggage"]["by_airline"]:
                B.HINDI_PAGES[B.extra_path(x["slug"])] = "hi/extra-baggage-charges/%s.html" % x["slug"]


def tool_links(B, current, p):
    """'More free tools' pills for every Hindi page: our Hindi tools and trip guides, then English tools that have no Hindi page."""
    hi = load_hindi()
    mine = [(B.HINDI_PATHS["baggage/index.html"], hi["airlines"]["crumb"]),
            (B.HINDI_PATHS["baggage/can-i-carry.html"], hi["flight_items"]["crumb"]),
            (B.HINDI_PATHS["baggage/train-luggage-rules.html"], hi["railways"]["crumb"])]
    if B.HINDI_PAGES.get("baggage/luggage-size-chart.html") == SIZE_PATH:
        mine.append((SIZE_PATH, "ट्रॉली बैग साइज चार्ट"))
    if B.HINDI_PAGES.get(B.EXTRA_PATH) == EXTRA_HUB:
        mine.append((EXTRA_HUB, "एक्स्ट्रा बैगेज चार्ज"))
    if B.HINDI_PAGES.get("baggage/checker.html") == CHECKER_PATH:
        mine.insert(1, (CHECKER_PATH, "केबिन बैग चेकर"))
    import hindi_tools
    mine += [t for t in hindi_tools.TOOLS_HI if B.HINDI_PAGES.get(hindi_tools.english_path(t[0])) == t[0]]
    mine += [("hi/guides/%s.html" % h["slug"], guide_short(h)) for h in guides_hi(B)]
    links = "".join(f'<li><a href="{p}{path}">{e(name)}</a></li>' for path, name in mine if path != current)
    if B.TRIPS_HI_DIR.exists():
        links += "".join(f'<li><a href="{p}hi/trips/{t["slug"]}.html">{e(t.get("place", t["title"]))} ट्रिप गाइड</a></li>'
                         for t in B.load_articles(B.TRIPS_HI_DIR) if "hi/trips/%s.html" % t["slug"] != current)
    links += "".join(f'<li><a href="{p}{t[0]}" lang="en">{e(t[1])} (English)</a></li>' for t in B.TOOLS if t[0] not in B.HINDI_PAGES)
    return f'<h2>और मुफ़्त टूल</h2><ul class="airline-links">{links}</ul>'


def head(B, crumbs, title, sub, tint, art, p, extra_line=""):
    """crumbs: (href or None, text) pairs after Home."""
    trail = "".join(f'<span>/</span><a href="{href}">{e(text)}</a>' if href else f"<span>/</span>{e(text)}" for href, text in crumbs)
    line = f'\n      <p class="muted small" lang="hi-Latn">{e(extra_line)}</p>' if extra_line else ""
    inner = f"""<nav class="crumbs"><a href="{p}index.html">होम</a>{trail}</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">{e(sub)}</p>{line}"""
    return B.page_head(tint, f'<div class="media media-tile tint-{tint}">{art}</div>', inner, p)


def faq_html(B, faq):
    return B.faq_block(faq, "सवाल-जवाब")


def finish(B, cfg, pages, lastmod, path, seo, desc, body, depth, crumbs, published, modified, faq_schema=None):
    schema = [B.tool_article(cfg, seo, desc, path, published, modified, "hi-IN"), B.crumbs_schema(cfg, crumbs)]
    if faq_schema:
        schema.append(faq_schema)
    pages.append(B.write(path, B.page(cfg, nfc(seo), nfc(desc), nfc(body), depth, path, schema, og_type="article", lang="hi")))
    lastmod[path] = modified


# ---------- trolley bag size chart ----------

def build_size_chart(B, cfg, deals_by_asin, airlines, intl, pages, lastmod):
    path, p = SIZE_PATH, "../"
    if SIZE_CHECKED != B.SIZE_CHART_UPDATED:
        warn("the English size chart was updated %s, the Hindi one matched %s. Update scripts/hindi_pages.py."
             % (B.SIZE_CHART_UPDATED, SIZE_CHECKED))
    num = B.num
    cm = lambda inches: num(round(inches * 2.54, 1))
    inch = lambda c: num(round(c / 2.54, 1))
    lb = lambda kg: num(round(kg * 2.20462, 1))

    size_rows = []
    for i, kind, trip in B.SIZE_ROWS:
        h = SIZE_ROWS_HI.get(i)
        if not h or (h[0], h[1]) != (kind, trip):
            warn("size chart row %d inch changed in English (%s, %s). Update SIZE_ROWS_HI." % (i, kind, trip))
        hk, ht = (h[2], h[3]) if h else (kind, trip)
        name = f'<a href="{B.SIZE_GUIDES[i]}" lang="en">{i} इंच</a>' if i in B.SIZE_GUIDES else f"{i} इंच"
        size_rows.append(f'<tr><th scope="row">{name}</th><td>{cm(i)} cm</td><td>{e(hk)}</td><td>{e(ht)}</td></tr>')
    for c, kind in B.CM_ROWS:
        if kind not in KINDS_HI:
            warn("size kind %r has no Hindi name in KINDS_HI" % kind)
    cm_rows = "".join(f'<tr><th scope="row">{c} cm</th><td>{inch(c)} इंच</td><td>{e(KINDS_HI.get(kind, kind))}</td></tr>' for c, kind in B.CM_ROWS)
    capacity_rows = []
    for row in B.CAPACITY_ROWS:
        h = CAPACITY_HI.get(tuple(row))
        if not h:
            warn("capacity row %r changed in English. Update CAPACITY_HI." % (row,))
            h = (row[1], row[4])
        kind, litres, empty = row[0], row[2], row[3]
        capacity_rows.append(f'<tr><th scope="row">{e(KINDS_HI.get(kind, kind))}</th><td>{e(h[0])}</td><td>{e(litres)}</td><td>{e(empty)}</td><td>{e(h[1])}</td></tr>')
    kg_rows = "".join(f'<tr><th scope="row">{k} kg</th><td>{lb(k)} lb</td></tr>' for k in B.KG_ROWS)

    air_rows, us_fit = "", []
    us = [22 * 2.54, 14 * 2.54, 9 * 2.54]
    for a in (airlines or {}).get("airlines", []) + [x for x in (intl or {}).get("airlines", []) if x.get("checker", True)]:
        c = a["cabin"]
        if not c.get("dims_cm"):
            continue
        total = c.get("total_cm")
        air_rows += (f'<tr><th scope="row"><a href="../baggage/{a["slug"]}.html" lang="en">{e(a["name"])}</a></th>'
                     f'<td>{" x ".join(num(x) for x in c["dims_cm"])} cm' + (f'<span class="why">कुल {num(total)} cm</span>' if total else "") + "</td>"
                     f'<td>{" x ".join(inch(x) for x in c["dims_cm"])} इंच' + (f'<span class="why">कुल {inch(total)} इंच</span>' if total else "") + "</td>"
                     + (f'<td>{num(c["kg"])} kg<span class="why">{lb(c["kg"])} lb</span></td></tr>' if c.get("kg") else "<td>सीमा नहीं बताई</td></tr>"))
        if B.size_fit(us, c)[0] and a.get("scope") != "international":
            us_fit.append(a["name"])
    us_cm, us_total = " x ".join(num(round(x, 1)) for x in us), num(round(sum(us), 1))
    us_answer = (f"22 x 14 x 9 इंच = {us_cm} cm, यानी कुल {us_total} cm। साइज के हिसाब से यह {' और '.join(us_fit)} की सीमा में आता है, "
                 "लेकिन बाक़ी भारतीय एयरलाइनों की सीमा से थोड़ा बड़ा है।") if us_fit else (
                 f"22 x 14 x 9 इंच = {us_cm} cm, यानी कुल {us_total} cm। यह हमारी लिस्ट की भारतीय एयरलाइनों की केबिन सीमा से थोड़ा बड़ा है।")
    indigo = next((a for a in (airlines or {}).get("airlines", []) if a["slug"] == "indigo"), None)

    quick = [f"1 इंच = 2.54 cm। यानी 20 इंच का बैग {cm(20)} cm, 24 इंच का {cm(24)} cm और 28 इंच का {cm(28)} cm होता है।",
             "भारतीय ब्रांड ज़्यादातर ट्रॉली को cm में ऊँचाई से बेचते हैं: केबिन के लिए लगभग 55 cm, मीडियम के लिए 65–69 cm और लार्ज के लिए 75–79 cm।",
             f"22 इंच का बैग ({cm(22)} cm) आम 55 cm केबिन ऊँचाई के सबसे क़रीब है। असली 20 इंच का बैग इससे छोटा होता है, लेकिन कुछ ब्रांड 55 cm बैग को "
             "\"20 इंच\" और 65 cm बैग को \"24 इंच\" कहकर बेचते हैं, इसलिए cm ज़रूर देखें।"]
    if indigo:
        dims = indigo["cabin"]["dims_cm"]
        quick.append(f"IndiGo की केबिन सीमा {' x '.join(num(x) for x in dims)} cm है, यानी {' x '.join(inch(x) for x in dims)} इंच।")
    quick.append("इंच वाला साइज सिर्फ़ ऊँचाई बताता है। एयरलाइन लंबाई, चौड़ाई और ऊँचाई तीनों देखती है, पहिए और हैंडल समेत।")

    faq = [
        ("ट्रॉली बैग का साइज कितना होता है?",
         f"भारत में ट्रॉली बैग तीन साइज में आते हैं: केबिन लगभग 55 cm ({inch(55)} इंच), मीडियम 65–69 cm ({inch(65)}–{inch(69)} इंच) "
         f"और लार्ज 75–79 cm ({inch(75)}–{inch(79)} इंच)। यह बैग की ऊँचाई है, पहियों समेत।"),
        ("छोटी ट्रॉली बैग का साइज cm में कितना होता है?",
         f"छोटी ट्रॉली का मतलब आमतौर पर केबिन ट्रॉली है, लगभग 55 cm ({inch(55)} इंच) ऊँची। कई ट्रॉली 36–41 cm चौड़ी होती हैं, लेकिन IndiGo की "
         "केबिन सीमा 55 x 35 x 25 cm है, इसलिए ख़रीदने से पहले तीनों साइड देखें।"),
        ("मीडियम ट्रॉली बैग का साइज कितना होता है?",
         f"भारत में बिकने वाली ज़्यादातर मीडियम ट्रॉली 65–69 cm ({inch(65)}–{inch(69)} इंच) ऊँची और कुल 135–147 cm होती हैं। यह हमारे पढ़े 36 मॉडल "
         "से है। उनमें 45 से 93 लीटर लिखा था, और आमतौर पर 69 लीटर।"),
        ("सबसे बड़ा ट्रॉली बैग कितने इंच का होता है?",
         f"हमारे चार्ट में सबसे बड़ा साइज 32 इंच ({cm(32)} cm) है, लंबी यात्रा के लिए। लेकिन ज़्यादातर भारतीय एयरलाइनें हर चेक-इन बैग को कुल 158 cm "
         "तक ही लेती हैं। 6 नवंबर 2026 को Amazon.in पर हमने 31 बड़े मॉडल देखे, उनमें से 26 की लिस्टिंग 158 cm से ज़्यादा थी। "
         "इसलिए बड़ा बैग लेने से पहले लंबाई, चौड़ाई और ऊँचाई जोड़कर देखें।"),
        ("20 इंच का बैग कितने cm का होता है?",
         f"20 इंच = {cm(20)} cm। यह भारत में बिकने वाली आम 55 cm केबिन ट्रॉली से छोटा है, हालाँकि कुछ ब्रांड 55 cm बैग को \"20 इंच\" कहकर बेचते हैं।"),
        ("24 इंच का सूटकेस केबिन में जाएगा या चेक-इन में?",
         f"चेक-इन में। 24 इंच = {cm(24)} cm, जो भारतीय एयरलाइनों की 55–56 cm की केबिन ऊँचाई से ज़्यादा है। यह छोटा मीडियम बैग है, 4–6 दिन के लिए अच्छा।"),
        ("55 cm का केबिन बैग कितने इंच का होता है?", f"55 cm = {inch(55)} इंच।"),
        ("22 x 14 x 9 इंच कितने cm होते हैं?", us_answer),
        ("23 kg कितने पाउंड होते हैं?",
         f"23 kg लगभग {lb(23)} lb है। 7 kg, यानी भारतीय एयरलाइनों में केबिन बैग की आम सीमा, लगभग {lb(7)} lb है।"),
        ("ट्रॉली बैग का साइज कैसे पता करें?",
         "लिस्टिंग में Product Dimensions देखें, या बैग के टैग पर। ख़ुद नापना हो तो फ़ीते से पहियों के नीचे से ऊपर तक ऊँचाई, फिर चौड़ाई और गहराई नापें, "
         "जेबें और हैंडल समेत। cm को इंच में बदलने के लिए 2.54 से भाग दें।"),
    ]
    faq_block, faq_schema = faq_html(B, faq)

    pick_rows = []
    for asin, label, why in B.SIZE_CHART_PICKS:
        if asin not in deals_by_asin:
            continue
        h = SIZE_PICKS_HI.get(asin)
        if not h or h[0] != why:
            warn("size chart pick %s changed in English. Update SIZE_PICKS_HI." % asin)
        pick_rows.append((deals_by_asin[asin], h[1] if h else label, h[2] if h else why))
    picks_html = B.top_picks(cfg, pick_rows, p, "हर साइज के लिए हमारी पसंद",
                             'हमने इन्हें क्यों चुना: <a href="../guides/cabin-luggage-guide.html#our-cabin-bag-picks" lang="en">केबिन</a>, '
                             '<a href="../guides/24-inch-trolley-bag-size.html#our-picks" lang="en">मीडियम</a> और '
                             '<a href="../guides/28-inch-trolley-bag-size.html#our-picks-all-within-158-cm-by-their-listed-size" lang="en">लार्ज</a> '
                             'पिक्स की तुलना (English)')
    end_html = B.next_step([("../guides/cabin-luggage-guide.html#our-cabin-bag-picks", "IndiGo और Air India में फिट केबिन ट्रॉली (English)"),
                            ("../guides/24-inch-trolley-bag-size.html#our-picks", "मीडियम चेक-इन ट्रॉली, 65–69 cm (English)"),
                            ("../guides/28-inch-trolley-bag-size.html#our-picks-all-within-158-cm-by-their-listed-size", "158 cm की सीमा में बड़ी ट्रॉली (English)"),
                            ("cabin-bag-checker.html", "अपना बैग हर एयरलाइन से मिलाएँ")],
                           "साइज मिल गया? अब बैग चुनें", "उस साइज के लिए हमारी चुनी ट्रॉलियाँ देखें, हर एक का लिस्टेड साइज, वज़न और कौन-सी एयरलाइन में फिट है।")
    size_fig = B.diagram_figure("luggage-sizes", p) if "luggage-sizes" in B.DIAGRAMS else ""
    title = "ट्रॉली बैग साइज चार्ट: cm, इंच, लीटर और kg"
    seo = "ट्रॉली बैग का साइज कितना होता है? cm और इंच में साइज चार्ट"
    desc = (f"ट्रॉली बैग का साइज cm में: 20 इंच = {cm(20)} cm, 24 इंच = {cm(24)} cm, 28 इंच = {cm(28)} cm। केबिन, मीडियम और लार्ज सूटकेस का साइज, "
            "लीटर, kg और एयरलाइन की सीमा।")
    big = (f'ज़्यादातर भारतीय एयरलाइनें हर चेक-इन बैग को <strong>कुल 158 cm</strong> (लंबाई + चौड़ाई + ऊँचाई) तक लेती हैं, जो लगभग {inch(158)} इंच है, '
           f'और <strong>32 kg</strong> (लगभग {lb(32)} lb) तक। कई बड़ी ट्रॉलियाँ इससे बड़ी होती हैं: 6 नवंबर 2026 को Amazon.in पर हमने 31 बड़े मॉडल '
           '<strong>जाँचे, उनमें से 26 की लिस्टिंग 158 cm से ज़्यादा थी</strong>। <a href="../guides/28-inch-trolley-bag-size.html" lang="en">बाक़ी 5 देखें (English)</a>।')
    body = f"""{head(B, [("../baggage/index.html", "बैगेज नियम"), (None, "साइज चार्ट")], title, "%s को अपडेट किया गया" % B.hi_date(B.SIZE_CHART_UPDATED),
                "luggage", B.icon("ruler", "icon media-icon"), p, "Trolley bag ka size kitna hota hai? Small, medium aur large trolley ka size cm aur inch mein.")}
<div class="wrap"><article class="guide">
<p class="lead">ट्रॉली बैग ऊँचाई के हिसाब से बिकते हैं। नीचे हर साइज इंच और cm में है, और यह भी कि वह कितने दिन की यात्रा के लिए ठीक है। किसी साइज की पूरी गाइड के लिए उस पर टैप करें।</p>
<h2>ट्रॉली बैग के साइज: इंच और cm में</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>इंच</th><th>cm</th><th>साइज</th><th>यात्रा</th></tr></thead><tbody>{"".join(size_rows)}</tbody></table></div>
<p class="small">साइज का मतलब बैग की ऊँचाई है। विक्रेता हमेशा नहीं बताते कि इसमें पहिए शामिल हैं या नहीं, इसलिए लिस्टिंग पर पूरा साइज देखें।</p>
{picks_html}
<h2>भारतीय ट्रॉली के साइज cm में, इंच में</h2>
<p>भारतीय ब्रांड ट्रॉली की ऊँचाई cm में लिखते हैं। यहाँ हर आम ऊँचाई इंच में है।</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>लिस्टेड ऊँचाई</th><th>इंच</th><th>साइज</th></tr></thead><tbody>{cm_rows}</tbody></table></div>
<div class="answer"><h2>सीधा जवाब</h2><ul>{"".join("<li>%s</li>" % e(x) for x in quick)}</ul></div>
<h2>ट्रॉली बैग का साइज कैसे नापें</h2>
<ul>
<li>बैग ख़ाली करके सीधा खड़ा करें, और खींचने वाला हैंडल पूरा अंदर कर दें।</li>
<li><strong>ऊँचाई:</strong> ज़मीन से, यानी पहियों के नीचे से, बैग के सबसे ऊपर तक। ऊपर वाला हैंडल भी गिनें।</li>
<li><strong>चौड़ाई:</strong> एक तरफ़ से दूसरी तरफ़ तक, साइड वाले हैंडल समेत।</li>
<li><strong>गहराई:</strong> आगे से पीछे तक, आगे की जेब और पीछे के पहियों समेत।</li>
<li>तीनों को जोड़ें। केबिन बैग अपनी एयरलाइन की सीमा में हो, और चेक-इन बैग कुल 158 cm से ज़्यादा न हो।</li>
</ul>
<p>ऑनलाइन ख़रीद रहे हैं? लिस्टिंग में Product Dimensions या Item dimensions देखें। \"24 इंच\" जैसा साइज आमतौर पर सिर्फ़ ऊँचाई बताता है।</p>
<h2>इंच, cm, kg और lb बदलें</h2>
<form class="checker" onsubmit="return false">
<div class="checker-fields"><label>संख्या<input id="cv-n" type="number" min="0" step="any" inputmode="decimal" placeholder="जैसे 22"></label>
<label>किससे<select id="cv-unit"><option value="in">इंच</option><option value="cm">cm</option><option value="kg">kg</option><option value="lb">lb</option></select></label></div>
<p class="checker-total" id="cv-out" aria-live="polite" data-units="cm|इंच|lb|kg"></p>
<p class="hint">आपके बैग का साइज इंच में है? नीचे तीनों साइड लिखें और उसे हर एयरलाइन से मिलाएँ।</p>
<div class="checker-fields"><label>लंबाई (इंच)<input id="cv-l" type="number" min="0" step="any" inputmode="decimal"></label>
<label>चौड़ाई (इंच)<input id="cv-w" type="number" min="0" step="any" inputmode="decimal"></label>
<label>ऊँचाई (इंच)<input id="cv-h" type="number" min="0" step="any" inputmode="decimal"></label></div>
<p class="checker-total" id="cv-bag" aria-live="polite" data-bag="आपका बैग: {{cm}} cm, कुल {{total}} cm"></p>
<p class="hint"><a id="cv-check" href="cabin-bag-checker.html" data-base="cabin-bag-checker.html" data-open="केबिन बैग चेकर खोलें" data-ready="इस बैग को हर एयरलाइन से मिलाएँ">केबिन बैग चेकर खोलें</a></p>
</form>
{size_fig}
{('<h2>केबिन बैग की सीमा इंच में: भारतीय और विदेशी एयरलाइनें</h2><div class="table-wrap"><table class="compare snug"><thead><tr><th>एयरलाइन</th><th>साइज की सीमा (cm)</th><th>इंच में</th><th>वज़न</th></tr></thead><tbody>' + air_rows + '</tbody></table></div><p class="checked">इकॉनमी की सीमा: भारतीय एयरलाइनों के लिए घरेलू उड़ानें, विदेशी एयरलाइनों के लिए भारत के रूट। हमारे <a href="flight-baggage-rules.html">फ्लाइट बैगेज नियम</a> और <a href="../baggage/international.html" lang="en">international baggage</a> पेजों से। उड़ान से पहले अपना टिकट देखें।</p>') if air_rows else ""}
<h2>लीटर और kg में साइज चार्ट</h2>
<p>6 नवंबर 2026 को Amazon.in पर पढ़े गए 80 ट्रॉली मॉडल से। कपड़ों वाला कॉलम हमारा मोटा अंदाज़ा है, कोई टेस्ट नहीं। असली सीमा आमतौर पर आपका एयरलाइन टिकट होता है। देखें <a href="../guides/trolley-bag-capacity-kg-litres.html" lang="en">trolley bag capacity in kg and litres (English)</a>।</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>साइज</th><th>ऊँचाई</th><th>लिस्टेड लीटर (आम)</th><th>ख़ाली बैग (आम)</th><th>कितने कपड़े आ सकते हैं</th></tr></thead><tbody>{"".join(capacity_rows)}</tbody></table></div>
<h2>चेक-इन बैग का साइज</h2>
<p>{big}</p>
<h2>किलो से पाउंड</h2>
<p>भारतीय एयरलाइनें kg में बताती हैं। विदेशी एयरलाइनें, अमेरिकी वेबसाइटें और कुछ लगेज स्केल पाउंड (lb) दिखाते हैं।</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>kg</th><th>पाउंड (lb)</th></tr></thead><tbody>{kg_rows}</tbody></table></div>
{end_html}
{faq_block}
<p>और मदद (English में): <a href="../guides/20-inch-trolley-bag-size.html" lang="en">20 inch</a>, <a href="../guides/22-inch-trolley-bag-size.html" lang="en">22 inch</a>, <a href="../guides/24-inch-trolley-bag-size.html" lang="en">24 inch</a>, <a href="../guides/26-inch-trolley-bag-size.html" lang="en">26 inch</a>, <a href="../guides/28-inch-trolley-bag-size.html" lang="en">28 inch</a> और <a href="../guides/32-inch-trolley-bag-size.html" lang="en">32 inch</a> ट्रॉली की पूरी जानकारी, <a href="../guides/trolley-bag-size-for-international-travel.html" lang="en">विदेश यात्रा के लिए बैग</a> और <a href="../guides/cabin-luggage-guide.html" lang="en">केबिन ट्रॉली कैसे चुनें</a>।</p>
{tool_links(B, path, p)}
<p class="checked">{HI_DISCLOSURE}</p>
</article></div>
<script src="../assets/sizes.js" defer></script>
{B.telegram_band(cfg, p)}"""
    finish(B, cfg, pages, lastmod, path, seo, desc, body, 1,
           [("होम", ""), ("बैगेज नियम", "hi/flight-baggage-rules.html"), ("ट्रॉली बैग साइज चार्ट", path)],
           B.SIZE_CHART_UPDATED, B.SIZE_CHART_UPDATED, faq_schema)


# ---------- "can I carry it?" item pages ----------

def build_carry(B, cfg, deals_by_asin, pages, lastmod):
    items = carry_hi(B)
    if not items:
        return
    data = json.loads(B.FLIGHT_ITEMS_FILE.read_text(encoding="utf-8"))
    hi = load_hindi()
    L, names = hi["labels"], hi["flight_items"]["items"]
    count = sum(len(g["items"]) for g in data["groups"])
    p = "../../"
    for h, a, it in items:
        path = "hi/can-i-carry/%s.html" % h["slug"]
        checked = it.get("rechecked", data["checked"])
        text = names.get(it["item"])
        if not text:
            warn("no Hindi rule for %r in data/hindi.json" % it["item"])
            text = {"name": it["item"], "rule": it["rule"]}
        rows = ""
        for where, label in (("cabin", "केबिन बैग"), ("checked", "चेक-इन बैग")):
            state, word = ANSWER_HI[it[where]]
            rows += f'<tr><th scope="row">{label}</th><td><span class="fit fit-{state}">{e(L[word])}</span> {e(h[where + "_short"])}</td></tr>'
        sources = [s.split("=", 1) for s in a.get("sources", "").split(" | ") if "=" in s]
        related = [r.split("=", 1) for r in h.get("related", "").split(" | ") if "=" in r]
        others = "".join(f'<li><a href="{x["slug"]}.html">{e(names.get(y["item"], {}).get("name", y["item"]))}</a></li>'
                         for x, _, y in items if x["slug"] != h["slug"])
        content = B.render_markdown(h["body"], cfg, deals_by_asin, p, "carry-hi/%s.md" % h["slug"])
        crumb = text["name"]
        sub = "%s को %s से जाँचा गया" % (B.hi_date(checked), h["checked_against"])
        body = f"""{head(B, [("../flight-baggage-rules.html", "बैगेज नियम"), ("../can-i-carry.html", "फ्लाइट में क्या ले जाएँ"), (None, crumb)],
                h["title"], sub, "watches", B.icon("shield", "icon media-icon"), p, h.get("hinglish", ""))}
<div class="wrap"><article class="guide">
<div class="answer"><h2>सीधा जवाब</h2>
<div class="table-wrap"><table class="compare snug"><tbody>{rows}</tbody></table></div>
<p class="checked">एक से ज़्यादा चीज़ें देखनी हैं? हमारी <a href="../can-i-carry.html">फ्लाइट में क्या ले जा सकते हैं</a> लिस्ट में सभी {count} चीज़ें देखें।</p></div>
<h2>नियम</h2>
<p>{e(text["rule"])} <a class="src" href="{e(it["source"])}" target="_blank" rel="noopener">स्रोत</a></p>
<p class="checked">{B.hi_date(checked)} को जाँचा गया। सुरक्षा कर्मचारी फिर भी कोई भी चीज़ रोक सकते हैं, और एयरलाइनें ज़्यादा सख़्त हो सकती हैं या नियम बदल सकती हैं, इसलिए उड़ान से पहले अपनी एयरलाइन से पूछ लें।</p>
{content}
<h2>स्रोत</h2>
<p lang="en">{B.sources_html([{"label": label, "url": url} for label, url in sources])}</p>
<h2>लोग और क्या पूछते हैं</h2>
<ul class="airline-links">{others}<li><a href="../can-i-carry.html">सभी {count} चीज़ें</a></li></ul>
{('<h2>ये भी देखें</h2><ul class="airline-links">%s</ul>' % "".join(f'<li><a href="{p}{e(u)}">{e(label)}</a></li>' for u, label in related)) if related else ""}
{tool_links(B, path, p)}
<p class="checked">{HI_DISCLOSURE}</p>
</article></div>
{B.telegram_band(cfg, p)}"""
        seo = h.get("seo_title", h["title"])
        updated = max(h["updated"], checked)
        faq = B.md_faq(h["body"].replace("## सवाल-जवाब", "## Questions"))
        faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": nfc(q), "acceptedAnswer": {"@type": "Answer", "text": nfc(ans)}} for q, ans in faq]} if faq else None
        finish(B, cfg, pages, lastmod, path, seo, h["description"], body, 2,
               [("होम", ""), ("फ्लाइट में क्या ले जाएँ", "hi/can-i-carry.html"), (crumb, path)], h["date"], updated, faq_schema)


def carry_links(B):
    """English item name -> Hindi item page path, for the Hindi 'can I carry it?' table."""
    return {it["item"]: "can-i-carry/%s.html" % h["slug"] for h, a, it in carry_hi(B)}


def build_all(B, cfg, deals, deals_by_asin, airlines, intl, extra, pages, lastmod):
    if B.HINDI_PAGES.get("baggage/luggage-size-chart.html") == SIZE_PATH:
        build_size_chart(B, cfg, deals_by_asin, airlines, intl, pages, lastmod)
    build_carry(B, cfg, deals_by_asin, pages, lastmod)
    if B.HINDI_PAGES.get(B.EXTRA_PATH) == EXTRA_HUB:
        build_extra(B, cfg, deals_by_asin, extra, pages, lastmod)
    if B.HINDI_PAGES.get("baggage/checker.html") == CHECKER_PATH:
        build_checker(B, cfg, deals, airlines, intl, pages, lastmod)
    build_guides(B, cfg, deals_by_asin, pages, lastmod)
    import hindi_tools
    hindi_tools.build_all(B, cfg, deals, pages, lastmod)


def check_links(B, paths):
    """Hindi pages link to each other and to English pages by hand, so stop the build on a link to a page we don't have.
    build.py calls this after every page is written."""
    bad = []
    for path in paths:
        html = (B.DOCS / path).read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#?]+)', html):
            if href.startswith(("http:", "https:", "mailto:", "//")):
                continue
            target = (B.DOCS / path).parent.joinpath(href).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                bad.append("%s -> %s" % (path, href))
    if bad:
        B.sys.exit("Error: Hindi pages link to missing pages:\n  " + "\n  ".join(sorted(set(bad))))


# ---------- extra baggage charges ----------

EXTRA_FIELDS = ("free", "prepaid_note", "airport_text", "piece_short", "piece_text", "cabin_short", "cabin_text", "lite", "notes")


def extra_hindi(B, extra):
    """slug -> Hindi wording of that airline's entry in data/extra_baggage.json, warning when the English has changed."""
    t = load_hindi()["extra_baggage"]
    if t["checked"] != extra["checked"]:
        warn("data/hindi.json extra_baggage was checked %s, but data/extra_baggage.json %s. Update the Hindi text."
             % (t["checked"], extra["checked"]))
    out = {}
    for x in extra["airlines"]:
        h = t["by_airline"].get(x["slug"])
        if not h:
            continue
        en = hashlib.sha1(json.dumps({k: x.get(k) for k in EXTRA_FIELDS}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:10]
        if h.get("en") != en:
            warn("the English extra baggage text for %s changed (fingerprint %s, Hindi written from %s). Update data/hindi.json "
                 "extra_baggage and set its 'en' to the new fingerprint." % (x["slug"], en, h.get("en")))
        out[x["slug"]] = h
    return out


def hi_airport_cost(x, kg):
    """Like build.airport_cost, in Hindi: '₹4,250 तक', '₹4,000 + टैक्स'."""
    text = "₹{:,}".format(int(x["airport_per_kg"] * kg))
    if x.get("airport_upto"):
        text += " तक"
    if x.get("airport_tax"):
        text += " + टैक्स"
    return text


def hi_prepaid_summary(B, x):
    if not x["prepaid"]:
        return None
    first = [(kg, price) for kg, price in x["prepaid"] if kg in (3, 5, 10)] or x["prepaid"][:3]
    parts = ["%d kg %s" % (kg, B.rupees(price)) for kg, price in first]
    rates = sorted(price / kg for kg, price in x["prepaid"])
    lo, hi_ = B.rupees(round(rates[0])), B.rupees(round(rates[-1]))
    rate = lo if lo == hi_ else "%s से %s" % (lo, hi_)
    return "%s और %s (लगभग %s प्रति kg)" % (", ".join(parts[:-1]), parts[-1], rate)


def build_extra(B, cfg, deals_by_asin, extra, pages, lastmod):
    H = extra_hindi(B, extra)
    rows_all = [x for x in extra["airlines"] if x["slug"] in H]
    checked, year = extra["checked"], extra["checked"][:4]
    day = B.hi_date(checked)
    rupees = B.rupees
    scale = deals_by_asin.get("B07Q822CWX")
    disclaimer = ('<p class="checked">फ़ीस अक्सर बदलती है और आपके किराए और रूट पर निर्भर कर सकती है। पैसे देते समय जो क़ीमत दिखे, वही अंतिम है, '
                  "इसलिए उड़ान से पहले अपनी बुकिंग और एयरलाइन की आधिकारिक वेबसाइट ज़रूर देखें।</p>")

    # Hub
    p = "../"
    with_prepaid = [x for x in rows_all if x["prepaid"]]
    per_kg = sorted(price / kg for x in with_prepaid for kg, price in x["prepaid"])
    airport = sorted(x["airport_per_kg"] for x in rows_all)
    pre_lo, pre_hi = rupees(round(per_kg[0])), rupees(round(per_kg[-1]))
    air_lo, air_hi = rupees(airport[0]), rupees(airport[-1])
    scale_link = f'<a href="../picks/{scale["asin"]}.html">लगेज स्केल</a>' if scale else "लगेज स्केल"
    slabs = (3, 5, 10, 15)
    pre_rows = []
    for x in rows_all:
        if x["prepaid"]:
            cells = "".join("<td>%s</td>" % (rupees(x["prepaid_map"][kg]) if kg in x["prepaid_map"] else "–") for kg in slabs)
        else:
            cells = '<td colspan="%d">लिखा नहीं (Air India के मुताबिक़ एयरपोर्ट रेट से 20%% तक कम)</td>' % len(slabs)
        pre_rows.append(f'<tr><th scope="row"><a href="extra-baggage-charges/{x["slug"]}.html">{e(x["name"])}</a></th>{cells}</tr>')
    air_rows = "".join(f'<tr><th scope="row">{e(x["name"])}</th><td>{e(H[x["slug"]]["airport_text"])}</td><td>{e(H[x["slug"]].get("piece_short", "–"))}</td>'
                       f'<td>{e(H[x["slug"]].get("cabin_short", "–"))}</td></tr>' for x in rows_all)
    five_rows, five_parts = [], []
    for x in rows_all:
        online = x["prepaid_map"].get(5)
        at_airport = hi_airport_cost(x, 5)
        if online:
            save = rupees(x["airport_per_kg"] * 5 - online) + (" तक" if x.get("airport_upto") else "")
            five_rows.append(f'<tr><th scope="row">{e(x["name"])}</th><td>{rupees(online)}</td><td>{e(at_airport)}</td><td>{e(save)}</td></tr>')
            five_parts.append("%s पर ऑनलाइन %s, एयरपोर्ट पर %s" % (x["name"], rupees(online), at_airport))
        else:
            five_rows.append(f'<tr><th scope="row">{e(x["name"])}</th><td>लिखा नहीं</td><td>{e(at_airport)}</td><td>20% तक</td></tr>')
            five_parts.append("%s पर एयरपोर्ट पर %s (ऑनलाइन क़ीमत लिखी नहीं)" % (x["name"], at_airport))
    small = [x for x in with_prepaid if min(x["prepaid_map"]) == 3]
    indigo = next((x for x in rows_all if x["slug"] == "indigo"), None)
    two_kg_line = ""
    if indigo and small and all(x["airport_per_kg"] * 2 < x["prepaid_map"][3] for x in small):
        two_kg_line = (f'<li><strong>सिर्फ़ 1 या 2 kg ज़्यादा?</strong> ऑनलाइन सबसे छोटा स्लैब 3 kg का है। IndiGo पर एयरपोर्ट पर 2 kg '
                       f'{rupees(indigo["airport_per_kg"] * 2)} का पड़ता है, जो 3 kg स्लैब ({rupees(indigo["prepaid_map"][3])}) से कम है। '
                       '3 kg स्लैब वाली बाक़ी एयरलाइनों पर भी यही बात है।</li>')
    faq = [("घरेलू उड़ानों पर एक्स्ट्रा बैगेज चार्ज प्रति kg कितना है?",
            f"एयरपोर्ट काउंटर पर IndiGo, Air India, Air India Express, Akasa Air और SpiceJet फ्री चेक-इन बैगेज (आमतौर पर 15 kg) से ऊपर हर kg के "
            f"{air_lo} से {air_hi} लेती हैं। उड़ान से पहले ऑनलाइन ख़रीदें तो लगभग {pre_lo} से {pre_hi} प्रति kg पड़ता है, 3, 5 और 10 kg जैसे स्लैब में।")]
    if indigo:
        faq.append(("IndiGo में एक्स्ट्रा बैगेज चार्ज प्रति kg कितना है?",
                    "एयरपोर्ट पर %s। ऑनलाइन IndiGo 3 kg के %s, 5 kg के %s और 10 kg के %s लेता है, यानी %s प्रति kg।" % (
                        H["indigo"]["airport_text"], rupees(indigo["prepaid_map"][3]), rupees(indigo["prepaid_map"][5]),
                        rupees(indigo["prepaid_map"][10]), rupees(indigo["prepaid_map"][5] // 5))))
    faq += [("5 kg एक्स्ट्रा बैगेज कितने का पड़ता है?", "; ".join(five_parts) + "।"),
            ("Air India में घरेलू उड़ान पर एक्स्ट्रा बैगेज चार्ज कितना है?",
             "एयरपोर्ट पर ₹800 प्रति kg + टैक्स। Air India कहता है कि पहले से ऑनलाइन पैसे देने पर 20% तक बचत होती है, लेकिन प्रीपेड क़ीमतें नहीं बताता: वे Manage Booking में दिखती हैं।"),
            ("क्या एयरपोर्ट पर एक्स्ट्रा बैगेज ख़रीद सकते हैं?",
             "हाँ। चेक-इन काउंटर पर एयरपोर्ट रेट से पैसे देने होते हैं, जो उड़ान से पहले ऑनलाइन ख़रीदने से प्रति kg महँगा है। ऑनलाइन ख़रीदना आमतौर पर उड़ान से 2 या 3 घंटे पहले बंद हो जाता है।"),
            ("केबिन बैग 7 kg से ज़्यादा हो तो क्या होगा?",
             "यह एयरलाइन पर निर्भर है। Air India ₹3,000 में 12 kg तक ले जाने देता है। Air India Express 3 या 5 kg और बेचता है (Xtra Carry-On), और SpiceJet पहले से ₹700 प्रति kg या "
             "एयरपोर्ट पर ₹750 प्रति kg लेता है, 5 kg तक। IndiGo और Akasa Air भारी केबिन बैग की कोई फ़ीस नहीं बताते, इसलिए उसे चेक-इन करना पड़ सकता है।"),
            ("क्या एक्स्ट्रा बैग के साथ एक्स्ट्रा वज़न मिलता है?",
             "नहीं। IndiGo, Air India Express, Akasa Air और SpiceJet पर दूसरा बैग लगभग ₹950 से ₹1,000 का है, और इस फ़ीस में कोई वज़न नहीं मिलता। फ्री बैगेज से ऊपर हर kg का चार्ज फिर भी लगता है।"),
            ("क्या प्रीपेड एक्स्ट्रा बैगेज का पैसा वापस मिलता है?",
             "इस्तेमाल न हुए किलो का नहीं: 5 kg ख़रीदें और 3 kg ज़्यादा ले जाएँ, तो कोई रिफ़ंड नहीं। एयरलाइन फ्लाइट कैंसिल करे तो पैसा वापस मिलता है, और कुछ एयरलाइनें समय पर पूरी बुकिंग कैंसिल करने पर भी लौटाती हैं।")]
    faq_block, faq_schema = faq_html(B, faq)
    sources = "".join(f'<li><strong>{e(x["name"])}:</strong> {B.sources_html(x["sources"])}</li>' for x in rows_all)
    pick_box = B.inline_pick(cfg, scale, p) if scale else ""
    title = "घरेलू उड़ानों पर एक्स्ट्रा बैगेज चार्ज"
    seo = "फ्लाइट में एक्स्ट्रा बैगेज चार्ज %s: IndiGo, Air India, Akasa, SpiceJet प्रति kg" % year
    desc = (f"IndiGo, Air India, Air India Express, Akasa Air और SpiceJet की घरेलू उड़ानों पर एक्स्ट्रा बैगेज चार्ज: ऑनलाइन स्लैब, एयरपोर्ट पर प्रति kg रेट, "
            f"एक्स्ट्रा बैग और 7 kg से भारी केबिन बैग। {day} को जाँचा गया।")
    body = f"""{head(B, [("flight-baggage-rules.html", "बैगेज नियम"), (None, "एक्स्ट्रा बैगेज चार्ज")], title,
                "%s को हर एयरलाइन की आधिकारिक वेबसाइट से जाँचा गया · घरेलू उड़ानें" % day, "luggage", B.icon("suitcase", "icon media-icon"), p,
                "Flight me extra baggage ka charge kitna lagta hai? IndiGo, Air India, Akasa aur SpiceJet ke rate.")}
<div class="wrap"><article class="guide">
<p class="lead">आपका सामान फ्री बैगेज से ज़्यादा है? यहाँ भारत की बड़ी एयरलाइनों के घरेलू उड़ानों पर एक्स्ट्रा किलो, एक्स्ट्रा बैग और भारी केबिन बैग के चार्ज हैं, और कम पैसे देने के तरीक़े भी।</p>
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li><strong>एयरपोर्ट पर:</strong> फ्री चेक-इन बैगेज (आमतौर पर 15 kg) से ऊपर हर kg के {air_lo} से {air_hi}।</li>
<li><strong>उड़ान से पहले ऑनलाइन:</strong> लगभग {pre_lo} से {pre_hi} प्रति kg, 3, 5 और 10 kg जैसे स्लैब में।</li>
<li><strong>एक्स्ट्रा बैग:</strong> लगभग ₹950 से ₹1,000, और इसमें कोई एक्स्ट्रा वज़न नहीं मिलता।</li>
<li><strong>7 kg से भारी केबिन बैग:</strong> हर एयरलाइन का नियम बहुत अलग है। नीचे टेबल देखें।</li>
</ul></div>
<h2>एयरलाइन के हिसाब से एक्स्ट्रा बैगेज चार्ज</h2>
<p>हर एयरलाइन की पूरी जानकारी: हर ऑनलाइन स्लैब, एक्स्ट्रा बैग, भारी केबिन बैग और Lite किराए।</p>
<ul class="airline-links">{"".join(f'<li><a href="extra-baggage-charges/{x["slug"]}.html">{e(x["name"])}</a></li>' for x in rows_all)}</ul>
<h2>ऑनलाइन (प्रीपेड) एक्स्ट्रा बैगेज</h2>
<p>बुकिंग के बाद ऑनलाइन ख़रीदे गए एक्स्ट्रा चेक-इन वज़न के हर स्लैब की क़ीमत।</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>एयरलाइन</th>{"".join("<th>%d kg</th>" % kg for kg in slabs)}</tr></thead><tbody>{"".join(pre_rows)}</tbody></table></div>
<h2>एयरपोर्ट पर, एक्स्ट्रा बैग और भारी केबिन बैग</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>एयरलाइन</th><th>एयरपोर्ट पर</th><th>एक्स्ट्रा बैग</th><th>7 kg से भारी केबिन बैग</th></tr></thead><tbody>{air_rows}</tbody></table></div>
<p class="checked">{day} को जाँचा गया। फ़ीस अक्सर बदलती है और आपके किराए और रूट पर निर्भर कर सकती है। पैसे देते समय जो क़ीमत दिखे, वही अंतिम है, इसलिए उड़ान से पहले अपनी बुकिंग और एयरलाइन की वेबसाइट ज़रूर देखें।</p>
<h2>एयरपोर्ट या ऑनलाइन: 5 kg एक्स्ट्रा कितने का</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>एयरलाइन</th><th>ऑनलाइन</th><th>एयरपोर्ट पर</th><th>बचत</th></tr></thead><tbody>{"".join(five_rows)}</tbody></table></div>
<p>यहाँ हर एयरलाइन पर ऑनलाइन ख़रीदना सस्ता है, लेकिन सिर्फ़ ₹50 से ₹100 प्रति kg। असली बचत उन किलो के पैसे न देने में है जिनकी ज़रूरत नहीं:</p>
<ul>
<li><strong>प्रीपेड किलो का पैसा वापस नहीं मिलता।</strong> 5 kg ख़रीदें और 3 kg ज़्यादा ले जाएँ, तो बाक़ी 2 kg बेकार जाते हैं।</li>
{two_kg_line}
<li><strong>पहले तौलें, फिर स्लैब ख़रीदें।</strong> पैक करके घर पर बैग तौलें, फिर सबसे छोटा स्लैब लें जो काफ़ी हो।</li>
<li><strong>ऑनलाइन ख़रीदने का समय जल्दी ख़त्म होता है:</strong> IndiGo, Air India, Air India Express और Akasa Air पर उड़ान से 2 घंटे पहले, SpiceJet पर 3 घंटे पहले।</li>
</ul>
<h2>एक्स्ट्रा बैगेज चार्ज से कैसे बचें</h2>
<ul>
<li><strong>घर पर बैग तौलें।</strong> एक {scale_link} एयरपोर्ट पर कुछ किलो के चार्ज से सस्ता पड़ता है। ज़्यादातर चेक-इन बैग 15 kg और केबिन बैग 7 kg तक जाते हैं।</li>
<li><strong>हल्का बैग चुनें।</strong> ख़ाली ट्रॉली का वज़न आमतौर पर केबिन साइज में लगभग 2.5 kg और मीडियम और लार्ज साइज में 3.4 से 4.3 kg होता है, और यह सब आपके फ्री वज़न में से जाता है। हमारे <a href="trolley-bag-size-chart.html">ट्रॉली बैग साइज चार्ट</a> में आम वज़न देखें।</li>
<li><strong>पैक करने से पहले जोड़ लें।</strong> हमारा <a href="../tools/bag-weight.html" lang="en">bag weight calculator (English)</a> बताता है कि बैग 7 kg और 15 kg से कम रहेगा या नहीं।</li>
<li><strong>केबिन बैग का साइज सही रखें।</strong> बहुत बड़ा केबिन बैग चेक-इन हो जाता है और आपके चेक-इन वज़न में गिना जाता है। <a href="cabin-bag-checker.html">केबिन बैग चेकर</a> आज़माएँ।</li>
<li><strong>भारी चीज़ें पहन लें।</strong> उड़ान के लिए जैकेट और सबसे भारी जूते पहनें।</li>
<li><strong>अपना किराया देखें।</strong> IndiGo Lite और Air India Express Xpress Lite किराए में चेक-इन बैग बिल्कुल नहीं मिलता।</li>
<li><strong>साथ में जा रहे हैं?</strong> SpiceJet एक बुकिंग के यात्रियों को चेक-इन बैगेज मिलाने देता है। बाक़ी एयरलाइनें हर यात्री का वज़न अलग गिनती हैं, इसलिए अपना टिकट देखें।</li>
<li><strong>हर बैग 32 kg से कम रखें।</strong> यहाँ कोई भी एयरलाइन इससे भारी एक बैग नहीं लेती, पैसे देने पर भी।</li>
</ul>
{pick_box}
{faq_block}
<h2>स्रोत</h2>
<p>एयरलाइनों के आधिकारिक पेज, {day} को पढ़े गए:</p>
<ul lang="en">{sources}</ul>
<p>हर एयरलाइन का फ्री बैगेज हमारे <a href="flight-baggage-rules.html">फ्लाइट बैगेज नियम</a> पेज पर देखें।</p>
{tool_links(B, EXTRA_HUB, p)}
<p class="checked">{HI_DISCLOSURE}</p>
</article></div>
{B.telegram_band(cfg, p)}"""
    finish(B, cfg, pages, lastmod, EXTRA_HUB, seo, desc, body, 1,
           [("होम", ""), ("बैगेज नियम", "hi/flight-baggage-rules.html"), ("एक्स्ट्रा बैगेज चार्ज", EXTRA_HUB)],
           extra.get("published", checked), checked, faq_schema)

    # One page per airline
    p = "../../"
    scale_link = f'<a href="{p}picks/{scale["asin"]}.html">लगेज स्केल</a>' if scale else "लगेज स्केल"
    for x in rows_all:
        h, name = H[x["slug"]], x["name"]
        path = "hi/extra-baggage-charges/%s.html" % x["slug"]
        summary = hi_prepaid_summary(B, x)
        if x["prepaid"]:
            rows = []
            for kg, price in x["prepaid"]:
                saving = x["airport_per_kg"] * kg - price
                save = (rupees(saving) + (" तक" if x.get("airport_upto") else "")) if saving > 0 else "–"
                rows.append(f'<tr><th scope="row">{kg} kg</th><td>{rupees(price)}</td><td>{e(hi_airport_cost(x, kg))}</td><td>{e(save)}</td></tr>')
            table = ('<div class="table-wrap"><table class="compare snug"><thead><tr><th>एक्स्ट्रा वज़न</th><th>ऑनलाइन</th><th>एयरपोर्ट पर</th>'
                     f'<th>बचत</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
            table_head = "%s ऑनलाइन एक्स्ट्रा बैगेज (घरेलू)" % name
        else:
            rows = "".join(f'<tr><th scope="row">{kg} kg</th><td>{e(hi_airport_cost(x, kg))}</td></tr>' for kg in (3, 5, 10, 15))
            table = ('<div class="table-wrap"><table class="compare snug"><thead><tr><th>एक्स्ट्रा वज़न</th><th>एयरपोर्ट पर</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table></div>')
            table_head = "%s एयरपोर्ट पर एक्स्ट्रा बैगेज (घरेलू)" % name
        notes = "".join("<li>%s</li>" % e(n) for n in h.get("notes", []))
        five = x["prepaid_map"].get(5)
        faq = [("%s में एक्स्ट्रा बैगेज चार्ज प्रति kg कितना है?" % name,
                "एयरपोर्ट पर %s की घरेलू उड़ानों में %s लगता है। " % (name, h["airport_text"])
                + ("उड़ान से पहले ऑनलाइन: %s।" % summary if summary else h["prepaid_note"])),
               ("%s में 5 kg एक्स्ट्रा बैगेज कितने का है?" % name,
                ("ऑनलाइन %s, या एयरपोर्ट पर %s।" % (rupees(five), hi_airport_cost(x, 5))) if five else
                ("एयरपोर्ट पर %s। %s प्रीपेड क़ीमत नहीं बताता; यह बुकिंग के बाद Manage Booking में दिखती है।" % (hi_airport_cost(x, 5), name))),
               ("%s में एयरपोर्ट पर एक्स्ट्रा बैगेज चार्ज कितना है?" % name,
                "फ्री चेक-इन बैगेज (%s) से ऊपर %s।" % (h.get("free", "अपना टिकट देखें"), h["airport_text"])),
               ("%s में एक्स्ट्रा बैगेज कैसे जोड़ें?" % name, h["prepaid_note"]),
               ("%s में केबिन बैग 7 kg से ज़्यादा हो तो क्या होगा?" % name, h["cabin_text"]),
               ("क्या %s एक्स्ट्रा बैग का अलग चार्ज लेता है?" % name, h["piece_text"])]
        faq_block, faq_schema = faq_html(B, faq)
        others = '<ul class="airline-links">' + "".join(
            f'<li><a href="{o["slug"]}.html">{e(o["name"])}</a></li>' for o in rows_all if o["slug"] != x["slug"]) + "</ul>"
        title = "%s एक्स्ट्रा बैगेज चार्ज: प्रति kg, ऑनलाइन और एयरपोर्ट पर" % name
        seo = "%s एक्स्ट्रा बैगेज चार्ज %s: प्रति kg रेट, ऑनलाइन और एयरपोर्ट" % (name, year)
        desc = ("%s की घरेलू उड़ानों पर एक्स्ट्रा बैगेज चार्ज: एयरपोर्ट पर %s%s। एक्स्ट्रा बैग: %s। 7 kg से भारी केबिन बैग: %s। %s को जाँचा गया।" % (
            name, h["airport_text"], ("; ऑनलाइन " + summary) if summary else "", h.get("piece_short", "नीचे देखें"),
            h.get("cabin_short", "नीचे देखें"), day))
        hinglish = "%s flight me extra baggage charges kitne hain? Per kg rate, 5 kg ka charge aur airport ka rate." % name
        prepaid_li = e(summary) if summary else "%s ने नहीं बताया (उसके मुताबिक़ एयरपोर्ट रेट से 20%% तक कम)" % e(name)
        body = f"""{head(B, [("../flight-baggage-rules.html", "बैगेज नियम"), ("../extra-baggage-charges.html", "एक्स्ट्रा बैगेज चार्ज"), (None, name)], title,
                    "%s को %s की आधिकारिक वेबसाइट से जाँचा गया · घरेलू उड़ानें" % (day, name), "luggage", B.icon("suitcase", "icon media-icon"), p, hinglish)}
<div class="wrap"><article class="guide">
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li><strong>फ्री चेक-इन बैगेज:</strong> {e(h.get("free", "अपना टिकट देखें"))}।</li>
<li><strong>ऑनलाइन (प्रीपेड):</strong> {prepaid_li}।</li>
<li><strong>एयरपोर्ट पर:</strong> {e(h["airport_text"])}।</li>
<li><strong>एक्स्ट्रा बैग:</strong> {e(h.get("piece_short", "नीचे देखें"))}।</li>
<li><strong>7 kg से भारी केबिन बैग:</strong> {e(h.get("cabin_short", "नीचे देखें"))}।</li>
</ul></div>
<h2>{e(table_head)}</h2>
{table}
<p>{e(h["prepaid_note"])}</p>
<h2>एक्स्ट्रा बैग</h2>
<p>{e(h["piece_text"])}</p>
<h2>7 kg से भारी केबिन बैग</h2>
<p>{e(h["cabin_text"])}</p>
{('<h2>Lite किराए</h2><p>' + e(h["lite"]) + '</p>') if h.get("lite") else ''}
{('<h2>ध्यान रखें</h2><ul>' + notes + '</ul>') if notes else ''}
<h2>कम पैसे कैसे दें</h2>
<ul>
<li><strong>घर पर बैग तौलें</strong>, {scale_link} से, फिर सबसे छोटा स्लैब ख़रीदें जो एक्स्ट्रा वज़न के लिए काफ़ी हो। इस्तेमाल न हुए प्रीपेड किलो का पैसा वापस नहीं मिलता।</li>
<li><strong>केबिन बैग का साइज देखें</strong>, हमारे <a href="../cabin-bag-checker.html">केबिन बैग चेकर</a> में: बहुत बड़ा बैग चेक-इन हो जाता है।</li>
<li><strong>पैकिंग लिस्ट जोड़ें</strong>, <a href="{p}tools/bag-weight.html" lang="en">bag weight calculator (English)</a> से।</li>
</ul>
<p>{e(name)} की बाक़ी एयरलाइनों से तुलना हमारे <a href="../extra-baggage-charges.html">एक्स्ट्रा बैगेज चार्ज</a> पेज पर देखें, और फ्री बैगेज <a href="../flight-baggage-rules.html">फ्लाइट बैगेज नियम</a> पेज पर।</p>
{faq_block}
<h2>स्रोत</h2>
<p>{e(name)} के आधिकारिक पेज, {day} को पढ़े गए: <span lang="en">{B.sources_html(x["sources"])}</span></p>
{disclaimer}
<h2>बाक़ी एयरलाइनों के एक्स्ट्रा बैगेज चार्ज</h2>
{others}
{tool_links(B, path, p)}
<p class="checked">{HI_DISCLOSURE}</p>
</article></div>
{B.telegram_band(cfg, p)}"""
        finish(B, cfg, pages, lastmod, path, seo, desc, body, 2,
               [("होम", ""), ("एक्स्ट्रा बैगेज चार्ज", EXTRA_HUB), (name, path)], extra.get("published", checked), checked, faq_schema)


# ---------- Hindi vs English drift check (trip guides and guides) ----------

NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def numbers(text):
    """Every number in a page's markdown, without link targets, URLs and [[...]] tokens (those are the same in both)."""
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", " ", text)
    return {n.replace(",", "") for n in NUMBER.findall(text)}


def check_twin(B, h, directory, source):
    """A Hindi page with `matches: <English updated date>` is checked against its English page: the date must match,
    and the body and glance must use the same numbers. Anything else prints a warning so the Hindi is updated too."""
    if not h.get("matches"):
        return
    a = next((x for x in B.load_articles(directory) if x["slug"] == h["slug"]), None)
    if a is None:
        B.sys.exit("Error: %s has no English page" % source)
    if h["matches"] != a["updated"]:
        warn("%s was matched to the English page of %s, but the English page was updated %s. Update the Hindi page and its matches."
             % (source, h["matches"], a["updated"]))
    en = numbers(a["body"] + "\n" + a.get("glance", ""))
    hi = numbers(h["body"] + "\n" + h.get("glance", ""))
    if hi - en:
        warn("%s has numbers the English page doesn't: %s" % (source, ", ".join(sorted(hi - en))))
    if en - hi:
        warn("%s is missing numbers from the English page: %s" % (source, ", ".join(sorted(en - hi))))


def hinglish_line(h):
    return f'\n      <p class="muted small" lang="hi-Latn">{e(h["hinglish"])}</p>' if h.get("hinglish") else ""


# ---------- guides (content/articles-hi/<slug>.md -> hi/guides/<slug>.html) ----------

GUIDES_HI_DIR = ROOT / "content" / "articles-hi"  # same file names as content/articles


_GUIDES_HI = None


def guides_hi(B):
    """content/articles-hi pages, each checked to have an English twin. Loaded once per build."""
    global _GUIDES_HI
    if _GUIDES_HI is not None:
        return _GUIDES_HI
    if not GUIDES_HI_DIR.exists():
        _GUIDES_HI = []
        return _GUIDES_HI
    english = {a["slug"] for a in B.load_articles()}
    out = []
    for h in B.load_articles(GUIDES_HI_DIR):
        if h["slug"] not in english:
            B.sys.exit("Error: content/articles-hi/%s.md has no English page in content/articles" % h["slug"])
        missing = [k for k in ("title", "description", "hinglish") if not h.get(k)]
        if missing:
            B.sys.exit("Error: content/articles-hi/%s.md is missing %s in its front matter" % (h["slug"], ", ".join(missing)))
        out.append(h)
    _GUIDES_HI = out
    return out


def guide_short(h):
    return h.get("short") or h["title"].split(":")[0]


def build_guides(B, cfg, deals_by_asin, pages, lastmod):
    for h in guides_hi(B):
        slug, p = h["slug"], "../../"
        path = "hi/guides/%s.html" % slug
        source = "content/articles-hi/%s.md" % slug
        check_twin(B, h, B.ARTICLES_DIR, source)
        content = B.render_markdown(h["body"], cfg, deals_by_asin, p, "articles-hi/%s.md" % slug)
        cat = h.get("category")
        art = B.media(cfg, cat, "media media-tile") if cat in cfg["categories"] else ""
        inner = f"""<nav class="crumbs"><a href="{p}index.html">होम</a><span>/</span><a href="{p}guides/index.html" lang="en">Guides</a></nav>
      <h1>{e(h['title'])}</h1>
      <p class="muted small">{B.hi_date(h['updated'])} को अपडेट किया गया &middot; {h['minutes']} मिनट में पढ़ें</p>{hinglish_line(h)}"""
        body = f"""{B.page_head(e(cat or 'none'), art, inner, p, h.get("photo"))}
<div class="wrap"><article class="guide">
{content}
{tool_links(B, path, p)}
<p class="checked">{HI_DISCLOSURE}</p>
</article></div>
{B.telegram_band(cfg, p)}"""
        image = B.photo_og(cfg, h["photo"]) if h.get("photo") in B.PHOTOS else B.abs_url(cfg, "assets/logo.png")
        seo = h.get("seo_title", h["title"])
        article = {"@context": "https://schema.org", "@type": "Article", "headline": nfc(seo), "description": nfc(h["description"]),
                   "datePublished": h["date"], "dateModified": h["updated"], "inLanguage": "hi-IN", "image": image,
                   "mainEntityOfPage": B.abs_url(cfg, path), "author": B.org_schema(cfg), "publisher": B.org_schema(cfg)}
        schema = [article, B.crumbs_schema(cfg, [("होम", ""), ("Guides", "guides/index.html"), (guide_short(h), path)])]
        faq = B.md_faq(h["body"].replace("## सवाल-जवाब", "## Questions"))
        if faq:
            schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": nfc(q), "acceptedAnswer": {"@type": "Answer", "text": nfc(ans)}} for q, ans in faq]})
        pages.append(B.write(path, B.page(cfg, nfc(seo), nfc(h["description"]), nfc(body), 2, path, schema,
                                          og_type="article", photo=h.get("photo"), lang="hi")))
        lastmod[path] = h["updated"]


# ---------- cabin bag checker (twin of baggage/checker.html, same airline data) ----------

CHECKER_PATH = "hi/cabin-bag-checker.html"
CHECKER_DATE = "2026-11-16"  # when the Hindi checker was first published
CHECKER_WORDS = {"total": "आपका बैग: कुल {total} cm (लंबाई + चौड़ाई + ऊँचाई)", "size": "साइज लिखें", "weight": "वज़न लिखें",
                 "none": "सीमा नहीं बताई", "fits": "फिट", "over": "{n} cm ज़्यादा", "big": "बहुत बड़ा",
                 "side": "एक साइड {n} cm ज़्यादा", "sum": "कुल {total} cm, यानी {over} cm ज़्यादा", "ok": "ठीक",
                 "spare": "{n} kg बाक़ी", "heavy": "बहुत भारी", "kgOver": "{n} kg ज़्यादा"}
VARIANTS_HI = {"Q400 planes": "Q400 विमान"}


def hi_join(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " और " + names[-1]


def hi_limit(B, c):
    parts = []
    if c.get("dims_cm"):
        parts.append(" x ".join(B.num(x) for x in c["dims_cm"]) + " cm")
    if c.get("total_cm"):
        parts.append("कुल %s cm" % B.num(c["total_cm"]))
    if c.get("kg"):
        parts.append("%s kg" % B.num(c["kg"]))
    return " · ".join(parts)


def build_checker(B, cfg, deals, airlines, intl, pages, lastmod):
    path, p = CHECKER_PATH, "../"
    num = B.num
    indian = airlines["airlines"]
    checked = airlines["checked"]
    rows_for_checker = []  # the same rows as the English checker (build.build_baggage)
    for a in indian + [x for x in (intl or {}).get("airlines", []) if x.get("checker", True)]:
        rows_for_checker.append((a["slug"], a["name"], a["slug"], a["cabin"]))
        for i, v in enumerate(a["cabin"].get("variants", []), 1):
            if v["label"] not in VARIANTS_HI:
                warn("checker variant %r has no Hindi name in VARIANTS_HI" % v["label"])
            rows_for_checker.append(("%s-%d" % (a["slug"], i), "%s (%s)" % (a["name"], VARIANTS_HI.get(v["label"], v["label"])), a["slug"],
                                     dict(a["cabin"], dims_cm=v.get("dims_cm"), total_cm=v.get("total_cm"))))
    picks = B.cabin_picks(deals)
    js = {"airlines": [{"slug": key, "name": name, "kg": c.get("kg"), "dims": c.get("dims_cm"), "total": c.get("total_cm"),
                        "either": bool(c.get("either"))} for key, name, page_slug, c in rows_for_checker],
          "picks": [{"asin": d["asin"], "title": d["title"], "dims": dims, "kg": kg} for d, dims, kg in picks], "t": CHECKER_WORDS}
    js_json = json.dumps(js, ensure_ascii=False).replace("</", "<\\/")
    options = "".join('<option value="%d">%s</option>' % (i, e(d["title"])) for i, (d, dims, kg) in enumerate(picks))
    result_rows = "".join(f'<tr data-slug="{key}"><th scope="row"><a href="../baggage/{page_slug}.html" lang="en">{e(name)}</a>'
                          f'<span class="why">{e(hi_limit(B, c))}</span></th>'
                          f'<td class="r-size"><span class="fit fit-na">{CHECKER_WORDS["size"]}</span></td>'
                          f'<td class="r-kg"><span class="fit fit-na">{CHECKER_WORDS["weight"]}</span></td></tr>'
                          for key, name, page_slug, c in rows_for_checker)

    # Picks: the same rows as the English checker, in Hindi
    size = lambda dims: " x ".join(num(x) for x in sorted(dims, reverse=True))
    trolleys = []
    for d, dims, kg in picks:
        names = [a["name"] for a in indian if B.size_fit(dims, a["cabin"])[0]]
        if d["category"] == "luggage" and names:
            trolleys.append((len(names), d, "%s के लिए केबिन ट्रॉली" % hi_join(names),
                             "लिस्टिंग में साइज %s cm%s।" % (size(dims), (", ख़ाली बैग %g kg का" % kg) if kg is not None else "")))
    pick_rows = [r[1:] for r in sorted(trolleys, key=lambda r: -r[0])]
    n = len(indian)
    for d, label, why in B.airline_top_rows("all %d airlines" % n, [a["cabin"] for a in indian], picks):
        if label == "Most room in a backpack":
            dims = next(x[1] for x in picks if x[0]["asin"] == d["asin"])
            pick_rows.append((d, "सभी %d एयरलाइनों में फिट बैकपैक" % n,
                              "%s लीटर। लिस्टिंग के साइज (%s cm) के हिसाब से सभी %d एयरलाइनों में फिट होने वाले हमारे बैकपैक में सबसे बड़ा।"
                              % (num(B.litres(d)), size(dims), n)))
    picks_html = B.top_picks(cfg, pick_rows, p, "बैग बड़ा है? ये अपने लिस्टेड साइज से फिट हैं",
                             '<a href="../baggage/index.html#our-picks-fit" lang="en">हमारी सभी पिक्स हर एयरलाइन से मिलाकर देखें (English)</a>')

    # Quick answer and questions, from the same airline data
    groups = {}
    for a in indian:
        if a["cabin"].get("dims_cm"):
            groups.setdefault(" x ".join(num(x) for x in a["cabin"]["dims_cm"]), []).append(a["name"])
    sizes_text = "; ".join("%s: %s cm" % (hi_join(names), dims) for dims, names in groups.items())
    totals = {a["cabin"].get("total_cm") for a in indian}
    kgs = {a["cabin"].get("kg") for a in indian}
    same = []
    if len(totals) == 1 and None not in totals:
        same.append("कुल साइज (लंबाई + चौड़ाई + ऊँचाई) %s cm तक" % num(totals.pop()))
    if len(kgs) == 1 and None not in kgs:
        same.append("वज़न %s kg तक" % num(kgs.pop()))
    same_text = (" सभी %d एयरलाइनों में %s।" % (n, " और ".join(same))) if same else ""
    answer = ('<div class="answer"><h2>केबिन बैग का साइज कितना होता है?</h2>'
              f'<p>भारत की {n} बड़ी एयरलाइनों में घरेलू इकॉनमी की केबिन बैग सीमा: {e(sizes_text)}।{e(same_text)}</p>'
              '<p class="checked">यह सबसे बड़ी साइड से सबसे छोटी तक है, पहियों और हैंडल समेत। हर एयरलाइन के पूरे नियम हमारे '
              '<a href="flight-baggage-rules.html">फ्लाइट बैगेज नियम</a> पेज पर हैं।</p></div>')
    by_slug = {a["slug"]: a for a in indian}
    faq = [("केबिन बैग का साइज कितना होता है?",
            "भारत की बड़ी एयरलाइनों में घरेलू इकॉनमी के लिए: %s।%s" % (sizes_text, same_text))]
    ind, ai = by_slug.get("indigo"), by_slug.get("air-india")
    if ind and ai and ind["cabin"].get("dims_cm") and ai["cabin"].get("dims_cm"):
        di, da = ind["cabin"]["dims_cm"], ai["cabin"]["dims_cm"]
        faq.append(("क्या 55 cm का ट्रॉली बैग केबिन में चलेगा?",
                    f"55 cm आमतौर पर बैग की सिर्फ़ ऊँचाई होती है। चौड़ाई और गहराई भी सीमा में होनी चाहिए: IndiGo में {num(di[1])} और "
                    f"{num(di[2])} cm तक, Air India में {num(da[1])} और {num(da[2])} cm तक। अपने बैग की तीनों साइड ऊपर चेकर में लिखें।"))
    faq.append(("केबिन बैग का साइज कैसे नापें?",
                "बैग सीधा खड़ा करें और खींचने वाला हैंडल अंदर कर दें। पहियों के नीचे से सबसे ऊपर तक ऊँचाई नापें, फिर चौड़ाई और गहराई, "
                "जेबों और हैंडल समेत। एयरलाइन पूरा बैग नापती है, सिर्फ़ उसका खोल नहीं।"))
    faq_block, faq_schema = faq_html(B, faq)

    title = "केबिन बैग साइज चेकर: मेरा बैग फ्लाइट में फिट होगा?"
    seo = "केबिन बैग साइज चेकर: IndiGo, Air India, Akasa, SpiceJet में बैग फिट होगा?"
    desc = ("अपने बैग की लंबाई, चौड़ाई, ऊँचाई और वज़न लिखें और देखें कि वह भारत की बड़ी एयरलाइनों की केबिन बैगेज सीमा में आता है या नहीं"
            + (", साथ में Emirates, Qatar Airways, Saudia, Singapore Airlines और दूसरी विदेशी एयरलाइनें।" if (intl or {}).get("airlines") else "।"))
    measure = B.diagram_figure("measure-bag", p) if "measure-bag" in B.DIAGRAMS else ""
    body = f"""{head(B, [("flight-baggage-rules.html", "बैगेज नियम"), (None, "केबिन बैग चेकर")], title,
                "एयरलाइन की सीमा %s को जाँची गई · इकॉनमी" % B.hi_date(checked), "luggage", B.icon("ruler", "icon media-icon"), p,
                "Cabin bag ka size kitna hota hai? Apne bag ka size likhiye aur har airline ki limit se milaiye.")}
<div class="wrap"><article class="guide">
<p class="lead">अपने बैग की लंबाई, चौड़ाई, ऊँचाई और पैक करने के बाद का वज़न लिखें। हर एयरलाइन के सामने दिखेगा कि बैग उसकी केबिन सीमा में आता है या नहीं।</p>
<form class="checker" id="bag-checker" onsubmit="return false">
  <label>हमारी किसी पिक से भरें (ज़रूरी नहीं)
    <select id="bc-pick"><option value="">बैग चुनें…</option>{options}</select>
  </label>
  <div class="checker-fields">
    <label>लंबाई (cm)<input id="bc-l" type="number" inputmode="decimal" min="0" step="0.5" placeholder="55"></label>
    <label>चौड़ाई (cm)<input id="bc-w" type="number" inputmode="decimal" min="0" step="0.5" placeholder="35"></label>
    <label>ऊँचाई (cm)<input id="bc-h" type="number" inputmode="decimal" min="0" step="0.5" placeholder="25"></label>
    <label>पैक बैग का वज़न (kg)<input id="bc-kg" type="number" inputmode="decimal" min="0" step="0.1" placeholder="7"></label>
  </div>
  <p class="checker-total" id="bc-total" aria-live="polite"></p>
  <p class="hint">पूरा बैग नापें, पहियों और हैंडल समेत। लिखते ही नतीजे बदलते हैं।</p>
</form>
<noscript><p>यह चेकर JavaScript से चलता है। आप हमारे <a href="flight-baggage-rules.html">फ्लाइट बैगेज नियम</a> पेज पर भी सीमाएँ मिला सकते हैं।</p></noscript>
<div class="table-wrap"><table class="result-table" id="bc-results"><thead><tr><th>एयरलाइन</th><th>साइज</th><th>वज़न</th></tr></thead><tbody>{result_rows}</tbody></table></div>
<p class="checked">नियम अक्सर बदलते हैं और आपके किराए, रूट और विमान पर निर्भर कर सकते हैं। उड़ान से पहले अपना टिकट और एयरलाइन की आधिकारिक वेबसाइट ज़रूर देखें।</p>
{answer}
{picks_html}
<h2>बैग का साइज कैसे नापें</h2>
{measure}
<ul>
<li><strong>ऊँचाई:</strong> ज़मीन से, यानी पहियों के नीचे से, बैग के सबसे ऊपर तक। ऊपर वाला हैंडल भी गिनें।</li>
<li><strong>चौड़ाई:</strong> एक तरफ़ से दूसरी तरफ़ तक, साइड वाले हैंडल समेत।</li>
<li><strong>गहराई:</strong> आगे से पीछे तक, आगे की जेब और पीछे के पहियों समेत।</li>
</ul>
<h2>यह चेकर कैसे काम करता है</h2>
<ul>
<li>हम आपके बैग की सबसे लंबी साइड को एयरलाइन की सबसे लंबी अनुमत साइड से मिलाते हैं, फिर बाक़ी दोनों को, क्योंकि बैग को घुमाकर भी रखा जा सकता है।</li>
<li>जब एयरलाइन कुल साइज (लंबाई + चौड़ाई + ऊँचाई) बताती है, तो हम आपकी तीनों साइड जोड़ते हैं।</li>
<li>ये इकॉनमी की आम सीमाएँ हैं: भारतीय एयरलाइनों के लिए घरेलू उड़ानें, और विदेशी एयरलाइनों के लिए भारत के रूट। आपका किराया, रूट या विमान इन्हें बदल सकता है।</li>
</ul>
<p>हर एयरलाइन के पूरे नियम हमारे <a href="flight-baggage-rules.html">फ्लाइट बैगेज नियम</a> पेज पर देखें, ट्रॉली का साइज इंच और cm में <a href="trolley-bag-size-chart.html">ट्रॉली बैग साइज चार्ट</a> में, और 7 kg से भारी बैग का चार्ज <a href="extra-baggage-charges.html">एक्स्ट्रा बैगेज चार्ज</a> पेज पर। ट्रॉली चुननी है? पढ़ें <a href="../guides/cabin-luggage-guide.html" lang="en">how to pick a cabin trolley (English)</a>।</p>
{faq_block}
{tool_links(B, path, p)}
<p class="checked">{HI_DISCLOSURE}</p>
</article></div>
<script type="application/json" id="bc-data">{js_json}</script>
<script src="../assets/checker.js" defer></script>
{B.telegram_band(cfg, p)}"""
    finish(B, cfg, pages, lastmod, path, seo, desc, body, 1,
           [("होम", ""), ("बैगेज नियम", "hi/flight-baggage-rules.html"), ("केबिन बैग चेकर", path)],
           CHECKER_DATE, max(CHECKER_DATE, checked), faq_schema)
