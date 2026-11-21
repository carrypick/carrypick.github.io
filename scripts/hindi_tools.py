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
import re
from html import escape as e

import hindi_pages as H
from common import ROOT

SHOE_FILE = ROOT / "data" / "shoe_sizes.json"
SHOE_EN, SHOE_PATH = "tools/shoe-size.html", "hi/shoe-size.html"
SHOE_MATCHED = "2026-11-20"
POWER_FILE = ROOT / "data" / "power_banks.json"
POWER_EN, POWER_PATH = "tools/power-bank-flight-check.html", "hi/power-bank-flight-check.html"
POWER_MATCHED = "2026-11-21"
PUBLISHED = "2026-11-21"

HI_GROUP = {"men": "पुरुषों", "women": "महिलाओं", "kids": "बच्चों"}
HI_AIRLINE_RULE = {
    "IndiGo": "सिर्फ़ केबिन बैग में। पावर रेटिंग पावर बैंक पर छपी होनी चाहिए। 160 Wh से ऊपर की इजाज़त नहीं।",
    "Air India": "सिर्फ़ केबिन बैग में, 100 Wh तक, एक यात्री के पास 2 से ज़्यादा स्पेयर बैटरी नहीं। ऊपर के बिन में नहीं।",
    "Akasa Air": "सिर्फ़ केबिन बैग में, 2 तक, हर एक 100 Wh तक, डिब्बे या प्लास्टिक बैग में। उड़ान के दौरान इस्तेमाल या चार्ज नहीं कर सकते, और ऊपर के बिन में नहीं रख सकते।",
}
HI_ON_BOARD = [
    ("उड़ान के दौरान पावर बैंक से फ़ोन चार्ज न करें, और पावर बैंक को भी चार्ज न करें।",
     "यह हर भारतीय एयरलाइन का नियम है: DGCA के Dangerous Goods Advisory Circular No. 01/2025 (11 नवंबर 2025) के मुताबिक़ उड़ान के दौरान पावर बैंक इस्तेमाल या चार्ज करने की अनुमति नहीं है (हमने इसे 21 नवंबर 2026 को DGCA की वेबसाइट पर पढ़ा)। Akasa Air की कंडीशंस ऑफ़ कैरिज़ भी यही कहती हैं।"),
    ("इसे सीट की जेब में, आगे वाली सीट के नीचे या अपने पास रखें, ऊपर के बिन में नहीं।", "DGCA का सर्कुलर 01/2025, Air India और Akasa Air, तीनों यही कहते हैं।"),
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

PACK_FILE = ROOT / "data" / "hindi_pack.json"
PACK_EN, PACK_PATH = "tools/packing-list-maker.html", "hi/packing-list-maker.html"
PACK_MATCHED = "2026-11-20"  # pack_maker.UPDATED when the Hindi words were written
PACK_TW = {  # words for static/pack-maker.js
    "perAdult": " (हर बड़े के लिए)", "by": {"flight": "फ़्लाइट से", "train": "ट्रेन से", "road": "कार या बस से"},
    "day": " दिन", "days": " दिन", "abroad": ", विदेश", "ready": "तैयार चेकलिस्ट: ", "guides": "इस ट्रिप की पैकिंग गाइड",
    "picks": "इस ट्रिप के लिए हमारी पसंद", "title": "आपकी पैकिंग लिस्ट: {s}", "packed": "{total} में से {done} पैक हो गए",
    "list": "पैकिंग लिस्ट: {s}", "make": "अपनी लिस्ट ख़ुद बनाएँ: ", "copied": "लिस्ट कॉपी हो गई। इसे किसी नोट या चैट में पेस्ट करें।",
    "nocopy": "यहाँ कॉपी नहीं हो पाई। लिस्ट को चुनकर हाथ से कॉपी करें।",
}
GIFT_FILE = ROOT / "data" / "gift_finder.json"
GIFT_WORDS = ROOT / "data" / "hindi_gift.json"
GIFT_EN, GIFT_PATH = "tools/gift-finder.html", "hi/gift-finder.html"
GIFT_TW = {  # words for static/gift-finder.js
    "q": "सवाल {n} / {total}", "title": "{head}: {for}",
    "note": "{for} “{size}” वाले आइडिया कम हैं, इसलिए नीचे हमारी दूसरी पसंद भी जोड़ी हैं।",
}
CLOTH_FILE = ROOT / "data" / "clothing_sizes.json"
CLOTH_WORDS = ROOT / "data" / "hindi_clothing.json"
CLOTH_EN, CLOTH_PATH = "tools/clothing-size.html", "hi/clothing-size.html"
CLOTH_TW = {  # words for static/clothing-size.js (the measures and column names are added from data/hindi_clothing.json)
    "inch": " इंच", "cm": " cm", "bigger": "बड़ा", "smaller": "छोटा", "chartEnd": "{m} के हिसाब से यह इस चार्ट से {what} है।",
    "between": "। आप दो साइज के बीच में हैं, इसलिए हमने बड़ा साइज चुना।", "or": " या ", "sep": ": ", "choose": "चुनें…",
    "note": "ब्रांड के हिसाब से साइज बदलते हैं, इसलिए प्रोडक्ट पेज का साइज चार्ट भी देखें।",
    "prompt": "अपना नाप लिखें, या जो साइज पता है वह चुनें, और हर ब्रांड के चार्ट पर देखें।", "forA": "{x} के लिए:",
    "add": "अपनी {m} भी लिखें: जो साइज इन सब में फ़िट हो वही ख़रीदें।", "andWord": " और ", "fits": "{title} में {size} का साइज {body} पर फ़िट होता है।",
    "others": "दूसरे चार्ट उसी शरीर के नाप से मिलाए गए हैं। ब्रांड के हिसाब से साइज बदलते हैं, इसलिए प्रोडक्ट पेज भी देखें।",
    "picksKids": "बच्चों के लिए हमारे ट्रैवल कपड़े: थर्मल सेट, हुडी, जैकेट और ट्रैक सूट। हर Amazon पेज पर ब्रांड का अपना उम्र वाला साइज चार्ट है: ऑर्डर से पहले ज़रूर देखें।",
    "picksNote": "{who} के लिए हमारे ट्रैवल कपड़े। हर Amazon पेज पर ब्रांड का अपना साइज चार्ट है: ऑर्डर से पहले ज़रूर देखें।",
    "men": "पुरुषों", "women": "महिलाओं", "plainHead": "^(साइज|UK साइज|उम्र)", "letter": "अक्षर साइज",
}
TOOLS_HI = []  # (hindi path, link text) of every Hindi tool page that exists, for the 'more free tools' pills


def english_path(hi_path):
    return {SHOE_PATH: SHOE_EN, POWER_PATH: POWER_EN, PACK_PATH: PACK_EN, GIFT_PATH: GIFT_EN, CLOTH_PATH: CLOTH_EN}.get(hi_path) or next((en for en, h in PAIRS.items() if h == hi_path), "")


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
    if CLOTH_FILE.exists() and CLOTH_WORDS.exists():
        B.HINDI_PAGES[CLOTH_EN] = CLOTH_PATH
        TOOLS_HI.append((CLOTH_PATH, "कपड़ों का साइज कन्वर्टर"))
    if GIFT_FILE.exists() and GIFT_WORDS.exists():
        B.HINDI_PAGES[GIFT_EN] = GIFT_PATH
        TOOLS_HI.append((GIFT_PATH, "गिफ़्ट फ़ाइंडर क्विज़"))
    if PACK_FILE.exists() and (ROOT / "data" / "packing.json").exists():
        B.HINDI_PAGES[PACK_EN] = PACK_PATH
        TOOLS_HI.append((PACK_PATH, "पैकिंग लिस्ट मेकर"))
    import what_to_wear_hi
    what_to_wear_hi.register(B, TOOLS_HI, PAIRS)  # hi/what-to-wear.html, built by what_to_wear.build()


def build_all(B, cfg, deals, pages, lastmod):
    if SHOE_FILE.exists():
        build_shoe(B, cfg, deals, pages, lastmod)
    if B.HINDI_PAGES.get(CLOTH_EN) == CLOTH_PATH:
        build_clothing(B, cfg, deals, pages, lastmod)
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
<p>और मदद: <a href="../guides/travel-shoes-guide.html" lang="en">which shoes to take on a trip (English)</a> और हमारा <a href="clothing-size.html">कपड़ों का साइज कन्वर्टर</a>, शर्ट, जीन्स, कुर्ता और बच्चों के कपड़ों के लिए।</p>
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
<p class="checked">उड़ान में इस्तेमाल का नियम DGCA के <a href="https://www.dgca.gov.in/digigov-portal/Upload?flag=iframeAttachView&attachId=It%2B0TP06x06YSOsdpSINLg%3D%3D&baseLocale=en_US" rel="nofollow">Dangerous Goods Advisory Circular No. 01/2025</a> (11 नवंबर 2025) से है, जिसे हमने 21 नवंबर 2026 को DGCA की वेबसाइट पर पढ़ा। ऊपर की Wh सीमा और संख्या एयरलाइनों के अपने पेजों से हैं।</p>
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
        ("क्या उड़ान के दौरान पावर बैंक इस्तेमाल कर सकते हैं?", "नहीं। DGCA के Dangerous Goods Advisory Circular No. 01/2025 (11 नवंबर 2025) के मुताबिक़ भारतीय उड़ानों में उड़ान के दौरान पावर बैंक इस्तेमाल या चार्ज नहीं कर सकते, और Akasa Air के नियम भी यही कहते हैं। फ़ोन बोर्डिंग से पहले चार्ज कर लें।"),
        ("IndiGo में सबसे बड़ा पावर बैंक कौन सा चलता है?", "IndiGo की सूची %s Wh तक के पावर बैंक की इजाज़त देती है (%s V पर लगभग %s mAh), बशर्ते पावर रेटिंग उस पर छपी हो।"
         % (high, volt, "{:,}".format(mah_for(high)))),
        ("कितने पावर बैंक ले जा सकते हैं?", "Air India और Akasa Air एक यात्री को 2 स्पेयर बैटरी की इजाज़त देती हैं, और पावर बैंक एक गिना जाता है। IndiGo की सूची में संख्या नहीं दी है, इसलिए दो तक रखें।"),
    ]
    _finish(B, cfg, pages, lastmod, path, seo, desc, "पावर बैंक फ्लाइट चेकर", body, faq, data["checked"])


def build_late(B, cfg, deals_by_asin, pages, lastmod):
    """Tools whose English pages are built after the Hindi pages (packing list maker, gift finder)."""
    if B.HINDI_PAGES.get(PACK_EN) == PACK_PATH:
        build_pack(B, cfg, deals_by_asin, pages, lastmod)
    if B.HINDI_PAGES.get(GIFT_EN) == GIFT_PATH:
        build_gift(B, cfg, deals_by_asin, pages, lastmod)


# ---------- packing list maker ----------

def hi_link(B, href, label):
    """(path from a Hindi page, label) for an English site path: the Hindi twin when there is one, else the English page marked (English)."""
    hi = B.HINDI_PAGES.get(href)
    if hi and (B.DOCS / hi).exists():
        return "../" + hi, label
    return "../" + href, label + " (English)"


def hi_note(B, html):
    def swap(m):
        path, label = hi_link(B, m.group(1), m.group(2))
        return '<a href="%s">%s</a>' % (path, label)
    return re.sub(r'<a href="\.\./([^"]+)">([^<]+)</a>', swap, html)


def build_pack(B, cfg, deals_by_asin, pages, lastmod):
    import pack_maker as P
    hw = json.loads(PACK_FILE.read_text(encoding="utf-8"))
    data = json.loads(B.PACKING_FILE.read_text(encoding="utf-8"))
    if P.UPDATED != PACK_MATCHED:
        H.warn("%s was written from the packing maker of %s, but scripts/pack_maker.py says %s. Update the Hindi words in data/hindi_pack.json."
               % (PACK_PATH, PACK_MATCHED, P.UPDATED))
    P.check(data, B, deals_by_asin)
    mk = data["maker"]
    trips = data["trips"]
    miss = [i["id"] for g in data["groups"] for i in g["items"] if i["id"] not in hw["items"]]
    miss += [g["name"] for g in data["groups"] if g["name"] not in hw["groups"]]
    miss += [t["slug"] for t in mk["types"] if t["slug"] not in hw["types"]]
    miss += [t["slug"] for t in trips if t["slug"] not in hw["trips"]]
    if len(mk["notes"]) != len(hw["notes"]):
        miss.append("notes (%d in English, %d in Hindi)" % (len(mk["notes"]), len(hw["notes"])))
    if miss:
        H.warn("data/hindi_pack.json has no Hindi for: %s (English shown for now)" % ", ".join(map(str, miss)))
    hw["items"] = dict({i["id"]: i["name"] for g in data["groups"] for i in g["items"]}, **hw["items"])
    hw["groups"] = dict({g["name"]: g["name"] for g in data["groups"]}, **hw["groups"])
    hw["types"] = dict({t["slug"]: t["label"] for t in mk["types"]}, **hw["types"])
    hw["trips"] = dict({t["slug"]: t["label"] for t in trips}, **hw["trips"])
    hw["notes"] = hw["notes"] + [n["text"] for n in mk["notes"][len(hw["notes"]):]]
    exists = lambda path: (B.DOCS / path).exists()
    list_path = {t["slug"]: "packing/" + ("index.html" if t["slug"] == "week" else t["slug"] + ".html") for t in trips}

    def item_json(item):
        out = {"id": item["id"], "name": hw["items"][item["id"]], "when": item["maker"]}
        if item.get("qty") is not None:
            out["qty"] = item["qty"]
        if item.get("cap") is not None:
            out["cap"] = item["cap"]
        if item.get("pick") and item["pick"] in deals_by_asin:
            out["href"], out["more"] = "../picks/%s.html" % item["pick"], "हमारी पसंद"
        elif item.get("link") and exists(item["link"]):
            hi = B.HINDI_PAGES.get(item["link"])
            if hi and exists(hi):
                out["href"], out["more"] = "../" + hi, "और देखें"
            else:
                out["href"], out["more"] = "../" + item["link"], "और देखें (English)"
        return out

    def link(href, en_label):
        if href not in hw["links"]:
            H.warn("data/hindi_pack.json has no Hindi label for %s (English shown for now)" % href)
            return ["../" + href, en_label + " (English)"]
        return list(hi_link(B, href, hw["links"][href]))

    guides = []
    for row in mk["guides"]:
        links = [link(href, label) for href, label in row["links"] if exists(href)]
        if links:
            guides.append({"when": row["maker"], "links": links})
    cats = cfg["categories"]
    shop = [{"when": row["maker"], "links": [["../category/%s.html" % c, hw["cats"].get(c, cats[c]["name"])] for c in row["cats"]
                                             if c in cats and exists("category/%s.html" % c)]} for row in mk["shop"]]
    payload = {
        "groups": [{"name": hw["groups"][g["name"]], "key": g["name"], "items": [item_json(i) for i in g["items"]]} for g in data["groups"]],
        "types": [{"slug": t["slug"], "label": hw["types"][t["slug"]], "list": "../" + list_path[t["list"]],
                   "list_label": hw["trips"][t["list"]] + " (English)", "where": t.get("where")} for t in mk["types"]],
        "seasons": mk["seasons"], "notes": [{"when": n["maker"], "html": hi_note(B, hw["notes"][i])} for i, n in enumerate(mk["notes"])],
        "guides": guides, "shop": [s for s in shop if s["links"]], "url": B.abs_url(cfg, PACK_PATH), "t": PACK_TW,
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    type_opts = "".join(f'<option value="{t["slug"]}">{e(hw["types"][t["slug"]])}</option>' for t in mk["types"])
    month_opts = "".join(f'<option value="{i + 1}">{mo}</option>' for i, mo in enumerate(B.HI_MONTHS))
    who_boxes = "".join(f'<label class="pm-pill"><input type="checkbox" name="who" value="{w["slug"]}"'
                        f'{" checked" if w["slug"] in ("men", "women") else ""}> <span>{e(hw["who"][w["slug"]])}</span></label>' for w in mk["who"])
    by_radios = "".join(f'<label class="pm-pill"><input type="radio" name="by" value="{b["slug"]}"'
                        f'{" checked" if b["slug"] == "flight" else ""}> <span>{e(hw["by"][b["slug"]])}</span></label>' for b in mk["by"])
    where_radios = "".join(f'<label class="pm-pill"><input type="radio" name="where" value="{w}"'
                           f'{" checked" if w == "india" else ""}> <span>{lab}</span></label>'
                           for w, lab in (("india", "भारत में"), ("abroad", "विदेश में")))
    ready = "".join(f'<li><a href="../{list_path[t["slug"]]}">{e(hw["trips"][t["slug"]])} (English)</a></li>' for t in trips)
    n_items = sum(len(g["items"]) for g in data["groups"])
    title = "पैकिंग लिस्ट मेकर: अपनी यात्रा की पैकिंग लिस्ट बनाएँ"
    seo = "पैकिंग लिस्ट मेकर: यात्रा की पैकिंग लिस्ट हिंदी में, मुफ़्त"
    desc = ("मुफ़्त पैकिंग लिस्ट मेकर: बीच, पहाड़, शहर, विदेश, तीर्थ, काम या शादी चुनें, दिन, महीना, कौन जा रहा है (पुरुष, महिला, बच्चे, शिशु) और फ़्लाइट, "
            "ट्रेन या सड़क। टिक करने, कॉपी करने या WhatsApp पर भेजने लायक़ चेकलिस्ट पाएँ।")
    head = H.head(B, [(None, "पैकिंग लिस्ट मेकर")], title, "मुफ़्त टूल · %s को अपडेट किया गया" % B.hi_date(P.UPDATED), "travel-gear",
                  B.icon("check", "icon media-icon"), "../", "Packing list in Hindi: yatra ke liye packing list banaiye, tick kijiye aur WhatsApp par bhejiye.")
    faq = [
        ("यात्रा की पैकिंग लिस्ट कैसे बनाएँ?", "यात्रा का प्रकार, दिन, महीना, कौन जा रहा है और कैसे जा रहे हैं, यह चुनें। मेकर लगभग %d आम चीज़ों की लिस्ट बनाता है, "
         "आपके दिनों के हिसाब से गिनती के साथ, और पैक करते समय आप टिक करते जाते हैं।" % n_items),
        ("7 दिन की यात्रा के लिए कितने कपड़े रखें?", "रोज़ एक टॉप और एक एक्स्ट्रा (8), हर 3 दिन पर एक पैंट या जीन्स (3), रोज़ एक अंडरवियर और एक एक्स्ट्रा (8) और 7 जोड़ी मोज़े। "
         "इससे लंबी यात्रा के लिए लगभग एक हफ़्ते के कपड़े रखें और वहीं धो लें।"),
        ("शिशु या बच्चों के लिए क्या पैक करें?", "शिशु के लिए: रोज़ लगभग 6 डायपर, वाइप्स, रोज़ का एक सेट कपड़े और 2 एक्स्ट्रा, खाना या फ़ॉर्मूला, कंबल और दवाइयाँ। "
         "बच्चों के लिए: हर दिन के कपड़े और 2 एक्स्ट्रा, ID, दवाइयाँ, बोतल, नाश्ता और व्यस्त रखने के लिए कुछ।"),
        ("क्या भारत में फ्लाइट में पावर बैंक ले जा सकते हैं?", "हाँ, पर सिर्फ़ केबिन बैग में, चेक-इन में कभी नहीं। उसे अपने पास रखें, ऊपर के बिन में नहीं, और उड़ान में इस्तेमाल न करें। "
         "कई एयरलाइनें 100 Wh तक के 2 पावर बैंक की इजाज़त देती हैं।"),
        ("क्या मेरे टिक सेव रहते हैं?", "हाँ, सिर्फ़ इसी डिवाइस पर, आपके ब्राउज़र में। हमें कुछ नहीं भेजा जाता। \"टिक हटाएँ\" बटन से इन्हें साफ़ करें।"),
        ("क्या मैं लिस्ट प्रिंट कर सकता हूँ या परिवार को भेज सकता हूँ?", "हाँ। काग़ज़ पर लिस्ट के लिए प्रिंट, कहीं भी चिपकाने के लिए लिस्ट कॉपी, या टेक्स्ट के रूप में भेजने के लिए WhatsApp पर भेजें इस्तेमाल करें। "
         "इसमें सिर्फ़ सामान होता है, आपका नाम या जानकारी नहीं।"),
    ]
    faq_html, faq_schema = H.faq_html(B, faq)
    body = f"""{head}
<div class="wrap"><article class="guide">
<p class="pm-nojs" id="pm-nojs">अपनी यात्रा की लिस्ट बनाने के लिए JavaScript चालू करें, या नीचे की तैयार लिस्टों में से कोई खोलें।</p>
<form class="checker pm-form" id="pm" onsubmit="return false" hidden>
<div class="pm-fields">
<label>यात्रा का प्रकार<select id="pm-type">{type_opts}</select></label>
<label>कितने दिन?<input id="pm-days" type="number" inputmode="numeric" min="1" max="30" value="5"></label>
<label>महीना<select id="pm-month">{month_opts}</select></label>
</div>
<fieldset class="pm-set"><legend>कौन जा रहा है? <span class="muted">जो लागू हों सब चुनें</span></legend><div class="pm-pills">{who_boxes}</div></fieldset>
<fieldset class="pm-set"><legend>कैसे जा रहे हैं</legend><div class="pm-pills">{by_radios}</div></fieldset>
<fieldset class="pm-set"><legend>कहाँ</legend><div class="pm-pills">{where_radios}</div></fieldset>
</form>
<div id="pm-out" hidden>
<h2 id="pm-title">आपकी पैकिंग लिस्ट</h2>
<p class="checker-total"><span id="pm-count" aria-live="polite"></span></p>
<p class="pm-actions"><button type="button" class="btn pm-btn" id="pm-print">प्रिंट</button> <button type="button" class="btn pm-btn2" id="pm-copy">लिस्ट कॉपी करें</button> <a class="btn btn-whatsapp" id="pm-wa" href="https://wa.me/" target="_blank" rel="noopener">WhatsApp पर भेजें</a> <button type="button" class="link-btn" id="pm-clear">टिक हटाएँ</button></p>
<p class="hint small muted" id="pm-copied" aria-live="polite"></p>
<div class="pm-notes" id="pm-notes"></div>
<div class="pack-list" id="pm-list"></div>
<p class="checked">गिनती हर व्यक्ति के लिए एक अंदाज़ा है। आपके टिक सिर्फ़ इसी ब्राउज़र में रहते हैं।</p>
<div class="pm-noprint" id="pm-after"></div>
</div>
<div class="pm-noprint">
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li>रोज़ एक टॉप और एक एक्स्ट्रा रखें, हर 3 दिन पर एक पैंट, और रोज़ का अंडरवियर और एक एक्स्ट्रा।</li>
<li>हफ़्ते से ज़्यादा रुकना है? लगभग 7 दिन के कपड़े रखें और वहीं धो लें: मेकर गिनती की सीमा रखता है।</li>
<li>फ़्लाइट से जा रहे हैं? पावर बैंक सिर्फ़ केबिन बैग में जाते हैं, और केबिन में तरल की हर बोतल 100 ml या कम, एक साफ़ 1 लीटर की बैग में।</li>
</ul></div>
<section class="pm-ready"><h2>तैयार पैकिंग लिस्ट</h2>
<p>तैयार लिस्ट चाहिए? हर एक में आपके दिनों के हिसाब से गिनती है, और पैक करते समय आप टिक कर सकते हैं।</p>
<ul>{ready}</ul></section>
{faq_html}
{H.tool_links(B, PACK_PATH, "../")}
<p class="checked">{H.HI_DISCLOSURE}</p>
</div>
</article></div>
<script type="application/json" id="pm-data">{blob}</script>
<script src="../assets/pack-maker.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    schema = [B.tool_article(cfg, seo, desc, PACK_PATH, PUBLISHED, max(PUBLISHED, P.UPDATED), "hi-IN"),
              B.crumbs_schema(cfg, [("होम", ""), ("पैकिंग लिस्ट मेकर", PACK_PATH)]), faq_schema,
              {"@context": "https://schema.org", "@type": "WebApplication", "name": "पैकिंग लिस्ट मेकर", "url": B.abs_url(cfg, PACK_PATH),
               "applicationCategory": "TravelApplication", "operatingSystem": "Any", "description": desc, "inLanguage": "hi-IN"}]
    pages.append(B.write(PACK_PATH, B.page(cfg, H.nfc(seo), H.nfc(desc), H.nfc(body), 1, PACK_PATH, schema, og_type="article", lang="hi", photo="packed-suitcase")))
    lastmod[PACK_PATH] = max(PUBLISHED, P.UPDATED)


# ---------- gift finder ----------

def build_gift(B, cfg, deals_by_asin, pages, lastmod):
    import gift_finder as G
    import urllib.parse
    hw = json.loads(GIFT_WORDS.read_text(encoding="utf-8"))
    data = json.loads(GIFT_FILE.read_text(encoding="utf-8"))
    if G.UPDATED != hw["matched"]:
        H.warn("%s was written from the gift finder of %s, but scripts/gift_finder.py says %s. Update data/hindi_gift.json." % (GIFT_PATH, hw["matched"], G.UPDATED))
    G.check(B, data, deals_by_asin)
    deal = deals_by_asin
    todo = set()

    def hi(kind, slug, field, en):
        v = hw["guides"].get(slug) if kind == "guides" else hw[kind].get(slug, {}).get(field)
        if not v:
            todo.add("%s %s" % (kind, slug))
            return en
        return v

    def guide(href, en_label):
        """(path from a Hindi page, Hindi label): the Hindi twin when it has the section, else the English page marked (English)."""
        path, _, anchor = href.partition("#")
        label = hi("guides", href, None, en_label)
        twin = B.HINDI_PAGES.get(path)
        if twin and (B.DOCS / twin).exists() and (not anchor or ('id="%s"' % anchor) in (B.DOCS / twin).read_text(encoding="utf-8")):
            return "../" + twin + ("#" + anchor if anchor else ""), label
        return "../" + href, label + (" (English)" if label != en_label else "")

    gl = lambda rows: [list(guide(h, t)) for h, t in rows]
    who = [dict(w, **{"for": hi("who", w["slug"], "for", w["for"]), "label": hi("who", w["slug"], "label", w["label"])}, guides=gl(w["guides"]))
           for w in data["who"]]
    occ = [dict(o, head=hi("occasions", o["slug"], "head", o["head"]), label=hi("occasions", o["slug"], "label", o["label"]), guides=gl(o["guides"]))
           for o in data["occasions"]]
    sizes = [dict(z, label=hi("sizes", z["slug"], "label", z["label"]), hint=hi("sizes", z["slug"], "hint", z.get("hint", ""))) for z in data["sizes"]]
    payload = {"who": [{k: v for k, v in w.items() if k != "line"} for w in who], "occasions": occ,
               "pairs": {k: dict(p, guides=gl(p.get("guides", []))) for k, p in data["pairs"].items()},
               "sizes": sizes, "size_of": data["size_of"], "show": G.SHOW, "t": GIFT_TW}
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pool = "".join(B.card(cfg, deal[a], "../").replace('<article class="card"', '<article class="card" data-asin="%s"' % a, 1) for a in data["size_of"])
    opts = lambda rows, q: "".join(f'<button type="button" class="gf-opt" data-q="{q}" data-v="{r["slug"]}">{e(r["label"])}'
                                   + (f'<small>{e(r["hint"])}</small>' if r.get("hint") else "") + "</button>" for r in rows)
    url = B.abs_url(cfg, GIFT_PATH)
    wa = "https://wa.me/?text=" + urllib.parse.quote(url, safe="")
    rows = []
    for w in who:
        orig = next(x for x in data["who"] if x["slug"] == w["slug"])
        links = " &middot; ".join(f'<a href="{e(h)}">{e(t)}</a>' for h, t in w["guides"])
        picks = ", ".join(f'<a href="../picks/{a}.html">{e(deal[a]["title"])}</a>' for a in orig["picks"][:G.NOJS_PICKS])
        rows.append(f"""<div class="gf-row" id="for-{w["slug"]}"><h3>{e(w["for"])}{" (सीक्रेट सैंटा)" if w.get("occasion") == "secret-santa" else ""}</h3>
<p>{e(hi("who", w["slug"], "line", orig["line"]))}</p>
<p><strong>पढ़ें:</strong> {links}</p>
<p class="small"><strong>टॉप पिक्स:</strong> {picks}</p></div>""")
    top = ["B0C3LRF94X", "B0F13ZFVVX", "B00NIWHQVI", "B018VZBTLY", "B08LKXV22C", "B0BS3M2XQV"]
    top_grid = "".join(B.card(cfg, deal[a], "../") for a in top if a in deal)
    title = "गिफ़्ट फ़ाइंडर क्विज़: कौन सा तोहफ़ा दें?"
    seo = "गिफ़्ट फ़ाइंडर क्विज़: पुरुष, महिला, बच्चों, बॉस और सहकर्मियों के लिए गिफ़्ट आइडिया"
    desc = ("मुफ़्त गिफ़्ट फ़ाइंडर क्विज़: चुनें कि तोहफ़ा किसके लिए है (सहकर्मी, बॉस, पत्नी, पति, बच्चे, मम्मी-पापा, घूमने वाला दोस्त या सीक्रेट सैंटा) "
            "और मौक़ा क्या है, फिर क्रिसमस, फ़ेयरवेल, नए साल, शादी और जन्मदिन के गिफ़्ट आइडिया देखें।")
    head = H.head(B, [(None, "गिफ़्ट फ़ाइंडर")], title, "मुफ़्त टूल · 2 या 3 आसान सवालों के जवाब दें · %s को अपडेट किया गया" % B.hi_date(G.UPDATED),
                  "watches", B.icon("gift", "icon media-icon"), "../", "Gift kya de? Kisko gift dena hai aur kab, bataiye, gift ideas mil jayenge.")
    faq = [
        ("पुरुषों के लिए क्रिसमस का अच्छा गिफ़्ट क्या है?",
         "एक घड़ी जो वह रोज़ पहने, जैसे Timex Classics या Titan Classique, WildHorn का चमड़े का वॉलेट गिफ़्ट सेट, या स्लिंग बैग। घूमने वाले आदमी के लिए वीकेंडर डफ़ल या टॉयलेटरी बैग।"),
        ("महिलाओं के लिए अच्छे गिफ़्ट आइडिया क्या हैं?",
         "Titan Raga जैसी ड्रेसी घड़ी, Zouk या Lavie का स्लिंग या टोट बैग, या ज़िप-अराउंड वॉलेट। घूमने वाली महिला के लिए हल्का क्रॉसबॉडी बैग या पैकिंग क्यूब्स।"),
        ("सहकर्मियों के लिए सीक्रेट सैंटा का अच्छा गिफ़्ट क्या है?",
         "ऐसी चीज़ जो ऑफ़िस में कोई भी इस्तेमाल कर सके: Milton की स्टील की बोतल, केबल और चार्जर ऑर्गनाइज़र, पुरुषों के लिए वॉलेट और पेन का सेट, या महिलाओं के लिए ज़िप-अराउंड वॉलेट। मज़ाक़ वाली या बहुत निजी चीज़ें न दें।"),
        ("सहकर्मी को फ़ेयरवेल में क्या गिफ़्ट दें?",
         "वॉलेट गिफ़्ट सेट, विदेश जा रहे व्यक्ति के लिए पासपोर्ट होल्डर, या नई नौकरी के लिए लैपटॉप बैकपैक। बॉस या सीनियर सहकर्मी के लिए Titan जैसी घड़ी, टीम की तरफ़ से।"),
        ("मम्मी-पापा को क्या गिफ़्ट दें?", "Titan Bandhan या Sonata Bandhan जैसी जोड़ी वाली घड़ियाँ, सर्दी के लिए गर्म थर्मल सेट, या पापा के लिए चलने के आरामदायक जूते।"),
        ("शादी में क्या गिफ़्ट दें?",
         "ऐसी चीज़ जो जोड़ा साथ में इस्तेमाल करे: कपल घड़ी सेट, नए घर के लिए 3 ट्रॉली बैग का सेट, या हनीमून के लिए केबिन ट्रॉली और वीकेंडर बैग। अगर जोड़े ने अपनी लिस्ट दी हो तो पहले उसे देखें।"),
        ("छोटा तोहफ़ा, अच्छा तोहफ़ा और बड़ा तोहफ़ा का क्या मतलब है?",
         "ये बताते हैं कि आप कितना बड़ा तोहफ़ा देना चाहते हैं, क़ीमत नहीं। छोटा तोहफ़ा डेस्क का तोहफ़ा या सीक्रेट सैंटा है, अच्छा तोहफ़ा दोस्त या परिवार के लिए है, और बड़ा तोहफ़ा पार्टनर, मम्मी-पापा या पूरी टीम की तरफ़ से। हम क़ीमतें नहीं दिखाते: Amazon.in पर देखें।"),
    ]
    faq_html, faq_schema = H.faq_html(B, faq)
    body = f"""{head}
<div class="wrap"><article class="guide">
<p class="pm-nojs" id="gf-nojs">झटपट क्विज़ के लिए JavaScript चालू करें, या नीचे व्यक्ति चुनकर हमारी गिफ़्ट गाइड और टॉप पिक्स देखें।</p>
<section class="checker gf" id="gf" hidden>
<p class="gf-step muted small" id="gf-step">सवाल 1 / 3</p>
<fieldset class="gf-q" id="gf-q-who"><legend>तोहफ़ा किसके लिए है?</legend><div class="gf-opts">{opts(who, "who")}</div></fieldset>
<fieldset class="gf-q" id="gf-q-occ" hidden><legend>मौक़ा क्या है?</legend><div class="gf-opts">{opts(occ, "occ")}</div></fieldset>
<fieldset class="gf-q" id="gf-q-size" hidden><legend>कितना बड़ा तोहफ़ा? <span class="muted">ज़रूरी नहीं</span></legend><div class="gf-opts gf-opts-1">{opts(sizes, "size")}
<button type="button" class="gf-opt gf-skip" data-q="size" data-v="">छोड़ें: सब दिखाएँ</button></div></fieldset>
<p class="gf-nav" id="gf-nav" hidden><button type="button" class="link-btn" id="gf-back">&larr; पीछे</button></p>
</section>
<section id="gf-result" hidden>
<h2 id="gf-title" tabindex="-1">गिफ़्ट आइडिया</h2>
<p class="muted small"><span id="gf-answers"></span> &middot; <button type="button" class="link-btn" id="gf-change">जवाब बदलें</button></p>
<p class="hint" id="gf-note" hidden></p>
<div class="grid" id="gf-grid" aria-live="polite"></div>
<div class="next-step gf-guides"><h2>पूरी गाइड पढ़ें</h2><ul id="gf-guides"></ul></div>
<p class="pm-actions"><button type="button" class="btn pm-btn2" id="gf-again">फिर से शुरू करें</button> <a class="btn btn-whatsapp" href="{e(wa)}" target="_blank" rel="noopener">WhatsApp पर भेजें</a></p>
</section>
<template id="gf-pool">{pool}</template>
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li><strong>समझ नहीं आ रहा क्या दें?</strong> घड़ी, अच्छा बैग या काम का ट्रैवल गियर ज़्यादातर लोगों को पसंद आता है और रोज़ इस्तेमाल होता है।</li>
<li>सहकर्मी या सीक्रेट सैंटा के लिए चीज़ काम की रखें, निजी नहीं: स्टील की बोतल, वॉलेट सेट या केबल ऑर्गनाइज़र।</li>
<li>बॉस के लिए पूरी टीम की तरफ़ से एक बड़ा तोहफ़ा दें। मम्मी-पापा के लिए जोड़ी वाली घड़ी।</li>
</ul></div>
<h2 id="by-person">व्यक्ति के हिसाब से गिफ़्ट आइडिया</h2>
{"".join(rows)}
<h2>सबसे ज़्यादा दिए जाने वाले हमारे गिफ़्ट पिक्स</h2>
<div class="grid">{top_grid}</div>
{faq_html}
{H.tool_links(B, GIFT_PATH, "../")}
<p class="checked">{H.HI_DISCLOSURE}</p>
</article></div>
<script type="application/json" id="gf-data">{blob}</script>
<script src="../assets/gift-finder.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    if todo:
        H.warn("%s has no Hindi for: %s (English shown for now). Add it to data/hindi_gift.json." % (GIFT_PATH, ", ".join(sorted(todo))))
    schema = [B.tool_article(cfg, seo, desc, GIFT_PATH, PUBLISHED, max(PUBLISHED, G.UPDATED), "hi-IN"),
              B.crumbs_schema(cfg, [("होम", ""), ("गिफ़्ट फ़ाइंडर", GIFT_PATH)]), faq_schema,
              {"@context": "https://schema.org", "@type": "WebApplication", "name": "गिफ़्ट फ़ाइंडर क्विज़", "url": url,
               "applicationCategory": "LifestyleApplication", "operatingSystem": "Any", "description": desc, "inLanguage": "hi-IN"}]
    pages.append(B.write(GIFT_PATH, B.page(cfg, H.nfc(seo), H.nfc(desc), H.nfc(body), 1, GIFT_PATH, schema, og_type="article", lang="hi", photo="gift-box")))
    lastmod[GIFT_PATH] = max(PUBLISHED, G.UPDATED)


# ---------- clothing size ----------

def build_clothing(B, cfg, deals, pages, lastmod):
    import clothing_size as C
    hw = json.loads(CLOTH_WORDS.read_text(encoding="utf-8"))
    data = json.loads(CLOTH_FILE.read_text(encoding="utf-8"))
    if C.UPDATED != hw["matched"] or data["checked"] != hw["matched"]:
        H.warn("%s was written from the clothing charts of %s, but clothing_size.py says %s and the data was checked %s. Update the Hindi page."
               % (CLOTH_PATH, hw["matched"], C.UPDATED, data["checked"]))
    charts = {c["id"]: c for c in data["charts"]}
    sources = {x["id"]: x for x in data["sources"]}
    todo = set()

    def w(kind, key, en):
        v = hw[kind].get(key)
        if not v:
            todo.add("%s %s" % (kind, key))
            return en
        return v

    num = B.num
    msr = lambda m: w("measures", m, m)
    colname = lambda c: w("cols", c, c)
    years = lambda t: t.replace(" years", " साल")

    def row(cid, size):
        return next(r for r in charts[cid]["rows"] if r["size"] == size)

    def cm(cid, size, m):
        lo, hi = C.span(row(cid, size)[m])
        return num(lo) + ("" if lo == hi else "–" + num(hi)) + " cm"

    def table(chart):
        title = w("charts", chart["id"], chart["title"])
        head = w("size_heads", chart["size_head"], chart["size_head"])
        heads = "".join("<th>%s</th>" % e(msr(m)) for m in chart["measures"]) + "".join('<th class="x">%s</th>' % e(colname(c)) for c in chart["cols"])
        rows = []
        for r in chart["rows"]:
            attrs = "".join(' data-m-%s="%s,%s"' % (m, round(C.to_cm(chart, C.span(r[m])[0]), 2), round(C.to_cm(chart, C.span(r[m])[1]), 2))
                            for m in chart["measures"] if C.span(r.get(m)))
            tds = "".join("<td>%s</td>" % C.cell(B, chart, r.get(m)) for m in chart["measures"])
            tds += "".join('<td class="x">%s</td>' % e(r.get(c) or "–") for c in chart["cols"])
            rows.append(f'<tr{attrs}><th scope="row">{e(years(r["size"]))}</th>{tds}</tr>')
        src = sources[chart["source"]]
        note = ""
        if chart.get("cols_source"):
            cs = sources[chart["cols_source"]]
            note = (f' US और EU साइज <a href="{e(cs["url"])}" target="_blank" rel="noopener" lang="en">{e(cs["label"])}</a> से हैं, जो उन्हें जोड़ों में देता है।')
        say = ""
        if chart.get("say"):
            t = chart["say"].replace("collar ", "कॉलर ")
            for c in chart["cols"]:
                t = t.replace("{%s}" % c, "{%s}" % colname(c))
            say = f' data-say="{e(t)}"'
        unit_note = "इंच cm से निकाले गए हैं।" if chart["unit"] == "cm" else "Libas इंच देता है; cm निकाले गए हैं।"
        return f"""<h3 id="chart-{chart["id"]}">{e(title)}</h3>
<div class="table-wrap"><table class="compare cs-table" id="cs-t-{chart["id"]}" data-chart="{chart["id"]}" data-title="{e(title)}" data-head="{e(head)}"{say}>
<thead><tr><th>{e(head)}</th>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<p class="hint small">शरीर का नाप, <a href="{e(chart["url"])}" target="_blank" rel="noopener" lang="en">{e(src["brand"])} की साइज गाइड</a> से।{note} {unit_note}</p>"""

    uk10, uk12 = row("ms-women-tops", "UK 10"), row("ms-women-tops", "UK 12")
    f38, lib_m = row("ms-men-formal", "38"), row("libas-kurta", "M")
    lev32 = row("levis-men-jeans", "32")
    w28, w30 = row("only-women-jeans", "28"), row("only-women-jeans", "30")
    m_trousers = next(r for r in charts["ms-men-trousers"]["rows"] if C.span(r["waist"])[0] <= lev32["waist"] <= C.span(r["waist"])[1])
    boy5 = row("ms-boys", "5–6 years")

    tables = []
    for who, _ in C.WHO:
        seen, parts = set(), []
        for g in [g for g in data["garments"] if g["who"] == who]:
            for cid in g["charts"]:
                if cid not in seen:
                    seen.add(cid)
                    parts.append(table(charts[cid]))
        tables.append(f'<h2 id="{who}">{e(w("who_head", who, who))}</h2>' + "".join(parts))
    garments_js = json.dumps([{"slug": g["slug"], "who": g["who"], "label": w("garments", g["slug"], g["label"]), "measures": g["measures"], "charts": g["charts"]}
                              for g in data["garments"]], ensure_ascii=False, separators=(",", ":"))
    who_opts = "".join(f'<option value="{k}">{e(w("who", k, k))}</option>' for k, _ in C.WHO)
    inputs = "".join(f'<label data-m="{m}" hidden>{e(msr(m))}<input id="cs-{m}" type="number" min="1" max="250" step="0.5" inputmode="decimal" placeholder="जैसे {ph}"></label>'
                     for m, ph in (("chest", "96"), ("bust", "88"), ("waist", "80"), ("hips", "98"), ("height", "116")))
    clothes = [d for d in deals if d["category"] == "clothing"]
    cards = "".join(B.card(cfg, d, "../").replace('<article class="card"', '<article class="card" data-for="%s"' % e(
        d.get("specs", {}).get("For", "").lower()), 1) for d in clothes)
    picks_html = (f"""<h2 id="picks">ट्रिप के लिए हमारे चुने कपड़े</h2>
<p id="cs-picks-note">पुरुषों और महिलाओं के लिए थर्मल, जैकेट और रेनवियर, और बच्चों के लिए कुछ पिक्स। हर Amazon पेज पर ब्रांड का अपना साइज चार्ट है: ऑर्डर से पहले ज़रूर देखें।</p>
<div class="grid" id="cs-picks">{cards}</div>""" if clothes else "")
    checked = B.hi_date(data["checked"])
    src_links = ", ".join(f'<a href="{e(x["url"])}" target="_blank" rel="noopener" lang="en">{e(x["label"])}</a>' for x in data["sources"])
    title = "कपड़ों का साइज चार्ट: पुरुष, महिला और बच्चों के लिए UK, US और EU से भारतीय साइज"
    seo = "कपड़ों का साइज चार्ट (भारत): UK, US, EU से भारतीय साइज, पुरुष, महिला, बच्चे"
    desc = ("कपड़ों का साइज कन्वर्टर। अपनी छाती, बस्ट, कमर या हिप्स cm या इंच में लिखें, या साइज चुनें, और M&S India, ONLY India, Libas और Levi's India के चार्ट से "
            "पुरुष, महिला और बच्चों के लिए UK, US, EU और अक्षर साइज (XS से XXL) देखें।")
    tw = dict(CLOTH_TW, measures={m: hw["measures"].get(m, m) for m in ("chest", "bust", "waist", "hips", "height")})
    body = f"""{_head(B, "कपड़ों का साइज", title, "मुफ़्त टूल · %s को जाँचा गया" % checked, "clothing", "jacket",
                     "Size chart in Hindi: kapde ka size cm ya inch mein napiye aur UK, US, EU, S M L size dekhiye.")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>सीधा जवाब</h2><ul>
<li><strong>भारत में कोई एक साइज सिस्टम नहीं है।</strong> Marks &amp; Spencer India जैसे स्टोर UK साइज बेचते हैं, और भारतीय ब्रांड अक्षर (S, M, L) और इंच (38 का कुर्ता, 32 की जीन्स) इस्तेमाल करते हैं।</li>
<li>M&amp;S के चार्ट में महिलाओं का UK {uk10["size"][3:]} {cm("ms-women-tops", "UK 10", "bust")} के बस्ट पर फ़िट होता है। यह साइज {uk10["Letter"]} है, और M&amp;S इसे US {uk10["US"]} और EU {uk10["EU"]} के साथ लिखता है।</li>
<li>अक्षर की जगह अपने शरीर का नाप cm या इंच में देखें। साइज ब्रांड के हिसाब से बदलते हैं, इसलिए ब्रांड का अपना चार्ट भी देखें।</li>
</ul></div>
<h2>पहला क़दम: अपना नाप लें</h2>
<ol>
<li><strong>छाती या बस्ट:</strong> पतला टॉप पहनें, और फ़ीता सबसे चौड़े हिस्से पर, बाँहों के नीचे से घुमाएँ। पीठ पर फ़ीता सीधा रखें।</li>
<li><strong>कमर:</strong> शरीर के सबसे पतले हिस्से पर, आमतौर पर नाभि के थोड़ा ऊपर। आराम से साँस छोड़ें; पेट अंदर न खींचें।</li>
<li><strong>हिप्स:</strong> पैर साथ रखकर खड़े हों और फ़ीता कूल्हों के सबसे चौड़े हिस्से पर घुमाएँ।</li>
<li><strong>बच्चे:</strong> बिना जूतों के दीवार से सटकर ऊँचाई नापें, और छाती सबसे चौड़े हिस्से पर।</li>
<li>फ़ीता कसा हुआ नहीं, बस ठीक से लगा रखें। फ़ीता नहीं है? धागा लें, फिर उसे स्केल पर रखकर नापें।</li>
</ol>
<h2>दूसरा क़दम: अपना साइज ढूँढें</h2>
<form class="checker" id="cs" onsubmit="return false" data-garments='{e(garments_js)}' hidden data-js>
<div class="checker-fields"><label>कपड़े किसके लिए<select id="cs-who">{who_opts}</select></label>
<label>क्या<select id="cs-garment"></select></label>
<label>इकाई<select id="cs-unit"><option value="cm">cm</option><option value="in">इंच</option></select></label>
{inputs}
<label>या, जो साइज पता है<select id="cs-size"><option value="">चुनें…</option></select></label></div>
<p class="checker-total" id="cs-out" aria-live="polite">{CLOTH_TW["prompt"]}</p>
<div id="cs-result" hidden>
<ul id="cs-r-list"></ul>
<p class="hint" id="cs-r-note"></p>
<p id="cs-r-links"><a href="#picks">हमारे चुने कपड़े देखें</a> &middot; <a href="../category/clothing.html" lang="en">All clothing and winter wear (English)</a> &middot; <a href="shoe-size.html">जूते का साइज कन्वर्टर</a></p>
</div>
</form>
<noscript><p>JavaScript बंद हो तो भी नीचे के चार्ट में अपना नाप देख सकते हैं।</p></noscript>
<h2>साइज चार्ट</h2>
<p>नीचे के सारे चार्ट शरीर के नाप के हैं: यानी उस छाती, कमर या हिप्स वाले शरीर पर जो साइज फ़िट होता है। हर चार्ट में उसी ब्रांड के अपने नंबर हैं, और हम हर चार्ट पर ब्रांड का नाम लिखते हैं। जहाँ ब्रांड अलग हैं, वहाँ हम दोनों दिखाते हैं।</p>
{"".join(tables)}
<p class="checked">{checked} को जाँचा, {src_links} पर। साइज ब्रांड और फ़िट (स्लिम, रेगुलर, रिलैक्स्ड) के हिसाब से बदलते हैं, इसलिए प्रोडक्ट पेज का साइज चार्ट ही भरोसे लायक़ है।</p>
<h2>महिलाओं के UK, US और EU साइज</h2>
<p>M&amp;S की अपनी तालिका UK, US और EU साइज जोड़ों में देती है: UK 8–10 यानी US 4–6 और EU 36–38 (Small), और UK 12–14 यानी US 8–10 और EU 40–42 (Medium)। UK 26 तक M&amp;S का US नंबर UK से 4 कम और EU नंबर 28 ज़्यादा होता है। दूसरे ब्रांड अलग हो सकते हैं, और M&amp;S पैंट के लिए US या EU साइज नहीं देता।</p>
<h2>महिलाओं की जीन्स के साइज 26, 28, 30, 32</h2>
<p>भारत में महिलाओं की जीन्स अक्सर नंबर से बिकती है। ONLY India के चार्ट में साइज {w28["size"]} की जीन्स {w28["Letter"]}, UK {w28["UK"]} और US {w28["US"]} है, {num(w28["waist"])} cm की कमर और {num(w28["hips"])} cm के हिप्स के लिए। साइज {w30["size"]} {w30["Letter"]} (UK {w30["UK"]}, US {w30["US"]}) है, {num(w30["waist"])} cm की कमर और {num(w30["hips"])} cm के हिप्स के लिए। ONLY हर जोड़ी के साइज को एक ही नंबर देता है (25 और 26, 27 और 28, वग़ैरह), इसलिए जोड़ी का कोई भी साइज उसी शरीर पर फ़िट होता है। ONLY के प्रोडक्ट पेज पर Size Details में हर साइज के कपड़े का अपना नाप भी होता है।</p>
<p>ब्रांड अलग होते हैं: ONLY की UK 10 जीन्स {cm("only-women-jeans", "30", "waist")} की कमर के लिए है, पर M&amp;S की UK 10 पैंट {cm("ms-women-bottoms", "UK 10", "waist")} की कमर के लिए। जिस ब्रांड का ख़रीद रहे हैं उसी का चार्ट देखें।</p>
<h2>पुरुषों की शर्ट के साइज 38, 39, 40, 42</h2>
<p>फ़ॉर्मल शर्ट भारत में अक्सर cm में कॉलर साइज से बिकती हैं। M&amp;S India के चार्ट में {f38["size"]} का कॉलर {f38["Letter"]} है, {cm("ms-men-formal", "38", "chest")} की छाती के साथ, और 42 का कॉलर L है। टी-शर्ट और कैज़ुअल शर्ट अक्षर से बिकती हैं: M&amp;S के चार्ट में M {cm("ms-men-tops", "M", "chest")} की छाती पर फ़िट होता है।</p>
<p>बच्चों के कपड़े उम्र से बिकते हैं, पर एक उम्र के बच्चे काफ़ी अलग होते हैं। पहले ऊँचाई देखें: अगर बच्चा दो साइज के बीच में है, तो बड़ा साइज लें।</p>
{picks_html}
<p>और मदद: हमारा <a href="shoe-size.html">जूते का साइज कन्वर्टर</a> (India/UK, US, EU और cm), <a href="../guides/winter-clothes-for-hill-trips.html" lang="en">winter clothes for hill trips (English)</a> और <a href="../category/clothing.html" lang="en">all our clothing picks (English)</a>।</p>
{{faq}}
""" + _tail(B, cfg, CLOTH_PATH, "clothing-size.js", "cs-t", tw)
    faq = [
        ("क्या 38 साइज की शर्ट M होती है या L?",
         "Marks & Spencer India की फ़ॉर्मल शर्ट के चार्ट में 38 का कॉलर %s है, %s की छाती के लिए। 41 या 42 का कॉलर L है। भारतीय ब्रांड भी यही कॉलर नंबर इस्तेमाल करते हैं, पर अक्षर अलग हो सकता है, इसलिए ब्रांड का चार्ट देखें।"
         % (f38["Letter"], cm("ms-men-formal", "38", "chest"))),
        ("पुरुषों के लिए XL साइज नंबर में कितना होता है?",
         "M&S India के चार्ट में XL शर्ट या टी-शर्ट %s की छाती पर (लगभग 44–46 इंच) और XL पैंट %s की कमर पर (लगभग 39–41 इंच) फ़िट होती है।"
         % (cm("ms-men-tops", "XL", "chest"), cm("ms-men-trousers", "XL", "waist"))),
        ("क्या 32 साइज की जीन्स L होती है या XL?",
         "आमतौर पर दोनों नहीं। Levi's India के 511 चार्ट में साइज 32 %s cm की कमर (लगभग 33.5 इंच) के लिए है। M&S India के पैंट चार्ट में वह कमर %s (%s) है।"
         % (num(lev32["waist"]), m_trousers["size"], cm("ms-men-trousers", m_trousers["size"], "waist"))),
        ("कपड़ों में UK साइज को भारतीय साइज में कैसे बदलें?",
         "भारत में कई स्टोर, जैसे Marks & Spencer India, कपड़े UK साइज में बेचते हैं, इसलिए UK 12 यहाँ भी वही साइज है। M&S के चार्ट में महिलाओं का UK 12 Medium है, %s के बस्ट के लिए।"
         % cm("ms-women-tops", "UK 12", "bust")),
        ("महिलाओं की 28 साइज की जीन्स क्या होती है?",
         "ONLY India के चार्ट में साइज 28 की जीन्स %s, UK %s और US %s है, %s cm की कमर (लगभग %s इंच) और %s cm के हिप्स के लिए।"
         % (w28["Letter"], w28["UK"], w28["US"], num(w28["waist"]), num(C.half(w28["waist"] / 2.54)), num(w28["hips"]))),
        ("महिलाओं की साइज 30 जीन्स का US और UK साइज क्या है?",
         "ONLY India के चार्ट में साइज 30 UK %s और US %s (%s) है, %s cm की कमर और %s cm के हिप्स के लिए।"
         % (w30["UK"], w30["US"], w30["Letter"], num(w30["waist"]), num(w30["hips"]))),
        ("महिलाओं के कपड़ों में US साइज से भारतीय साइज क्या होता है?",
         "M&S की तालिका में US 4–6 यानी UK 8–10 और EU 36–38 (Small), और US 8–10 यानी UK 12–14 और EU 40–42 (Medium)। भारत में साइज आमतौर पर UK साइज या अक्षर में लिखे होते हैं।"),
        ("कुर्ती साइज 38 का क्या मतलब है?",
         "Libas के कुर्ता चार्ट में 38 इंच में बस्ट का नाप है: साइज %s %s इंच के बस्ट, %s इंच की कमर और %s इंच के हिप्स पर फ़िट होता है।" % (lib_m["size"], lib_m["bust"], lib_m["waist"], lib_m["hips"])),
        ("भारत में 5 साल के बच्चे का साइज क्या होता है?",
         "M&S India के लड़कों के चार्ट में 5–6 साल %s cm की ऊँचाई और %s cm की छाती के लिए है। बच्चे की ऊँचाई नापें, क्योंकि एक उम्र के बच्चे काफ़ी अलग होते हैं।"
         % (num(boy5["height"]), num(boy5["chest"]))),
        ("छाती, कमर और हिप्स कैसे नापें?",
         "मुलायम फ़ीता लें। छाती या बस्ट: सबसे चौड़े हिस्से पर, बाँहों के नीचे से। कमर: सबसे पतले हिस्से पर, नाभि के ऊपर। हिप्स: कूल्हों के सबसे चौड़े हिस्से पर, पैर साथ रखकर। फ़ीता सीधा और ठीक से लगा हो, कसा हुआ नहीं।"),
    ]
    if todo:
        H.warn("%s has no Hindi for: %s (English shown for now). Add it to data/hindi_clothing.json." % (CLOTH_PATH, ", ".join(sorted(todo))))
    _finish(B, cfg, pages, lastmod, CLOTH_PATH, seo, desc, "कपड़ों का साइज", body, faq, data["checked"])
