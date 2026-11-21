"""The "Cite or link to this tool" box for the free tool pages (English pages only).

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


TOOLS = {
    "tools/power-bank-flight-check.html": _power_bank,
    "baggage/checker.html": _checker,
    "tools/packing-list-maker.html": _simple("flight_items.json"),
    "tools/shoe-size.html": _simple("shoe_sizes.json"),
    "tools/clothing-size.html": _simple("clothing_sizes.json"),
    "tools/gift-finder.html": _gift_finder,
}
NAMES = {"tools/power-bank-flight-check.html": "Power bank flight checker (mAh to Wh)"}
NOTES = {
    "tools/packing-list-maker.html": "Packing items come from our own checklists; the cabin and liquids rules come from these official pages.",
    "tools/gift-finder.html": "Gift ideas are chosen by the CarryPick team. The tool uses no outside data, so there is nothing else to cite.",
}


def box(cfg, path, title):
    if path not in TOOLS or not cfg.get("base_url"):
        return ""
    checked, sources = TOOLS[path]()
    url = cfg["base_url"].rstrip("/") + "/" + path
    name = NAMES.get(path) or (title.split(":")[0].strip() if len(title) > 60 else title)
    snippet = '<a href="%s">%s</a>' % (url, name)
    date_html = ("<li><strong>Last checked:</strong> %s</li>" % _fmt(checked)) if checked else ""
    items = "".join('<li><a href="%s" target="_blank" rel="noopener">%s</a> (read on %s)</li>'
                    % (e(u), e(label), _fmt(checked)) for label, u in sources)
    note = ('<p class="small muted">%s</p>' % e(NOTES[path])) if path in NOTES else ""
    src_html = ""
    if items or note:
        count = " (%d)" % len(sources) if sources else ""
        src_html = '<details><summary>Sources%s</summary>%s%s</details>' % (
            count, note, ("<ul>%s</ul>" % items) if items else "")
    return f"""<section class="cite-box" aria-labelledby="cite-h">
<h2 id="cite-h">Cite or link to this tool</h2>
<p class="small muted">Free to link from your blog, school project or travel guide. No sign-up, no embed code.</p>
<ul class="cite-facts"><li><strong>Title:</strong> {e(name)}</li><li><strong>URL:</strong> <a href="{e(url)}">{e(url)}</a></li>{date_html}</ul>
<label class="small" for="cite-snip">Copy this link (plain HTML):</label>
<textarea id="cite-snip" class="cite-snip" rows="2" readonly onclick="this.select()">{e(snippet)}</textarea>
{src_html}
</section>
"""


def insert(cfg, path, title, body):
    """Put the box just above "More free travel tools", else above the share bar or band."""
    html = box(cfg, path, title)
    if not html:
        return body
    for marker in ("<h2>More free travel tools</h2>", '<section class="band">'):
        if marker in body:
            return body.replace(marker, html + marker, 1)
    return body + html
