"""Trip calculators, kept out of build.py:

- tools/trip-budget-calculator.html + static/trip-budget.js: a trip budget with a split-the-bill (settle up) part.
- tools/road-trip-cost-calculator.html + static/road-trip.js: fuel needed, fuel cost, tolls and parking, per person.

Every amount on these pages is typed in by the reader. CarryPick publishes no prices, estimates or "average cost"
figures here: the fields start empty and the pages show only what the reader's own numbers add up to.
Inputs are kept in this browser (localStorage) and can be shared in the link (#plan=...), so friends open the same plan.
Without JS, the budget page shows a printable checklist and the road trip page shows the formula.

build.py calls register(B) where it lists TOOLS, and build_all(B, ...) with the other tools.
"""
from html import escape as e

import more_tools

BUDGET = "tools/trip-budget-calculator.html"
ROAD = "tools/road-trip-cost-calculator.html"
UPDATED = "2026-11-21"
BUDGET_PICKS = ["B0DCZ3WDTB", "B0DWSS3Q5K", "B0C3RB9X98", "B0CJC1SVH7", "B0D62KP35W", "B07Q822CWX"]
ROAD_PICKS = ["B0DCZ3WDTB", "B0C3RB9X98", "B00NIWHQVI", "B0C7BM18PB", "B094JBDRKX", "B0CJC1SVH7"]
ROAD_GUIDES = [("manali", "Manali"), ("shimla-in-december", "Shimla"), ("rishikesh-in-december", "Rishikesh"),
               ("jaipur", "Jaipur"), ("udaipur", "Udaipur"), ("goa", "Goa"), ("bhutan-by-road", "Bhutan by road")]

# (id, label, hint shown under the field, how it is counted)
BUDGET_FIELDS = [
    ("people", "People", "How many are going", "count"),
    ("nights", "Nights", "Nights away", "count"),
    ("travel", "Travel there and back, per person", "Flight, train or bus tickets for one person, both ways", "x people"),
    ("hotel", "Hotel, per room per night", "What one room costs for one night", "x rooms x nights"),
    ("rooms", "Rooms", "How many rooms you need", "count"),
    ("food", "Food, per person per day", "Meals, tea and snacks for one person", "x people x days"),
    ("local", "Local transport, per day", "Cabs, autos, scooter or car hire for the group", "x days"),
    ("activities", "Activities and entry tickets", "For the whole group, for the whole trip", "total"),
    ("visa", "Visa or permit fees, per person", "Leave empty if you don't need one", "x people"),
    ("shopping", "Shopping and gifts", "For the whole group", "total"),
    ("buffer", "Buffer %", "Extra for surprises, like 10", "percent"),
]
ROAD_FIELDS = [
    ("km", "Distance, one way (km)", "From Google Maps or your route"),
    ("mileage", "Mileage (km per litre)", "Your car's real mileage on highways"),
    ("fuelp", "Fuel price, per litre", "Today's price at your pump"),
    ("tolls", "Tolls, one way", "FASTag or cash tolls on the route"),
    ("parking", "Parking", "For the whole trip"),
    ("people", "People sharing", "Who splits the bill"),
]


def register(B):
    B.TOOLS.append((BUDGET, "Trip budget calculator", "Free tool", "Trip budget calculator: plan and split the bill",
                    "Type in your own travel, hotel, food and ticket amounts and see the total, the share per person and per day, and who owes whom.",
                    "Plan my budget", "wallet", "travel-gear", ""))
    B.TOOLS.append((ROAD, "Road trip fuel cost calculator", "Free tool", "Road trip fuel cost calculator",
                    "Enter the distance, your car's mileage and today's fuel price to see the fuel needed, the cost with tolls and the share per person.",
                    "Work out my fuel", "pin", "luggage", ""))


CURRENCIES = [("INR", "₹ Indian rupee (INR)"), ("USD", "$ US dollar (USD)"), ("EUR", "€ Euro (EUR)"), ("GBP", "£ British pound (GBP)"),
              ("AED", "AED UAE dirham"), ("SGD", "S$ Singapore dollar (SGD)"), ("THB", "฿ Thai baht (THB)"), ("JPY", "¥ Japanese yen (JPY)"),
              ("AUD", "A$ Australian dollar (AUD)")]


def _currency(prefix):
    opts = "".join(f'<option value="{c}">{e(n)}</option>' for c, n in CURRENCIES)
    return (f'<label>Currency<select id="{prefix}-cur">{opts}</select>'
            f'<span class="hint small">Changes only the symbol. You type your own amounts: we don\'t convert or show rates</span></label>')


def _field(prefix, fid, label, hint, step="1", mode="decimal"):
    return (f'<label>{e(label)}<input id="{prefix}-{fid}" type="number" min="0" step="{step}" inputmode="{mode}" placeholder="">'
            f'<span class="hint small">{e(hint)}</span></label>')


def _picks(B, cfg, deals, asins, head, lead):
    by = {d["asin"]: d for d in deals}
    cards = "".join(B.card(cfg, by[a], "../") for a in asins if a in by)
    if not cards:
        return ""
    return f'<h2 id="picks">{e(head)}</h2>\n<p>{e(lead)}</p>\n<div class="grid">{cards}</div>'


def _share_row(prefix):
    return (f'<div class="tc-actions"><a class="btn btn-amazon" id="{prefix}-wa" href="https://wa.me/" target="_blank" rel="noopener">Share on WhatsApp</a>'
            f'<button type="button" class="btn tc-ghost" id="{prefix}-copy">Copy link</button>'
            f'<button type="button" class="btn tc-ghost" id="{prefix}-reset">Clear</button></div>'
            f'<p class="hint small" id="{prefix}-saved">Your numbers stay in this browser. The share link carries them, so friends open the same plan.</p>')


def build_budget(B, cfg, deals, pages, lastmod):
    fields = "".join(_field("tb", fid, label, hint, "1" if how in ("count", "percent") else "any",
                            "numeric" if how in ("count", "percent") else "decimal")
                     for fid, label, hint, how in BUDGET_FIELDS)
    rows = [("Travel there and back", "per person x people"), ("Hotel", "per room per night x rooms x nights"),
            ("Food", "per person per day x people x days"), ("Local transport", "per day x days"),
            ("Activities and entry tickets", "whole group"), ("Visa or permit fees", "per person x people"),
            ("Shopping and gifts", "whole group"), ("Buffer for surprises", "% of everything above")]
    checklist = "".join(f'<tr><th scope="row">{e(n)}<br><span class="muted small">{e(h)}</span></th><td class="tc-blank"></td></tr>' for n, h in rows)
    picks = _picks(B, cfg, deals, BUDGET_PICKS, "Small things that help on any trip",
                   "A power bank, a cable pouch, packing cubes, a cabin bag and a luggage scale: our picks for keeping a trip simple.")
    title = "Trip budget calculator: plan your trip and split the bill with friends"
    seo = "Trip budget calculator India: plan a trip and split expenses with friends"
    desc = ("Free trip budget calculator in rupees, dollars, euros, pounds and more. Type in your own travel, hotel, food, local transport, tickets, visa and shopping amounts "
            "to see the total, the cost per person and per day, then split the bill and see who owes whom. Share the plan on WhatsApp.")
    body = f"""{more_tools._head(B, title, "Trip budget calculator", "A free tool. Updated " + B.fmt_date(UPDATED), "travel-gear", "wallet")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Add up six things:</strong> travel there and back, the hotel, food, local transport, activities and tickets, and visa or permit fees. Then add shopping and a buffer.</li>
<li><strong>Hotel</strong> = one room's rate for a night x rooms x nights. <strong>Food</strong> = one person's daily spend x people x days.</li>
<li>We count days as nights + 1, because you eat and travel on the day you go home too.</li>
<li>You type every amount. We don't guess or show prices: check them on the booking sites for your dates.</li>
</ul></div>
<div class="tc-print" id="tb-print">
<h2>Trip budget checklist</h2>
<p>Print this page and fill in the blanks. With JavaScript on, the calculator does the sums for you.</p>
<div class="table-wrap"><table class="compare"><thead><tr><th>What</th><th>Your amount</th></tr></thead><tbody>
{checklist}<tr><th scope="row"><strong>Total</strong></th><td class="tc-blank"></td></tr>
<tr><th scope="row">Per person (total ÷ people)</th><td class="tc-blank"></td></tr>
<tr><th scope="row">Per day (total ÷ days)</th><td class="tc-blank"></td></tr></tbody></table></div>
</div>
<form class="checker" id="tb" onsubmit="return false" hidden>
<h2 class="tc-h">Your trip budget</h2>
<div class="checker-fields tc-fields">{_currency("tb")}{fields}</div>
<div id="tb-result" aria-live="polite">
<p class="checker-total" id="tb-out">Type in your people, nights and amounts to see your total.</p>
<div class="tc-bar" id="tb-bar" hidden></div>
<ul class="tc-legend" id="tb-legend"></ul>
</div>
{_share_row("tb")}
</form>
<section class="checker" id="sp" hidden>
<h2 class="tc-h" id="split">Split the bill</h2>
<p class="hint">Add everyone, then add what each person paid. We split each payment equally among the people it is for, and work out the fewest payments to settle up.</p>
<div class="tc-row"><label>Friend's name<input id="sp-name" type="text" maxlength="30" autocomplete="off"></label><button type="button" class="btn btn-amazon" id="sp-add-f">Add friend</button></div>
<ul class="tc-chips" id="sp-friends"></ul>
<div class="tc-row tc-exp"><label>Who paid<select id="sp-payer"></select></label>
<label>For what<input id="sp-what" type="text" maxlength="40" placeholder="Hotel, dinner, cab…" autocomplete="off"></label>
<label>Amount<input id="sp-amt" type="number" min="0" step="any" inputmode="decimal"></label>
<button type="button" class="btn btn-amazon" id="sp-add-e">Add payment</button></div>
<fieldset class="tc-for" id="sp-for-box" hidden><legend class="small">Split between (untick anyone who wasn't part of it)</legend><div id="sp-for"></div></fieldset>
<ul class="tc-list" id="sp-exp"></ul>
<div id="sp-out" aria-live="polite"></div>
</section>
<h2>How to plan a trip budget</h2>
<ol>
<li><strong>Book travel first.</strong> Flights and trains change the most with dates, so check them before the rest.</li>
<li><strong>Price the stay by room, not by person.</strong> Two people often share a room, so enter the rooms you need.</li>
<li><strong>Food and local transport are daily.</strong> Enter one day's spend; the calculator multiplies by the days.</li>
<li><strong>Add tickets and permits.</strong> Entry fees, rides, inner line permits or a visa can add up.</li>
<li><strong>Keep a buffer.</strong> A buffer covers a late cab, a missed meal plan or a rainy day indoors.</li>
</ol>
<p>Going by car? Work out the fuel with our <a href="road-trip-cost-calculator.html">road trip fuel cost calculator</a> and put the result in "Local transport" or "Travel". Packing next? Use the <a href="packing-list-maker.html">packing list maker</a> and the <a href="what-to-wear.html">what-to-wear helper</a>.</p>
<p>Need trip ideas? Read our <a href="../trips/index.html">trip guides</a>: Goa, Manali, Jaipur, Kerala, Udaipur, Bhutan, Nepal and more.</p>
{picks}
{{faq}}
{B.tool_pills("../", BUDGET)}
</article></div>
<script src="../assets/trip-budget.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("How do I calculate my trip budget?",
         "Add travel there and back for everyone, the hotel (room rate x rooms x nights), food (daily spend x people x days), local transport (daily spend x days), activities and tickets, visa or permit fees and shopping. Then add a buffer, like 10%. Divide by the number of people to get the cost per person."),
        ("How do I calculate the cost per person for a trip?",
         "Add up the whole trip for the group, then divide by the number of people. The calculator does this for you, and the split the bill section shows who should pay whom if one person paid more."),
        ("How do I split trip expenses with friends?",
         "Add each friend, then add each payment with who paid it. The tool shares every payment equally among the people it was for, works out how much each person paid over or under their share, and lists the fewest payments that settle everyone up."),
        ("Can I share the trip budget on WhatsApp?",
         "Yes. Tap Share on WhatsApp: the link carries your numbers and names, so friends open the same plan. Nothing is sent to CarryPick; it stays in the link and in your browser."),
        ("Can I use a currency other than rupees?",
         "Yes. Pick ₹, USD, EUR, GBP, AED, SGD, THB, JPY or AUD at the top. It changes only the symbol and number format of the amounts you type. We don't convert money or show exchange rates."),
        ("Does this trip budget calculator show prices?",
         "No. You type in every amount from the booking sites you use. Prices change with dates and seasons, so we don't guess them."),
        ("How many days should I count for food?",
         "Count nights + 1. A 5-night trip has 6 days of meals, because you eat on the day you leave and the day you come back."),
        ("How much buffer should I keep for a trip?",
         "Many travellers keep 10% to 15% extra. Type the % you want; the calculator adds it on top of everything else."),
    ]
    more_tools._finish(B, cfg, pages, lastmod, BUDGET, seo, desc, "Trip budget calculator", body, faq, UPDATED)


def build_road(B, cfg, deals, pages, lastmod):
    fields = "".join(_field("rt", fid, label, hint, "any", "numeric" if fid == "people" else "decimal")
                     for fid, label, hint in ROAD_FIELDS)
    guides = "".join(f'<li><a href="../trips/{s}.html">{e(n)}</a></li>' for s, n in ROAD_GUIDES)
    picks = _picks(B, cfg, deals, ROAD_PICKS, "Handy for a long drive",
                   "A power bank and cable pouch for phones and maps, a steel bottle, a neck pillow for the back seat and a waterproof phone pouch.")
    title = "Road trip fuel cost calculator: petrol, diesel or CNG, with tolls"
    seo = "Fuel cost calculator for trip India: petrol, diesel, CNG road trip cost"
    desc = ("Free road trip fuel cost calculator. Enter the distance in km or miles, your car's mileage (km/l, mpg or km/kg for CNG), "
            "the fuel price you pay, tolls, parking and people, and see the fuel needed, fuel cost, total and cost per person.")
    body = f"""{more_tools._head(B, title, "Road trip fuel cost calculator", "A free tool. Updated " + B.fmt_date(UPDATED), "luggage", "pin")}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>Fuel needed</strong> = distance in km ÷ mileage in km per litre. A 600 km round trip in a car that does 15 km/l needs 40 litres.</li>
<li><strong>Fuel cost</strong> = fuel needed x the price per litre at your pump. For CNG, use km per kg and the price per kg.</li>
<li><strong>Trip cost</strong> = fuel cost + tolls + parking. Divide by the people in the car for each person's share.</li>
</ul></div>
<form class="checker" id="rt" onsubmit="return false" hidden>
<h2 class="tc-h">Your road trip</h2>
<div class="checker-fields tc-fields">
{_currency("rt")}
<label>Distance in<select id="rt-dist"><option value="km">Kilometres (km)</option><option value="mi">Miles</option></select></label>
<label>Fuel measured in<select id="rt-vol"><option value="l">Litres</option><option value="gal">US gallons</option></select><span class="hint small">CNG always goes by kg</span></label>
<label>Fuel<select id="rt-fuel"><option value="petrol">Petrol</option><option value="diesel">Diesel</option><option value="cng">CNG</option></select><span class="hint small">CNG goes by km per kg</span></label>
<label class="tc-check"><input id="rt-round" type="checkbox" checked> Round trip (there and back)</label>
{fields}</div>
<div id="rt-result" aria-live="polite"><p class="checker-total" id="rt-out">Type in the distance, mileage and fuel price to see your fuel cost.</p>
<ul class="tc-legend" id="rt-list"></ul></div>
{_share_row("rt")}
</form>
<h2>How to work out fuel cost for a trip</h2>
<ol>
<li><strong>Distance:</strong> check the route on a map. Add 10% or so for wrong turns, sightseeing and drives around town.</li>
<li><strong>Mileage:</strong> use what your car really does, not the brochure figure. Hills, AC and a full car bring it down.</li>
<li><strong>Fuel price:</strong> type the price at your pump today. It differs from state to state.</li>
<li><strong>Tolls:</strong> check the toll plazas on your route on the NHAI or a maps app, and enter the one-way total; we double it for a round trip.</li>
</ol>
<p>Using a bike? It works the same way: enter your bike's km per litre.</p>
<h2>Road trip guides</h2>
<p>Trips you can do by car, with roads, rules and what to pack:</p>
<ul class="airline-links">{guides}</ul>
<p>Planning the whole trip? Add hotels, food and tickets in our <a href="trip-budget-calculator.html">trip budget calculator</a>, and split the bill with friends there. Packing? Try the <a href="packing-list-maker.html">packing list maker</a>.</p>
{picks}
{{faq}}
{B.tool_pills("../", ROAD)}
</article></div>
<script src="../assets/road-trip.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    faq = [
        ("How do I calculate petrol cost for a trip?",
         "Divide the distance in km by your car's mileage in km per litre to get the litres needed, then multiply by the petrol price per litre. For a round trip, double the distance first."),
        ("How much fuel do I need for 600 km?",
         "It depends on mileage: at 15 km/l you need 40 litres, at 12 km/l 50 litres, and at 20 km/l 30 litres. Multiply the litres by the price at your pump."),
        ("How do I calculate CNG cost for a trip?",
         "CNG is sold by the kg. Divide the distance by your car's km per kg, then multiply by the CNG price per kg. Choose CNG in the calculator and it switches to km/kg."),
        ("How do I include tolls in a road trip cost?",
         "Add the toll plazas on your route for one way and enter the total. With round trip on, the calculator doubles the tolls."),
        ("How do I split fuel cost with friends?",
         "Enter how many people share the car. The calculator divides fuel, tolls and parking equally. For hotel and food too, use our trip budget calculator's split the bill section."),
        ("Can I use miles, gallons or dollars?",
         "Yes. Choose miles instead of km and US gallons instead of litres, and the mileage field becomes miles per gallon (mpg). Pick a currency too: it changes only the symbol. We don't convert units of money or show rates, so type the price you pay."),
        ("Does this calculator use today's fuel price?",
         "No. Fuel prices change by city and by day, so you type the price you pay. We don't publish prices."),
    ]
    more_tools._finish(B, cfg, pages, lastmod, ROAD, seo, desc, "Road trip fuel cost calculator", body, faq, UPDATED)


def build_all(B, cfg, deals, pages, lastmod):
    build_budget(B, cfg, deals, pages, lastmod)
    build_road(B, cfg, deals, pages, lastmod)
