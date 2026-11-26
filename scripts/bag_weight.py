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
UPDATED = "2026-11-26"
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


# Excess baggage on international flights from India, Indian airlines' own fee pages, read on 26 Nov 2026.
# Only the routes and figures we read; re-check before changing. Each row: airline, route, pre-booked, at the airport, source.
INTL_FEES_CHECKED = "2026-11-26"
INTL_FEES = [
    ("Akasa Air", "India to Abu Dhabi, Doha or Riyadh", "5 kg ₹6,000, 10 kg ₹12,000", "₹1,500 per kg",
     "https://www.akasaair.com/add-ons/excess-baggage"),
    ("Air India Express", "India to the UAE, Qatar, Oman, Bahrain or Saudi Arabia", "5 kg ₹6,800, 10 kg ₹13,600", "₹1,500 to ₹1,650 per kg",
     "https://www.airindiaexpress.com/content/dam/airindiaexpress/documents/mandatory-disclosure/fees-and-charges.pdf"),
    ("Air India Express", "India to Singapore or Thailand", "5 kg ₹7,000 (Singapore), ₹7,700 (Thailand)", "₹2,000 per kg",
     "https://www.airindiaexpress.com/content/dam/airindiaexpress/documents/mandatory-disclosure/fees-and-charges.pdf"),
    ("SpiceJet", "India to Dubai or Sharjah", "5 kg ₹5,500, 10 kg ₹11,000", "Not on the page we read",
     "https://corporate.spicejet.com/ExcessBaggage.aspx"),
]
WORKED_OVER = (2, 3, 4, 5, 8, 10)


def _cheapest_pack(prepaid, over):
    fits = [(price, kg) for kg, price in prepaid if kg >= over]
    return min(fits) if fits else None


def _worked_table(B, rows):
    """Cost of being 2 to 10 kg over on each domestic airline: the airport rate x kg, against the smallest
    pre-booked pack that covers it. All from data/extra_baggage.json; nothing estimated."""
    head = "".join("<th>%d kg over</th>" % k for k in WORKED_OVER)
    body = []
    for r in rows:
        f = r["fees"]
        cells = []
        for k in WORKED_OVER:
            airport = B.rupees(k * f["airport_per_kg"]) + (" + tax" if f["tax"] else "") + (" (up to)" if f["upto"] else "")
            pack = _cheapest_pack(f["prepaid"], k) if f["prepaid"] else None
            online = ("Online %s (%d kg pack)" % (B.rupees(pack[0]), pack[1])) if pack else "Online: not listed"
            cheaper = pack and not f["tax"] and not f["upto"] and pack[0] < k * f["airport_per_kg"]
            cells.append("<td>Airport %s<br>%s%s</td>" % (airport, "<strong>" + online + "</strong>" if cheaper else online, ""))
        body.append(f'<tr><th scope="row"><a href="../{f["page"]}">{e(r["name"])}</a></th>{"".join(cells)}</tr>')
    return ('<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th>%s</tr></thead><tbody>%s</tbody></table></div>'
            % (head, "".join(body)))


def _intl_indian_table(B):
    body = "".join(f'<tr><th scope="row">{e(a)}</th><td>{e(route)}</td><td>{e(pre)}</td><td>{e(air)}</td>'
                   f'<td><a href="{e(url)}" target="_blank" rel="noopener">Official page</a></td></tr>' for a, route, pre, air, url in INTL_FEES)
    return ('<div class="table-wrap"><table class="compare"><thead><tr><th>Airline</th><th>Route</th><th>Pre-booked</th><th>At the airport</th><th>Source</th></tr></thead>'
            '<tbody>%s</tbody></table></div>' % body)


def build(B, cfg, deals, pages, lastmod):
    rows = load(B)
    if not rows:
        return
    dom = [r for r in rows if r["scope"] == "domestic"]
    intl = [r for r in rows if r["scope"] == "international"]
    world = [r for r in rows if r["scope"] == "worldwide"]
    by_asin = {d["asin"]: d for d in deals}
    picks = [(by_asin[a], label, why) for a, label, why in WEIGHT_PICKS if a in by_asin]
    scale_html = '<a href="../guides/luggage-scale.html">luggage scale</a>'
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    n = len(rows)
    title = "Excess baggage calculator: allowance and overweight fee by airline"
    seo = "Excess baggage calculator: overweight fee by airline"
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
<li><strong>Excess baggage charge = kg over your allowance × the airline's rate per kg.</strong> With a 15 kg allowance and a 19 kg bag, you are 4 kg over: on IndiGo that is 4 × ₹800 = ₹3,200 at the airport.</li>
<li>On flights within India the airport rate is ₹775 (SpiceJet) to ₹850 (Air India Express, "up to") per kg. Pre-booked packs work out at about ₹695 to ₹750 per kg, but only in fixed sizes: if you are 4 kg over, a 5 kg pack can cost more than paying at the counter.</li>
<li>Weigh each bag at home with a {scale_html}, then type the real weights below. The tool compares them with your airline's allowance for your fare. Every allowance and fee comes from the airline's own website, with the date we checked it; the price shown when you pay is final.</li>
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
<h2>How to calculate excess baggage</h2>
<ol>
<li><strong>Find your free allowance.</strong> It is on your ticket or in Manage Booking, for example "15 kg, 1 piece". Cheap fares such as IndiGo Lite and Air India Express Xpress Lite include no checked bag at all.</li>
<li><strong>Weigh each packed bag.</strong> Use a luggage scale, or stand on a bathroom scale with and without the bag and take the difference.</li>
<li><strong>Subtract.</strong> Total checked weight minus the allowance = kg over. Your cabin bag has its own limit (usually 7 kg) and is weighed separately.</li>
<li><strong>Multiply by the airline's rate.</strong> On flights within India that is the per-kg rate at the airport, or the price of the smallest pre-booked pack that covers your extra kg.</li>
<li><strong>Add any piece fee.</strong> A second checked bag usually costs a handling fee (₹950 to ₹1,000 on IndiGo, Akasa Air, SpiceJet and Air India Express) on top of its weight.</li>
</ol>
<h3>What it costs to be 2 to 10 kg over, flights within India</h3>
<p>Worked out from each airline's own fee list (airport rate × kg, and the smallest pre-booked pack that covers it). Bold means pre-booking is cheaper. We re-read the per-kg rates and packs on IndiGo, Air India, Air India Express, Akasa Air and SpiceJet's websites on {B.fmt_date(INTL_FEES_CHECKED)}.</p>
{_worked_table(B, [r for r in dom if r.get("fees")])}
<p class="checked">Pre-booked kilos are usually not refunded if you use fewer, and Air India shows its online price only in Manage Booking ("save up to 20%", it says). Buy a pack only when its size matches your extra weight, or move a few kilos to your cabin bag first.</p>
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
<p>On international flights extra weight costs much more per kg than within India. Indian airlines publish route prices; this is what we read on their own pages on {B.fmt_date(INTL_FEES_CHECKED)} for flights from India:</p>
{_intl_indian_table(B)}
<p>IndiGo's fees page lists international per-kg rates in each country's currency, and Air India shows its prices when you book. Foreign airlines price extra weight by route, so most don't publish one rate per kg. This is what their pages say:</p>
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
<p>More help: <a href="../guides/luggage-scale.html">how to use a luggage scale</a>, <a href="../baggage/index.html">baggage rules for Indian airlines</a>, <a href="../baggage/checker.html">will my bag fit?</a> <a href="../guides/trolley-bag-capacity-kg-litres.html">how many kg a trolley bag holds</a> and <a href="../guides/lightest-cabin-trolley-bag.html">the lightest trolleys by empty weight</a>.</p>
{{faq}}
{B.tool_pills("../", PATH)}
</article></div>
<script src="../assets/bag-weight.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("How to calculate excess baggage?", "Add up what your checked bags weigh, subtract the free allowance on your ticket, and multiply the kg over by the airline's rate. Example: 19 kg on a 15 kg IndiGo fare is 4 kg over, so 4 × ₹800 = ₹3,200 at the airport. Pre-booked online, 3 kg costs ₹2,250 and 5 kg ₹3,750."),
        ("How much is excess baggage per kg in India?", "At the airport, on flights within India: IndiGo and Akasa Air ₹800 per kg, Air India ₹800 per kg plus tax, Air India Express up to ₹850 per kg and SpiceJet ₹775 per kg (their own fee pages, read on 26 Nov 2026)."),
        ("What are IndiGo's excess baggage charges on domestic flights?", "IndiGo's fees page lists ₹800 per kg at the airport. Pre-booked: 3 kg ₹2,250, 5 kg ₹3,750, 10 kg ₹7,500, 15 kg ₹11,250, 20 kg ₹15,000, 25 kg ₹18,750, 30 kg ₹22,500 and 40 kg ₹30,000."),
        ("What are Air India's excess baggage charges per kg?", "Air India's excess baggage page lists INR 800 per kg plus taxes for travel within India, and says paying ahead saves up to 20%. The prepaid price is shown in Manage Booking, not on the page."),
        ("Is it cheaper to pre-book extra baggage?", "Per kg, yes: the packs work out at about ₹695 to ₹750 per kg against ₹775 to ₹850 at the counter. But packs come in fixed sizes (3, 5, 10 kg and up) and unused kilos aren't refunded, so if you are 4 kg over, a 5 kg pack (₹3,750 on IndiGo) costs more than 4 kg at the airport (₹3,200)."),
        ("What are extra baggage charges per kg on international flights?", "Much higher than within India. Akasa Air lists ₹1,500 per kg at the airport from India to Abu Dhabi, Doha and Riyadh, and Air India Express ₹1,500 to ₹1,650 per kg to the Gulf and ₹2,000 to Singapore and Thailand (read 26 Nov 2026). Pre-booking 5 kg costs about ₹5,500 to ₹7,700 on these routes."),
        ("What if my cabin bag is over 7 kg?", "Most airlines will check it in, and its weight then counts towards your checked allowance. Air India, Air India Express and SpiceJet sell extra cabin kg on domestic flights; the calculator shows the charge when your airline has one."),
        ("Does my jacket count in my baggage weight?", "Clothes you wear aren't weighed with your bags, so wearing your heaviest jacket and shoes leaves more room in your allowance."),
        ("What is the most one checked bag can weigh?", "32 kg on the airlines here, even if your allowance is higher or you pay for more. Air India's excess baggage page says each bag can't weigh more than 32 kg, and Air India Express's fee list says the same. Split heavy luggage into two bags."),
    ]
    faq_html, faq_schema = B.faq_block(faq)
    body = body.replace("{faq}", faq_html)
    crumbs = B.crumbs_schema(cfg, [("Home", ""), ("Excess baggage calculator", PATH)])
    pages.append(B.write(PATH, B.page(cfg, seo, desc, body, 1, PATH,
                                      [B.tool_article(cfg, seo, desc, PATH, "2026-11-03", UPDATED), crumbs, faq_schema], og_type="article")))
    lastmod[PATH] = UPDATED
