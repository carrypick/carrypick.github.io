"""Hindi twin of the visa guide: hi/guides/visa-free-countries-for-indians.html.

Same countries, statuses, sources and checked dates as the English page (data/visa_india.json, built by visa_india.py);
the Hindi words for each country are in data/hindi_visa_words.json. "h" in that file is a short hash of the English
text the Hindi was written from: when someone changes the English row, the build prints a warning (like the other
Hindi pages) so the Hindi is updated at the same time. A row with no Hindi yet shows its English text.
The search box and filter use the same static/visa-india.js, with Hindi words from a JSON block on the page.
"""

import hashlib
import json
import re
from html import escape as e

import hindi_pages as H
import visa_india as V
from common import ROOT

WORDS_FILE = ROOT / "data" / "hindi_visa_words.json"
HI_PATH = "hi/guides/visa-free-countries-for-indians.html"
PUBLISHED = "2026-11-21"
FIELDS = ("name", "status", "stay", "fee", "conditions", "with_visa", "until", "say")
HI_STATUS = {  # key: (label, heading)
    "visa-free": ("वीज़ा-फ़्री", "भारतीयों के लिए वीज़ा-फ़्री देश"),
    "visa-on-arrival": ("वीज़ा ऑन अराइवल", "भारतीय पासपोर्ट वालों के लिए वीज़ा ऑन अराइवल वाले देश"),
    "e-visa": ("ई-वीज़ा", "भारतीयों के लिए ई-वीज़ा वाले देश"),
    "visa-needed": ("वीज़ा ज़रूरी", "जहाँ भारतीयों को यात्रा से पहले वीज़ा चाहिए"),
    "check": ("दूतावास से पूछें", "पक्का नहीं: दूतावास से पूछें"),
}
LINK_WORDS = {"Packing list": "पैकिंग लिस्ट", "December trip guide": "दिसंबर ट्रिप गाइड", "By-road guide": "सड़क से जाने की गाइड",
              "Long weekend guide": "लॉन्ग वीकेंड गाइड", "Trip guide": "ट्रिप गाइड", "What to carry to Dubai": "दुबई में क्या ले जा सकते हैं"}
JS_WORDS = {"all": "सभी {n} देश दिख रहे हैं।", "some": "{n} देश दिख रहे हैं।", "someLabel": "{n} देश दिख रहे हैं ({label})।",
            "none": "कोई देश नहीं मिला। हमारी सूची में अभी {n} मशहूर देश हैं; बाक़ी के लिए भारत में उस देश के दूतावास से पूछें।"}


def digest(c):
    blob = json.dumps({k: c.get(k) for k in FIELDS}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:8]


def register(B, TOOLS_HI):
    if V.DATA_FILE.exists() and WORDS_FILE.exists():
        B.HINDI_PAGES[V.PATH] = HI_PATH
        TOOLS_HI.append((HI_PATH, "भारतीयों के लिए वीज़ा गाइड"))


def _link(B, m):
    href, label = m.group(1), m.group(2)
    href = "../../" + href[3:] if href.startswith("../") else "../../guides/" + href
    en = href[6:]
    hi = B.HINDI_PAGES.get(en)
    return '<a href="%s">%s</a>' % (("../../" + hi) if hi else href, LINK_WORDS.get(label, label))


def build(B, cfg, pages, lastmod):
    data = V.load()
    words = json.loads(WORDS_FILE.read_text(encoding="utf-8"))
    cs = data["countries"]
    by = {k: [c for c in cs if c["status"] == k] for k in V.STATUS}
    bys = {c["slug"]: c for c in cs}
    checked = max(c["checked"] for c in cs)
    n = len(cs)
    confirmed = n - len(by["check"])
    p = "../../"
    todo = []

    def hw(c, key):
        w = words.get(c["slug"], {})
        if w.get("h") == digest(c):
            return w.get(key)
        if c["slug"] not in todo:
            todo.append(c["slug"])
        return c.get(key)

    def name(c):
        return words.get(c["slug"], {}).get("name") or c["name"]

    def names(k):
        return H.hi_join(['<a href="#%s">%s</a>' % (c["slug"], e(name(c))) for c in by[k]])

    def plain(k):
        return H.hi_join([name(c) for c in by[k]])

    def tag(status):
        return '<span class="vz-tag vz-%s">%s</span>' % (V.STATUS[status][1], e(HI_STATUS[status][0]))

    def row(c):
        src = "<br>".join('<a href="%s" target="_blank" rel="noopener" lang="en">%s</a>' % (e(s["url"]), e(s["label"])) for s in c["sources"])
        cond = "".join("<li>%s</li>" % e(x) for x in (hw(c, "conditions") or []))
        extra = ""
        if c.get("with_visa"):
            extra += '<p class="vz-also"><strong>अमेरिका, यूके या शेंगेन वीज़ा हो तो:</strong> %s</p>' % e(hw(c, "with_visa"))
        if c.get("until"):
            extra += '<p class="vz-also"><strong>कब तक:</strong> %s</p>' % e(hw(c, "until"))
        links = [re.sub(r'<a href="([^"]+)">([^<]+)</a>', lambda m: _link(B, m), x) for x in V.our_links(B, c["slug"])]
        if links:
            extra += '<p class="vz-also">CarryPick पर: %s</p>' % " &middot; ".join(links)
        search = " ".join([name(c), c["name"], c.get("aka", ""), HI_STATUS[c["status"]][0], V.STATUS[c["status"]][0]]).lower()
        aka = (' <span class="muted small" lang="en">(%s)</span>' % e(c["aka"])) if c.get("aka") else ""
        fee = hw(c, "fee") or "आधिकारिक पेज देखें"
        stay = hw(c, "stay") or "–"
        return (f'<tr id="{e(c["slug"])}" data-status="{c["status"]}" data-q="{e(search)}">'
                f'<th scope="row">{e(name(c))}{aka}</th>'
                f'<td data-l="स्टेटस">{tag(c["status"])}</td>'
                f'<td data-l="ज़्यादा से ज़्यादा ठहराव">{e(stay)}</td>'
                f'<td data-l="फ़ीस">{e(fee)}</td>'
                f'<td data-l="क्या चाहिए">{("<ul>" + cond + "</ul>") if cond else ""}{extra}</td>'
                f'<td data-l="आधिकारिक स्रोत" class="vz-src">{src}<br><span class="muted small">{B.hi_date(c["checked"])} को जाँचा</span></td></tr>')

    answer = []
    for k in ("visa-free", "visa-on-arrival", "e-visa", "visa-needed"):
        if by[k]:
            answer.append("<li><strong>%s (%d):</strong> %s।</li>" % (e(HI_STATUS[k][0]), len(by[k]), names(k)))
    if by["check"]:
        answer.append("<li><strong>पक्का नहीं (%d):</strong> %s। हम इनका नियम किसी आधिकारिक पेज पर पक्का नहीं कर पाए, इसलिए दूतावास से पूछें।</li>"
                      % (len(by["check"]), names("check")))
    opts = "".join('<option value="%s">%s (%d)</option>' % (k, e(HI_STATUS[k][0]), len(by[k])) for k in V.STATUS if by[k])
    rows = "".join(row(c) for c in cs)
    sections = "".join(f"<h3>{e(HI_STATUS[k][1])}</h3><p>{names(k)}।</p>" for k in ("visa-free", "visa-on-arrival", "e-visa", "visa-needed") if by[k])
    with_visa = [c for c in cs if c.get("with_visa")]
    with_html = ""
    if with_visa:
        with_html = ("<h2>अमेरिका, यूके या शेंगेन वीज़ा हो तो ये देश आसान हैं</h2>"
                     "<p>कुछ देश उन भारतीयों के लिए एंट्री आसान करते हैं जिनके पास अमेरिका, यूके या किसी शेंगेन देश का वैध वीज़ा या रेज़िडेंस परमिट है। "
                     "कौन-कौन से वीज़ा चलते हैं यह हर देश में अलग है, इसलिए उस देश की पंक्ति में दिया आधिकारिक पेज पढ़ें।</p><ul>%s</ul>"
                     % "".join('<li><a href="#%s"><strong>%s</strong></a>: %s</li>' % (c["slug"], e(name(c)), e(hw(c, "with_visa"))) for c in with_visa))
    pk = [(V.PACKING[s], bys[s]) for s in V.PACKING if s in bys and (B.ARTICLES_DIR / ("%s-packing-list.md" % V.PACKING[s])).exists()]
    pk_html = ""
    if pk:
        pk_html = ('<p>पैकिंग कर रहे हैं? %s की हमारी पैकिंग लिस्ट और <a href="%spacking/abroad.html">विदेश यात्रा की चेकलिस्ट</a> देखें।</p>'
                   % (H.hi_join(['<a href="%sguides/%s-packing-list.html">%s</a>' % (p, slug, e("बाली" if slug == "bali" else "दुबई" if slug == "dubai" else name(c)))
                                 for slug, c in pk]), p))
    date = B.hi_date(checked)
    title = "भारतीयों के लिए वीज़ा-फ़्री देश %s: वीज़ा ऑन अराइवल और ई-वीज़ा की लिस्ट" % checked[:4]
    seo = "भारतीयों के लिए वीज़ा फ्री देश %s: वीज़ा ऑन अराइवल और ई-वीज़ा लिस्ट" % checked[:4]
    desc = ("भारतीय पासपोर्ट वालों के लिए कौन से देश वीज़ा-फ़्री हैं? थाईलैंड, मलेशिया और नेपाल से दुबई, सिंगापुर और यूके तक %d मशहूर देश: वीज़ा-फ़्री, "
            "वीज़ा ऑन अराइवल, ई-वीज़ा या वीज़ा ज़रूरी, ठहराव, शर्तें और हर देश का आधिकारिक स्रोत, %s को जाँचा।" % (n, date))
    body = f"""{H.head(B, [("%sguides/visa-free-countries-for-indians.html" % p, "Visa guide")], title,
                       "%s को हर देश की आधिकारिक साइट पर जाँचा · भारतीय पासपोर्ट, घूमने की यात्राएँ" % date, "travel-gear", B.icon("globe", "icon media-icon"), p,
                       "Indians ke liye visa free countries: visa on arrival aur e-visa ki list, har desh ka official source aur date ke saath.")}
<div class="wrap"><article class="guide">
{V.CSS}
<div class="answer"><h2>सीधा जवाब</h2><ul>
{"".join(answer)}
</ul></div>
<p class="note"><strong>वीज़ा के नियम अक्सर बदलते हैं, कभी-कभी सिर्फ़ कुछ दिन की सूचना पर।</strong> हम हर नियम उस देश की अपनी आधिकारिक वेबसाइट पर पढ़ते हैं और जाँच की तारीख़ दिखाते हैं। बुकिंग से पहले भारत में उस देश के दूतावास या हाई कमीशन और अपनी एयरलाइन से पक्का कर लें: काग़ज़ सही न हों तो एयरलाइन चढ़ने से मना कर सकती है।</p>
<h2>देश चुनें</h2>
<form class="checker vz-form" id="vz" onsubmit="return false" hidden data-js>
<label>देश खोजें<input id="vz-q" type="search" placeholder="जैसे थाईलैंड, दुबई, बाली" autocomplete="off"></label>
<label>दिखाएँ<select id="vz-s"><option value="">सभी ({n})</option>{opts}</select></label>
<p class="checker-total" id="vz-out" aria-live="polite">सभी {n} देश दिख रहे हैं।</p>
</form>
<div class="table-wrap vz-wrap"><table class="compare vz-table" id="vz-t">
<thead><tr><th>देश</th><th>स्टेटस</th><th>ज़्यादा से ज़्यादा ठहराव</th><th>फ़ीस</th><th>क्या चाहिए</th><th>आधिकारिक स्रोत</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="checked">{n} में से {confirmed} देश आधिकारिक पेज पर पक्के किए गए; हर पंक्ति में उसकी अपनी तारीख़ है। यह आम भारतीय पासपोर्ट पर घूमने की यात्राओं के लिए है। काम, पढ़ाई, ट्रांज़िट और लंबे ठहराव के नियम अलग हैं। "फ़ीस" में सिर्फ़ वही है जो आधिकारिक पेज बताता है; फ़ीस बदलती रहती है, इसलिए पैसे देने से पहले जाँचें। आवेदन सिर्फ़ पंक्ति में दी आधिकारिक साइट पर करें: नक़ली वीज़ा वेबसाइटें ज़्यादा पैसे लेती हैं।</p>
<h2>वीज़ा-फ़्री, वीज़ा ऑन अराइवल और ई-वीज़ा: मतलब क्या है</h2>
<ul>
<li><strong>वीज़ा-फ़्री:</strong> वीज़ा नहीं चाहिए। इमिग्रेशन पर पासपोर्ट दिखाते हैं, और अफ़सर फिर भी वापसी का टिकट, होटल बुकिंग या ठहरने लायक़ पैसे दिखाने को कह सकता है।</li>
<li><strong>वीज़ा ऑन अराइवल:</strong> पहुँचने पर एयरपोर्ट पर वीज़ा मिलता है, कभी-कभी फ़ीस देकर। कुछ देश उड़ान से पहले ऑनलाइन आवेदन भी करने देते हैं।</li>
<li><strong>ई-वीज़ा:</strong> यात्रा से पहले ऑनलाइन आवेदन करते हैं और मंज़ूरी का काग़ज़ प्रिंट या फ़ोन में साथ रखते हैं। आवेदन सिर्फ़ आधिकारिक वेबसाइट पर करें।</li>
<li><strong>वीज़ा ज़रूरी:</strong> यात्रा से पहले आवेदन करना होता है, आमतौर पर भारत में वीज़ा सेंटर पर बायोमेट्रिक्स के साथ। हफ़्तों या महीनों पहले आवेदन करें।</li>
</ul>
{sections}
{with_html}
<h2>उड़ान से पहले</h2>
<ul>
<li><strong>पासपोर्ट:</strong> ज़्यादातर देश चाहते हैं कि पासपोर्ट पहुँचने या लौटने के कुछ महीने बाद तक वैध रहे, अक्सर 6 महीने, और उसमें ख़ाली पन्ने हों। पंक्ति देखें।</li>
<li><strong>वापसी का टिकट और होटल:</strong> दोनों के प्रिंट या स्क्रीनशॉट साथ रखें। जहाँ वीज़ा नहीं चाहिए वहाँ भी इमिग्रेशन अक्सर दोनों माँगता है।</li>
<li><strong>पैसे:</strong> कुछ देश ठहरने लायक़ पैसे दिखाने को कहते हैं। कार्ड और कुछ नक़द साथ रखें।</li>
<li><strong>पहुँचने के फ़ॉर्म:</strong> कई देश अब पहुँचने से कुछ दिन पहले ऑनलाइन अराइवल कार्ड या रजिस्ट्रेशन माँगते हैं। पंक्ति में लिखा है कि हमें कहाँ मिला।</li>
</ul>
{pk_html}
<p>विदेश जा रहे हैं? <a href="{p}baggage/international.html" lang="en">भारत से अंतरराष्ट्रीय उड़ानों के बैगेज नियम</a> देखें, और विदेश से क्या बिना ड्यूटी लाया जा सकता है यह हमारे <a href="{p}baggage/customs.html" lang="en">भारतीय कस्टम नियम</a> में है।</p>
<p>यह गाइड अंग्रेज़ी में भी है: <a href="{p}{V.PATH}" lang="en">Visa-free countries for Indians</a>।</p>
{{faq}}
{H.tool_links(B, HI_PATH, p)}
<p class="checked">{H.HI_DISCLOSURE}</p>
</article></div>
<script type="application/json" id="vz-t">{json.dumps(JS_WORDS, ensure_ascii=False)}</script>
<script src="{p}assets/visa-india.js" defer></script>
{B.telegram_band(cfg, p)}"""

    def say(slug):
        return hw(bys[slug], "say") if slug in bys else None

    faq = [("भारतीयों के लिए कौन से देश वीज़ा-फ़्री हैं?",
            "हमारी सूची के %d मशहूर देशों में से ये देश भारतीय पासपोर्ट वालों को घूमने की यात्रा के लिए बिना वीज़ा आने देते हैं: %s। "
            "नियम बदलते रहते हैं, इसलिए बुकिंग से पहले दूतावास से पक्का कर लें।" % (n, plain("visa-free")))]
    if by["visa-on-arrival"]:
        faq.append(("भारतीय पासपोर्ट वालों को किन देशों में वीज़ा ऑन अराइवल मिलता है?",
                    "हमारी सूची में: %s। रिटर्न टिकट, होटल बुकिंग और ठहरने लायक़ पैसे साथ रखें, क्योंकि इमिग्रेशन ये माँग सकता है।" % plain("visa-on-arrival")))
    if by["e-visa"]:
        faq.append(("भारतीयों के लिए किन देशों में ई-वीज़ा है?", "हमारी सूची में: %s। आवेदन सिर्फ़ हर पंक्ति में दी आधिकारिक वेबसाइट पर करें।" % plain("e-visa")))
    for slug, q in (("thailand", "क्या थाईलैंड भारतीयों के लिए वीज़ा-फ़्री है?"), ("uae", "क्या दुबई के लिए भारतीयों को वीज़ा चाहिए?"),
                    ("malaysia", "क्या मलेशिया भारतीयों के लिए वीज़ा-फ़्री है?"), ("vietnam", "क्या वियतनाम भारतीयों के लिए वीज़ा-फ़्री है?"),
                    ("singapore", "क्या सिंगापुर के लिए भारतीयों को वीज़ा चाहिए?"), ("sri-lanka", "क्या श्रीलंका के लिए भारतीयों को वीज़ा चाहिए?")):
        if say(slug) and bys[slug]["status"] != "check":
            faq.append((q, say(slug)))
    if with_visa:
        faq.append(("अमेरिकी वीज़ा हो तो मैं कौन से देश जा सकता हूँ?",
                    "हमारी सूची में %s उन भारतीयों के लिए एंट्री आसान करते हैं जिनके पास कुछ वैध वीज़ा या रेज़िडेंस परमिट हैं, अक्सर अमेरिका, यूके या शेंगेन देशों के। "
                    "कौन-से वीज़ा चलते हैं यह हर आधिकारिक पेज बताता है।" % H.hi_join([name(c) for c in with_visa])))
    if "schengen" in bys and bys["schengen"]["status"] == "visa-needed":
        faq.append(("क्या यूरोप का कोई देश भारतीयों के लिए वीज़ा-फ़्री है?",
                    "कोई शेंगेन देश नहीं: फ़्रांस, जर्मनी, इटली, स्विट्ज़रलैंड और बाक़ी शेंगेन देशों के लिए भारतीयों को शेंगेन वीज़ा चाहिए। %s" % (say("schengen") or "")))
    faq.append(("क्या नेपाल और भूटान बिना पासपोर्ट के जा सकते हैं?", " ".join(x for x in (say("nepal"), say("bhutan")) if x) or "दूतावास से पूछें।"))

    faq_block, faq_schema = H.faq_html(B, faq)
    body = body.replace("{faq}", faq_block)
    schema = [B.tool_article(cfg, seo, desc, HI_PATH, PUBLISHED, max(PUBLISHED, checked), "hi-IN"),
              B.crumbs_schema(cfg, [("होम", ""), ("Visa guide", HI_PATH)])]
    if faq_schema:
        schema.append(faq_schema)
    pages.append(B.write(HI_PATH, B.page(cfg, H.nfc(seo), H.nfc(desc), H.nfc(body), 2, HI_PATH, schema, og_type="article", lang="hi")))
    lastmod[HI_PATH] = max(PUBLISHED, checked)
    if todo:
        H.warn("%s: Hindi words for %s are missing or older than the English row in data/visa_india.json; the English text shows for now. "
               "Update data/hindi_visa_words.json (run scripts/hindi_visa.py to print the new hashes)." % (HI_PATH, ", ".join(todo)))


if __name__ == "__main__":
    d = json.loads(V.DATA_FILE.read_text(encoding="utf-8"))
    w = json.loads(WORDS_FILE.read_text(encoding="utf-8"))
    for c in d["countries"]:
        w.setdefault(c["slug"], {})["h"] = digest(c)
    WORDS_FILE.write_text(json.dumps(w, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("hashes written for", len(d["countries"]), "countries")
