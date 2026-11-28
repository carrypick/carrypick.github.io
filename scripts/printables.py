"""Free printable packing checklists: one-page A4 PDFs in docs/printables/ (backlink kit, plan A8, 28 Nov 2026).

Each PDF is made from the same source as its page, so they stay in sync:
- packing.json lists (week, abroad, train): the same items and quantities as packing/*.html for that trip's days;
- guide lists (Goa, Umrah): the list items of chosen sections of content/articles/<slug>.md.

The PDF has tick boxes, "CarryPick · carrypick.github.io", the checked date and the page it comes from.
No product links and no affiliate links. robots.txt disallows /printables/ (scripts/build.py), so Google
doesn't index copies of our pages.

Google Chrome prints the PDFs (headless). A PDF is printed again only when its HTML changes: the hash of each
one is kept in data/printables.json, because Chrome writes a new creation date every time.

Run: python3 scripts/printables.py   (build.py also calls build() at the end of every build)
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "printables"
HASHES = ROOT / "data" / "printables.json"
PACKING_FILE = ROOT / "data" / "packing.json"
ARTICLES = ROOT / "content" / "articles"
SITE = "carrypick.github.io"
CHROME = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "google-chrome", "chromium", "chromium-browser"]

# file stem -> where it comes from, and the page(s) that link to it (build.py adds the line near the top).
PRINTABLES = {
    "packing-checklist-week": {"kind": "packing", "trip": "week", "title": "Packing checklist for a week-long trip",
                               "from": "packing/index.html"},
    "packing-checklist-international-trip": {"kind": "packing", "trip": "abroad", "title": "Packing checklist for an international trip",
                                             "from": "packing/abroad.html"},
    "packing-checklist-train-journey": {"kind": "packing", "trip": "train", "title": "Packing checklist for a train journey in India",
                                        "from": "guides/things-to-carry-in-train-journey.html"},
    "goa-packing-checklist": {"kind": "guide", "slug": "goa-packing-list", "title": "Goa packing checklist",
                              "sections": ["Clothes", "Shoes", "Sun, skin and health", "Beach bag", "What to pack for women", "What to pack for men", "What to pack for kids"],
                              "from": "guides/goa-packing-list.html"},
    "umrah-packing-checklist": {"kind": "guide", "slug": "umrah-packing-list", "title": "Umrah packing checklist",
                                "sections": ["Documents and money", "What to pack for men", "What to pack for ladies", "What to pack for kids",
                                             "Slippers and shoes", "Toiletries: unscented for ihram", "Medicines and health",
                                             "Phone, plugs and power bank", "Small things that help"],
                                # Rules and notes, not things to pack (the page explains them). Each must still be on the page.
                                "skip": ["Rawdah visit in Madinah", "Saudi customs", "Ladies", "Meningitis vaccine is required for every pilgrim",
                                         "India is not on the polio or yellow fever lists", "The flu vaccine is advised",
                                         "Bring only enough for your stay", "Narcotic or psychotropic medicines",
                                         "Indian phone and laptop chargers work"],
                                "from": "guides/umrah-packing-list.html"},
}

# Which pages show which PDFs (path -> stems). The packing hub lists the three packing.json lists.
LINKS = {
    "packing/index.html": ["packing-checklist-week", "packing-checklist-international-trip", "packing-checklist-train-journey"],
    "packing/abroad.html": ["packing-checklist-international-trip"],
    "packing/train.html": ["packing-checklist-train-journey"],
    "guides/things-to-carry-in-train-journey.html": ["packing-checklist-train-journey"],
    "guides/goa-packing-list.html": ["goa-packing-checklist"],
    "guides/umrah-packing-list.html": ["umrah-packing-checklist"],
}
SHORT = {"packing-checklist-week": "week-long trip", "packing-checklist-international-trip": "international trip",
         "packing-checklist-train-journey": "train journey", "goa-packing-checklist": "Goa", "umrah-packing-checklist": "Umrah"}

QTY_RULES = {"per_day": lambda n: n, "per_day_plus_1": lambda n: n + 1, "per_day_plus_2": lambda n: n + 2,
             "per_2_days": lambda n: n / 2, "per_3_days": lambda n: n / 3, "six_per_day": lambda n: 6 * n}


def pack_qty(rule, days, cap=None):
    """Same rule as pack_qty() in build.py and quantities() in static/packing.js."""
    if rule is None:
        return None
    value = rule if isinstance(rule, (int, float)) else QTY_RULES[rule](days)
    value = max(1, -(-value // 1)) if not isinstance(value, int) else max(1, value)
    value = min(cap, value) if cap else value
    return int(value)


def fmt_date(value):
    y, m, d = (int(x) for x in value.split("-"))
    months = "January February March April May June July August September October November December".split()
    return "%d %s %d" % (d, months[m - 1], y)


def link_line(path, p):
    """The one line near the top of a page that links to its PDF(s), or "" if the page has none."""
    stems = [s for s in LINKS.get(path, []) if (OUT / (s + ".pdf")).exists()]
    if not stems:
        return ""
    if len(stems) == 1:
        return ('<p class="printable"><a href="%sprintables/%s.pdf">Free printable checklist (PDF)</a>: '
                'one A4 page with tick boxes, to print and pack with.</p>' % (p, stems[0]))
    return ('<p class="printable">Free printable checklists (PDF), one A4 page each: %s.</p>' % ", ".join(
        '<a href="%sprintables/%s.pdf">%s</a>' % (p, s, e(SHORT[s])) for s in stems))


def clean(text):
    text = re.sub(r"\[\[[^\]]*\]\]", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def guide_item(line):
    """One tick-box item from a Markdown list line: the bold lead if there is one, else the first sentence."""
    text = clean(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line))
    m = re.match(r"\*\*(.+?)\*\*", text)
    if m:
        text = m.group(1)
    else:
        text = re.split(r"(?<=[a-z0-9)])\. ", text.replace("**", ""))[0]
    return text.strip().rstrip(".:,;").strip()


def guide_groups(cfg):
    src = (ARTICLES / (cfg["slug"] + ".md")).read_text(encoding="utf-8")
    meta_block, body = re.match(r"^---\n(.*?)\n---\n(.*)$", src, re.S).groups()
    meta = dict(line.split(": ", 1) for line in meta_block.splitlines() if ": " in line)
    sections, name = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            sections[name] = []
        elif name and re.match(r"^(?:[-*]|\d+\.)\s+", line):
            sections[name].append(guide_item(line))
    skip = set(cfg.get("skip", ()))
    found = {x for v in sections.values() for x in v}
    if skip - found:
        sys.exit("Error: printables: %s.md no longer has the skipped item(s) %s" % (cfg["slug"], ", ".join(sorted(skip - found))))
    groups = []
    for want in cfg["sections"]:
        if want not in sections:
            sys.exit("Error: printables: section '%s' not found in %s.md" % (want, cfg["slug"]))
        items = [(x, None) for x in dict.fromkeys(sections[want]) if x and x not in skip and not x.endswith("?")]
        if not items:
            sys.exit("Error: printables: section '%s' in %s.md has no list items" % (want, cfg["slug"]))
        heading = re.sub(r"^What to pack for ", "For ", want)
        groups.append((heading[0].upper() + heading[1:], items))
    return groups, meta.get("updated", meta["date"]), None


def packing_groups(cfg):
    data = json.loads(PACKING_FILE.read_text(encoding="utf-8"))
    trip = {t["slug"]: t for t in data["trips"]}[cfg["trip"]]
    groups = []
    for g in data["groups"]:
        items = [(i["name"], pack_qty(i.get("qty"), trip["days"], i.get("cap"))) for i in g["items"]
                 if i["trips"] == "all" or cfg["trip"] in i["trips"]]
        if items:
            groups.append((g["name"], items))
    # Same date rule as build_packing(): the hub, merged lists and hills carry PACKING_UPDATED.
    build_src = (ROOT / "scripts" / "build.py").read_text(encoding="utf-8")
    updated = re.search(r'^PACKING_UPDATED = "([\d-]+)"', build_src, re.M).group(1)
    if cfg["trip"] not in ("week", "weekend", "beach", "train", "wedding", "hills"):
        updated = "2026-11-03"
    return groups, updated, "Quantities are for %d days. Clothes are capped where you can wash and wear again." % trip["days"]


def html_for(stem, cfg, font):
    groups, updated, note = (packing_groups if cfg["kind"] == "packing" else guide_groups)(cfg)
    url = "https://%s/%s" % (SITE, cfg["from"])
    cols = "".join(
        '<section><h2>%s</h2><ul>%s</ul></section>' % (e(name), "".join(
            '<li><span class="box"></span><span>%s%s</span></li>' % (e(text), ' <b>× %d</b>' % q if q else "") for text, q in items))
        for name, items in groups)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{e(cfg['title'])} | CarryPick</title>
<style>
@page {{ size: A4; margin: 12mm 13mm 11mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1d2433; font-size: {font}pt; line-height: 1.28; }}
header {{ display: flex; justify-content: space-between; align-items: baseline; border-bottom: 2px solid #0f6e6a; padding-bottom: 4mm; margin-bottom: 4mm; }}
.brand {{ white-space: nowrap; margin-left: 6mm; font-weight: 700; color: #0f6e6a; font-size: 11pt; }}
h1 {{ font-size: 17pt; margin: 0 0 1mm; }}
.meta {{ color: #555; font-size: 8.5pt; margin: 0; }}
.cols {{ column-count: 2; column-gap: 8mm; }}
section {{ break-inside: avoid; margin-bottom: 3.2mm; }}
h2 {{ font-size: {font + 1.5}pt; margin: 0 0 1.2mm; color: #0f6e6a; text-transform: uppercase; letter-spacing: .03em; }}
ul {{ list-style: none; margin: 0; padding: 0; }}
li {{ display: flex; gap: 2.2mm; margin: 0 0 1.1mm; break-inside: avoid; }}
.box {{ flex: none; width: 3.4mm; height: 3.4mm; border: 1.2px solid #1d2433; border-radius: 0.6mm; margin-top: 0.3mm; }}
b {{ font-weight: 600; color: #444; white-space: nowrap; }}
footer {{ margin-top: 3mm; border-top: 1px solid #ccc; padding-top: 2.5mm; font-size: 8pt; color: #555; }}
footer a {{ color: #0f6e6a; text-decoration: none; }}
</style></head><body>
<header><div><h1>{e(cfg['title'])}</h1><p class="meta">Checked {fmt_date(updated)}{(' · ' + e(note)) if note else ''}</p></div>
<div class="brand">CarryPick · {SITE}</div></header>
<div class="cols">{cols}</div>
<footer>CarryPick · {SITE} · Free to print and share. The full list, with the reasons and the rules, is at
<a href="{url}">{e(SITE + '/' + cfg['from'])}</a>. Rules change: check your airline, railway or tour group before you travel.</footer>
</body></html>
"""


def find_chrome():
    for c in CHROME:
        if Path(c).exists() or shutil.which(c):
            return c
    return None


def print_pdf(chrome, html, target):
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        src.write_text(html, encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                        "--user-data-dir=" + str(Path(tmp) / "profile"), "--print-to-pdf=" + str(target), src.as_uri()],
                       check=True, capture_output=True, timeout=120)


def page_count(pdf):
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


def build(force=False):
    """Print any PDF whose HTML changed. Returns the list of stems printed."""
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    chrome = find_chrome()
    done = []
    for stem, cfg in PRINTABLES.items():
        target = OUT / (stem + ".pdf")
        # The biggest font that still fits on one page; the hash is of the 10 pt HTML so it only changes with the content.
        key = hashlib.sha256(html_for(stem, cfg, 10).encode("utf-8")).hexdigest()
        if not force and hashes.get(stem, {}).get("html") == key and target.exists():
            continue
        if not chrome:
            print("Warning: printables: %s.pdf is out of date, but Google Chrome was not found to print it." % stem)
            continue
        for font in (10, 9.5, 9, 8.5, 8, 7.5):
            print_pdf(chrome, html_for(stem, cfg, font), target)
            if page_count(target) == 1:
                break
        else:
            sys.exit("Error: printables: %s.pdf doesn't fit on one A4 page even at 7.5 pt. Use fewer sections." % stem)
        hashes[stem] = {"html": key, "font": font}
        done.append(stem)
    for old in OUT.glob("*.pdf"):
        if old.stem not in PRINTABLES:
            old.unlink()
    HASHES.write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return done


if __name__ == "__main__":
    printed = build(force="--force" in sys.argv)
    print("Printed %d checklist PDF(s)%s" % (len(printed), (": " + ", ".join(printed)) if printed else ""))
