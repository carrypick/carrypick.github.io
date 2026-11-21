"""Hindi twin of the what-to-wear helper: hi/what-to-wear.html.

Built by what_to_wear.build() from the same results (cases) and pick cards as the English page, with the Hindi words in
data/hindi_what_to_wear.json (months, bands, items with their women/men wording, and a 'text' map from each English note,
snow line and place name to Hindi). Same static/what-to-wear.js; its words come from "t" in #ww-data.
hindi_tools.register() calls register() so the language menu, hreflang and the Hindi tool pills know the page.
A missing Hindi word shows the English and prints a warning; an old 'matched' date prints a warning too.
"""
import json
from html import escape as e

import hindi_pages as H
from common import ROOT

WORDS = ROOT / "data" / "hindi_what_to_wear.json"
EN, PATH = "tools/what-to-wear.html", "hi/what-to-wear.html"
PUBLISHED = "2026-11-21"
NAME = "क्या पहनें: मौसम के हिसाब से कपड़े"
HEADS = {"By day": "दिन में", "Evenings and nights": "शाम और रात", "Shoes": "जूते", "Also pack": "ये भी रखें"}
WHO_HI = {"all": "सबके लिए", "women": "महिलाएँ", "men": "पुरुष"}
PACK_HI = {"packing/hills.html": "सर्दियों की हिल ट्रिप पैकिंग लिस्ट", "packing/beach.html": "बीच ट्रिप पैकिंग लिस्ट",
           "packing/weekend.html": "वीकेंड ट्रिप पैकिंग लिस्ट", "packing/index.html": "पैकिंग चेकलिस्ट",
           "packing/abroad.html": "विदेश ट्रिप पैकिंग लिस्ट"}


def register(B, tools_hi, pairs):
    if WORDS.exists() and (ROOT / "data" / "what_to_wear.json").exists():
        B.HINDI_PAGES[EN] = PATH
        pairs[EN] = PATH
        tools_hi.append((PATH, "क्या पहनें हेल्पर"))


def build(B, cfg, pages, lastmod, data, cases, months_of, pool, W):
    """W is the what_to_wear module (temp, lo, summary helpers)."""
    if B.HINDI_PAGES.get(EN) != PATH:
        return
    import hindi_tools
    hw = json.loads(WORDS.read_text(encoding="utf-8"))
    if hw["matched"] < data["updated"]:
        H.warn("%s was written from the what-to-wear data of %s, but data/what_to_wear.json says %s. Update data/hindi_what_to_wear.json."
               % (PATH, hw["matched"], data["updated"]))
    todo = set()

    def tx(en):
        if not en:
            return ""
        if en not in hw["text"]:
            todo.add(en)
            return en
        return hw["text"][en]

    def item(i, field="label", who=None):
        h = hw["items"].get(i)
        if not h:
            todo.add("item " + i)
            it = data["items"][i]
            return it.get("for", {}).get(who, it[field]) if who else it[field]
        return h.get("for", {}).get(who, h[field]) if who else h[field]

    mname = hw["months"]
    places = {p["slug"]: p for p in data["places"]}
    temp = W.temp

    def li(i):
        if not data["items"][i].get("for"):
            return f"<li>{e(item(i))}</li>"
        alt = "".join(f'<span data-for="{w}" hidden>{e(item(i, who=w))}</span>' for w in ("women", "men"))
        return f'<li><span data-for="all">{e(item(i))}</span>{alt}</li>'

    def weather_lines(p, o):
        lines = []
        for name, r in o["rows"]:
            if r.get("rain_mm") is not None:
                rain = "बारिश लगभग %s mm" % B.num(r["rain_mm"])
            else:
                rain = ("बारिश: " + tx(r["rain_text"])) if r.get("rain_text") else ""
            if r.get("range"):
                t = "रात में लगभग %s से दिन में %s तक" % (temp(r["night"]), temp(r["day"]))
            else:
                t = "दिन में लगभग %s, रात में लगभग %s" % (temp(r["day"]), temp(r["night"]))
            lead = "" if len(o["rows"]) == 1 and name == p["name"] else "<strong>%s:</strong> " % e(tx(name))
            lines.append("<li>%s%s%s</li>" % (lead, t, ("; " + e(rain)) if rain else ""))
        return "".join(lines)

    def links(p):
        out = []

        def add(href, label):
            if (B.DOCS / href.split("#")[0]).exists():
                out.append(hindi_tools.hi_link(B, href, label))
        if p.get("guide"):
            add(p["guide"], "%s ट्रिप गाइड" % tx(p["name"]))
        if p.get("packing"):
            add(p["packing"], PACK_HI.get(p["packing"], "%s पैकिंग लिस्ट" % tx(p["name"])))
        for h, t in p.get("more", []):
            add(h, tx(t))
        add("tools/packing-list-maker.html", "अपनी पैकिंग लिस्ट बनाएँ")
        return " &middot; ".join(f'<a href="{e(h)}">{e(t)}</a>' for h, t in out)

    def src_line(o):
        return "; ".join((f'<a href="{e(s["url"])}" target="_blank" rel="noopener" lang="en">{e(s["label"])}</a>' if s.get("url")
                          else f'<span lang="en">{e(s["label"])}</span>') + ", %s को जाँचे" % B.hi_date(s["checked"]) for s in o["sources"])

    def band_word(b):
        return hw["bands"].get(b["id"], b["label"])

    results, rows_html = [], []
    for slug, ms in months_of.items():
        p = places[slug]
        for n, mon in enumerate(ms):
            o = cases[(slug, mon)]
            key = "%s-%s" % (slug, mon)
            flags = []
            if o["snow"] or o["snow_note"]:
                flags.append("<li><strong>बर्फ़:</strong> %s।</li>" % e(tx(o["snow"] or o["snow_note"])))
            if o["rain"] >= data["rain"]["min_mm"] and not o["snow"]:
                if o["cold"] < 0:
                    flags.append("<li><strong>बारिश या बर्फ़:</strong> महीने में लगभग %s mm तक (बर्फ़ को पानी के रूप में गिना गया), इसलिए गीले और ठंडे दिनों के लिए पैक करें।</li>" % B.num(round(o["rain"])))
                else:
                    flags.append("<li><strong>बारिश:</strong> महीने में लगभग %s mm तक, इसलिए बौछारों के लिए तैयार रहें।</li>" % B.num(round(o["rain"])))
            groups = "".join(f'<h4>{e(HEADS[h])}</h4><ul class="ww-list">' + "".join(li(i) for i in its) + "</ul>" for h, its in o["groups"])
            if o["day_band"] is o["night_band"]:
                bands = "दिन और रात दोनों %s" % e(band_word(o["day_band"]))
            else:
                bands = "दिन में %s, रात में %s" % (e(band_word(o["day_band"])), e(band_word(o["night_band"])))
            if len(o["rows"]) > 1:
                bands += " (सबसे ठंडी रातें: %s)" % e(tx(min(o["rows"], key=lambda nr: W.lo(nr[1]["night"]))[0]))
            note = p.get("notes", {}).get(mon, p["note"])
            results.append(f"""<div class="ww-case" data-case="{key}" data-picks="{" ".join(o["picks"])}" data-picks-women="{" ".join(o["picks_for"]["women"])}" data-picks-men="{" ".join(o["picks_for"]["men"])}">
<h2 class="ww-title" tabindex="-1">{e(mname[mon])} में {e(tx(p["name"]))} में क्या पहनें</h2>
<ul class="ww-weather">{weather_lines(p, o)}{"".join(flags)}</ul>
<p class="muted small">कपड़े इस तापमान के हिसाब से: {bands}।</p>
<div class="ww-groups">{groups}</div>
<p class="pm-notes">{e(tx(note))}</p>
<p class="small"><strong>ट्रिप की तैयारी:</strong> {links(p)}</p>
<p class="checked">आँकड़े: {src_line(o)}। ये {"आम रेंज" if o["range"] else "लंबे समय के औसत"} हैं, इसलिए जाने से कुछ दिन पहले मौसम का पूर्वानुमान ज़रूर देखें।</p>
</div>""")
            weather = "<br>".join(f'{e(tx(nm)) + ": " if len(o["rows"]) > 1 else ""}{temp(r["day"])} / {temp(r["night"])}' for nm, r in o["rows"])
            texts = [r.get("rain_text", "") for _, r in o["rows"] if r.get("rain_text")]
            known = any(r.get("rain_mm") is not None for _, r in o["rows"])
            wet = ("बर्फ़ हो सकती है" if o["snow"] else "बारिश की संभावना" if o["rain"] >= data["rain"]["min_mm"]
                   else "कुछ बौछारें" if any("shower" in t.lower() for t in texts) else "ज़्यादातर सूखा" if known or texts else "–")
            wear = "; ".join(", ".join(item(i, "short") for i in its) for _, its in o["groups"])
            first = f'<th rowspan="{len(ms)}" id="{slug}">{e(tx(p["name"]))}</th>' if n == 0 else ""
            rows_html.append(f"<tr>{first}<td>{e(mname[mon])}</td><td>{weather}</td><td>{wet}</td><td>{e(wear)}</td></tr>")

    def opt_group(where, label):
        return f'<optgroup label="{label}">' + "".join(
            f'<option value="{p["slug"]}">{e(tx(p["name"]))}</option>' for p in data["places"] if p["where"] == where) + "</optgroup>"

    payload = {"months": mname, "places": {s: {"name": tx(places[s]["name"]), "months": ms} for s, ms in months_of.items()},
               "t": {"more": "अभी हमारे पास इन महीनों के जाँचे हुए आँकड़े हैं: {m}। और महीने जल्द आएँगे।", "sep": ", "}}
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    url = B.abs_url(cfg, PATH)
    wa = "https://wa.me/?text=" + __import__("urllib.parse").parse.quote(url, safe="")

    def say(slug, mon, who="all"):
        p, o = places[slug], cases[(slug, mon)]
        r = o["rows"][0][1]
        if len(o["rows"]) == 1:
            w = (("रात में लगभग %s से दिन में %s तक" % (temp(r["night"]), temp(r["day"]))) if r.get("range")
                 else "दिन में लगभग %s और रात में लगभग %s" % (temp(r["day"]), temp(r["night"])))
        else:
            w = "; ".join("%s में दिन लगभग %s, रात लगभग %s" % (tx(nm), temp(x["day"]), temp(x["night"])) for nm, x in o["rows"][:2])
        wear = "; ".join("%s: %s" % (HEADS[h], ", ".join(item(i, who=who) if (who != "all" and data["items"][i].get("for")) else item(i, "short") for i in its))
                         for h, its in o["groups"])
        return "%s में %s का मौसम: %s। पहनें: %s।" % (mname[mon], tx(p["name"]), w, wear)

    faq = [
        ("अक्टूबर में मनाली में क्या पहनें?", say("manali", "oct") + " अक्टूबर में धूप और सूखा मौसम रहता है, पर रातें ठंडी होती हैं, इसलिए गर्म जैकेट रखें।"),
        ("दिसंबर में मनाली में क्या पहनें?", say("manali", "dec") + " बर्फ़ गिर सकती है पर पक्का नहीं, इसलिए वॉटरप्रूफ़ जूते ले जाएँ।"),
        ("अक्टूबर में कश्मीर में क्या पहनें?", say("kashmir", "oct") + " गुलमर्ग श्रीनगर से काफ़ी ठंडा है।"),
        ("दिसंबर में दुबई में महिलाएँ क्या पहनें?", say("dubai", "dec", "women") + " सार्वजनिक जगहों पर कंधे और पेट ढककर रखें, और स्विमवियर सिर्फ़ बीच और पूल पर पहनें।"),
        ("गोवा में पुरुष क्या पहनें?", say("goa", "dec", "men") + " शहर में जाते समय स्विमवियर के ऊपर शर्ट डालें।"),
        ("कुछ ही महीने क्यों दिखते हैं?", "हम सिर्फ़ वही महीने दिखाते हैं जिनके सरकारी मौसम आँकड़े हमारे पास हैं (भारत के लिए IMD, नेपाल के लिए DHM, दुबई के लिए UAE का मौसम विभाग), ज़्यादातर अक्टूबर से मार्च। हम किसी महीने का मौसम अंदाज़े से नहीं लिखते।"),
    ]
    faq_block, faq_schema = H.faq_html(B, faq)
    all_months = sorted({m for ms in months_of.values() for m in ms}, key=W.month_order(data).index)
    band_rows = "".join(f'<tr><th>{e(band_word(b))}</th><td>{e(", ".join(item(i, "short") for i in b["day"]))}</td>'
                        f'<td>{e(", ".join(item(i, "short") for i in b["night"]))}</td><td>{e(", ".join(item(i, "short") for i in b["shoes"] + b.get("extras", [])))}</td></tr>'
                        for b in data["bands"])
    title = "मनाली, कश्मीर, गोवा, दुबई में क्या पहनें: महीने के हिसाब से"
    seo = "क्या पहनें: मनाली, कश्मीर, गोवा, दुबई, अक्टूबर से मार्च"
    desc = ("मुफ़्त हेल्पर: जगह और महीना चुनें, जैसे अक्टूबर या दिसंबर में मनाली या कश्मीर, गोवा, दुबई या नेपाल, महिलाओं या पुरुषों के लिए, "
            "और दिन-रात का तापमान और कपड़ों की आसान लिस्ट देखें।")
    head = H.head(B, [(None, "क्या पहनें")], title, "%d जगहों के लिए मुफ़्त टूल। अपडेट: %s" % (len(data["places"]), B.hi_date(data["updated"])),
                  "clothing", B.icon("jacket", "icon media-icon"), "../", "Kya pehnein: Manali, Kashmir, Goa, Dubai mein kaunse kapde le jaayein")
    body = f"""{head}
<div class="wrap"><article class="guide">
<p class="small"><a href="../{EN}" lang="en" hreflang="en">Read in English</a></p>
<p class="pm-nojs" id="ww-nojs">झटपट चुनने के लिए JavaScript चालू करें, या नीचे की टेबल में अपनी जगह देखें।</p>
<form class="checker ww" id="ww" onsubmit="return false" hidden>
<div class="checker-fields"><label>कहाँ जा रहे हैं?<select id="ww-place">{opt_group("india", "भारत में")}{opt_group("abroad", "विदेश")}</select></label>
<label>महीना<select id="ww-month"></select></label>
<label>किसके लिए<select id="ww-for">{"".join(f'<option value="{k}">{v}</option>' for k, v in WHO_HI.items())}</select></label></div>
<p class="hint" id="ww-more" aria-live="polite"></p>
</form>
<section id="ww-result" hidden>
<div id="ww-case"></div>
<h3 id="ww-picks-head">इस ट्रिप के लिए हमारी पसंद</h3>
<div class="grid" id="ww-grid"></div>
<p class="pm-actions"><a class="btn btn-whatsapp" id="ww-wa" href="{e(wa)}" target="_blank" rel="noopener">WhatsApp पर भेजें</a></p>
</section>
<template id="ww-cases">{"".join(results)}</template>
<template id="ww-pool">{pool}</template>
<script type="application/json" id="ww-data">{blob}</script>
<div class="answer"><h2>झटपट जवाब</h2><ul>
<li><strong>परतों में कपड़े पहनें।</strong> सर्दियों में दिन और रात के तापमान में 10–17 °C का फ़र्क़ हो सकता है, पहाड़ों में भी और राजस्थान में भी।</li>
<li>रात 5 °C से कम हो तो थर्मल, पफ़र जैकेट, टोपी और दस्ताने रखें। दिन 25 °C से ऊपर हो तो हल्के सूती कपड़े, धूप का चश्मा और सनस्क्रीन रखें।</li>
<li>बर्फ़ या बारिश वाली जगह जा रहे हैं? वॉटरप्रूफ़ जूते, या रेन पोंचो और फ़ोन पाउच जोड़ें।</li>
</ul></div>
<h2 id="table">हर जगह, हर महीने क्या पहनें</h2>
<p>दिन और रात के तापमान हर जगह के मौसम विभाग के लंबे समय के औसत हैं (भारत के लिए IMD, नेपाल के लिए DHM, विदेश में वहाँ के राष्ट्रीय मौसम विभाग); हर नतीजे में स्रोत लिखा है। टेबल सबके लिए है; महिलाओं या पुरुषों के कपड़ों के लिए ऊपर "किसके लिए" चुनें। हम सिर्फ़ इन महीनों के आँकड़े दिखाते हैं: {", ".join(mname[m] for m in all_months)}।</p>
<div class="table-wrap"><table class="compare snug ww-table"><thead><tr><th>जगह</th><th>महीना</th><th>दिन / रात</th><th>बारिश या बर्फ़</th><th>क्या पहनें</th></tr></thead>
<tbody>{"".join(rows_html)}</tbody></table></div>
<h2 id="rules">हम कपड़े कैसे चुनते हैं</h2>
<p>दिन के कपड़े महीने के सबसे गर्म दिन के हिसाब से, और शाम के कपड़े सबसे ठंडी रात के हिसाब से। जहाँ सिर्फ़ रेंज मिलती है (दिसंबर-जनवरी में मनाली), वहाँ दिन के कपड़े बीच के तापमान से। महीने में {data["rain"]["min_mm"]} mm या ज़्यादा बारिश हो तो रेन पोंचो, फ़ोन पाउच और जल्दी सूखने वाले कपड़े जुड़ते हैं, और बर्फ़ की संभावना हो तो वॉटरप्रूफ़ जूते, दस्ताने और धूप का चश्मा।</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>तापमान</th><th>दिन में</th><th>रात में</th><th>जूते और बाक़ी</th></tr></thead>
<tbody>{band_rows}</tbody></table></div>
{faq_block}
{H.tool_links(B, PATH, "../")}
<p class="checked">{H.HI_DISCLOSURE}</p>
</article></div>
<script src="../assets/what-to-wear.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    if todo:
        H.warn("%s has no Hindi for: %s (English shown for now). Add it to data/hindi_what_to_wear.json." % (PATH, "; ".join(sorted(todo))))
    schema = [B.tool_article(cfg, seo, desc, PATH, PUBLISHED, max(PUBLISHED, data["updated"]), "hi-IN"),
              B.crumbs_schema(cfg, [("होम", ""), ("क्या पहनें", PATH)]), faq_schema,
              {"@context": "https://schema.org", "@type": "WebApplication", "name": NAME, "url": url, "inLanguage": "hi-IN",
               "applicationCategory": "TravelApplication", "operatingSystem": "Any", "description": desc}]
    pages.append(B.write(PATH, B.page(cfg, H.nfc(seo), H.nfc(desc), H.nfc(body), 1, PATH, schema, og_type="article", lang="hi", photo="snow-jacket")))
    lastmod[PATH] = max(PUBLISHED, data["updated"])
