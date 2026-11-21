"""Excess baggage calculator: tools/bag-weight.html (the URL is kept from the old bag weight estimator).

Reads data/airlines.json (flights within India), data/airlines_intl.json (international flights) and
data/extra_baggage.json (domestic excess fees), so airlines added there appear here on the next build.
The traveller picks the airline, route and fare, types what each bag really weighs, and static/bag-weight.js
compares it with the allowance and shows the airline's own excess charges from our data.

Without JS the page shows the same allowance and excess fee tables. No number here is made up: allowances are
read from each fare's text with parse_allowance() and, when a fare depends on the route, the tool asks for the
figure on the traveller's ticket instead of guessing.
"""

import json
import re
from html import escape as e

import carry_on_guide

PATH = "tools/bag-weight.html"
UPDATED = "2026-11-21"
KG = r"(\d+(?:\.\d+)?) kg"
# Picks under the calculator. Keep the reasons true to each pick's listed specs in data/deals.json.
WEIGHT_PICKS = [
    ("B07Q822CWX", "Weigh it at home", "A hand-held luggage scale: hook the bag on and lift. It reads up to 50 kg in 0.1 kg steps, and the battery is included."),
    ("B0F5HGLC5Q", "Light cabin trolley", "2.2 kg empty, so about 4.8 kg of a 7 kg cabin limit is left for your things. Fits Air India by its listed size."),
    ("B0GNSKLF5Z", "Light medium trolley", "2.52 kg empty, the lightest medium trolley we found, so about 12.5 kg of a 15 kg fare is left for your things."),
]
# Rough empty weights, the same figures our luggage pages state. Only for "no scale?".
BAG_TYPES = [("Backpack", 0.6), ("Duffle bag", 1.2), ("Soft cabin trolley", 2.4), ("Hard cabin trolley", 2.7),
             ("Medium check-in trolley", 3.5), ("Large check-in trolley", 4.5)]


def parse_allowance(text):
    """A fare's checked allowance text -> {"kg": total} or {"per_bag", "pieces"} (+ "note"), or None when it isn't one clear figure."""
    s = text.strip()

    def rest(r):
        r = r.strip(" ,;")
        if re.search(r"\d+ kg", r):
            return None  # a second kg figure: the allowance depends on the route
        return r.strip("()")

    m = re.match(r"no (free )?(check-in|checked) bag", s, re.I)
    if m:
        return {"kg": 0, "pieces": 0, "note": rest(s[m.end():]) or ""}
    pats = [
        (r"^(\d+) (?:bags|pieces), (?:each )?(?:up to )?" + KG + r"(?: each)?(.*)$", lambda m: {"per_bag": float(m[2]), "pieces": int(m[1])}),
        (r"^1 (?:bag|piece),? (?:up to )?" + KG + r"(.*)$", lambda m: {"per_bag": float(m[1]), "pieces": 1}),
        (r"^" + KG + r" \+ " + KG + r" extra(.*)$", lambda m: {"kg": float(m[1]) + float(m[2])}),
        (r"^" + KG + r", (?:up to )?(\d+) pieces?(.*)$", lambda m: {"kg": float(m[1]), "pieces": int(m[2])}),
        (r"^" + KG + r"(.*)$", lambda m: {"kg": float(m[1])}),
    ]
    for pat, make in pats:
        m = re.match(pat, s, re.I)
        if m:
            note = rest(m.groups()[-1])
            if note is None:
                return None
            out = make(m)
            out["note"] = note
            return out
    return None


def max_bag_kg(note):
    """'No single bag may weigh more than 32 kg' -> 32, when the airline's note says so."""
    m = re.search(r"(?:single|no bag|each bag must weigh less than)[^.]*?\b(\d+) kg", note or "", re.I)
    return int(m.group(1)) if m else None


def personal_rule(a):
    """(shared, kg): shared means the personal item counts inside the cabin bag's kg (or isn't allowed separately)."""
    text = (a.get("personal") or {}).get("summary", "")
    cabin = a["cabin"].get("summary", "")
    if re.search(r"same|within|one piece only|no separate", text, re.I) or re.search(r"in total|included", cabin, re.I):
        return True, None
    m = re.search(r"(?:up to|and) (\d+(?:\.\d+)?) kg", text) or re.search(r"plus a (\d+(?:\.\d+)?) kg personal item", cabin)
    return False, (float(m.group(1)) if m else None)


def airline_record(a, scope, extra, checked):
    shared, pkg = personal_rule(a)
    fares = []
    for c in a["checkin"]:
        if c["fare"].lower().startswith("each bag"):
            continue
        fares.append(dict(fare=c["fare"], text=c["allowance"], rule=parse_allowance(c["allowance"])))
    rec = dict(slug=a["slug"], name=a.get("page_name") or a["name"], scope=scope, page=carry_on_guide.page_href(dict(a, scope=scope), ""),
               official=a["official_url"], sources=a["sources"], checked=a.get("checked") or checked,
               cabin_kg=a["cabin"].get("kg"), cabin_text=a["cabin"].get("summary", ""),
               personal_text=(a.get("personal") or {}).get("summary", ""), personal_shared=shared, personal_kg=pkg,
               fares=fares, note=a.get("checkin_note", ""), max_bag=max_bag_kg(a.get("checkin_note")))
    each = [c["allowance"] for c in a["checkin"] if c["fare"].lower().startswith("each bag")]
    if each:
        rec["each_bag"] = each[0]
    if extra:
        rec["fees"] = dict(airport_per_kg=extra["airport_per_kg"], airport_text=extra["airport_text"],
                           upto=bool(extra.get("airport_upto")), tax=bool(extra.get("airport_tax")),
                           prepaid=extra["prepaid"] or [], prepaid_note=extra.get("prepaid_note", ""),
                           piece_text=extra["piece_text"], cabin_text=extra["cabin_text"], lite=extra.get("lite", ""),
                           page="baggage/extra-baggage-charges/%s.html" % extra["slug"], checked=extra["checked"],
                           sources=extra["sources"])
    elif a.get("excess"):
        rec["excess"] = dict(summary=a["excess"]["summary"], points=a["excess"].get("points", []))
    return rec


def load(B):
    dom = B.load_airlines()
    if not dom:
        return None
    intl = B.load_airlines(B.INTL_AIRLINES_FILE)
    extra = B.load_extra_baggage(dom)
    fees = {x["slug"]: dict(x, checked=extra["checked"]) for x in extra["airlines"]} if extra else {}
    out = [airline_record(a, "domestic", fees.get(a["slug"]), dom["checked"]) for a in dom["airlines"]]
    if intl:
        out += [airline_record(a, "international", None, intl["checked"]) for a in intl["airlines"]]
    world = carry_on_guide.load_world(B)
    if world:
        out += [airline_record(a, "worldwide", None, world["checked"]) for a in world["airlines"]]
    return out


def register(B):
    if B.AIRLINES_FILE.exists():
        B.TOOLS.append((PATH, "Excess baggage calculator", "Free tool", "Excess baggage calculator",
                        "Type what your bags really weigh: see your airline's allowance, how many kg you're over and the official excess fee.",
                        "Check my bags", "check", "luggage", "bathroom-scale"))


def _allowance_table(B, rows):
    body = []
    for r in rows:
        personal = r["personal_text"] or "Not stated"
        fares = "".join("<li><strong>%s:</strong> %s</li>" % (e(f["fare"]), e(f["text"])) for f in r["fares"])
        if r.get("each_bag"):
            fares += "<li><strong>Each bag:</strong> %s</li>" % e(r["each_bag"])
        cabin = r["cabin_text"] + ("" if r["cabin_kg"] else " (no cabin weight limit in our data)")
        body.append(f'<tr><th scope="row"><a href="../{r["page"]}">{e(r["name"])}</a><span class="why">Checked {B.fmt_date(r["checked"])}</span></th>'
                    f'<td>{e(cabin)}</td><td>{e(personal)}</td><td><ul class="bw-fares">{fares}</ul></td></tr>')
    return ('<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Cabin bag</th><th>Personal item</th>'
            '<th>Checked bags by fare</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(body))


def _fee_table(B, rows):
    body = []
    for r in rows:
        f = r["fees"]
        pre = ", ".join("%d kg %s" % (kg, B.rupees(p)) for kg, p in f["prepaid"]) or "Not listed: " + f["prepaid_note"]
        body.append(f'<tr><th scope="row"><a href="../{f["page"]}">{e(r["name"])}</a><span class="why">Checked {B.fmt_date(f["checked"])}</span></th>'
                    f'<td>{e(f["airport_text"])}</td><td>{e(pre)}</td><td>{e(f["piece_text"])}</td><td>{e(f["cabin_text"])}</td></tr>')
    return ('<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>At the airport</th><th>Pre-booked online</th>'
            '<th>Extra bag</th><th>Heavy cabin bag</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(body))


def _intl_fee_table(B, rows):
    body = []
    for r in rows:
        if r.get("excess"):
            cell = e(r["excess"]["summary"]) + "."
        else:
            cell = 'Not in our data yet. See <a href="%s" target="_blank" rel="noopener">%s\'s official baggage page</a>.' % (e(r["official"]), e(r["name"]))
        body.append(f'<tr><th scope="row"><a href="../{r["page"]}">{e(r["name"])}</a></th><td>{cell}</td></tr>')
    return ('<div class="table-wrap"><table class="result-table"><thead><tr><th>Airline</th><th>Excess or extra bag fees</th></tr></thead>'
            '<tbody>%s</tbody></table></div>' % "".join(body))


def build(B, cfg, deals, pages, lastmod):
    rows = load(B)
    if not rows:
        return
    dom = [r for r in rows if r["scope"] == "domestic"]
    intl = [r for r in rows if r["scope"] == "international"]
    world = [r for r in rows if r["scope"] == "worldwide"]
    by_asin = {d["asin"]: d for d in deals}
    picks = [(by_asin[a], label, why) for a, label, why in WEIGHT_PICKS if a in by_asin]
    scale = by_asin.get("B07Q822CWX")
    scale_html = f'<a href="../picks/{scale["asin"]}.html">luggage scale</a>' if scale else "luggage scale"
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    n = len(rows)
    title = "Excess baggage calculator: allowance and overweight fee by airline"
    seo = "Excess baggage calculator: baggage allowance and overweight fee by airline"
    desc = ("Type what your cabin bag, personal item and checked bags weigh. See your airline's allowance by fare, how many kg "
            "you're over and the official excess baggage charge, for %d airlines. Free, no sign-up." % n)
    dom_names = B.and_list(e(r["name"]) for r in dom)
    opts = lambda rs: "".join('<option value="%s">%s</option>' % (e(r["slug"]), e(r["name"])) for r in rs)
    rough = "".join("<li>%s: about %s kg empty</li>" % (e(name), B.num(kg)) for name, kg in BAG_TYPES)
    dom_checked = max(r["checked"] for r in dom)
    fee_checked = max(r["fees"]["checked"] for r in dom if r.get("fees"))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>Excess baggage calculator</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">A free tool. {n} airlines. Updated {B.fmt_date(UPDATED)}</p>"""
    head = B.page_head("travel-gear", f'<div class="media media-tile tint-travel-gear">{B.icon("check", "icon media-icon")}</div>', inner, "../")
    body = f"""{head}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li>Weigh each bag at home with a {scale_html}, then type the real weights below. The tool compares them with your airline's allowance for your fare.</li>
<li>On flights within India, {dom_names} charge about ₹775 to ₹850 per kg over the allowance at the airport. Pre-booking extra kg online is usually cheaper.</li>
<li>Every allowance and fee here comes from the airline's own website, with the date we checked it. Your ticket and the airline's site are final.</li>
</ul></div>
<form class="checker bw-calc" id="bw" onsubmit="return false" hidden>
<div class="checker-fields bw-top">
<label>Flight<select id="bw-route"><option value="domestic">Within India</option><option value="international">International (to or from India)</option><option value="worldwide">US and Europe airlines</option></select></label>
<label>Airline<select id="bw-airline" data-domestic="{e(opts(dom))}" data-international="{e(opts(intl))}" data-worldwide="{e(opts(world))}">{opts(dom)}</select></label>
<label class="bw-wide">Fare<select id="bw-fare"></select></label>
</div>
<p class="hint" id="bw-allow"></p>
<label id="bw-own-wrap" hidden>Checked allowance on your ticket (kg)<input id="bw-own" type="number" min="0" max="100" step="1" inputmode="decimal" placeholder="e.g. 30"></label>
<fieldset class="bw-weights"><legend>What each bag weighs (kg)</legend>
<div class="checker-fields">
<label>Cabin bag<input id="bw-cabin" type="number" min="0" max="60" step="0.1" inputmode="decimal" placeholder="e.g. 7.5"></label>
<label>Personal item<input id="bw-personal" type="number" min="0" max="30" step="0.1" inputmode="decimal" placeholder="e.g. 2"></label>
<span id="bw-bags" class="bw-bags"><label>Checked bag 1<input class="bw-bag" type="number" min="0" max="60" step="0.1" inputmode="decimal" placeholder="e.g. 16"></label></span>
</div>
<p class="hint"><button type="button" class="link-btn" id="bw-add">+ Add another checked bag</button> <button type="button" class="link-btn" id="bw-clear">Start again</button></p>
</fieldset>
<div id="bw-out" aria-live="polite"></div>
</form>
<noscript><p class="small">The calculator needs JavaScript. The tables below show the same allowances and fees.</p></noscript>
<script type="application/json" id="bw-data">{data}</script>
<p class="checked">Allowances checked on each airline's site between {B.fmt_date(min(r["checked"] for r in rows))} and {B.fmt_date(max(r["checked"] for r in rows))}; domestic excess fees checked {B.fmt_date(fee_checked)}. Fees change often, and the price shown when you pay is final.</p>
<h2>Excess baggage charges on flights within India</h2>
<p>What each airline charges per kg over your free allowance, at the airport and pre-booked online, from its own fees page. Each airline name opens its full extra baggage page.</p>
{_fee_table(B, [r for r in dom if r.get("fees")])}
<h2>Baggage allowance by airline: flights within India</h2>
{_allowance_table(B, dom)}
<h2>Baggage allowance by airline: international flights</h2>
<p>Economy allowances on flights to and from India, from each airline's own pages.</p>
{_allowance_table(B, intl)}
<h2>Baggage allowance by airline: US and European airlines</h2>
<p>American, Delta, United, Southwest, Ryanair, easyJet, Air France and KLM, from their own websites. Compare carry-on sizes on our <a href="../{carry_on_guide.PATH}">carry-on size by airline</a> chart.</p>
{_allowance_table(B, world)}
<h2>Excess baggage on international flights</h2>
<p>International airlines price extra weight by route, so most don't publish one rate per kg. This is what their pages say.</p>
{_intl_fee_table(B, intl + world)}
<h2>How to avoid excess baggage fees</h2>
<ul>
<li><strong>Weigh every bag at home.</strong> A {scale_html} is cheaper than one extra kilo at most airport counters.</li>
<li><strong>Move weight to where you have room.</strong> If your checked bag is over but your cabin bag is under its limit, move heavy things like shoes or books into the cabin bag, within its size and weight limit.</li>
<li><strong>Wear the heaviest clothes.</strong> Put on your jacket and heaviest shoes for the flight instead of packing them.</li>
<li><strong>Pre-book extra kg online.</strong> On flights within India, the airlines' own fee lists show pre-booked kg cost less than paying at the counter. Buy the smallest pack that covers the extra.</li>
<li><strong>Check your fare.</strong> Lite and Basic fares often include no checked bag at all. See our <a href="../baggage/extra-baggage-charges.html">extra baggage charges</a> and <a href="../baggage/international.html">international baggage rules</a>.</li>
</ul>
<details class="bw-rough"><summary>No scale? Rough empty bag weights</summary>
<p class="small">These are typical empty weights only. They tell you how much of your allowance the bag itself uses, not what your packed bag weighs.</p>
<ul>{rough}</ul></details>
{B.top_picks(cfg, picks, "../", "Weigh it at home, or start with a lighter bag")}
<p>More help: <a href="../baggage/index.html">baggage rules for Indian airlines</a>, <a href="../baggage/checker.html">will my bag fit?</a> and <a href="../guides/trolley-bag-capacity-kg-litres.html">how many kg a trolley bag holds</a>.</p>
{{faq}}
{B.tool_pills("../", PATH)}
</article></div>
<script src="../assets/bag-weight.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("How is excess baggage calculated?", "Airlines compare what your bags weigh at check-in with the free allowance on your ticket. On flights within India, IndiGo, Air India, Akasa Air, SpiceJet and Air India Express charge a rate per kg over the allowance at the airport (about ₹775 to ₹850 per kg in their fee lists), or sell cheaper kg packs online before you fly."),
        ("How much is excess baggage per kg on IndiGo?", "IndiGo's fees page lists ₹800 per kg at the airport for domestic flights. Pre-booked online, 3 kg costs ₹2,250 and 5 kg ₹3,750. See the table above for the other slabs and the date we checked."),
        ("Is it cheaper to pre-book extra baggage?", "Usually, yes. On flights within India the airlines' own fee lists show pre-booked kg at about ₹695 to ₹750 per kg against ₹775 to ₹850 at the counter. Buy the smallest pack that covers your extra weight, as unused kg aren't refunded."),
        ("What if my cabin bag is over 7 kg?", "Most airlines will check it in, and its weight then counts towards your checked allowance. Air India, Air India Express and SpiceJet sell extra cabin kg on domestic flights; the calculator shows the charge when your airline has one."),
        ("Does my jacket count in my baggage weight?", "Clothes you wear aren't weighed with your bags, so wearing your heaviest jacket and shoes leaves more room in your allowance."),
    ]
    faq_html, faq_schema = B.faq_block(faq)
    body = body.replace("{faq}", faq_html)
    crumbs = B.crumbs_schema(cfg, [("Home", ""), ("Excess baggage calculator", PATH)])
    pages.append(B.write(PATH, B.page(cfg, seo, desc, body, 1, PATH,
                                      [B.tool_article(cfg, seo, desc, PATH, "2026-11-03", UPDATED), crumbs, faq_schema], og_type="article")))
    lastmod[PATH] = UPDATED
