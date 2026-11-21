"""Visa guide for Indian passport holders (guides/visa-free-countries-for-indians.html), kept out of build.py:

- data/visa_india.json: one entry per country, read on that country's own official page (immigration, foreign
  ministry, official e-visa portal, or its embassy in India), with the URL and the date we read it. A rule we could
  not confirm on an official page has status "check" ("Check the embassy") and no stay or fee. We never guess.
- static/visa-india.js: the search box and status filter. Without JavaScript the page is the full table.

build.py calls register(B) where it lists TOOLS, build(B, ...) after the trip guides (so links to our packing lists and
trip guides can be checked), and link_line(B, p) for the one-line links on the baggage and packing pages.
"""

import json
from html import escape as e

import more_tools
from common import ROOT

DATA_FILE = ROOT / "data" / "visa_india.json"
PATH = "guides/visa-free-countries-for-indians.html"
STATUS = {  # key: (label, short css class, heading)
    "visa-free": ("Visa-free", "vf", "Visa-free countries for Indians"),
    "visa-on-arrival": ("Visa on arrival", "voa", "Visa on arrival countries for Indian passport holders"),
    "e-visa": ("e-Visa", "ev", "e-Visa countries for Indians"),
    "visa-needed": ("Visa needed", "vn", "Countries where Indians need a visa before travel"),
    "check": ("Check the embassy", "ck", "Not confirmed: check with the embassy"),
}
# Our packing list for a country (content/articles/<slug>-packing-list.md), and the trip-guide slug prefixes to look for.
PACKING = {"thailand": "thailand", "uae": "dubai", "indonesia": "bali", "vietnam": "vietnam", "maldives": "maldives",
           "sri-lanka": "sri-lanka", "singapore": "singapore", "nepal": "nepal", "bhutan": "bhutan"}
TRIP_PREFIX = {"thailand": ("thailand", "bangkok", "phuket"), "uae": ("dubai", "uae", "abu-dhabi"), "indonesia": ("bali", "indonesia"),
               "malaysia": ("malaysia", "kuala-lumpur", "langkawi"), "vietnam": ("vietnam",), "sri-lanka": ("sri-lanka",),
               "maldives": ("maldives",), "singapore": ("singapore",), "nepal": ("nepal",), "bhutan": ("bhutan",),
               "japan": ("japan", "tokyo"), "hong-kong": ("hong-kong",), "georgia": ("georgia",), "kazakhstan": ("kazakhstan", "almaty")}
CSS = """<style>
.vz-form{display:grid;gap:10px;grid-template-columns:1fr;margin:18px 0}
@media(min-width:620px){.vz-form{grid-template-columns:2fr 1fr}}
.vz-tag{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.8rem;font-weight:700;white-space:nowrap;border:1px solid var(--line)}
.vz-vf{background:#e3f4e8;color:#14532d;border-color:#9fd5b0}.vz-voa{background:#e6f0fb;color:#1e3a8a;border-color:#a9c4ea}
.vz-ev{background:#fdf3dc;color:#713f12;border-color:#e9cf8b}.vz-vn{background:#fbe7e7;color:#7f1d1d;border-color:#e8b0b0}
.vz-ck{background:var(--tint-none);color:var(--ink)}
.vz-table ul{margin:0;padding-left:18px}.vz-table li{margin:0 0 3px}
.vz-table td.vz-src{min-width:150px}.vz-also{margin:6px 0 0;font-size:.85rem}
@media(max-width:719px){
.vz-wrap{border:0;box-shadow:none;background:none;overflow:visible}
.vz-table,.vz-table tbody,.vz-table tr,.vz-table th,.vz-table td{display:block;min-width:0!important;width:auto}
.vz-table{min-width:0}.vz-table thead{display:none}
.vz-table tr{border:1px solid var(--line);border-radius:14px;background:var(--surface);margin:0 0 12px;padding:4px 0}
.vz-table th,.vz-table td{border:0;padding:5px 14px}
.vz-table tbody th{font-size:1.05rem}
.vz-table td[data-l]::before{content:attr(data-l);display:block;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
}
</style>"""


def load():
    if not DATA_FILE.exists():
        return None
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    for c in data["countries"]:
        missing = [k for k in ("slug", "name", "status", "say", "sources", "checked") if not c.get(k)]
        if missing or c["status"] not in STATUS:
            raise SystemExit("Error: data/visa_india.json: %s is missing %s or has an unknown status" % (c.get("slug", "?"), ", ".join(missing)))
        if c["status"] != "check" and not c.get("stay"):
            raise SystemExit("Error: data/visa_india.json: %s has a confirmed status but no stay" % c["slug"])
        if any("amazon" in s["url"].lower() for s in c["sources"]):
            raise SystemExit("Error: data/visa_india.json: %s cites an Amazon page" % c["slug"])
    return data


def register(B):
    data = load()
    if not data:
        return
    B.TOOLS.append((PATH, "Visa guide for Indians", "Free guide", "Visa-free countries for Indians",
                    "Visa-free, visa on arrival, e-visa or visa needed: search %d countries, with official sources and dates." % len(data["countries"]),
                    "Check a country", "globe", "travel-gear", "plane-window"))


def link_line(B, p, lead="Going abroad?"):
    """One plain line linking to the visa guide, for the baggage and packing pages."""
    if not DATA_FILE.exists():
        return ""
    return ('<p>%s Check if you need a visa first: our <a href="%s%s">visa guide for Indian passport holders</a> '
            'lists visa-free, visa on arrival and e-visa countries, with official sources.</p>' % (e(lead), p, PATH))


def our_links(B, slug):
    out = []
    pk = PACKING.get(slug)
    if pk and (B.ARTICLES_DIR / ("%s-packing-list.md" % pk)).exists():
        out.append('<a href="%s-packing-list.html">Packing list</a>' % pk)
    for prefix in TRIP_PREFIX.get(slug, ()):
        for f in sorted(B.TRIPS_DIR.glob(prefix + "*.md")):
            label = ("December trip guide" if "december" in f.stem else "By-road guide" if "by-road" in f.stem
                     else "Long weekend guide" if "long-weekend" in f.stem else "Trip guide")
            out.append('<a href="../trips/%s.html">%s</a>' % (f.stem, label))
    if slug == "uae" and (B.CUSTOMS_DIR / "uae-dubai.md").exists():
        out.append('<a href="../baggage/customs/uae-dubai.html">What to carry to Dubai</a>')
    return out


def tag(status):
    label, cls, _ = STATUS[status]
    return '<span class="vz-tag vz-%s">%s</span>' % (cls, e(label))


def row(B, c):
    src = "<br>".join('<a href="%s" target="_blank" rel="noopener">%s</a>' % (e(s["url"]), e(s["label"])) for s in c["sources"])
    cond = "".join("<li>%s</li>" % e(x) for x in c.get("conditions", []))
    extra = ""
    if c.get("with_visa"):
        extra += '<p class="vz-also"><strong>With a US, UK or Schengen visa:</strong> %s</p>' % e(c["with_visa"])
    if c.get("until"):
        extra += '<p class="vz-also"><strong>Until:</strong> %s</p>' % e(c["until"])
    links = our_links(B, c["slug"])
    if links:
        extra += '<p class="vz-also">On CarryPick: %s</p>' % " &middot; ".join(links)
    search = " ".join([c["name"], c.get("aka", ""), STATUS[c["status"]][0]]).lower()
    aka = (' <span class="muted small">(%s)</span>' % e(c["aka"])) if c.get("aka") else ""
    return (f'<tr id="{e(c["slug"])}" data-status="{c["status"]}" data-q="{e(search)}">'
            f'<th scope="row">{e(c["name"])}{aka}</th>'
            f'<td data-l="Status">{tag(c["status"])}</td>'
            f'<td data-l="Max stay">{e(c.get("stay") or "–")}</td>'
            f'<td data-l="Fee">{e(c.get("fee") or "See official page")}</td>'
            f'<td data-l="What you need">{("<ul>" + cond + "</ul>") if cond else ""}{extra}</td>'
            f'<td data-l="Official source" class="vz-src">{src}<br><span class="muted small">Checked {B.fmt_date(c["checked"])}</span></td></tr>')


def build(B, cfg, pages, lastmod):
    data = load()
    if not data:
        return
    cs = data["countries"]
    by = {k: [c for c in cs if c["status"] == k] for k in STATUS}
    bys = {c["slug"]: c for c in cs}
    checked = max(c["checked"] for c in cs)
    year = checked[:4]
    n = len(cs)
    confirmed = n - len(by["check"])

    def names(k):
        return B.and_list('<a href="#%s">%s</a>' % (c["slug"], e(c["name"])) for c in by[k]) if by[k] else ""

    def plain(k):
        return B.and_list(c["name"] for c in by[k]) if by[k] else "none of the countries in our table"

    answer = []
    for k in ("visa-free", "visa-on-arrival", "e-visa", "visa-needed"):
        if by[k]:
            answer.append("<li><strong>%s (%d):</strong> %s.</li>" % (e(STATUS[k][0]), len(by[k]), names(k)))
    if by["check"]:
        answer.append("<li><strong>Not confirmed (%d):</strong> %s. We could not confirm the rule on an official page, so check with the embassy.</li>"
                      % (len(by["check"]), names("check")))

    opts = "".join('<option value="%s">%s (%d)</option>' % (k, e(STATUS[k][0]), len(by[k])) for k in STATUS if by[k])
    rows = "".join(row(B, c) for c in cs)
    sections = "".join(f'<h3>{e(STATUS[k][2])}</h3><p>{names(k)}.</p>' for k in ("visa-free", "visa-on-arrival", "e-visa", "visa-needed") if by[k])
    with_visa = [c for c in cs if c.get("with_visa")]
    with_html = ""
    if with_visa:
        with_html = ("<h2>Countries Indians can visit with a US, UK or Schengen visa</h2>"
                     "<p>Some countries make it easier if you already hold a valid visa or residence permit from the US, the UK or a Schengen country. "
                     "The exact list of accepted visas differs, so read the official page in the row.</p><ul>%s</ul>"
                     % "".join('<li><a href="#%s"><strong>%s</strong></a>: %s</li>' % (c["slug"], e(c["name"]), e(c["with_visa"])) for c in with_visa))
    pk_links = [(PACKING[s], bys[s]["name"]) for s in PACKING if s in bys and (B.ARTICLES_DIR / ("%s-packing-list.md" % PACKING[s])).exists()]
    pk_html = ("<p>Packing for the trip? See our packing lists for %s, and the <a href=\"../packing/abroad.html\">trip abroad checklist</a>.</p>"
               % B.and_list('<a href="%s-packing-list.html">%s</a>' % (slug, e("Bali" if slug == "bali" else "Dubai" if slug == "dubai" else name))
                            for slug, name in pk_links)) if pk_links else ""

    title = "Visa-free countries for Indians %s: visa on arrival and e-visa list" % year
    seo = "Visa free countries for Indians %s: visa on arrival, e-visa list" % year
    desc = ("Which countries are visa free for Indian passport holders in %s? %d popular countries, from Thailand, Malaysia and Nepal to Dubai, "
            "Singapore and the UK: visa-free, visa on arrival, e-visa or visa needed, with stay, conditions and the official source for each, checked %s."
            % (year, n, B.fmt_date(checked)))
    body = f"""{more_tools._head(B, title, "Visa guide for Indians", "Checked %s on each country's official site · Indian passport, tourist trips" % B.fmt_date(checked), "travel-gear", "globe")}
<div class="wrap"><article class="guide">
{CSS}
<div class="answer"><h2>Quick answer</h2><ul>
{"".join(answer)}
</ul></div>
<p class="note"><strong>Visa rules change often, sometimes with only a few days' notice.</strong> We read each rule on the country's own official website and show the date we checked it. Before you book, confirm with the country's embassy or high commission in India and with your airline: airlines can refuse to board you if your papers are not right.</p>
<h2>Check a country</h2>
<form class="checker vz-form" id="vz" onsubmit="return false" hidden data-js>
<label>Search a country<input id="vz-q" type="search" placeholder="e.g. Thailand, Dubai, Bali" autocomplete="off"></label>
<label>Show<select id="vz-s"><option value="">All ({n})</option>{opts}</select></label>
<p class="checker-total" id="vz-out" aria-live="polite">Showing all {n} countries.</p>
</form>
<div class="table-wrap vz-wrap"><table class="compare vz-table" id="vz-t">
<thead><tr><th>Country</th><th>Status</th><th>Max stay</th><th>Fee</th><th>What you need</th><th>Official source</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="checked">{confirmed} of {n} countries confirmed on an official page; each row shows its own date. For tourist trips on an ordinary Indian passport. Work, study, transit and long stays have other rules. "Fee" shows only what the official page states; fees change, so check before you pay. Apply only on the official site in the row: look-alike visa websites charge extra.</p>
<h2>Visa-free, visa on arrival and e-visa: what it means</h2>
<ul>
<li><strong>Visa-free:</strong> no visa. You show your passport at immigration, and the officer can still ask for a return ticket, hotel booking or money for your stay.</li>
<li><strong>Visa on arrival:</strong> you get the visa at the airport when you land, sometimes for a fee. Some countries also let you apply online before you fly.</li>
<li><strong>e-Visa:</strong> you apply online before you travel and carry the approval, printed or on your phone. Apply only on the official website.</li>
<li><strong>Visa needed:</strong> you apply before you travel, usually with biometrics at a visa centre in India. Apply weeks or months ahead.</li>
</ul>
{sections}
{with_html}
<h2>Before you fly</h2>
<ul>
<li><strong>Passport:</strong> most countries want it valid for some months after you arrive or leave, often 6 months, and with blank pages. Check the row.</li>
<li><strong>Return ticket and hotel:</strong> carry printouts or screenshots. Immigration often asks for both, even where no visa is needed.</li>
<li><strong>Money:</strong> some countries ask you to show enough money for your stay. Carry a card and some cash.</li>
<li><strong>Arrival forms:</strong> several countries now ask for an online arrival card or registration a few days before you land. The row says where we found one.</li>
</ul>
{pk_html}
<p>Flying out? See the <a href="../baggage/international.html">baggage rules for international flights from India</a>, and what you can bring back duty free in our <a href="../baggage/customs.html">Indian customs rules</a>.</p>
{{faq}}
{B.tool_pills("../", PATH)}
</article></div>
<script src="../assets/visa-india.js" defer></script>
{B.telegram_band(cfg, "../")}"""

    def say(slug):
        return bys[slug]["say"] if slug in bys else None

    faq = [("Which countries are visa free for Indians?",
            "Of the %d popular countries in our table, these let Indian passport holders in without a visa for a tourist trip: %s. "
            "Rules change, so confirm with the embassy before you book." % (n, plain("visa-free")))]
    if by["visa-on-arrival"]:
        faq.append(("Which countries give visa on arrival to Indian passport holders?",
                    "In our table: %s. Carry a return ticket, a hotel booking and enough money, as immigration can ask for them." % plain("visa-on-arrival")))
    if by["e-visa"]:
        faq.append(("Which countries have an e-visa for Indians?",
                    "In our table: %s. Apply only on the official website linked in each row." % plain("e-visa")))
    for slug, q in (("thailand", "Is Thailand visa free for Indians?"), ("uae", "Do Indians need a visa for Dubai?"),
                    ("malaysia", "Is Malaysia visa free for Indians?"), ("vietnam", "Is Vietnam visa free for Indians?"),
                    ("singapore", "Do Indians need a visa for Singapore?"), ("sri-lanka", "Do Indians need a visa for Sri Lanka?")):
        if say(slug) and bys[slug]["status"] != "check":
            faq.append((q, say(slug)))
    if with_visa:
        faq.append(("Which countries can I visit with a US visa?",
                    "In our table, %s make entry easier for Indians who hold certain valid visas or residence permits, often from the US, UK or Schengen countries. "
                    "Each official page lists which visas count." % B.and_list(c["name"] for c in with_visa)))
    if "schengen" in bys and bys["schengen"]["status"] == "visa-needed":
        faq.append(("Are any European countries visa free for Indians?",
                    "No Schengen country is: Indians need a Schengen visa for France, Germany, Italy, Switzerland and the other Schengen countries. %s"
                    % (say("schengen") or "")))
    faq.append(("Can I travel to Nepal and Bhutan without a passport?",
                " ".join(x for x in (say("nepal"), say("bhutan")) if x) or "Check with the embassy."))
    more_tools._finish(B, cfg, pages, lastmod, PATH, seo, desc, "Visa guide for Indians", body, faq, checked)
