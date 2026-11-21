"""Carry-on size by airline (worldwide): guides/carry-on-size-by-airline.html.

One table of cabin bag limits for every airline in data/airlines.json, airlines_intl.json and airlines_world.json
(US and European airlines that don't fly our India routes), built from the same data as the cabin bag checker,
so airlines added there appear here too. World airlines have no page of their own: their row anchor here is
their page (the checker and the excess baggage calculator link to it).
"""

import json
from html import escape as e

from common import ROOT

WORLD_FILE = ROOT / "data" / "airlines_world.json"
PATH = "guides/carry-on-size-by-airline.html"
UPDATED = "2026-11-21"
GROUPS = [("North America", "US airlines"), ("Europe", "European airlines"), ("Gulf", "Gulf airlines"), ("Asia", "Asian airlines"),
          ("India", "Indian airlines (flights within India)")]


def load_world(B):
    return B.load_airlines(WORLD_FILE) if WORLD_FILE.exists() else None


def page_href(a, p):
    """Where an airline's name links: its baggage page, or its row on this guide for world airlines."""
    if a.get("scope") == "worldwide":
        return "%s%s#%s" % (p, PATH, a["slug"])
    return "%sbaggage/%s.html" % (p, a["slug"])


def _inch(cm):
    return ("%.1f" % (cm / 2.54)).rstrip("0").rstrip(".")


def build(B, cfg, deals, pages, lastmod):
    dom = B.load_airlines()
    intl = B.load_airlines(B.INTL_AIRLINES_FILE)
    world = load_world(B)
    if not (dom and intl and world):
        return
    rows = [dict(a, region=a.get("region") or "India", checked=a.get("checked") or dom["checked"]) for a in dom["airlines"]]
    rows += [dict(a, checked=a.get("checked") or intl["checked"]) for a in intl["airlines"] if a.get("checker", True)]
    rows += [dict(a, checked=a.get("checked") or world["checked"]) for a in world["airlines"]]
    sections = []
    for key, label in GROUPS:
        group = [a for a in rows if a.get("region") == key]
        if not group:
            continue
        trs = []
        for a in group:
            c = a["cabin"]
            dims = c.get("dims_cm")
            size = ("%s cm<span class=\"why\">%s in</span>" % (" x ".join(B.num(x) for x in dims), " x ".join(_inch(x) for x in dims))) if dims else "Not given"
            kg = ("%s kg" % B.num(c["kg"])) if c.get("kg") else "No limit given"
            src = a["sources"][0]
            trs.append(f'<tr id="{e(a["slug"])}"><th scope="row"><a href="{e(page_href(a, "../"))}">{e(a.get("page_name") or a["name"])}</a>'
                       f'<span class="why"><a href="{e(src["url"])}" target="_blank" rel="noopener">Official page</a>, checked {B.fmt_date(a["checked"])}</span></th>'
                       f'<td>{size}</td><td>{kg}</td><td>{e((a.get("personal") or {}).get("summary", "Not stated"))}</td>'
                       f'<td>{e(a.get("checkin_summary", ""))}</td></tr>')
        sections.append(f'<h2>{e(label)}</h2><div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Carry-on size</th>'
                        f'<th>Carry-on weight</th><th>Personal item</th><th>Checked bags</th></tr></thead><tbody>{"".join(trs)}</tbody></table></div>')
    world_names = B.and_list(e(a["name"]) for a in world["airlines"])
    n = len(rows)
    title = "Carry-on size by airline (worldwide): cabin bag limits chart"
    seo = "Carry-on size by airline: cabin bag size and weight chart for %d airlines" % n
    desc = ("Carry-on bag size and weight limits for %d airlines, from American, Delta, United, Ryanair and easyJet to Emirates, "
            "Lufthansa and IndiGo, in cm and inches, read on each airline's own website." % n)
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span><a href="../baggage/index.html">Baggage rules</a><span>/</span>Carry-on size by airline</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">{n} airlines. Updated {B.fmt_date(UPDATED)}</p>"""
    head = B.page_head("luggage", f'<div class="media media-tile tint-luggage">{B.icon("ruler", "icon media-icon")}</div>', inner, "../")
    body = f"""{head}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li>The most common carry-on limit is about 55 x 35 x 25 cm or 56 x 36 x 23 cm (22 x 14 x 9 in), including wheels and handles.</li>
<li>US airlines (American, Delta, United) give no weight limit for the carry-on; most airlines in Asia, the Gulf and India allow 7 kg, Lufthansa 8 kg, and Air France and KLM 12 kg together with the small bag.</li>
<li>Low-cost airlines like Ryanair and easyJet include only a small under-seat bag for free; the full-size cabin bag costs extra.</li>
</ul></div>
<p>A bag that fits the strictest airline you fly will fit them all. Type your bag's size into our <a href="../baggage/checker.html">cabin bag checker</a> to test it against every airline at once, and check your packed weights with the <a href="../tools/bag-weight.html">excess baggage calculator</a>.</p>
{"".join(sections)}
<p class="checked">Every limit comes from the airline's own website, read on the date shown. {world_names} were added on {B.fmt_date(world["checked"])}. Rules can change, and some planes have smaller bins, so check your booking before you fly.</p>
<h2>How to measure a carry-on</h2>
<ul>
<li><strong>Include wheels and handles.</strong> Most airlines measure the bag as it is, with wheels, handles and outside pockets.</li>
<li><strong>Measure it packed.</strong> A soft bag stuffed full can be several cm thicker than when it's empty.</li>
<li><strong>Know your inches.</strong> 22 x 14 x 9 inches is about 56 x 36 x 23 cm. See our <a href="../baggage/luggage-size-chart.html">luggage size chart</a> for more.</li>
</ul>
<p>More help: <a href="../baggage/international.html">international baggage rules</a>, <a href="../baggage/index.html">baggage rules for Indian airlines</a> and <a href="../baggage/extra-baggage-charges.html">extra baggage charges</a>.</p>
{{faq}}
{B.tool_pills("../", PATH)}
</article></div>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("What is the standard carry-on size?", "There is no single world standard. The most common limits are 55 x 35 x 25 cm in Europe and Asia and 22 x 14 x 9 inches (56 x 36 x 23 cm) on American and United. Southwest allows a bigger 24 x 16 x 10 inch bag."),
        ("Do US airlines weigh carry-on bags?", "American, Delta, United and Southwest give no weight limit for carry-on bags on the pages we read. Your bag must fit the size limit and the overhead bin."),
        ("Is a personal item free on Ryanair and easyJet?", "Yes. Ryanair includes one small bag up to 40 x 30 x 20 cm, and easyJet one under-seat bag up to 45 x 36 x 20 cm and 15 kg. A larger cabin bag costs extra unless your fare includes it."),
        ("What carry-on size fits most airlines?", "A bag of 55 x 35 x 20 cm weighing up to 7 kg packed fits most airlines in this chart, but not Qatar Airways (50 cm long) or Gulf Air (45 cm long). Test your own bag in our cabin bag checker."),
    ]
    faq_html, faq_schema = B.faq_block(faq)
    body = body.replace("{faq}", faq_html)
    crumbs = B.crumbs_schema(cfg, [("Home", ""), ("Baggage rules", "baggage/index.html"), ("Carry-on size by airline", PATH)])
    pages.append(B.write(PATH, B.page(cfg, seo, desc, body, 1, PATH,
                                      [B.tool_article(cfg, seo, desc, PATH, UPDATED, UPDATED), crumbs, faq_schema], og_type="article")))
    lastmod[PATH] = UPDATED
