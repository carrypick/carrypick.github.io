"""Hindi twins of our newest tools, built from the same data files and the same JS as the English pages:

- hi/shoe-size.html               <- tools/shoe-size.html (data/shoe_sizes.json, static/shoe-size.js)
- hi/power-bank-flight-check.html <- tools/power-bank-flight-check.html (data/power_banks.json, static/power-bank.js)
(more are added below as they are finished)

The JS files read their words from a <script type="application/json" id="xx-t"> block on the page, so the Hindi page
only has to carry its own words. Every page works without JS: the charts are plain tables.
hindi_pages.register() calls register() here (language menu + hreflang), hindi_pages.build_all() calls build_all().
Each *_MATCHED date is the date of the English data these Hindi words were written from: when the data is checked again,
the build prints a warning, so update the Hindi at the same time.
"""

import json
from html import escape as e

import hindi_pages as H
from common import ROOT

SHOE_FILE = ROOT / "data" / "shoe_sizes.json"
SHOE_EN, SHOE_PATH = "tools/shoe-size.html", "hi/shoe-size.html"
SHOE_MATCHED = "2026-11-20"
POWER_FILE = ROOT / "data" / "power_banks.json"
POWER_EN, POWER_PATH = "tools/power-bank-flight-check.html", "hi/power-bank-flight-check.html"
POWER_MATCHED = "2026-11-20"
PUBLISHED = "2026-11-21"

HI_GROUP = {"men": "पुरुषों", "women": "महिलाओं", "kids": "बच्चों"}
HI_AIRLINE_RULE = {
    "IndiGo": "सिर्फ़ केबिन बैग में। पावर रेटिंग पावर बैंक पर छपी होनी चाहिए। 160 Wh से ऊपर की इजाज़त नहीं।",
    "Air India": "सिर्फ़ केबिन बैग में, 100 Wh तक, एक यात्री के पास 2 से ज़्यादा स्पेयर बैटरी नहीं। ऊपर के बिन में नहीं।",
    "Akasa Air": "सिर्फ़ केबिन बैग में, 2 तक, हर एक 100 Wh तक, डिब्बे या प्लास्टिक बैग में। उड़ान के दौरान इस्तेमाल या चार्ज नहीं कर सकते, और ऊपर के बिन में नहीं रख सकते।",
}
HI_ON_BOARD = [
    ("उड़ान के दौरान पावर बैंक से फ़ोन चार्ज न करें, और पावर बैंक को भी चार्ज न करें।",
     "Akasa Air की कंडीशंस ऑफ़ कैरिज़ में यह लिखा है। जनवरी 2026 की ख़बरों के मुताबिक़ DGCA की डेंजरस गुड्स एडवाइज़री सर्कुलर ने इसे सभी भारतीय उड़ानों में बंद किया है, पर हमें DGCA की वेबसाइट पर वह सर्कुलर नहीं मिला। इसलिए इसे हर एयरलाइन का नियम मानें।"),
    ("इसे सीट की जेब में, आगे वाली सीट के नीचे या अपने पास रखें, ऊपर के बिन में नहीं।", "Air India और Akasa Air, दोनों यही कहती हैं।"),
    ("MOBIKINS MK-PB-04 पावर बैंक भारत आने, जाने और भारत के अंदर हर उड़ान में, किसी भी बैग में, बैन है।",
     "Air India और Akasa Air के पेज बताते हैं कि DGCA ने इसे बैन किया है।"),
    ("हर पावर बैंक को उसके डिब्बे या अलग प्लास्टिक बैग में रखें, ताकि उसके सिरे धातु से न छुएँ।", "Air India और Akasa Air यही कहती हैं।"),
]
SHOE_TW = {  # words for static/shoe-size.js
    "kids": " (बच्चों का)", "choose": "चुनें…", "uk": "India / UK ", "cm": " cm",
    "picksKids": "बच्चों के जूते अभी हमारे पास नहीं हैं। ये बड़ों के लिए हमारे ट्रैवल शूज़ हैं। हर Amazon पेज पर ब्रांड का अपना साइज चार्ट है।",
    "picksNote": "{g} के लिए हमारे ट्रैवल शूज़। हर Amazon पेज पर ब्रांड का अपना साइज चार्ट है: ऑर्डर से पहले ज़रूर देखें।",
    "men": "पुरुषों", "women": "महिलाओं", "sizeOut": "{label} का India/UK साइज {uk} = US {us} = EU {eu}।",
    "note": "साइज ब्रांड के हिसाब से बदलते हैं, इसलिए प्रोडक्ट पेज का साइज चार्ट भी देखें।",
    "prompt": "अपने पैर की लंबाई cm में लिखें, या जो साइज पता है वह चुनें, और हर साइज सिस्टम में देखें।",
    "outside": "{cm} cm का पैर इस चार्ट ({lo}–{hi} cm) से बाहर है। ", "tryKids": "बच्चों का चार्ट देखें।",
    "babyShop": "बेबी शूज़ के साइज दुकान पर पूछें।", "bigBrands": "बड़े साइज बनाने वाले ब्रांड ढूँढें।",
    "tryAdults": "महिलाओं या पुरुषों का चार्ट देखें।", "tryMen": "पुरुषों का चार्ट देखें।",
    "fits": "आपका {cm} cm का पैर चार्ट के इस साइज में आता है। साइज ब्रांड के हिसाब से बदलते हैं, इसलिए प्रोडक्ट पेज भी देखें।",
    "between": "आपका पैर दो साइज के बीच में है, इसलिए हमने बड़ा साइज चुना। साइज ब्रांड के हिसाब से बदलते हैं, इसलिए प्रोडक्ट पेज भी देखें।",
    "again": "इस चार्ट के लिए अपना साइज फिर से चुनें।", "now": "अब अपना साइज चुनें।",
}
POWER_TW = {  # words for static/power-bank.js
    "your": "आपका पावर बैंक {wh} Wh का है।", "calc": "{mah} mAh x {v} V ÷ 1,000 = {wh} Wh।",
    "prompt": "अपने पावर बैंक के mAh लिखें और देखें कि उसका वॉट-आवर (Wh) कितना है और फ्लाइट में ले जा सकते हैं या नहीं।",
    "yes": "केबिन बैग में ले जा सकते हैं", "close": "एयरलाइन की मंज़ूरी चाहिए", "no": "भारतीय उड़ानों में इजाज़त नहीं",
    "yesNote": "इसे अपने पास रखें, ऊपर के बिन में नहीं, और उड़ान में इसे इस्तेमाल या चार्ज न करें। इसे कभी चेक-इन बैग में न रखें।",
    "closeNote": "यह {low} Wh से ऊपर है। कुछ एयरलाइनें इसे ले जाने देती हैं, कुछ नहीं: उड़ान से पहले अपनी एयरलाइन से पूछें, या छोटा पावर बैंक लें।",
    "noNote": "यह {high} Wh से ऊपर है, जो यहाँ की किसी भी एयरलाइन की सबसे ऊँची सीमा है, चाहे केबिन में हो या चेक-इन में। इसे घर पर छोड़ दें।",
    "yesCell": "हाँ", "noCell": "नहीं", "over": "{max} Wh से ज़्यादा",
}

TOOLS_HI = []  # (hindi path, link text) of every Hindi tool page that exists, for the 'more free tools' pills


def english_path(hi_path):
    return {SHOE_PATH: SHOE_EN, POWER_PATH: POWER_EN}.get(hi_path) or next((en for en, h in PAIRS.items() if h == hi_path), "")


PAIRS = {}  # filled below by register(): English path -> Hindi path (all tools)


def _json(words):
    return json.dumps(words, ensure_ascii=False).replace("</", "<\\/")


def register(B):
    """Pair each Hindi tool with its English page. Called by hindi_pages.register before any page is written."""
    del TOOLS_HI[:]
    if SHOE_FILE.exists():
        B.HINDI_PAGES[SHOE_EN] = SHOE_PATH
        TOOLS_HI.append((SHOE_PATH, "जूते का साइज कन्वर्टर"))
    if POWER_FILE.exists():
        B.HINDI_PAGES[POWER_EN] = POWER_PATH
        TOOLS_HI.append((POWER_PATH, "पावर बैंक फ्लाइट चेकर"))


def build_all(B, cfg, deals, pages, lastmod):
    if SHOE_FILE.exists():
        build_shoe(B, cfg, deals, pages, lastmod)
    if POWER_FILE.exists():
        build_power(B, cfg, deals, pages, lastmod)


def _finish(B, cfg, pages, lastmod, path, seo, desc, crumb, body, faq, modified):
    faq_block, faq_schema = H.faq_html(B, faq)
    body = body.replace("{faq}", faq_block)
    H.finish(B, cfg, pages, lastmod, path, seo, desc, body, 1, [("होम", ""), (crumb, path)], PUBLISHED, max(PUBLISHED, modified), faq_schema)


def _head(B, crumb, title, sub, tint, glyph, hinglish):
    return H.head(B, [(None, crumb)], title, sub, tint, B.icon(glyph, "icon media-icon"), "../", hinglish)


def _tail(B, cfg, path, script, words_id, words):
    return f"""{H.tool_links(B, path, "../")}
<p class="checked">{H.HI_DISCLOSURE}</p>
</article></div>
<script type="application/json" id="{words_id}">{_json(words)}</script>
<script src="../assets/{script}" defer></script>
{B.telegram_band(cfg, "../")}"""


# ---------- shoe size ----------

def hi_cm(B, row):
    lo, hi = row["cm"]
    return "%s–%s cm" % (B.num(lo), B.num(hi))


def build_shoe(B, cfg, deals, pages, lastmod):
    data = json.loads(SHOE_FILE.read_text(encoding="utf-8"))
    if data["checked"] != SHOE_MATCHED:
        H.warn("%s was written from the shoe size data of %s, but data/shoe_sizes.json was checked %s. Update the Hindi page."
               % (SHOE_PATH, SHOE_MATCHED, data["checked"]))
    path = SHOE_PATH
    groups = {g["slug"]: g for g in data["groups"]}
    men, women, kids = groups["men"], groups["women"], groups["kids"]
    num = B.num

    def find(group, uk=None, eu=None, cm=None):
        for r in group["rows"]:
            if (uk and r["uk"] == uk and not r.get("kids")) or (eu and r["eu"] == eu) or (cm and r["cm"][1] >= cm):
                return r
        raise SystemExit("Error: shoe size chart has no row for %s" % (uk or eu or cm))

    m8, w40, m26, k5 = find(men, uk="8"), find(women, eu="40"), find(men, cm=26), next(r for r in kids["rows"] if r["age"].startswith("4.5"))
    m6, w6 = find(men, uk="6"), find(women, uk="6")
    uk_label = lambda r: r["uk"] + (" (बच्चों का)" if r.get("kids") else "")

    tables = []
    for g in data["groups"]:
        label = HI_GROUP[g["slug"]]
        age_head = "<th>उम्र (लगभग)</th>" if g["slug"] == "kids" else ""
        rows = "".join(
            f'<tr data-uk="{e(r["uk"])}" data-kids="{1 if r.get("kids") else 0}" data-us="{e(r["us"])}" data-eu="{e(r["eu"])}" '
            f'data-lo="{r["cm"][0]}" data-hi="{r["cm"][1]}"><th scope="row">{e(uk_label(r))}</th><td>{e(r["us"])}</td><td>{e(r["eu"])}</td>'
            f'<td>{hi_cm(B, r)}</td>' + (f'<td>{e(r["age"])} साल</td>' if g["slug"] == "kids" else "") + "</tr>"
            for r in g["rows"])
        tables.append(f"""<h3 id="chart-{g["slug"]}">{label} के जूतों का साइज चार्ट ({e(g["brand"])})</h3>
<div class="table-wrap"><table class="compare ss-table" id="ss-t-{g["slug"]}" data-group="{g["slug"]}" data-label="{label} के जूते"><thead><tr><th>India / UK</th><th>US</th><th>EU</th><th>पैर की लंबाई</th>{age_head}</tr></thead><tbody>{rows}</tbody></table></div>""")

    shoes = [d for d in deals if d["category"] == "shoes"]
    cards = "".join(B.card(cfg, d, "../").replace('<article class="card"', '<article class="card" data-for="%s"' % e(
        d.get("specs", {}).get("For", "").lower()), 1) for d in shoes)
    picks_html = (f"""<h2 id="picks">हमारी पसंद के जूते</h2>
<p id="ss-picks-note">पुरुषों और महिलाओं के लिए ट्रैवल शूज़, सैंडल और चप्पल। हर Amazon पेज पर ब्रांड का अपना साइज चार्ट है: ऑर्डर से पहले ज़रूर देखें।</p>
<div class="grid" id="ss-picks">{cards}</div>""" if shoes else "")
    src = " और ".join(f'<a href="{e(s["url"])}" target="_blank" rel="noopener" lang="en">{e(s["label"])}</a>' for s in data["sources"])
    checked = B.hi_date(data["checked"])
    title = "जूते का साइज चार्ट: India/UK से US, EU और cm"
    seo = "जूते का साइज चार्ट (भारत): UK, US, EU और cm, पुरुष, महिला और बच्चों के लिए"
    desc = ("जूते का साइज कन्वर्टर। अपने पैर की लंबाई cm में नापें या अपना साइज चुनें, और Bata India और Campus के साइज चार्ट से "
            "पुरुष, महिला और बच्चों के लिए India/UK, US और EU साइज देखें।")
    body = f"""{_head(B, "जूते का साइज", title, "मुफ़्त टूल · %s को जाँचा गया" % checked, "shoes", "shoe",
                     "Shoe size chart in Hindi: foot ka size cm mein napiye aur India, UK, US, EU size dekhiye.")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li><strong>India और UK का साइज एक ही नंबर होता है।</strong> India 8 यानी UK 8।</li>
<li>Bata India के चार्ट में पुरुषों का UK {m8["uk"]} यानी US {m8["us"]} और EU {m8["eu"]}, पैर की लंबाई {hi_cm(B, m8)}।</li>
<li>पैर की लंबाई cm में नापना साइज चुनने का सबसे पक्का तरीक़ा है। साइज ब्रांड के हिसाब से बदलते हैं, इसलिए ब्रांड का अपना चार्ट भी देखें।</li>
</ul></div>
<h2>पहला क़दम: अपना पैर नापें</h2>
<ol>
<li>एक काग़ज़ दीवार के सहारे ज़मीन पर रखें।</li>
<li>उस पर खड़े हों, एड़ी दीवार से लगी हो। वही मोज़े पहनें जो आप जूतों के साथ पहनेंगे।</li>
<li>किसी से अपने सबसे लंबे अँगूठे/उँगली के सिरे पर निशान लगवाएँ। (यह हमेशा बड़ा अँगूठा नहीं होता।)</li>
<li>दीवार से निशान तक स्केल से cm में नापें। दोनों पैर नापें और जो लंबा हो वह लें।</li>
<li>शाम को नापें, जब पैर सबसे बड़े होते हैं।</li>
</ol>
<h2>दूसरा क़दम: अपना साइज ढूँढें</h2>
<form class="checker" id="ss" onsubmit="return false">
<div class="checker-fields"><label>जूते किसके लिए<select id="ss-who"><option value="men">पुरुष</option><option value="women">महिला</option><option value="kids">बच्चे</option></select></label>
<label>पैर की लंबाई (cm)<input id="ss-cm" type="number" min="10" max="35" step="0.1" inputmode="decimal" placeholder="जैसे 26"></label>
<label hidden data-js>या, जो साइज पता है<select id="ss-sys"><option value="uk">India / UK</option><option value="us">US</option><option value="eu">EU</option></select></label>
<label hidden data-js>साइज<select id="ss-size"><option value="">चुनें…</option></select></label></div>
<p class="checker-total" id="ss-out" aria-live="polite">{SHOE_TW["prompt"]}</p>
<div id="ss-result" hidden>
<div class="table-wrap"><table class="compare snug"><tbody>
<tr><th scope="row">India / UK</th><td id="ss-r-uk"></td></tr>
<tr><th scope="row">US</th><td id="ss-r-us"></td></tr>
<tr><th scope="row">EU</th><td id="ss-r-eu"></td></tr>
<tr><th scope="row">पैर की लंबाई</th><td id="ss-r-cm"></td></tr>
</tbody></table></div>
<p class="hint" id="ss-r-note"></p>
<p id="ss-r-links"><a href="#picks">हमारे जूते देखें</a> &middot; <a href="../category/shoes.html" lang="en">All shoes and sandals (English)</a> &middot; <a href="../guides/travel-shoes-guide.html" lang="en">Which shoes to take on a trip (English)</a></p>
</div>
</form>
<noscript><p>JavaScript बंद हो तो भी नीचे के चार्ट में अपनी पंक्ति देख सकते हैं।</p></noscript>
<h2>जूतों के साइज चार्ट</h2>
<p>पुरुषों और महिलाओं के साइज Bata India की साइज गाइड से हैं। बच्चों के साइज Campus के किड्स साइज चार्ट से हैं। पैर की लंबाई का मतलब आपके पैर की लंबाई है, जूते की नहीं।</p>
{"".join(tables)}
<p class="checked">{checked} को जाँचा, {src} पर। साइज ब्रांड के हिसाब से बदलते हैं: स्पोर्ट्स ब्रांड अक्सर उसी UK साइज के लिए अलग US साइज देते हैं, और कुछ जूते छोटे या चौड़े होते हैं। हर प्रोडक्ट पेज का साइज चार्ट ही भरोसे लायक़ है।</p>
<p>बच्चों के साइज 7 से 13 तक जाते हैं, फिर 1 से दोबारा शुरू होते हैं। थोड़ी बढ़ने की जगह छोड़ें: अगर बच्चे का पैर दो साइज के बीच में है, तो बड़ा साइज लें।</p>
{picks_html}
<p>और मदद: <a href="../guides/travel-shoes-guide.html" lang="en">which shoes to take on a trip (English)</a> और हमारा <a href="../tools/clothing-size.html" lang="en">clothing size converter (English)</a>, शर्ट, जीन्स, कुर्ता और बच्चों के कपड़ों के लिए।</p>
{{faq}}
""" + _tail(B, cfg, path, "shoe-size.js", "ss-t", SHOE_TW)
    faq = [
        ("क्या भारत का जूता साइज UK साइज जैसा ही होता है?", "हाँ। भारत में जूते UK साइज में बिकते हैं, इसलिए India 8 और UK 8 एक ही हैं।"),
        ("UK %s का US और EU साइज क्या है?" % m8["uk"],
         "Bata India के चार्ट में पुरुषों का UK %s यानी US %s और EU %s है, पैर की लंबाई %s। दूसरे ब्रांड में US साइज अलग हो सकता है, इसलिए ब्रांड का अपना चार्ट देखें।"
         % (m8["uk"], m8["us"], m8["eu"], hi_cm(B, m8))),
        ("महिलाओं के लिए भारत में साइज %s क्या होता है?" % w40["eu"],
         "Bata India के महिलाओं के चार्ट में EU %s यानी India/UK %s और US %s है, पैर की लंबाई %s।" % (w40["eu"], w40["uk"], w40["us"], hi_cm(B, w40))),
        ("26 cm के पैर का जूता साइज क्या होगा?",
         "पुरुषों के लिए Bata India के चार्ट में लगभग India/UK %s (EU %s), जो %s के पैर को कवर करता है।" % (m26["uk"], m26["eu"], hi_cm(B, m26))),
        ("घर पर पैर का साइज cm में कैसे नापें?",
         "काग़ज़ पर खड़े हों, एड़ी दीवार से लगी हो, सबसे लंबी उँगली के सिरे पर निशान लगाएँ और दीवार से निशान तक cm में नापें। दोनों पैर शाम को नापें और जो लंबा हो वह लें।"),
        ("क्या पुरुषों और महिलाओं के जूतों के साइज एक जैसे होते हैं?",
         "Bata India के चार्ट में पैर की उतनी ही लंबाई के लिए UK नंबर एक ही होता है, पर EU नंबर अलग है: पुरुषों का UK %s यानी EU %s, महिलाओं का UK %s यानी EU %s।"
         % (m6["uk"], m6["eu"], w6["uk"], w6["eu"])),
        ("भारत में 5 साल का बच्चा कौन सा जूता साइज पहनता है?",
         "Campus के चार्ट में अक्सर बच्चों का लगभग UK %s (उम्र %s, पैर %s)। बच्चे तेज़ी से बढ़ते हैं, इसलिए उम्र की जगह पैर नापें।"
         % (k5["uk"], k5["age"], hi_cm(B, k5))),
    ]
    _finish(B, cfg, pages, lastmod, path, seo, desc, "जूते का साइज", body, faq, data["checked"])


# ---------- power bank ----------

def build_power(B, cfg, deals, pages, lastmod):
    data = json.loads(POWER_FILE.read_text(encoding="utf-8"))
    if data["checked"] != POWER_MATCHED:
        H.warn("%s was written from the power bank rules of %s, but data/power_banks.json was checked %s. Update the Hindi page."
               % (POWER_PATH, POWER_MATCHED, data["checked"]))
    import more_tools as M
    path = POWER_PATH
    airlines = data["airlines"]
    for a in airlines:
        if a["name"] not in HI_AIRLINE_RULE:
            H.warn("power bank airline %r has no Hindi rule in hindi_tools.HI_AIRLINE_RULE" % a["name"])
    if len(data["on_board"]) != len(HI_ON_BOARD):
        H.warn("data/power_banks.json has %d on-board points but hindi_tools.HI_ON_BOARD has %d" % (len(data["on_board"]), len(HI_ON_BOARD)))
    volt = data["voltage"]
    num = B.num
    checked = B.hi_date(data["checked"])
    low, high = min(a["max_wh"] for a in airlines), max(a["max_wh"] for a in airlines)
    by_low = H.hi_join([a["name"] for a in airlines if a["max_wh"] == low])
    by_high = H.hi_join([a["name"] for a in airlines if a["max_wh"] == high])
    mah_for = lambda wh: int(round(wh * 1000 / volt, -2))
    yes_no = lambda ok: '<span class="fit fit-yes">हाँ</span>' if ok else '<span class="fit fit-no">नहीं</span>'

    head_cells = "".join("<th>%s</th>" % e(a["name"]) for a in airlines)
    size_rows = "".join(
        f'<tr><th scope="row">{m:,} mAh</th><td>{num(m * volt / 1000)} Wh</td>'
        + "".join("<td>%s</td>" % yes_no(m * volt / 1000 <= a["max_wh"]) for a in airlines) + "</tr>"
        for m in M.POWER_SIZES)
    airline_rows = "".join(
        f'<tr><th scope="row">{e(a["name"])}</th><td>{a["max_wh"]} Wh तक</td>'
        f'<td>{e(HI_AIRLINE_RULE.get(a["name"], a["rule"]))} <a class="src" href="{e(a["source"])}" target="_blank" rel="noopener">स्रोत</a></td></tr>'
        for a in airlines)
    on_board = "".join(f'<li><strong>{e(t)}</strong> <span class="muted">{e(who)}</span></li>' for t, who in HI_ON_BOARD)
    sources = ", ".join(f'<a href="{e(a["source"])}" target="_blank" rel="noopener" lang="en">{e(a["source_label"])}</a>' for a in airlines)
    picks = [d for d in deals if "power bank" in d["title"].lower()]
    picks_html = ('<h2 id="picks">हमारे चुने पावर बैंक</h2><div class="grid">%s</div>' % "".join(B.card(cfg, d, "../") for d in picks)) if picks else ""
    more_links = ('<a href="#picks">हमारे चुने पावर बैंक</a> &middot; ' if picks else "") + '<a href="can-i-carry/power-bank.html">पावर बैंक के पूरे नियम</a>'
    title = "क्या मेरा पावर बैंक फ्लाइट में ले जा सकते हैं? mAh से Wh चेकर"
    seo = "पावर बैंक फ्लाइट में ले जा सकते हैं? mAh से Wh चेकर: IndiGo, Air India, Akasa"
    desc = ("अपने पावर बैंक के mAh लिखें और देखें कि उसके वॉट-आवर (Wh) कितने हैं और IndiGo, Air India और Akasa Air केबिन में ले जाने देती हैं या नहीं। "
            "पावर बैंक चेक-इन बैग में कभी नहीं जाते। नियम %s को जाँचे गए।" % checked)
    ap_rows = "".join(f'<tr data-max="{a["max_wh"]}"><th scope="row">{e(a["name"])}</th><td class="pb-cabin"></td><td><span class="fit fit-no">नहीं</span></td></tr>'
                      for a in airlines)
    body = f"""{_head(B, "पावर बैंक फ्लाइट चेकर", title, "मुफ़्त टूल · नियम %s को जाँचे गए" % checked, "travel-gear", "shield",
                     "Power bank kitne mAh tak flight mein le ja sakte hain? mAh likhiye, Wh aur airline ka jawab dekhiye.")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li><strong>पावर बैंक सिर्फ़ केबिन बैग में जाते हैं, चेक-इन में कभी नहीं।</strong> यहाँ की हर भारतीय एयरलाइन यही कहती है।</li>
<li>{low} Wh तक (लगभग {mah_for(low):,} mAh) तीनों एयरलाइनों में चलता है। {by_high} {high} Wh तक की इजाज़त देती है; {by_low} {low} Wh पर रुक जाती हैं।</li>
<li>उड़ान में पावर बैंक इस्तेमाल या चार्ज नहीं कर सकते, और उसे ऊपर के बिन में नहीं रख सकते।</li>
</ul></div>
<form class="checker" id="pb" onsubmit="return false" data-volt="{volt}" data-low="{low}" data-high="{high}">
<div class="checker-fields"><label>क्षमता (mAh)<input id="pb-mah" type="number" min="100" max="100000" step="100" inputmode="numeric" placeholder="जैसे 20000"></label>
<label>सेल वोल्टेज (V)<input id="pb-v" type="number" min="1" max="30" step="0.01" inputmode="decimal" value="{volt}"></label>
<label>या लेबल पर लिखे Wh<input id="pb-wh" type="number" min="1" max="1000" step="0.1" inputmode="decimal" placeholder="जैसे 74"></label></div>
<p class="hint">mAh और Wh पावर बैंक के पीछे छपे होते हैं। ज़्यादातर में {volt} V के सेल होते हैं; लेबल पर दूसरा वोल्टेज लिखा हो तो वही लिखें।</p>
<p class="checker-total" id="pb-out" aria-live="polite">{POWER_TW["prompt"]}</p>
<div id="pb-result" hidden>
<div class="table-wrap"><table class="compare snug" id="pb-airlines"><thead><tr><th>एयरलाइन</th><th>केबिन बैग</th><th>चेक-इन</th></tr></thead><tbody>
{ap_rows}
</tbody></table></div>
<p class="hint" id="pb-note"></p>
<p>{more_links}</p>
</div>
</form>
<noscript><p>JavaScript बंद हो तो भी नीचे की तालिकाओं में अपना पावर बैंक देख सकते हैं।</p></noscript>
<h2>आम पावर बैंक के साइज</h2>
<p>वॉट-आवर = mAh x {volt} ÷ 1,000। हर एयरलाइन में सिर्फ़ केबिन बैग में।</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>पावर बैंक</th><th>लगभग</th>{head_cells}</tr></thead><tbody>{size_rows}</tbody></table></div>
<h2>एयरलाइन के हिसाब से नियम</h2>
<p>यहाँ की कोई भी एयरलाइन पावर बैंक को चेक-इन बैग में नहीं जाने देती।</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>एयरलाइन</th><th>केबिन बैग</th><th>एयरलाइन क्या कहती है</th></tr></thead><tbody>{airline_rows}</tbody></table></div>
<p class="checked">{checked} को जाँचा, {sources} पर। सिक्योरिटी स्टाफ़ किसी भी चीज़ को मना कर सकता है और एयरलाइनें नियम बदल सकती हैं, इसलिए उड़ान से पहले अपनी एयरलाइन से पूछ लें।</p>
<h2>विमान में</h2>
<ul>{on_board}</ul>
<h2>"एयरलाइन की मंज़ूरी चाहिए" का मतलब</h2>
<p>{low} Wh से ऊपर और {high} Wh तक का पावर बैंक {by_high} की सूची में चलता है, पर {by_low} के पेज सिर्फ़ {low} Wh तक की इजाज़त देते हैं। उड़ान से पहले अपनी एयरलाइन से पूछें, या छोटा पावर बैंक लें। {high} Wh से ऊपर का पावर बैंक यहाँ की कोई एयरलाइन नहीं ले जाने देती।</p>
<p class="checked">पक्का नहीं: उड़ान में इस्तेमाल पर DGCA का सर्कुलर हमें DGCA की अपनी वेबसाइट पर नहीं मिला, इसलिए वह नियम Akasa Air के पेज और ख़बरों से है। बाक़ी सब कुछ एयरलाइनों के अपने पेजों से है, BCAS या DGCA के सर्कुलर से नहीं।</p>
{picks_html}
<p>और मदद: <a href="can-i-carry/power-bank.html">फ्लाइट में पावर बैंक ले जा सकते हैं?</a>, <a href="can-i-carry.html">और क्या-क्या ले जा सकते हैं</a> और <a href="flight-baggage-rules.html">भारतीय एयरलाइनों के बैगेज नियम</a>।</p>
{{faq}}
""" + _tail(B, cfg, path, "power-bank.js", "pb-t", POWER_TW)
    faq = [
        ("क्या 20000 mAh का पावर बैंक भारत में फ्लाइट में ले जा सकते हैं?",
         "हाँ, केबिन बैग में। %s V पर यह लगभग %s Wh का है, जो %s की %s Wh और %s की %s Wh सीमा से कम है।"
         % (volt, num(20000 * volt / 1000), by_low, low, by_high, high)),
        ("mAh को Wh में कैसे बदलें?", "mAh को वोल्टेज से गुणा करें और 1,000 से भाग दें। %s V के सेल वाले 10,000 mAh के पावर बैंक के लिए: 10,000 x %s ÷ 1,000 = %s Wh।"
         % (volt, volt, num(10000 * volt / 1000))),
        ("क्या पावर बैंक चेक-इन बैग में रख सकते हैं?", "नहीं। IndiGo, Air India और Akasa Air तीनों चेक-इन बैग में पावर बैंक मना करती हैं। Akasa Air कहती है कि पावर बैंक वाला चेक-इन बैग विमान में चढ़ाया ही नहीं जाएगा।"),
        ("क्या उड़ान के दौरान पावर बैंक इस्तेमाल कर सकते हैं?", "नहीं। Akasa Air के नियम उड़ान में पावर बैंक इस्तेमाल या चार्ज करने से मना करते हैं, और ख़बरें कहती हैं कि DGCA ने इसे सभी भारतीय उड़ानों में बैन किया है। फ़ोन बोर्डिंग से पहले चार्ज कर लें।"),
        ("IndiGo में सबसे बड़ा पावर बैंक कौन सा चलता है?", "IndiGo की सूची %s Wh तक के पावर बैंक की इजाज़त देती है (%s V पर लगभग %s mAh), बशर्ते पावर रेटिंग उस पर छपी हो।"
         % (high, volt, "{:,}".format(mah_for(high)))),
        ("कितने पावर बैंक ले जा सकते हैं?", "Air India और Akasa Air एक यात्री को 2 स्पेयर बैटरी की इजाज़त देती हैं, और पावर बैंक एक गिना जाता है। IndiGo की सूची में संख्या नहीं दी है, इसलिए दो तक रखें।"),
    ]
    _finish(B, cfg, pages, lastmod, path, seo, desc, "पावर बैंक फ्लाइट चेकर", body, faq, data["checked"])
