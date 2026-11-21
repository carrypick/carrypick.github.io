"""The "Cite or link to this tool" box for the free tool pages, in English and on their Hindi twins (HI_TOOLS).

build.page() calls box() for every page; it returns "" unless the path is one of TOOLS.
The box shows the title, the full URL, the last-checked date, a one-line plain <a href>
snippet to copy (no iframe, no script) and a dated "Sources" list read from the same
data file the tool uses, so the dates and links always match the tool.
"""
import json
from datetime import datetime
from html import escape as e

from common import ROOT

DATA = ROOT / "data"


def _load(name):
    path = DATA / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _fmt(value):
    d = datetime.strptime(value[:10], "%Y-%m-%d")
    return "%d %s" % (d.day, d.strftime("%b %Y"))


def _power_bank():
    d = _load("power_banks.json")
    seen, src = set(), []
    for a in d.get("airlines", []):
        if a.get("source") and a["source"] not in seen:
            seen.add(a["source"])
            src.append((a.get("source_label") or a["name"], a["source"]))
    return d.get("checked"), src


def _checker():
    dates, src = [], []
    for name in ("airlines.json", "airlines_intl.json"):
        d = _load(name)
        if d.get("checked"):
            dates.append(d["checked"])
        for a in d.get("airlines", []):
            if a.get("sources"):
                s = a["sources"][0]
                src.append(("%s: %s" % (a["name"], s["label"]), s["url"]))
    return (max(dates) if dates else None), src


def _simple(name):
    def get():
        d = _load(name)
        return d.get("checked"), [(s["label"], s["url"]) for s in d.get("sources", [])]
    return get


def _gift_finder():
    return _load("gift_finder.json").get("updated"), []


def _what_to_wear():
    d = _load("what_to_wear.json")
    seen, src = set(), []
    for s in [p.get("source", {}) for p in d.get("places", [])] + list(d.get("sources", {}).values()):
        if s.get("url") and s["url"] not in seen:
            seen.add(s["url"])
            src.append((s["label"], s["url"]))
    return d.get("updated"), src


TOOLS = {
    "tools/power-bank-flight-check.html": _power_bank,
    "baggage/checker.html": _checker,
    "tools/packing-list-maker.html": _simple("flight_items.json"),
    "tools/shoe-size.html": _simple("shoe_sizes.json"),
    "tools/clothing-size.html": _simple("clothing_sizes.json"),
    "tools/gift-finder.html": _gift_finder,
    "tools/what-to-wear.html": _what_to_wear,
    "tools/trip-budget-calculator.html": lambda: ("2026-11-21", []),
    "tools/road-trip-cost-calculator.html": lambda: ("2026-11-21", []),
}
# Hindi tool page -> its English tool (same data, same dates), and the Hindi name for the box.
HI_TOOLS = {
    "hi/power-bank-flight-check.html": ("tools/power-bank-flight-check.html", "पावर बैंक फ्लाइट चेकर (mAh से Wh)"),
    "hi/cabin-bag-checker.html": ("baggage/checker.html", "केबिन बैग चेकर"),
    "hi/packing-list-maker.html": ("tools/packing-list-maker.html", "पैकिंग लिस्ट मेकर"),
    "hi/shoe-size.html": ("tools/shoe-size.html", "जूते का साइज कन्वर्टर"),
    "hi/clothing-size.html": ("tools/clothing-size.html", "कपड़ों का साइज कन्वर्टर"),
    "hi/gift-finder.html": ("tools/gift-finder.html", "गिफ़्ट फ़ाइंडर क्विज़"),
    "hi/what-to-wear.html": ("tools/what-to-wear.html", "क्या पहनें हेल्पर"),
}
HI_WORDS = {"head": "इस टूल का हवाला दें या लिंक करें",
            "lead": "अपने ब्लॉग, स्कूल प्रोजेक्ट या ट्रैवल गाइड से मुफ़्त में लिंक करें। न साइन-अप, न एम्बेड कोड।",
            "title": "नाम", "url": "URL", "checked": "आख़िरी बार जाँचा", "copy": "यह लिंक कॉपी करें (सादा HTML):",
            "sources": "स्रोत", "read": "%s को पढ़ा"}
HI_NOTES = {
    "tools/packing-list-maker.html": "पैकिंग के सामान हमारी अपनी चेकलिस्ट से हैं; केबिन और लिक्विड के नियम इन सरकारी पेजों से।",
    "tools/gift-finder.html": "गिफ़्ट आइडिया CarryPick टीम ने चुने हैं। टूल कोई बाहरी डेटा इस्तेमाल नहीं करता, इसलिए हवाला देने के लिए और कुछ नहीं है।",
}
HI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]


def _fmt_hi(value):
    d = datetime.strptime(value[:10], "%Y-%m-%d")
    return "%d %s %d" % (d.day, HI_MONTHS[d.month - 1], d.year)
NAMES = {"tools/power-bank-flight-check.html": "Power bank flight checker (mAh to Wh)"}
NOTES = {
    "tools/packing-list-maker.html": "Packing items come from our own checklists; the cabin and liquids rules come from these official pages.",
    "tools/gift-finder.html": "Gift ideas are chosen by the CarryPick team. The tool uses no outside data, so there is nothing else to cite.",
    "tools/trip-budget-calculator.html": "Every amount comes from the person using the tool. It uses no outside data or prices, so there is nothing else to cite.",
    "tools/road-trip-cost-calculator.html": "Every amount, including the fuel price, comes from the person using the tool. It uses no outside data or prices.",
}


def box(cfg, path, title, lang="en"):
    if not cfg.get("base_url") or (path not in HI_TOOLS if lang == "hi" else path not in TOOLS):
        return ""
    hi = lang == "hi"
    en_path = HI_TOOLS[path][0] if hi else path
    if en_path not in TOOLS:
        return ""
    checked, sources = TOOLS[en_path]()
    url = cfg["base_url"].rstrip("/") + "/" + path
    if hi:
        name = HI_TOOLS[path][1]
    else:
        name = NAMES.get(path) or (title.split(":")[0].strip() if len(title) > 60 else title)
    fmt = _fmt_hi if hi else _fmt
    w = HI_WORDS if hi else {"head": "Cite or link to this tool",
                             "lead": "Free to link from your blog, school project or travel guide. No sign-up, no embed code.",
                             "title": "Title", "url": "URL", "checked": "Last checked", "copy": "Copy this link (plain HTML):",
                             "sources": "Sources", "read": "read on %s"}
    snippet = '<a href="%s">%s</a>' % (url, name)
    date_html = ("<li><strong>%s:</strong> %s</li>" % (w["checked"], fmt(checked))) if checked else ""
    items = "".join('<li><a href="%s" target="_blank" rel="noopener"%s>%s</a> (%s)</li>'
                    % (e(u), ' lang="en"' if hi else "", e(label), w["read"] % fmt(checked)) for label, u in sources)
    notes = HI_NOTES if hi else NOTES
    note = ('<p class="small muted">%s</p>' % e(notes[en_path])) if en_path in notes else ""
    src_html = ""
    if items or note:
        count = " (%d)" % len(sources) if sources else ""
        src_html = '<details><summary>%s%s</summary>%s%s</details>' % (
            w["sources"], count, note, ("<ul>%s</ul>" % items) if items else "")
    return f"""<section class="cite-box" aria-labelledby="cite-h">
<h2 id="cite-h">{e(w["head"])}</h2>
<p class="small muted">{e(w["lead"])}</p>
<ul class="cite-facts"><li><strong>{e(w["title"])}:</strong> {e(name)}</li><li><strong>{e(w["url"])}:</strong> <a href="{e(url)}">{e(url)}</a></li>{date_html}</ul>
<label class="small" for="cite-snip">{e(w["copy"])}</label>
<textarea id="cite-snip" class="cite-snip" rows="2" readonly onclick="this.select()">{e(snippet)}</textarea>
{src_html}
</section>
"""


def insert(cfg, path, title, body, lang="en"):
    """Put the box just above "More free travel tools" (Hindi: "और मुफ़्त टूल"), else above the share bar or band."""
    html = box(cfg, path, title, lang)
    if not html:
        return body
    for marker in ("<h2>More free travel tools</h2>", "<h2>और मुफ़्त टूल</h2>", '<section class="band">'):
        if marker in body:
            return body.replace(marker, html + marker, 1)
    return body + html
