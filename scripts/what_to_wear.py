"""What-to-wear helper (tools/what-to-wear.html, static/what-to-wear.js).

data/what_to_wear.json holds the weather numbers (official climate normals, each with its source and checked date: the
place's "source", or a month's "src" key into "sources") and the outfit rules: temperature bands, a rain threshold and snow extras, written once.
This module works out every place + month outfit at build time, so the JS only picks which ready-made result to show.
Months we have no numbers for are never shown or guessed.
Without JavaScript the page shows a table of every place and month and the outfit for it.
"For: everyone / women / men": items may carry "for" wording and "picks_for" picks; every result holds all three
wordings (the women and men ones hidden) and three pick lists, so the JS only swaps which is shown.
The Hindi twin (hi/what-to-wear.html) is built here too, from the same results and data/hindi_what_to_wear.json.
build.py calls register(B) where it lists TOOLS, and build(B, ...) after the guides, so guide links can be checked.
"""
import json
import re
import sys
import urllib.parse
from html import escape as e

from common import ROOT

FILE = ROOT / "data" / "what_to_wear.json"
PATH = "tools/what-to-wear.html"
MAKER = "tools/packing-list-maker.html"
SHOW = 6  # pick cards in a result
WHO = ("all", "women", "men")


def register(B):
    if not FILE.exists():
        return
    B.TOOLS.append((PATH, "What to wear helper", "Free tool", "What should I wear there?",
                    "Pick a place and month, like Manali in December or Dubai in January, and see the temperatures and what to wear.",
                    "What to wear", "jacket", "clothing", "snow-jacket"))


def temp(x):
    """17 -> '17 °C', -3 -> '−3 °C', [30, 31] -> '30–31 °C'."""
    def n(v):
        return ("%.1f" % v).rstrip("0").rstrip(".").replace("-", "−")
    return (n(x[0]) + "–" + n(x[1]) if isinstance(x, list) else n(x)) + " °C"


def hi(x):
    return max(x) if isinstance(x, list) else x


def lo(x):
    return min(x) if isinstance(x, list) else x


def band(data, t):
    for b in data["bands"]:
        if b["below"] is None or t < b["below"]:
            return b


def month_order(data):
    """Months from October, the start of our season, round to September."""
    keys = [k for k, _ in data["months"]]
    start = keys.index("oct")
    return keys[start:] + keys[:start]


def place_months(data, p):
    have = {k for s in p["spots"] for k in s["months"]}
    return [k for k in month_order(data) if k in have]


def is_range(rows):
    return any(r.get("range") for _, r in rows)


def sources(data, p, mon):
    """The sources of one place and month: each spot's month 'src' key, else the place's own source."""
    out = []
    for s in p["spots"]:
        r = s["months"].get(mon)
        if r is not None:
            src = data["sources"][r["src"]] if r.get("src") else p["source"]
            if src not in out:
                out.append(src)
    return out


def item_picks(item, who):
    return item.get("picks_for", {}).get(who, item.get("picks", [])) if who != "all" else item.get("picks", [])


def outfit(data, p, mon):
    """Same result the page shows: bands, items in groups, flags and picks (for everyone, women and men) for one place and month."""
    rows = [(s["name"], s["months"][mon]) for s in p["spots"] if mon in s["months"]]
    cold = min(lo(r["night"]) for _, r in rows)
    warm = max(hi(r["day"]) for _, r in rows)
    if is_range(rows):  # the guide gives "about -3 to 17 °C": dress the day for the middle, not the warmest hour
        warm = (warm + cold) / 2
    rain = max((r.get("rain_mm") or 0) for _, r in rows)
    db, nb = band(data, warm), band(data, cold)
    snow = p.get("snow", {}).get(mon, "")
    shoes = nb["shoes"] if nb["id"] == "freezing" else db["shoes"]
    if snow:
        shoes = ["waterproof-shoes"] + [s for s in shoes if s != "warm-shoes"]
    extras = list(db.get("extras", []))
    if rain >= data["rain"]["min_mm"] and not snow:
        extras += data["rain"]["extras"]
    if snow:
        extras += data["snow"]["extras"]
    groups = [("By day", db["day"]), ("Evenings and nights", nb["night"]), ("Shoes", shoes), ("Also pack", extras)]
    seen, clean = set(), []
    for head, items in groups:
        items = [i for i in items if not (i in seen or seen.add(i))]
        if items:
            clean.append((head, items))
    every = [i for _, items in clean for i in items]
    picks_for = {}
    for who in WHO:
        picks = []
        for n in range(3):  # first pick of every item, then the second ones, so a poncho isn't crowded out by jackets
            for i in every:
                row = item_picks(data["items"][i], who)
                if n < len(row) and row[n] not in picks:
                    picks.append(row[n])
        picks_for[who] = picks[:SHOW]
    return {"rows": rows, "warm": warm, "cold": cold, "rain": rain, "day_band": db, "night_band": nb, "range": is_range(rows),
            "snow": snow, "snow_note": p.get("snow_note", {}).get(mon, ""), "groups": clean, "picks": picks_for["all"],
            "picks_for": picks_for, "sources": sources(data, p, mon)}


def summary(data, o):
    """A short outfit line for the table, like 'thermals, a puffer jacket, cap and gloves; warm boots'."""
    parts = []
    for head, items in o["groups"]:
        words = [data["items"][i]["short"] for i in items]
        parts.append(", ".join(words))
    return "; ".join(parts)


def check(B, data, deals_by_asin):
    months = {k for k, _ in data["months"]}
    items = data["items"]
    for b in data["bands"]:
        for key in ("day", "night", "shoes", "extras"):
            for i in b.get(key, []):
                if i not in items:
                    sys.exit("Error: what to wear band %s uses unknown item %s" % (b["id"], i))
    for i in data["rain"]["extras"] + data["snow"]["extras"]:
        if i not in items:
            sys.exit("Error: what to wear rain/snow uses unknown item %s" % i)
    for k, it in items.items():
        for a in it.get("picks", []) + [a for who in it.get("picks_for", {}).values() for a in who]:
            if a not in deals_by_asin:
                sys.exit("Error: what to wear item %s uses %s, which is not in data/deals.json" % (k, a))
        for who in list(it.get("for", {})) + list(it.get("picks_for", {})):
            if who not in WHO[1:]:
                sys.exit("Error: what to wear item %s has wording or picks for %r (use women or men)" % (k, who))
    for key, src in data.get("sources", {}).items():
        if not src.get("checked") or not src.get("label"):
            sys.exit("Error: what to wear source %s needs a label and a checked date" % key)
    slugs = set()
    for p in data["places"]:
        if p["slug"] in slugs:
            sys.exit("Error: what to wear has two places called %s" % p["slug"])
        slugs.add(p["slug"])
        if not p.get("source", {}).get("checked"):
            sys.exit("Error: what to wear %s has no source checked date" % p["slug"])
        for s in p["spots"]:
            for mon, r in s["months"].items():
                if mon not in months:
                    sys.exit("Error: what to wear %s has unknown month %s" % (p["slug"], mon))
                if "day" not in r or "night" not in r:
                    sys.exit("Error: what to wear %s %s %s needs a day and a night number" % (p["slug"], s["name"], mon))
                if r.get("src") and r["src"] not in data.get("sources", {}):
                    sys.exit("Error: what to wear %s %s %s uses unknown source %s" % (p["slug"], s["name"], mon, r["src"]))
        for key in ("snow", "snow_note", "notes"):
            for mon in p.get(key, {}):
                if mon not in place_months(data, p):
                    sys.exit("Error: what to wear %s has a %s for %s but no numbers for that month" % (p["slug"], key, mon))
    if re.search(r"(₹|\bRs\.?\s?|\bINR\s?)\d|\bratings?\b|\bout of 5\b|\d stars?\b|★|\bprice|\bcheap|\bbudget",
                 json.dumps(data, ensure_ascii=False), re.I):
        sys.exit("Error: data/what_to_wear.json mentions a price or rating.")


def build(B, cfg, deals_by_asin, pages, lastmod):
    if not FILE.exists():
        return
    data = json.loads(FILE.read_text(encoding="utf-8"))
    check(B, data, deals_by_asin)
    updated = data["updated"]
    mname = dict((k, v) for k, v in data["months"])
    items = data["items"]
    url = B.abs_url(cfg, PATH)
    wa = "https://wa.me/?text=" + urllib.parse.quote(url, safe="")

    def built(href):
        return (B.DOCS / href.split("#")[0]).exists()

    def links(p):
        out = []
        if p.get("guide") and built(p["guide"]):
            out.append((p["guide"], "%s trip guide" % p["name"]))
        if p.get("packing") and built(p["packing"]):
            label = "%s packing list" % p["name"] if p["packing"].startswith("guides/") else {
                "packing/hills.html": "Winter hill trip packing list", "packing/beach.html": "Beach trip packing list",
                "packing/weekend.html": "Weekend trip packing list", "packing/index.html": "Packing checklists",
                "packing/abroad.html": "International trip packing list"}.get(p["packing"], "Packing list")
            out.append((p["packing"], label))
        out += [(h, t) for h, t in p.get("more", []) if built(h)]
        if built(MAKER):
            out.append((MAKER, "Make your own packing list"))
        return out

    def src_line(o, checked="checked on"):
        return "; ".join((f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(s["label"])}</a>' if s.get("url") else e(s["label"]))
                         + ", %s %s" % (checked, B.fmt_date(s["checked"])) for s in o["sources"])

    def li(i):
        """One outfit line: the everyone wording, plus hidden women and men wordings where the item has them."""
        it = items[i]
        if not it.get("for"):
            return f"<li>{e(it['label'])}</li>"
        alt = "".join(f'<span data-for="{w}" hidden>{e(it["for"].get(w, it["label"]))}</span>' for w in WHO[1:])
        return f'<li><span data-for="all">{e(it["label"])}</span>{alt}</li>'

    def weather_lines(p, o):
        lines = []
        for name, r in o["rows"]:
            rain = ("rain about %s mm" % B.num(r["rain_mm"])) if r.get("rain_mm") is not None else (r.get("rain_text", "").lower() and "rain: " + r["rain_text"].lower())
            if r.get("range"):
                t = "about %s at night to %s by day" % (temp(r["night"]), temp(r["day"]))
            else:
                t = "days about %s, nights about %s" % (temp(r["day"]), temp(r["night"]))
            lead = "" if len(o["rows"]) == 1 and name == p["name"] else "<strong>%s:</strong> " % e(name)
            lines.append("<li>%s%s%s</li>" % (lead, t, ("; " + e(rain)) if rain else ""))
        return "".join(lines)

    # Every place + month, worked out once: a result block for the JS and a table row for everyone.
    results, table_rows, months_of, cases = [], [], {}, {}
    for p in data["places"]:
        ms = place_months(data, p)
        months_of[p["slug"]] = ms
        link_html = " &middot; ".join(f'<a href="../{e(h)}">{e(t)}</a>' for h, t in links(p))
        have = ", ".join(mname[m] for m in ms)
        for i, mon in enumerate(ms):
            o = outfit(data, p, mon)
            cases[(p["slug"], mon)] = o
            key = "%s-%s" % (p["slug"], mon)
            flags = []
            if o["snow"]:
                flags.append("<li><strong>Snow:</strong> %s.</li>" % e(o["snow"]))
            elif o["snow_note"]:
                flags.append("<li><strong>Snow:</strong> %s.</li>" % e(o["snow_note"]))
            if o["rain"] >= data["rain"]["min_mm"] and not o["snow"]:
                if o["cold"] < 0:  # below freezing much of it falls as snow: the normals count both as water
                    flags.append("<li><strong>Rain or snow:</strong> up to about %s mm in the month (snow counted as water), so pack for wet and cold days.</li>" % B.num(round(o["rain"])))
                else:
                    flags.append("<li><strong>Rain:</strong> up to about %s mm in the month, so pack for showers.</li>" % B.num(round(o["rain"])))
            groups = "".join(f'<h4>{e(h)}</h4><ul class="ww-list">' + "".join(li(i) for i in its) + "</ul>"
                             for h, its in o["groups"])
            def lc(b):
                return e(b["label"][0].lower() + b["label"][1:])
            bands = (f'{lc(o["day_band"])}, day and night' if o["day_band"] is o["night_band"] else
                     f'{lc(o["day_band"])} by day and {lc(o["night_band"])} at night')
            if len(o["rows"]) > 1:
                bands += " (coldest nights: %s)" % e(min(o["rows"], key=lambda nr: lo(nr[1]["night"]))[0])
            results.append(f"""<div class="ww-case" data-case="{key}" data-picks="{" ".join(o["picks"])}" data-picks-women="{" ".join(o["picks_for"]["women"])}" data-picks-men="{" ".join(o["picks_for"]["men"])}">
<h2 class="ww-title" tabindex="-1">What to wear in {e(p["name"])} in {e(mname[mon])}</h2>
<ul class="ww-weather">{weather_lines(p, o)}{"".join(flags)}</ul>
<p class="muted small">Dress for: {bands}.</p>
<div class="ww-groups">{groups}</div>
<p class="pm-notes">{e(p.get("notes", {}).get(mon, p["note"]))}</p>
<p class="small"><strong>Plan the trip:</strong> {link_html}</p>
<p class="checked">Numbers: {src_line(o)}. These are {"usual ranges" if o["range"] else "long-term averages"}, so check the forecast a few days before you go.</p>
</div>""")
            weather = "<br>".join(f'{e(n) + ": " if len(o["rows"]) > 1 else ""}{temp(r["day"])} / {temp(r["night"])}' for n, r in o["rows"])
            texts = [r.get("rain_text", "") for _, r in o["rows"] if r.get("rain_text")]
            known = any(r.get("rain_mm") is not None for _, r in o["rows"])
            wet = ("Snow possible" if o["snow"] else "Rain likely" if o["rain"] >= data["rain"]["min_mm"]
                   else "A few showers" if any("shower" in t.lower() for t in texts) else "Mostly dry" if known or texts else "–")
            first = f'<th rowspan="{len(ms)}" id="{p["slug"]}"><a href="../{e(p.get("guide") or p["packing"])}">{e(p["name"])}</a></th>' if i == 0 else ""
            table_rows.append(f"<tr>{first}<td>{e(mname[mon])}</td><td>{weather}</td><td>{wet}</td><td>{e(summary(data, o))}</td></tr>")

    def opt_group(where, label):
        return f'<optgroup label="{label}">' + "".join(
            f'<option value="{p["slug"]}">{e(p["name"])}</option>' for p in data["places"] if p["where"] == where) + "</optgroup>"

    place_opts = opt_group("india", "In India") + opt_group("abroad", "Abroad")
    payload = {"months": dict(data["months"]), "places": {p["slug"]: {"name": p["name"], "months": months_of[p["slug"]]} for p in data["places"]}}
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    pool_asins = []
    for o in cases.values():
        for who in WHO:
            pool_asins.extend(a for a in o["picks_for"][who] if a not in pool_asins)
    pool = "".join(B.card(cfg, deals_by_asin[a], "../").replace('<article class="card"', '<article class="card" data-asin="%s"' % a, 1)
                   for a in pool_asins)

    band_rows = "".join(f'<tr><th>{e(b["label"])}</th><td>{e(", ".join(items[i]["short"] for i in b["day"]))}</td>'
                        f'<td>{e(", ".join(items[i]["short"] for i in b["night"]))}</td><td>{e(", ".join(items[i]["short"] for i in b["shoes"] + b.get("extras", [])))}</td></tr>'
                        for b in data["bands"])
    all_months = sorted({m for ms in months_of.values() for m in ms}, key=month_order(data).index)
    n_places = len(data["places"])

    def say(slug, mon, who="all"):
        """A plain FAQ answer for a place and month, from the same outfit rules."""
        p = next(x for x in data["places"] if x["slug"] == slug)
        o = cases[(slug, mon)]
        if len(o["rows"]) == 1:
            r = o["rows"][0][1]
            w = ("about %s at night to %s by day" if r.get("range") else "days about %s and nights about %s")
            w = w % ((temp(r["night"]), temp(r["day"])) if r.get("range") else (temp(r["day"]), temp(r["night"])))
        else:
            w = "; ".join("%s days about %s, nights about %s" % (n, temp(r["day"]), temp(r["night"])) for n, r in o["rows"][:2])
        def word(i):
            w = items[i].get("for", {}).get(who) if who != "all" else None
            return (w[0].lower() + w[1:]) if w else items[i]["short"]
        wear = "; ".join("%s: %s" % (h.lower(), ", ".join(word(i) for i in its)) for h, its in o["groups"])
        return "%s in %s has %s. Wear %s." % (p["name"], mname[mon], w, wear)

    faq = [
        ("What to wear in Manali in December?", say("manali", "dec") + " Snow is possible but not certain, so take waterproof shoes."),
        ("What to wear in Kashmir in December?", say("kashmir", "dec") + " Gulmarg often gets snow, and Chillai Kalan starts on 21 December."),
        ("What to wear in Manali in October?", say("manali", "oct") + " October is dry and sunny, but nights are cold, so pack a warm jacket."),
        ("What to wear in Kashmir in October?", say("kashmir", "oct") + " Gulmarg is far colder than Srinagar, so take your warmest layers for a day trip there."),
        ("What to wear in Dubai in December for ladies?", say("dubai", "dec", "women") + " Cover your shoulders and midriff in public places, and keep swimwear for the beach and pool."),
        ("What to wear in Goa for men?", say("goa", "dec", "men") + " Put a shirt or kaftan over swimwear when you go into town."),
        ("What to wear in Shimla in December?", say("shimla", "dec") + " Snow is more likely in January and February."),
        ("What to wear in Thailand?", say("thailand", "dec") + " Cover your shoulders for temples and the Grand Palace."),
        ("What to wear in Varanasi in winter?", say("varanasi", "jan") + " Early mornings on the ghats are the coldest part of the day."),
        ("Why can I only pick some months?",
         "We only show months we have official climate numbers for (IMD for India, DHM for Nepal, the UAE's met office for Dubai), mostly October to March. We never guess the weather for other months. More months are coming."),
        ("Is there a version for women or men?",
         "Yes. Pick Women or Men under For and the outfit list changes: for example kurtas, palazzos and a stole for women, and shirts and chinos for men, and the picks show women's or men's jackets, thermals and shoes."),
    ]
    faq_html, faq_schema = B.faq_block(faq)

    title = "What to wear in Manali, Kashmir, Goa, Dubai and more, by month"
    seo = "What to wear in Manali, Kashmir, Goa, Dubai: October to March"
    desc = ("Free what-to-wear helper: pick a place and month, like Manali or Kashmir in October or December, Goa, Dubai or Nepal, "
            "for women or men, and see day and night temperatures and a simple outfit list.")
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>What to wear</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">A free tool for {n_places} places. Updated {B.fmt_date(updated)}</p>"""
    head = B.page_head("clothing", f'<div class="media media-tile tint-clothing">{B.icon("jacket", "icon media-icon")}</div>', inner, "../")
    body = f"""{head}
<div class="wrap"><article class="guide">
<p class="pm-nojs" id="ww-nojs">Turn on JavaScript for the quick picker, or find your place in the table below.</p>
<form class="checker ww" id="ww" onsubmit="return false" hidden>
<div class="checker-fields"><label>Where are you going?<select id="ww-place">{place_opts}</select></label>
<label>Month<select id="ww-month"></select></label>
<label>For<select id="ww-for"><option value="all">Everyone</option><option value="women">Women</option><option value="men">Men</option></select></label></div>
<p class="hint" id="ww-more" aria-live="polite"></p>
</form>
<section id="ww-result" hidden>
<div id="ww-case"></div>
<h3 id="ww-picks-head">Our picks for this trip</h3>
<div class="grid" id="ww-grid"></div>
<p class="pm-actions"><a class="btn btn-whatsapp" id="ww-wa" href="{e(wa)}" target="_blank" rel="noopener">Share on WhatsApp</a></p>
</section>
<template id="ww-cases">{"".join(results)}</template>
<template id="ww-pool">{pool}</template>
<script type="application/json" id="ww-data">{blob}</script>
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Dress in layers.</strong> Days and nights can differ by 10–17 °C in winter, in the hills and in Rajasthan alike.</li>
<li>Below 5 °C at night, pack thermals, a puffer jacket, a cap and gloves. Above 25 °C by day, pack light cotton, sunglasses and sunscreen.</li>
<li>Going where it snows or rains? Add waterproof shoes, or a poncho and a phone pouch.</li>
</ul></div>
<h2 id="table">What to wear in each place, by month</h2>
<p>Day and night are long-term averages from each place's weather service (IMD for India, DHM for Nepal, the national met offices abroad); each result names its source. The table shows the outfit for everyone; pick Women or Men above for kurtas, stoles, chinos and matching picks. We show only the months we have checked numbers for ({", ".join(mname[m] for m in all_months)}). More months coming.</p>
<div class="table-wrap"><table class="compare snug ww-table"><thead><tr><th>Place</th><th>Month</th><th>Day / night</th><th>Rain or snow</th><th>What to wear</th></tr></thead>
<tbody>{"".join(table_rows)}</tbody></table></div>
<h2 id="rules">How we pick the clothes</h2>
<p>Day clothes follow the warmest day in the month, and evening clothes the coldest night. Where a guide gives only a range, as for Manali in December and January, day clothes follow the middle of it. Below 0 °C at night, a wet month's rain may fall as snow. Rain of {data["rain"]["min_mm"]} mm or more in a month adds a poncho, a phone pouch and quick-dry clothes, and a chance of snow adds waterproof shoes, gloves and sunglasses.</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Temperature</th><th>By day</th><th>At night</th><th>Shoes and extras</th></tr></thead>
<tbody>{band_rows}</tbody></table></div>
<p>Packing too? Make a list for your days, month and family with the <a href="packing-list-maker.html">packing list maker</a>, or read <a href="../guides/winter-clothes-for-hill-trips.html">what to wear on a winter hill trip</a>.</p>
{faq_html}
{B.tool_pills("../", PATH)}
</article></div>
<script src="../assets/what-to-wear.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    crumbs = B.crumbs_schema(cfg, [("Home", ""), ("What to wear", PATH)])
    app = {"@context": "https://schema.org", "@type": "WebApplication", "name": "What to wear helper", "url": url,
           "applicationCategory": "TravelApplication", "operatingSystem": "Any", "description": desc}
    pages.append(B.write(PATH, B.page(cfg, seo, desc, body, 1, PATH,
                                      [B.tool_article(cfg, seo, desc, PATH, updated, updated), crumbs, faq_schema, app],
                                      og_type="article", photo="snow-jacket")))
    lastmod[PATH] = updated
