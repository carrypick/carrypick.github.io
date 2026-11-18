"""Make Pinterest pin images (1000 x 1500) and pins.json from our own facts and photos.

Renders simple HTML with headless Chrome, so nothing needs installing. No Amazon images, prices or ratings.
Usage: python3 scripts/make_pins.py            # every pin
       python3 scripts/make_pins.py size-chart # only this pin
"""

import json
import subprocess
import sys
import tempfile
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "marketing" / "pinterest"
PHOTOS = ROOT / "static" / "photos"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SITE = "https://carrypick.github.io/"
FONTS = "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700;800&display=swap"
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
LOGO = """<svg viewBox="0 0 640 640" width="64" height="64"><rect width="640" height="640" rx="120" fill="#0f4c5c"/>
<path d="M252 300V232a68 68 0 0 1 136 0V300" fill="none" stroke="#fff" stroke-width="22" stroke-linecap="round"/>
<path d="M178 268H462L492 498Q495 522 471 522H169Q145 522 148 498Z" fill="#f97316"/>
<polyline points="252,412 300,460 392,366" fill="none" stroke="#fff" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

CSS = """*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1000px;height:1500px;overflow:hidden}
body{font-family:'Plus Jakarta Sans',Arial,sans-serif;background:#f7f5f0;color:#14202b;display:flex;flex-direction:column}
.head{background:#0f4c5c;color:#fff;padding:76px 64px 64px}
.kicker{font-size:30px;font-weight:700;letter-spacing:.02em;color:#ffc79e;margin-bottom:20px}
h1{font-size:82px;line-height:1.08;font-weight:800;letter-spacing:-.02em}
.body{flex:1;padding:44px 64px 24px;display:flex;flex-direction:column;gap:26px;min-height:0}
table{width:100%;border-collapse:collapse;font-size:34px;background:#fff;border-radius:22px;overflow:hidden;box-shadow:0 0 0 2px #e7e2d8}
th{background:#fde3cf;text-align:left;padding:17px 22px;font-size:29px;font-weight:800}
td{padding:17px 22px;border-top:2px solid #efeadf;font-weight:500}
td:first-child{font-weight:800}
.note{font-size:31px;line-height:1.32;color:#3a4652;font-weight:500}
.note strong{color:#14202b;font-weight:800}
.stat{font-size:158px;line-height:1;font-weight:800;color:#c2410c;letter-spacing:-.03em}
.stat-note{font-size:42px;line-height:1.24;font-weight:700}
.group{background:#fff;border-radius:22px;padding:24px 30px;box-shadow:0 0 0 2px #e7e2d8}
.group h2{font-size:32px;font-weight:800;color:#c2410c;margin-bottom:8px}
.group p{font-size:35px;line-height:1.3;font-weight:500}
.big{display:flex;gap:22px}
.big>div{flex:1;background:#fff;border-radius:22px;padding:28px 26px;box-shadow:0 0 0 2px #e7e2d8}
.big b{display:block;font-size:68px;line-height:1.05;font-weight:800;color:#0f4c5c}
.big span{display:block;font-size:30px;line-height:1.24;font-weight:500;margin-top:10px}
.foot{display:flex;align-items:center;gap:18px;padding:24px 64px 40px;font-size:34px;font-weight:800;color:#0f4c5c}
.foot small{margin-left:auto;font-size:30px;font-weight:700;color:#5b6573}
.photo{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.shade{position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,53,64,.05) 28%,rgba(10,53,64,.9) 62%,rgba(10,53,64,.98) 100%)}
.over{position:absolute;left:0;right:0;bottom:0;padding:0 64px 44px;color:#fff}
.over h1{font-size:96px;margin-bottom:26px}
.over p{font-size:42px;line-height:1.28;font-weight:500;margin-bottom:34px}
.over .foot{padding:0;color:#fff}
.over .foot small{color:#d8e4e8}
.head.small{padding:56px 64px 48px}
.head.small h1{font-size:68px}
.head.small+.body{gap:16px}
.head.small+.body td,.head.small+.body th{padding:11px 22px}
.art{position:relative;flex:none;height:604px;border-radius:22px;overflow:hidden;box-shadow:0 0 0 2px #e7e2d8}
.art img{position:absolute;left:0;top:-50px;width:1325px}"""


def table(head, rows):
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (
        "".join("<th>%s</th>" % e(c) for c in head),
        "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % e(c) for c in r) for r in rows))


def group(title, text):
    return '<div class="group"><h2>%s</h2><p>%s</p></div>' % (e(title), e(text))


def foot():
    return '<div class="foot">%s<span>CarryPick</span><small>carrypick.github.io</small></div>' % LOGO


def chart(kicker, title, body):
    return ('<div class="head"><p class="kicker">%s</p><h1>%s</h1></div><div class="body">%s</div>%s'
            % (e(kicker), e(title), body, foot()))


def photo(slot, title, sub):
    src = (PHOTOS / (slot + "-1600.webp")).as_uri()
    return ('<img class="photo" src="%s" alt=""><div class="shade"></div><div class="over"><h1>%s</h1><p>%s</p>%s</div>'
            % (src, e(title), e(sub), foot()))


def pick(kicker, title, asin, rows, note):
    """A pick pin: the drawing part of our own share image (static/picks/<ASIN>-*.jpg), cropped, with listed facts.
    The share image keeps its "Illustration, not a product photo" label inside the crop."""
    found = sorted((ROOT / "static" / "picks").glob(asin + "-*.jpg"))
    if not found:
        sys.exit("Error: no share image for %s. Run scripts/make_pick_images.py first." % asin)
    return ('<div class="head small"><p class="kicker">%s</p><h1>%s</h1></div><div class="body"><div class="art"><img src="%s" alt=""></div>%s'
            '<p class="note">%s</p></div>%s' % (e(kicker), e(title), found[-1].as_uri(), table(["From the listing", ""], rows), note, foot()))


CARRY = "Can I carry it? Flights in India"
CHECKED_10 = '<p class="note">Checked on airline sites on 10 Nov 2026. Rules change, so check before you fly.</p>'

PINS = [
    dict(slug="size-chart", board="Luggage Size Guides", link="baggage/luggage-size-chart.html",
         title="Trolley bag size chart: inches to cm",
         description="Trolley bag sizes from 18 to 32 inches in cm, with the kind of bag and trip length for each. Some brands sell 55 cm bags as 20 inch, so check the cm before you buy.",
         alt="A chart of trolley bag sizes from 18 to 32 inches converted to cm, with bag type and trip length.",
         html=chart("Luggage size guide", "Trolley bag size chart: inches to cm", table(
             ["Inches", "cm", "Size", "Trip"],
             [["18", "45.7", "Small cabin", "1–3 days"], ["20", "50.8", "Cabin", "2–4 days"], ["22", "55.9", "Cabin", "2–4 days"],
              ["24", "61", "Small medium", "4–6 days"], ["26", "66", "Medium", "5–8 days"], ["28", "71.1", "Large", "8–12 days"],
              ["30", "76.2", "Large", "10+ days"], ["32", "81.3", "Extra large", "Long trips"]])
             + '<p class="note"><strong>Check the cm.</strong> Some brands sell 55 cm bags as "20 inch" and 65 cm bags as "24 inch".</p>')),
    dict(slug="large-158", board="Luggage Size Guides", link="guides/28-inch-trolley-bag-size.html",
         title="Most large trolley bags go over the airline size limit",
         description="We checked 31 large trolley bags on Amazon.in: 26 are listed over the 158 cm limit most Indian airlines set for a checked bag. See the 5 that aren't, and whether you need a large bag at all.",
         alt="26 of 31 large trolleys checked are listed over 158 cm. The five within the limit are listed by name with their total size.",
         html=chart("Before you buy a large trolley", "Most large trolleys go over the airline limit",
                    '<div><div class="stat">26 of 31</div><p class="stat-note">large trolleys we checked are listed over 158 cm in total</p></div>'
                    + table(["Within 158 cm", "Total"], [["Skybags Swirl 75 cm", "152 cm"], ["L'Attitude Meridian 75 cm", "154 cm"], ["Safari Astra Neo 76 cm", "155 cm"],
                                                          ["Safari Crescent 76 cm", "155 cm"], ["American Tourister Liftoff+ 79 cm", "158 cm"]])
                    + '<p class="note">Listed sizes on Amazon.in, 6 Nov 2026. Sellers can change them.</p>')),
    dict(slug="twenty-inch", board="Luggage Size Guides", link="guides/20-inch-trolley-bag-size.html",
         title='Is your "20 inch" trolley bag really 20 inches?',
         description="A 20 inch trolley is 50.8 cm, but many sold as 20 inch in India are 55 cm or taller. See the cabin limits of Indian airlines, how much it holds and which bags fit.",
         alt="20 inches is 50.8 cm, but some cabin bags sold as 20 inch are listed at 56 to 58 cm. Airlines also check width and depth.",
         html=chart("Cabin bag guide", 'Is your "20 inch" trolley really 20 inches?',
                    '<div class="big"><div><b>50.8 cm</b><span>what 20 inches really is</span></div><div><b>56–58 cm</b><span>listed height of some bags sold as "20 inch"</span></div></div>'
                    + group("Height isn't enough", "Airlines also check width and depth, wheels and handles included.")
                    + group("IndiGo's cabin limit", "55 x 35 x 25 cm and 7 kg, including the bag.")
                    + '<p class="note"><strong>70 of 83</strong> hard "55 cm" trolleys we checked were too wide for that limit.</p>')),
    dict(slug="medium-pack", board="Luggage Size Guides", link="guides/24-inch-trolley-bag-size.html",
         title="24 inch trolley bag: how much can you really pack?",
         description="A 24 inch trolley is 61 cm, but most medium bags in India are 65–69 cm. The bag's own weight counts towards your allowance. See what 36 medium trolleys really measure.",
         alt="A table showing how much you can pack on 15, 20 and 25 kg allowances with light, typical and heavy medium trolleys.",
         html=chart("Medium trolley guide", "24 inch trolley: how much can you pack?",
                    '<p class="note"><strong>The bag\'s own weight counts.</strong> Medium trolleys we checked weigh 2.52–4.5 kg empty.</p>'
                    + table(["Allowance", "Light bag 2.52 kg", "Typical 3.4 kg", "Heavy 4.5 kg"],
                            [["15 kg", "12.48 kg", "11.6 kg", "10.5 kg"], ["20 kg", "17.48 kg", "16.6 kg", "15.5 kg"], ["25 kg", "22.48 kg", "21.6 kg", "20.5 kg"]])
                    + group("24 inches is 61 cm", 'Many bags sold as "24 inch" are listed at 65 cm or more. It\'s a check-in bag, not a cabin bag.'))),
    dict(slug="cabin-limits", board="Flight and Train Baggage Rules", link="baggage/index.html",
         title="Cabin bag size limits for Indian airlines",
         description="Cabin bag limits for IndiGo, Air India, Air India Express, Akasa Air and SpiceJet in cm, on one page. Most allow 7 kg, but the sizes differ. Check your own bag with our free checker.",
         alt="A table of cabin bag size limits in cm for IndiGo, Air India, Air India Express, Akasa Air and SpiceJet.",
         html=chart("Flying in India", "Cabin bag limits for Indian airlines", table(
             ["Airline", "Size in cm", "Weight"],
             [["IndiGo", "55 x 35 x 25", "7 kg"], ["Air India", "55 x 40 x 20", "7 kg"], ["Air India Express", "56 x 36 x 23", "7 kg"],
              ["Akasa Air", "55 x 35 x 25", "7 kg"], ["SpiceJet Boeing", "55 x 35 x 25", "7 kg"], ["SpiceJet Q400", "50 x 35 x 23", "7 kg"]])
             + '<p class="note"><strong>"55 cm" is only the height.</strong> Check the width and depth too, with wheels and handles.</p>'
             + '<p class="note">Checked on airline sites on 3 Nov 2026. Rules change, so check before you fly.</p>')),
    dict(slug="dont-pack", board="Flight and Train Baggage Rules", link="baggage/can-i-carry.html",
         title="What you can't pack for a flight in India",
         description="Dry coconut, camphor and lighters are banned in all bags. Power banks can only go in your cabin bag. Search our list to see what you can carry on Indian flights.",
         alt="Lists of items banned in all bags, items not allowed in cabin bags, and the rules for power banks and liquids on Indian flights.",
         html=chart("Flying in India", "Don't pack these for your flight",
                    group("Banned in all bags", "Dry coconut, camphor, lighters, matches, e-cigarettes, firecrackers")
                    + group("Not in your cabin bag", "Knives, scissors, tools, cricket bats, spice powders")
                    + group("Cabin bag only", "Power banks. Don't use or charge them during the flight.")
                    + group("Liquids in your cabin bag", "100 ml or less each, all in one clear 1-litre bag")
                    + '<p class="note">Checked on 3 Nov 2026. Check your airline before you fly.</p>')),
    dict(slug="train-luggage", board="Flight and Train Baggage Rules", link="baggage/train-luggage-rules.html",
         title="Indian Railways luggage limits by class",
         description="How much luggage you can carry free on Indian trains, class by class, and the suitcase size limits in each coach. Checked against Indian Railways' own rules.",
         alt="A table of free luggage limits by train class on Indian Railways, with suitcase size limits.",
         html=chart("Travelling by train", "Indian Railways luggage limits", table(
             ["Class", "Free luggage"],
             [["AC First", "70 kg"], ["AC 2-tier, First Class", "50 kg"], ["AC 3-tier, AC Chair Car", "40 kg"], ["Sleeper", "40 kg"], ["Second Class", "35 kg"]])
             + group("Suitcase size in the coach", "Up to 100 x 60 x 25 cm. In AC 3-tier and AC Chair Car: only 55 x 45 x 22.5 cm.")
             + '<p class="note">Checked on 3 Nov 2026. Check Indian Railways before you travel.</p>')),
    dict(slug="new-year-gifts", board="Gift Ideas", link="guides/new-year-gift-ideas.html",
         title="New Year gift ideas people actually use",
         description="Useful New Year gift ideas for 2027: watches for him and her, pair watches for parents, handbags and small travel gifts. Plus how to choose and when to order.",
         alt="A wrapped gift with a pink ribbon, with the words New Year gift ideas people actually use.",
         html=photo("gift-box", "New Year gift ideas people actually use", "Watches, bags and small travel gifts for family and friends")),
    dict(slug="republic-weekend", board="India Trip Ideas", link="trips/republic-day-long-weekend-2027.html",
         title="Republic Day long weekend 2027: 4-day trip ideas",
         description="26 January 2027 is a Tuesday, so one day off gives you 4 days. Compare Jaipur, Manali, Goa and Kerala, see how parade tickets work, and when train booking opens.",
         alt="Hawa Mahal in Jaipur, with the words Republic Day long weekend 2027.",
         html=photo("jaipur-hawa-mahal", "Republic Day long weekend 2027", "1 day off = 4 days, 23–26 January. Jaipur, Manali, Goa or Kerala?")),
    dict(slug="parade-tickets", board="India Trip Ideas", link="trips/republic-day-parade-tickets-2027.html",
         title="Republic Day parade tickets 2027: how to book, price and rules",
         description="How Republic Day parade and Beating Retreat tickets work: the Defence Ministry's Aamantran site and Delhi counters, last year's prices and dates, the ID you need and what you can't take in. 2027 dates aren't announced yet.",
         alt="A table of last year's Republic Day ticket sale dates and prices, where to book, and items not allowed at the parade.",
         html=chart("Republic Day 2027, New Delhi", "Parade tickets: what to know", table(
             ["Last year (2026)", ""],
             [["Ticket sale", "5–14 Jan, from 9 AM"], ["Parade", "₹100 and ₹20"], ["Beating Retreat", "₹100"],
              ["Its rehearsal", "₹20"], ["Parade rehearsal", "Free pass"]])
             + group("Where to book", "The Defence Ministry's Aamantran website or app, or ticket counters in Delhi.")
             + group("Not allowed inside", "Bags, food, water bottles, power banks, umbrellas, coins.")
             + '<p class="note"><strong>2027 dates not announced yet.</strong> Checked 16 Nov 2026.</p>')),
    dict(slug="where-to-go", board="India Trip Ideas", link="trips/where-to-go-in-december-january.html",
         title="Where to go in India in December and January",
         description="Beach, snow, forts or backwaters? Compare Goa, Manali, Jaipur and Kerala for a Christmas or New Year trip: the weather, how to get there, crowds and what to pack.",
         alt="A houseboat on the Kerala backwaters, with the words Where to go in India this winter.",
         html=photo("kerala-houseboat", "Where to go in India this winter", "Beaches in Goa, snow in Manali, forts in Jaipur or backwaters in Kerala")),
    dict(slug="goa-winter", board="India Trip Ideas", link="trips/goa.html",
         title="Goa for Christmas and New Year: a simple trip guide",
         description="Plan Goa for December and January: the weather, Mopa or Dabolim airport, trains, taxis and scooters, beach rules and fines, and New Year crowds.",
         alt="A beach in Goa with palm trees, with the words Going to Goa this winter?",
         html=photo("goa-palolem", "Going to Goa this winter?", "Weather, which airport to use, beach rules and fines, and what to pack")),
    dict(slug="hill-clothes", board="Packing and What to Wear", link="guides/winter-clothes-for-hill-trips.html",
         title="What to wear on a winter hill trip in India",
         description="What to wear in Manali and the hills in winter: how to dress in three layers, which thermals and jackets to take, and small things like caps, gloves and sunglasses.",
         alt="A person in a winter jacket in the snow, with the words What to wear on a winter hill trip.",
         html=photo("snow-jacket", "What to wear on a winter hill trip", "Simple layers for Manali and the hills")),
    dict(slug="manali-winter", board="India Trip Ideas", link="trips/manali.html",
         title="Manali in winter: snow, roads and a New Year trip guide",
         description="Plan Manali for December and January: when snow usually comes, getting there from Delhi and Chandigarh, Rohtang and the Atal Tunnel in winter, green tax and what to pack.",
         alt="Manali town with mountains, with the words Manali in winter: snow isn't guaranteed.",
         html=photo("manali-town", "Manali in winter: snow isn't guaranteed", "When snow usually comes, the roads, green tax and what to pack")),
    dict(slug="kerala-winter", board="India Trip Ideas", link="trips/kerala.html",
         title="Kerala in winter: Kochi, Munnar and the backwaters",
         description="Plan Kerala for December and January: the weather, airports, the Cochin Carnival in Fort Kochi, houseboats in Alappuzha, Eravikulam in Munnar and beach safety.",
         alt="A houseboat on the Kerala backwaters, with the words Kerala in winter.",
         html=photo("kerala-houseboat", "Kerala in winter", "Kochi, Munnar, houseboats and the New Year carnival")),
    dict(slug="jaipur-winter", board="India Trip Ideas", link="trips/jaipur.html",
         title="Jaipur in winter: a simple trip guide",
         description="Plan Jaipur for December and January: cold mornings, monument hours and the composite ticket, getting there from Delhi and Agra, the metro, markets and January festivals.",
         alt="Hawa Mahal in Jaipur, with the words Jaipur in winter.",
         html=photo("jaipur-hawa-mahal", "Jaipur in winter", "Forts, palaces, monument tickets and cold mornings")),
    dict(slug="hill-packing", board="Packing and What to Wear", link="packing/hills.html",
         title="Hill station packing list for winter",
         description="A simple winter packing list for Manali, Shimla and Kashmir. Choose your trip length and tick things off as you pack.",
         alt="Boots on a mountain trail, with the words Hill station packing list for winter.",
         html=photo("boots-mountain", "Hill station packing list for winter", "For Manali, Shimla and Kashmir")),
    dict(slug="beach-packing", board="Packing and What to Wear", link="packing/beach.html",
         title="Beach trip packing list for Goa and more",
         description="A simple beach trip packing list for Goa and more. Choose your trip length and tick things off as you pack.",
         alt="Palm trees by a beach in Goa, with the words Beach trip packing list.",
         html=photo("goa-palolem", "Beach trip packing list", "For Goa and more. Tick things off as you pack")),
    dict(slug="shoes-table", board="Packing and What to Wear", link="guides/travel-shoes-guide.html",
         title="Which shoes to take on a trip in India",
         description="Choose shoes by the trip: waterproof shoes for snow, walking shoes for forts, sandals for the beach and slip-ons for flights. Most trips need only two pairs.",
         alt="A table matching snow, forts, beach, rain and flights to the shoes to take.",
         html=chart("Packing light", "Which shoes for which trip?", table(
             ["Trip", "What to take"],
             [["Snow", "Waterproof shoes or boots with a grippy sole"], ["Forts and cities", "Cushioned walking shoes"], ["Beach", "Sandals or flip-flops"],
              ["Rainy places", "Sandals that can get wet"], ["Flights and trains", "Slip-on shoes"]])
             + '<p class="note"><strong>Most trips need only two pairs:</strong> one to walk in, and one light pair for the hotel or the beach.</p>')),
    dict(slug="sunscreen-100ml", board="Packing and What to Wear", link="guides/travel-sunscreen-guide.html",
         title="Sunscreen on a flight: the 100 ml cabin bag rule",
         description="Sunscreen, lotion and face wash count as liquids on flights. See the 100 ml rule, what SPF and PA mean, and how much sunscreen a trip really needs.",
         alt="The rules for sunscreen in a cabin bag: 100 ml or less, one clear 1-litre bag, and bigger bottles in the check-in bag.",
         html=chart("Flying with skincare", "Sunscreen on a flight: the 100 ml rule",
                    group("Each container: 100 ml or less", "A half-empty 200 ml bottle still isn't allowed, because the rule is about the size of the container.")
                    + group("One clear bag", "All your liquids go in one clear, resealable bag of up to 1 litre.")
                    + group("Anything bigger", "It goes in your check-in bag.")
                    + group("It's not only sunscreen", "Lotion, face wash and gel count as liquids too."))),
    dict(slug="bag-weight", board="Luggage Size Guides", link="tools/bag-weight.html",
         title="How much does your bag weigh before you pack?",
         description="Empty bags use up your baggage allowance too. See typical weights for backpacks, duffles and trolleys, then add up your things with our free bag weight calculator.",
         alt="A table of typical empty weights for a backpack, duffle bag and cabin, medium and large trolleys.",
         html=chart("Before you pack", "How heavy is your bag when it's empty?", table(
             ["Bag", "Typical weight"],
             [["Backpack", "0.6 kg"], ["Duffle bag", "1.2 kg"], ["Soft cabin trolley", "2.4 kg"], ["Hard cabin trolley", "2.7 kg"], ["Medium check-in trolley", "3.5 kg"], ["Large check-in trolley", "4.5 kg"]])
             + '<p class="note"><strong>It all counts.</strong> Add up your things with our free bag weight calculator. Real bags vary, so weigh yours.</p>')),
    dict(slug="watch-size", board="Watches and Everyday Bags", link="tools/watch-size.html",
         title="What watch size suits your wrist?",
         description="A simple guide to dial size by wrist size in cm. Measure your wrist, then use our free watch size tool. It's a rule of thumb, not a fixed rule.",
         alt="A table matching wrist sizes in cm to watch dial sizes in mm.",
         html=chart("Choosing a watch", "What watch size suits your wrist?", table(
             ["Wrist", "Dial size"],
             [["Under 15 cm", "28–36 mm"], ["15–16.5 cm", "34–38 mm"], ["16.5–18 cm", "38–42 mm"], ["18–19.5 cm", "40–44 mm"], ["Over 19.5 cm", "42–46 mm"]])
             + '<p class="note"><strong>A rule of thumb, not a fixed rule.</strong> Wrap a tape or thread around your wrist to measure it.</p>')),
    dict(slug="laptop-backpack", board="Watches and Everyday Bags", link="tools/laptop-backpack.html",
         title="Will your laptop fit your backpack?",
         description="Typical laptop sizes by screen size in cm, so you can check a backpack's sleeve before you buy. Use our free laptop backpack tool. Real laptops vary by a few cm.",
         alt="A table of typical laptop width and depth in cm for 13.3 to 17.3 inch screens.",
         html=chart("Choosing a backpack", "Will your laptop fit your backpack?", table(
             ["Screen", "Typical size"],
             [["13.3 inch", "30–31 x 21–22 cm"], ["14 inch", "31–33 x 21–23 cm"], ["15.6 inch", "35–36 x 23–25 cm"], ["16 inch", "35–36 x 24–26 cm"], ["17.3 inch", "39–40 x 26–28 cm"]])
             + '<p class="note"><strong>Real laptops vary by a few cm.</strong> Compare your laptop with the sleeve size on the listing.</p>')),
    dict(slug="handbag-type", board="Watches and Everyday Bags", link="guides/handbag-and-sling-guide.html",
         title="Handbag, tote or sling: which should you choose?",
         description="Tote, satchel or crossbody sling? Compare them for work and travel, and see airline personal bag limits in India.",
         alt="A table comparing tote, satchel and crossbody sling bags, with what each is best for and what to watch out for.",
         html=chart("Choosing a bag", "Tote, satchel or sling?", table(
             ["Type", "Best for", "Watch out for"],
             [["Tote", "Office, laptop, daily use", "Heavy on one shoulder"], ["Satchel", "Work, smart occasions", "Holds less than a tote"], ["Crossbody sling", "Sightseeing, markets, airports", "Rarely fits a tablet"]])
             + '<p class="note"><strong>Start with what you carry,</strong> then choose the shape.</p>')),
    dict(slug="vip-store", board="Luggage Size Guides", link="guides/vip-bags-guide.html",
         title="VIP trolley bags: sizes, warranty and returns",
         description="Thinking of buying from VIP's own website? See its cabin, medium and large sizes, the warranty, delivery, the 3-day return rule and what to check first.",
         alt="Facts about buying from VIP's own store: sizes, warranty, delivery and the 3-day return rule.",
         html=chart("Buying direct", "VIP trolley bags on VIP's own store", table(
             ["What", "VIP's site says"],
             [["Sizes", "Cabin, medium and large"], ["Warranty", "3 years on the models we read"], ["Delivery", "3–5 business days"], ["Returns", "Within 3 days, unused, with tags"]])
             + '<p class="note"><strong>Check before you order.</strong> The pages we read gave no width, depth or bag weight. Read on 6 Nov 2026.</p>')),
    dict(slug="wedding-gifts", board="Gift Ideas", link="guides/wedding-gift-guide.html",
         title="Wedding gift ideas couples actually use",
         description="Pair watches for the couple, watches for the bride and groom, and bags for the honeymoon, with tips to pick the right one.",
         alt="A watch on a wrist, with the words Wedding gift ideas couples actually use.",
         html=photo("watch-mesh", "Wedding gift ideas couples actually use", "Pair watches and bags for the honeymoon")),
    # 15 Nov 2026: pages that had no pin yet. Luggage size pins got the only impressions so far, so most of these are luggage and flight rules.
    dict(slug="trolley-kg", board="Luggage Size Guides", link="guides/trolley-bag-capacity-kg-litres.html",
         title="How many kg does a trolley bag hold? 55, 65 and 75 cm sizes",
         description="Listed litres and a rough kg guide for cabin, medium and large trolleys, from 80 models on Amazon.in. Your fare usually sets the real limit, and the empty bag's weight counts too.",
         alt="A table of typical listed litres, rough kg of clothes and empty weight for 55 cm, 65–69 cm and 75–80 cm trolley bags.",
         html=chart("Trolley bag capacity", "How many kg does a trolley hold?", table(
             ["Size", "Litres", "Clothes, rough", "Empty bag"],
             [["Cabin 55 cm", "39 L", "6–12 kg", "2.5 kg"], ["Medium 65–69 cm", "69 L", "10–21 kg", "3.4 kg"], ["Large 75–80 cm", "108 L", "16–32 kg", "4.3 kg"]])
             + '<p class="note"><strong>The kg column is our rough estimate,</strong> not a test: about 0.15–0.3 kg per litre of packed clothes.</p>'
             + group("Your ticket sets the limit", "On a 15 kg fare, a typical medium bag leaves 11.6 kg for your things. A typical large one leaves 10.7 kg.")
             + '<p class="note">Typical listed figures from 80 models on Amazon.in, 6 Nov 2026.</p>')),
    dict(slug="at-vs-safari", board="Luggage Size Guides", link="guides/american-tourister-vs-safari.html",
         title="American Tourister vs Safari trolley bags: which is better?",
         description="We compared the two brands' trolleys on Amazon.in by empty weight, listed litres and full size. American Tourister was lighter, Safari listed more litres. Neither wins on everything, and we haven't tested them.",
         alt="A table comparing typical American Tourister and Safari medium and large trolleys by empty weight, listed litres and total size.",
         html=chart("Trolley bags compared", "American Tourister vs Safari", table(
             ["Typical listing", "Am. Tourister", "Safari"],
             [["Medium: empty weight", "3.3 kg", "3.5 kg"], ["Medium: litres", "70 L", "75.5 L"], ["Large: empty weight", "4 kg", "4.5 kg"],
              ["Large: litres", "104 L", "113 L"], ["Large: total size", "167 cm", "160 cm"]])
             + '<div class="big"><div><b>Lighter</b><span>American Tourister</span></div><div><b>More litres</b><span>Safari</span></div></div>'
             + '<p class="note">Listings read on Amazon.in on 6 Nov 2026. We haven\'t tested these bags.</p>')),
    dict(slug="brands-weight", board="Luggage Size Guides", link="guides/best-trolley-bag-brands-india.html",
         title="Best trolley bag brands in India: 7 brands compared by weight",
         description="American Tourister, Safari, Aristocrat, Skybags, Kamiliant, VIP and L'Attitude compared by what their Amazon.in listings say: empty weight, litres and full size. There's no single best brand, so choose by your fare and airline.",
         alt="A table of typical empty weights and litres of medium trolleys from seven brands, from 2.97 kg to 3.75 kg.",
         html=chart("Medium trolleys compared", "Which trolley brand is lightest?", table(
             ["Brand", "Empty weight", "Litres"],
             [["Kamiliant", "2.97 kg", "65 L"], ["L'Attitude", "3.24 kg", "60 L"], ["American Tourister", "3.3 kg", "70 L"], ["Safari", "3.5 kg", "75.5 L"],
              ["Aristocrat", "3.5 kg", "71 L"], ["Skybags", "3.57 kg", "66 L"], ["VIP", "3.75 kg", "68 L"]])
             + '<p class="note"><strong>Typical medium bags</strong> in Amazon.in listings, 6 Nov 2026. Only 1 VIP listing, so treat it as rough.</p>')),
    dict(slug="pc-vs-pp", board="Luggage Size Guides", link="guides/polycarbonate-vs-polypropylene-luggage.html",
         title="Polycarbonate vs polypropylene trolley bags: which is better?",
         description="Sellers say polycarbonate is tougher and polypropylene lighter. We checked 62 Amazon.in listings by weight, and the gap was only 0.2–0.25 kg in medium and large bags. See which shell suits your trip.",
         alt="A table of typical weights of polypropylene and polycarbonate cabin, medium and large trolleys.",
         html=chart("Hard trolley shells", "Polycarbonate vs polypropylene",
                    '<p class="note"><strong>Sellers say</strong> polycarbonate (PC) is tougher and polypropylene (PP) is lighter. We checked the weight.</p>'
                    + table(["Size", "PP: typical", "PC: typical"], [["Cabin", "2.53 kg", "2.4 kg"], ["Medium", "3.3 kg", "3.5 kg"], ["Large", "4.25 kg", "4.5 kg"]])
                    + '<div class="big"><div><b>0.2 kg</b><span>about how much lighter PP was in medium and large bags</span></div>'
                      '<div><b>2 kg</b><span>the lightest cabin bag we read, and it was PC</span></div></div>'
                    + '<p class="note">Listings on Amazon.in, 6 Nov 2026. We haven\'t drop-tested anything.</p>')),
    dict(slug="backpack-litres", board="Luggage Size Guides", link="guides/backpack-size-chart-litres.html",
         title="Backpack size chart in litres: which size do you need?",
         description="What 20, 30, 40 and 60 litre backpacks suit, and the largest size that fits Indian airline cabin limits. For most people who fly, 30–40 litres is the largest useful size.",
         alt="A chart of backpack sizes in litres, what each suits and whether it usually fits as a cabin bag on Indian flights.",
         html=chart("Backpack size guide", "Backpack size chart in litres", table(
             ["Litres", "Good for", "Cabin bag?"],
             [["15–20 L", "School, college, daily", "Usually"], ["20–30 L", "Office, day trips", "Usually"], ["30–40 L", "2–4 day trips", "Often"],
              ["40–50 L", "3–5 days, light treks", "Rarely"], ["50–70 L", "Treks of a few days", "No"], ["70 L+", "Long treks", "No"]])
             + '<p class="note"><strong>30–40 L is the largest useful size</strong> for most people who fly. IndiGo\'s 55 x 35 x 25 cm box holds 48 L, and a full backpack bulges.</p>')),
    dict(slug="carry-power-bank", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/power-bank.html",
         title="Can I carry a power bank on a flight in India?",
         description="Power banks go in your cabin bag only, never in check-in. See how many you can take, the 100 Wh limit in mAh, and the rules on IndiGo, Air India and Akasa Air.",
         alt="Power bank rules on Indian flights: cabin bag only, up to 2 of 100 Wh or less, banned in check-in bags, and no charging on board.",
         html=chart(CARRY, "Power bank on a flight: which bag?",
                    group("Cabin bag: yes", "Up to 2 power banks of 100 Wh or less on Akasa Air and Air India. Keep it with you, not in the overhead bin.")
                    + group("Check-in bag: no", "IndiGo, Air India and Akasa Air all ban power banks in check-in bags, even switched off.")
                    + group("On board", "You can't use or charge it during the flight. IndiGo needs the rating printed on it.")
                    + CHECKED_10)),
    dict(slug="carry-perfume", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/perfume.html",
         title="Can I carry perfume on a flight in India?",
         description="Small bottles of 100 ml or less can go in your cabin bag, but not on IndiGo. In check-in you can take up to 2 litres of toiletries in total. Rules for attar, deo sprays and how to pack perfume.",
         alt="Perfume rules on Indian flights: 100 ml bottles in the cabin liquids bag, not in the cabin on IndiGo, up to 2 litres in check-in.",
         html=chart(CARRY, "Perfume on a flight: cabin or check-in?",
                    group("Cabin bag: small bottles only", "100 ml or less each, inside your clear 1-litre liquids bag.")
                    + group("Flying IndiGo?", "IndiGo's list doesn't allow perfume or deo in the cabin at all. Pack it in check-in.")
                    + group("Check-in bag: yes", "Up to 2 litres or 2 kg of perfume and toiletries in total, and no bottle over 500 ml.")
                    + CHECKED_10)),
    dict(slug="carry-trimmer", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/trimmer.html",
         title="Can I carry a trimmer on a flight in India?",
         description="A trimmer with a built-in battery can go in your cabin bag. In check-in it must be switched fully off. What IndiGo's list says, plus blades, scissors in grooming kits and spare batteries.",
         alt="Trimmer rules on Indian flights: cabin bag yes with a built-in battery, check-in yes when switched fully off.",
         html=chart(CARRY, "Trimmer on a flight: which bag?",
                    group("Cabin bag: yes", "If it has a built-in battery. IndiGo's list says a trimmer without a battery goes in check-in only.")
                    + group("Check-in bag: yes", "Switched fully off and protected so it can't turn on in the bag.")
                    + group("Grooming kit?", "Scissors are banned in the cabin, and many kits have a small pair. Take them out, or pack the kit in check-in.")
                    + CHECKED_10)),
    dict(slug="carry-ghee", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/ghee.html",
         title="Can I carry ghee on a flight in India?",
         description="Ghee goes in your check-in bag, up to 5 kg or 5 litres. In the cabin it counts as a liquid, and IndiGo doesn't allow it there at all. How to pack a ghee tin so it doesn't leak.",
         alt="Ghee rules on Indian flights: up to 5 kg in check-in, only 100 ml containers in the cabin, not in the cabin on IndiGo.",
         html=chart(CARRY, "Ghee on a flight: cabin or check-in?",
                    group("Check-in bag: yes", "Up to 5 litres or 5 kg per person, packed so it can't leak.")
                    + group("Cabin bag: only a little", "Ghee counts as a liquid: containers of 100 ml or less, in your clear 1-litre bag.")
                    + group("Flying IndiGo?", "IndiGo doesn't allow ghee in the cabin at all.")
                    + CHECKED_10)),
    dict(slug="carry-alcohol", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/alcohol.html",
         title="Can I carry alcohol on a domestic flight in India?",
         description="On domestic flights, alcohol goes in check-in: up to 5 litres of 24–70% drinks in sealed shop packing. Plus beer and wine, duty-free bottles, dry states and how to pack bottles.",
         alt="Alcohol rules on Indian domestic flights: up to 5 litres in check-in, not in the cabin unless bought after security, no drinking on board.",
         html=chart(CARRY, "Alcohol on a domestic flight",
                    group("Check-in bag: yes", "Up to 5 litres per person of 24–70% alcohol, in its shop packing. Nothing over 70%.")
                    + group("Cabin bag: no", "Not alcohol from outside the airport. If you buy it after security, it can go in the cabin, sealed in the shop's bag.")
                    + group("Also", "You can't drink it on board, or take it to or from dry states such as Bihar and Gujarat.")
                    + CHECKED_10)),
    dict(slug="carry-umbrella", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/umbrella.html",
         title="Can I carry an umbrella on a flight in India?",
         description="A folding umbrella can go in your cabin bag, and on some airlines on top of your cabin allowance. An umbrella with a sharp tip goes in check-in. Rules for IndiGo, Air India, Akasa Air and SpiceJet.",
         alt="Umbrella rules on Indian flights: folding or blunt-tip umbrellas in the cabin, sharp-tip umbrellas in check-in.",
         html=chart(CARRY, "Umbrella on a flight: which bag?",
                    group("Cabin bag: folding or blunt tip", "A folding umbrella, or one with a blunt tip, can go in the cabin.")
                    + group("Sharp tip: check-in only", "Your check-in bag can take any umbrella, including a long one with a sharp tip.")
                    + group("On top of your allowance", "SpiceJet lets you carry one on top of your cabin bag allowance.")
                    + CHECKED_10)),
    dict(slug="carry-sweets", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/sweets-and-home-food.html",
         title="Can I carry sweets and home food on a flight in India?",
         description="Dry sweets, namkeen and snacks are fine in both bags. Sweets in syrup count as liquid, and oily food has its own rules. What IndiGo, Air India and Akasa Air allow, and how to pack food.",
         alt="Food rules on Indian flights: dry sweets and snacks in both bags, sweets in syrup count as liquid, no oily food on IndiGo.",
         html=chart(CARRY, "Sweets and home food on a flight",
                    group("Cabin bag", "Yes for dry sweets, snacks and biscuits. Sweets in syrup count as liquid.")
                    + group("Not on board", "Oily, messy or strong-smelling food.")
                    + group("Check-in bag", "Yes for dry sweets and food packed so it can't leak. IndiGo doesn't take oily food, even in check-in.")
                    + CHECKED_10)),
    dict(slug="carry-medicines", board="Flight and Train Baggage Rules", link="baggage/can-i-carry/medicines.html",
         title="Can I carry medicines on a flight in India?",
         description="Yes. Keep medicines in your cabin bag. When you need a prescription, syrups over 100 ml, insulin and ice packs, and IndiGo's check-in rule for medicines without a prescription.",
         alt="Medicine rules on Indian flights: keep them in your cabin bag, liquids over 100 ml with a prescription, check-in only with a prescription on IndiGo.",
         html=chart(CARRY, "Medicines on a flight: keep them with you",
                    group("Cabin bag: yes", "Keep the medicines you need with you. Liquid medicines over 100 ml are allowed if you need them on the journey and carry the prescription.")
                    + group("Check-in bag", "Yes, with a prescription on IndiGo. Akasa Air advises against it, because a bag can be late or lost.")
                    + CHECKED_10)),
    dict(slug="cabin-rules", board="Flight and Train Baggage Rules", link="guides/cabin-luggage-guide.html",
         title="Cabin bag rules in India: 7 kg, 115 cm, and why 55 cm isn't enough",
         description="Most Indian airlines allow one 7 kg cabin bag up to 115 cm in total. A trolley sold as \"55 cm\" tells you only its height. We checked 83 hard 55 cm trolleys, and 70 were too wide for IndiGo.",
         alt="Cabin bag rules on Indian flights: 7 kg, 115 cm in total, and a 55 cm bag that adds up to 116 cm.",
         html=chart("Flying in India", "Cabin bag rules: 7 kg and 115 cm",
                    '<div class="big"><div><b>7 kg</b><span>one cabin bag, the bag included</span></div><div><b>115 cm</b><span>length + width + height, wheels included</span></div></div>'
                    + group('"55 cm" is only the height', "Safari Pentagon Pro 55 cm: 55 + 38 + 23 = 116 cm. A little over 115 cm on paper.")
                    + group("Plus a personal item", "IndiGo allows one up to 3 kg, like a purse or a small laptop bag.")
                    + '<p class="note"><strong>70 of 83</strong> hard "55 cm" trolleys we checked were 36–41 cm wide, over IndiGo\'s 35 cm limit.</p>')),
    dict(slug="bag-checker", board="Flight and Train Baggage Rules", link="baggage/checker.html",
         title="Will your cabin bag fit? Free cabin bag size checker",
         description="Type your bag's length, width, height and weight to see if it fits the cabin limits of IndiGo, Air India, Air India Express, Akasa Air and SpiceJet, plus Emirates, Qatar Airways, Saudia and more.",
         alt="Three steps to check a cabin bag, and the cabin size limits of IndiGo, Akasa Air, SpiceJet, Air India and Air India Express.",
         html=chart("Free tool", "Will your cabin bag fit?",
                    group("1. Measure all three sides", "Height, width and depth in cm, with the wheels and handles.")
                    + group("2. Weigh it packed", "Most Indian airlines allow 7 kg, including the bag.")
                    + group("3. Type them in", "See which airlines your bag fits, and by how many cm it's over.")
                    + table(["Airline", "Cabin size limit"], [["IndiGo, Akasa, SpiceJet", "55 x 35 x 25 cm"], ["Air India", "55 x 40 x 20 cm"], ["Air India Express", "56 x 36 x 23 cm"]]))),
    dict(slug="indigo-rules", board="Flight and Train Baggage Rules", link="baggage/indigo.html",
         title="IndiGo baggage rules: cabin bag size and check-in allowance",
         description="IndiGo allows one 7 kg cabin bag up to 55 x 35 x 25 cm and 115 cm in total, plus a 3 kg personal item. Check-in is 15 kg on Saver and Flexi Plus fares and none on Lite. Each checked bag can be up to 158 cm.",
         alt="IndiGo baggage limits: a 7 kg cabin bag of 55 x 35 x 25 cm, and check-in allowance by fare from none on Lite to 15 kg plus 10 kg on the student fare.",
         html=chart("IndiGo domestic flights", "IndiGo baggage rules",
                    '<div class="big"><div><b>7 kg</b><span>cabin bag, 55 x 35 x 25 cm, 115 cm in total</span></div><div><b>15 kg</b><span>check-in on Saver and Flexi Plus fares</span></div></div>'
                    + table(["Fare", "Check-in bag"], [["Lite", "None, cabin bag only"], ["Saver, Flexi Plus", "15 kg, 1 piece"], ["IndiGo UpFront", "15 kg + 5 kg"], ["Student fare", "15 kg + 10 kg"]])
                    + '<p class="note"><strong>Plus one personal item up to 3 kg.</strong> Checked on IndiGo\'s site on 3 Nov 2026.</p>')),
    dict(slug="air-india-rules", board="Flight and Train Baggage Rules", link="baggage/air-india.html",
         title="Air India baggage rules: cabin bag size and check-in by fare",
         description="Air India allows one 7 kg cabin bag up to 55 x 40 x 20 cm, so a deep trolley can be too thick. Free check-in is 15 kg on Value and 25 kg on Flex. Classic is 20 kg on one Air India page and 15 kg on another.",
         alt="Air India baggage limits: a 7 kg cabin bag of 55 x 40 x 20 cm, and check-in of 15 kg on Value, 20 kg on Classic and 25 kg on Flex.",
         html=chart("Air India domestic flights", "Air India baggage rules",
                    '<div class="big"><div><b>7 kg</b><span>cabin bag, 55 x 40 x 20 cm</span></div><div><b>20 cm</b><span>deep at most, slimmer than many trolleys</span></div></div>'
                    + table(["Fare", "Check-in bag"], [["Economy Value", "15 kg, 1 piece"], ["Economy Classic", "20 kg (one page says 15 kg)"], ["Economy Flex", "25 kg, up to 2 pieces"]])
                    + '<p class="note"><strong>Check the allowance on your ticket.</strong> Checked on Air India\'s site on 3 Nov 2026.</p>')),
    dict(slug="gulf-rules", board="Flight and Train Baggage Rules", link="baggage/international.html",
         title="Baggage allowance from India to the Gulf: Emirates, Qatar, Saudia and more",
         description="Cabin bag size and checked baggage by fare for 12 airlines flying from India to the Gulf and Singapore, including Emirates, Qatar Airways, Etihad, flydubai, Air Arabia, Saudia, IndiGo and Air India.",
         alt="A table of cabin bag limits for Emirates, Qatar Airways, Etihad, flydubai, Air Arabia and Saudia on flights from India.",
         html=chart("Flying to the Gulf", "Cabin bag limits for Gulf flights", table(
             ["Airline", "Cabin bag"],
             [["Emirates", "7 kg, 55 x 38 x 22 cm"], ["Qatar Airways", "7 kg, 50 x 37 x 25 cm"], ["Etihad", "7 kg, 56 x 36 x 23 cm"],
              ["flydubai", "7 kg, 55 x 38 x 20 cm"], ["Air Arabia", "7 kg, 55 x 40 x 20 cm"], ["Saudia", "7 kg, 56 x 45 x 25 cm"]])
             + '<p class="note"><strong>Checked bags depend on your fare:</strong> none on some basic fares, up to 40 kg on others.</p>'
             + '<p class="note">Checked on airline sites on 3 Nov 2026. Rules change, so check before you fly.</p>')),
    dict(slug="size-by-trip", board="Luggage Size Guides", link="guides/luggage-size-guide.html",
         title="What size luggage do you need? Cabin, medium or large by trip length",
         description="Match your bag to your trip: a backpack for a weekend, a 55 cm cabin trolley for 2–4 days, a 65–69 cm medium bag for a week, and a 75–79 cm large bag for 10 days or more. Plus hard vs soft luggage.",
         alt="A table matching trip length to bag size, from a 30–40 litre backpack for a weekend to a 75–79 cm large trolley for 10 days or more.",
         html=chart("Luggage size guide", "What size luggage do you need?", table(
             ["Trip", "Bag"],
             [["Weekend, 1–3 days", "Duffle or backpack, 30–40 L"], ["2–4 days", "Cabin trolley, about 55 cm"], ["A week, 5–8 days", "Medium trolley, 65–69 cm"], ["10 days or more", "Large trolley, 75–79 cm"]])
             + group("The bag's own weight counts", "A hard cabin trolley often weighs 2.5–3 kg, and a medium one around 3.5 kg.")
             + '<p class="note"><strong>Check the total size of a large bag.</strong> Most we checked are listed over the 158 cm airline limit.</p>')),
    dict(slug="pick-indigo-cabin", board="Luggage Size Guides", link="picks/B097JLKP8X.html",
         title="A hard cabin trolley listed at exactly IndiGo's 55 x 35 x 25 cm limit",
         description="Most hard 55 cm trolleys are too wide for IndiGo. This Safari polycarbonate cabin bag is listed at 55 x 35 x 25 cm, 43 L and 2.7 kg, with a laptop section. The picture is our own drawing from its listed size, not a product photo.",
         alt="Our drawing of the Safari 55 cm cabin trolley at its listed 55 x 35 x 25 cm, inside IndiGo's dashed cabin limit. Illustration, not a product photo.",
         html=pick("Cabin bag that fits IndiGo", "Fits IndiGo's limit by listed size", "B097JLKP8X",
                   [["Listed size", "55 x 35 x 25 cm"], ["Weight", "2.7 kg"], ["Fits", "IndiGo, Akasa Air, SpiceJet"]],
                   "<strong>Safari 55 cm cabin trolley.</strong> Our drawing, to its listed size. Not a product photo.")),
    dict(slug="pick-air-india-cabin", board="Luggage Size Guides", link="picks/B0F5HGLC5Q.html",
         title="Cabin trolley for Air India: listed at 55 x 40 x 20 cm and 2.2 kg",
         description="Air India's cabin limit is 55 x 40 x 20 cm, so many trolleys are too deep. The American Tourister Liftoff+ Small is listed at exactly that size and 2.2 kg, with a TSA lock. It's 5 cm too wide for IndiGo. Our own drawing, not a product photo.",
         alt="Our drawing of the American Tourister Liftoff+ Small at its listed 55 x 40 x 20 cm, wider than IndiGo's dashed limit. Illustration, not a product photo.",
         html=pick("Cabin bag for Air India", "Slim enough for Air India's 20 cm limit", "B0F5HGLC5Q",
                   [["Listed size", "55 x 40 x 20 cm, 2.2 kg"], ["Air India", "Fits by listed size"], ["IndiGo (dashed)", "5 cm too wide"]],
                   "<strong>American Tourister Liftoff+ Small.</strong> Our drawing, to its listed size. Not a product photo.")),
    dict(slug="pick-light-medium", board="Luggage Size Guides", link="picks/B0GNSKLF5Z.html",
         title="The lightest medium trolley we found: 2.52 kg, good for 15 kg fares",
         description="The Kamiliant Rock-Lite 68 cm is listed at 2.52 kg, the lightest of the 36 medium trolleys we checked on Amazon.in. On a 15 kg fare, that leaves about 12.5 kg for your things. The picture is our own drawing, not a product photo.",
         alt="Our drawing of the Kamiliant Rock-Lite 68 cm medium trolley at its listed size. Illustration, not a product photo.",
         html=pick("Medium bag for a 15 kg fare", "The lightest medium trolley we found", "B0GNSKLF5Z",
                   [["Listed size", "68 x 47 x 29 cm"], ["Weight", "2.52 kg"], ["Litres", "66 L"]],
                   "<strong>Kamiliant Rock-Lite 68 cm.</strong> Lightest of 36 medium trolleys we checked. Our drawing, not a product photo.")),
    dict(slug="pick-158-large", board="Luggage Size Guides", link="picks/B0F5HLYQK3.html",
         title="A large trolley listed at exactly the 158 cm airline limit, and only 3.5 kg",
         description="Most large trolleys we checked go over 158 cm in total. The American Tourister Liftoff+ 79 cm is listed at 79 x 49 x 30 cm, exactly 158 cm, and 3.5 kg, with a TSA lock. The picture is our own drawing, not a product photo.",
         alt="Our drawing of the American Tourister Liftoff+ 79 cm large trolley at its listed 79 x 49 x 30 cm. Illustration, not a product photo.",
         html=pick("Large bag within 158 cm", "Exactly 158 cm, and only 3.5 kg", "B0F5HLYQK3",
                   [["Listed size", "79 x 49 x 30 cm"], ["Total", "158 cm"], ["Weight", "3.5 kg"]],
                   "<strong>American Tourister Liftoff+ 79 cm.</strong> Our drawing, to its listed size. Not a product photo.")),
    dict(slug="pick-pc-large", board="Luggage Size Guides", link="picks/B097G7K6FZ.html",
         title="A large polycarbonate trolley listed within the 158 cm limit",
         description="The Safari Astra Neo 76 cm is listed at 76 x 51 x 28 cm, 155 cm in total, with 98 litres and a hard polycarbonate shell. Most large bags we checked go over 158 cm. The picture is our own drawing, not a product photo.",
         alt="Our drawing of the Safari Astra Neo 76 cm large trolley at its listed 76 x 51 x 28 cm. Illustration, not a product photo.",
         html=pick("Large polycarbonate bag", "155 cm in total, under the 158 cm limit", "B097G7K6FZ",
                   [["Listed size", "76 x 51 x 28 cm"], ["Litres", "98 L"], ["Weight", "4.3 kg"]],
                   "<strong>Safari Astra Neo 76 cm.</strong> Our drawing, to its listed size. Not a product photo.")),
    dict(slug="pick-valex", board="Watches and Everyday Bags", link="picks/B0BTD4S4XF.html",
         title="A 28 litre laptop backpack that fits Indian airlines' cabin limits",
         description="The American Tourister Valex is listed at 47.5 x 32.5 x 20 cm and 510 g, with a sleeve for laptops up to 17 inches. By listed size it fits IndiGo, Air India, Air India Express, Akasa Air and SpiceJet. Our own drawing, not a product photo.",
         alt="Our drawing of the American Tourister Valex 28 litre backpack at its listed size, inside IndiGo's dashed cabin limit. Illustration, not a product photo.",
         html=pick("Laptop backpack for flights", "28 L that fits all five airlines", "B0BTD4S4XF",
                   [["Listed size", "47.5 x 32.5 x 20 cm"], ["Weight", "510 g"], ["Laptop", "Up to 17 inch"]],
                   "<strong>American Tourister Valex 28 L.</strong> Fits IndiGo, Air India, Air India Express, Akasa Air and SpiceJet by listed size.")),
    dict(slug="pick-scale", board="Packing and What to Wear", link="picks/B07Q822CWX.html",
         title="Weigh your bag at home before the airport does",
         description="A small digital luggage scale weighs bags up to 50 kg in 0.1 kg steps, so you can check your 7 kg cabin bag and 15 kg check-in bag before you leave. This one weighs about 150 g. The picture is our own drawing, not a product photo.",
         alt="Our drawing of a digital luggage scale with a hook. Illustration, not a product photo.",
         html=pick("Before you fly", "Weigh your bag at home first", "B07Q822CWX",
                   [["Weighs up to", "50 kg"], ["Steps", "0.1 kg"], ["Its own weight", "About 150 g"]],
                   "<strong>GoTrippin digital luggage scale.</strong> Our drawing, not a product photo.")),
    # 15 Nov 2026 (later): pages other sessions published the same day.
    dict(slug="extra-baggage", board="Flight and Train Baggage Rules", link="baggage/extra-baggage-charges.html",
         title="Extra baggage charges in India: IndiGo, Air India, Akasa, SpiceJet",
         description="What extra kg cost on domestic flights, from each airline's own pages: prepaid slabs, the airport rate per kg, extra bag fees and heavier cabin bags. Buying extra kg online before you fly costs less per kg than at the counter.",
         alt="A table of extra baggage charges on Indian domestic flights: 5 kg bought ahead and the airport rate per kg for IndiGo, Akasa Air, Air India Express, SpiceJet and Air India.",
         html=chart("Flying in India", "Extra baggage charges by airline", table(
             ["Airline", "5 kg ahead", "At the airport"],
             [["IndiGo", "₹3,750", "₹800 a kg"], ["Akasa Air", "₹3,750", "₹800 a kg"], ["Air India Express", "₹3,750", "Up to ₹850 a kg"],
              ["SpiceJet", "₹3,475", "₹775 a kg"], ["Air India", "Not listed", "₹800 a kg + tax"]])
             + group("Pay ahead, not at the counter", "Extra kg bought online before you fly cost less per kg than at the airport.")
             + '<p class="note">From each airline\'s own pages, 15 Nov 2026. Fees change, so check before you fly.</p>')),
    dict(slug="kashmir-december", board="India Trip Ideas", link="trips/kashmir-in-december.html",
         title="Kashmir in December: weather, snow in Gulmarg and what to wear",
         description="Plan Srinagar, Gulmarg, Pahalgam and Sonamarg for December: IMD temperatures, when snow usually comes, Chillai Kalan from 21 December, the Gulmarg Gondola, trains and roads in winter, and what to wear.",
         alt="Yellow gondola cabins above snowy slopes in Gulmarg, with the words Kashmir in December.",
         html=photo("gulmarg-gondola", "Kashmir in December", "Snow in Gulmarg, the gondola, winter roads and what to wear")),
    dict(slug="manali-december", board="Packing and What to Wear", link="guides/what-to-wear-in-manali-in-december.html",
         title="What to wear in Manali in December: layers, shoes and packing list",
         description="Manali in December is about 14 °C by day and 0 °C at night, and colder at the Atal Tunnel. Dress in layers you can add and take off, and wear waterproof shoes with a good grip. Packing lists for men, women and kids.",
         alt="Manali's average December day and night temperatures, and a table of four clothing layers to wear.",
         html=chart("Manali in December", "What to wear in Manali in December",
                    '<div class="big"><div><b>14 °C</b><span>a typical December day in Manali</span></div><div><b>0 °C</b><span>a typical night. The snow points are colder</span></div></div>'
                    + table(["Layer", "What to wear"], [["1. Next to skin", "Thermal top and bottom"], ["2. Middle", "Sweater or fleece"], ["3. Outside", "Padded jacket with a hood"], ["4. Extras", "Cap, gloves, woollen socks"]])
                    + group("Shoes", "Waterproof, with a good grip.")
                    + '<p class="note">IMD long-term averages. Snow is possible but not certain.</p>')),
    dict(slug="goa-packing", board="Packing and What to Wear", link="guides/goa-packing-list.html",
         title="Goa packing list for December and January: what to pack",
         description="Goa in winter is hot by day and pleasant at night, with almost no rain. So pack light clothes, good sun care, one warm layer and the right shoes. A short list, plus what to pack for women, men and kids.",
         alt="Goa's average December day and night temperatures, and a short packing list: light clothes, one warm layer, sun care and shoes.",
         html=chart("Goa in December", "Goa packing list: the short version",
                    '<div class="big"><div><b>33 °C</b><span>a typical December day</span></div><div><b>21 °C</b><span>a typical night, with almost no rain</span></div></div>'
                    + group("Clothes", "Light cotton or linen, swimwear, and one outfit that covers shoulders and knees for churches.")
                    + group("One warm layer", "A light sweater or shawl for evenings, flights and AC buses.")
                    + group("Sun and shoes", "Sunscreen, sunglasses, a cap, flip-flops and sandals with straps."))),
    # 15 Nov 2026: Christmas gift pages (feature_until 26 Dec), so these should go out by early December.
    dict(slug="secret-santa", board="Gift Ideas", link="guides/secret-santa-gift-ideas-for-office.html",
         title="Secret Santa gift ideas for office colleagues (men and women)",
         description="Useful Secret Santa gifts for the office: a wallet gift set for a male colleague, a zip-around wallet for a female colleague, and a steel bottle or gadget organiser when you don't know them well. Plus simple rules for the gift exchange.",
         alt="Secret Santa gift ideas for office colleagues: a wallet gift set, a zip-around wallet, a steel bottle, a gadget organiser and a toiletry bag.",
         html=chart("Office Secret Santa", "Secret Santa gifts colleagues actually use",
                    group("For a male colleague", "A leather wallet, keychain and pen set that comes in a gift box.")
                    + group("For a female colleague", "A zip-around wallet with 3 sections and card slots.")
                    + group("If you don't know them well", "A steel bottle for the desk, or a padded organiser for chargers and cables.")
                    + group("If they travel for work", "A light toiletry bag or a luggage scale.")
                    + '<p class="note"><strong>Skip perfume and clothes</strong> unless you know them well. Order by mid-December.</p>')),
    dict(slug="boss-gifts", board="Gift Ideas", link="guides/gift-for-boss.html",
         title="Gift ideas for your boss: Christmas and farewell",
         description="Gift ideas for a male or female boss that look smart and get used: classic Titan watches, leather wallets, work bags, and travel gear for a boss who flies for work. Plus why a team gift and a signed card work best.",
         alt="A watch on a wrist, with the words Gift ideas for your boss.",
         html=photo("watch-wrist", "Gift ideas for your boss", "Watches, work bags and travel gear for a male or female boss")),
    dict(slug="traveller-gifts", board="Gift Ideas", link="guides/gifts-for-travellers.html",
         title="Gifts for someone who travels a lot",
         description="People who travel a lot already have a suitcase. Give the small things they use on every trip: a toiletry bag, a gadget organiser, a passport holder or a luggage scale. Ideas for men and women, for work trips and holidays.",
         alt="Gifts for someone who travels a lot, by type of traveller: work trips, trips abroad, train journeys and a bigger group gift.",
         html=chart("Gift ideas", "Gifts for someone who travels a lot",
                    group("Flies for work", "A toiletry bag and a padded organiser for chargers and cables.")
                    + group("Going abroad", "A passport holder with SIM and card slots, and a luggage scale.")
                    + group("Takes trains and buses", "A steel bottle and a neck pillow with an eye mask.")
                    + group("A bigger gift from a group", "A cabin trolley whose listed size fits their airline.")
                    + '<p class="note"><strong>Small things get used most:</strong> most travellers already own a suitcase.</p>')),
    # 18 Nov 2026: family Christmas gift pages (feature_until 26 Dec), so these should also go out by early December.
    dict(slug="kids-christmas-gifts", board="Gift Ideas", link="guides/christmas-gifts-for-kids.html",
         title="Christmas gifts for kids: useful ideas for boys and girls",
         description="Christmas gifts kids use every day: a first analog watch from Titan's kids' brand Zoop in blue or pink, a school bag for younger kids or teens, a steel sipper bottle, and travel gifts for a December family trip. Plus simple return gift ideas for a Christmas party.",
         alt="Wrapped gifts under a Christmas tree, with the words Christmas gifts for kids.",
         html=photo("christmas-tree-gifts", "Christmas gifts for kids", "Watches, school bags and bottles for boys and girls")),
    dict(slug="christmas-gifts-for-her", board="Gift Ideas", link="guides/christmas-gift-for-girlfriend-or-wife.html",
         title="Christmas gift ideas for your girlfriend or wife (plus mom and sister)",
         description="Christmas gifts she'll use: a dressy Titan Raga watch for your girlfriend, a Titan Karishma or a neat tote for your wife, a zip-around wallet as a smaller gift, and a light crossbody bag or packing cubes if she loves to travel. Plus ideas for mom and your sister.",
         alt="Christmas gift ideas for a girlfriend, a wife, a woman who loves to travel and mom.",
         html=chart("Christmas gifts", "Christmas gifts for your girlfriend or wife",
                    group("For your girlfriend", "A dressy Titan Raga watch, or a vegan leather sling.")
                    + group("For your wife", "A Titan Karishma watch, or a small tote with 5 pockets.")
                    + group("If she loves to travel", "A crossbody bag of about 140 g, or packing cubes.")
                    + group("For mom", "Pair watches for mom and dad, or a thermal set for winter.")
                    + '<p class="note"><strong>A smaller gift:</strong> a zip-around wallet. Skip clothes in a size you have to guess.</p>')),
    dict(slug="christmas-gifts-for-him", board="Gift Ideas", link="guides/christmas-gift-for-boyfriend-or-husband.html",
         title="Christmas gift ideas for your boyfriend or husband (plus dad and brother)",
         description="Christmas gifts he'll use: a Timex Classics watch or polarized sunglasses for your boyfriend, a Titan Classique or a wallet gift set for your husband, a weekender duffle if he travels, and an easy-to-read Casio or a thermal set for dad.",
         alt="Christmas gift ideas for a boyfriend, a husband, a man who loves to travel and dad.",
         html=chart("Christmas gifts", "Christmas gifts for your boyfriend or husband",
                    group("For your boyfriend", "A Timex Classics watch, or polarized sunglasses.")
                    + group("For your husband", "A Titan Classique watch, or a wallet, keychain and pen set.")
                    + group("If he loves to travel", "A 35 litre weekender duffle, or a toiletry bag.")
                    + group("For dad", "A Casio watch with a date window, or a thermal set.")
                    + '<p class="note"><strong>Upgrade what he uses every day:</strong> a watch, a wallet or a work bag.</p>')),
    # 16 Nov 2026: winter trip guides.
    dict(slug="shimla-december", board="India Trip Ideas", link="trips/shimla-in-december.html",
         title="Shimla in December: snow chances, weather and what to wear",
         description="Shimla in December is about 12 °C by day and 4 °C at night (IMD averages). Snow usually comes from late December to early March, and is much more likely in January and February. Plus the Kalka–Shimla toy train, snow at Kufri and Narkanda, winter roads and what to wear.",
         alt="Snow on the pine trees and houses of a Shimla hillside, with the words Shimla in December.",
         html=photo("shimla-snow", "Shimla in December", "Snow chances, the toy train, winter roads and what to wear")),
    dict(slug="rishikesh-december", board="India Trip Ideas", link="trips/rishikesh-in-december.html",
         title="Rishikesh in December: weather, rafting, Ganga aarti and what to wear",
         description="Rishikesh in winter has sunny days and cold nights, and no snow. Rafting is open from September to June. This winter Ram Jhula and Lakshman Jhula are closed, and the Haridwar Kumbh starts on 14 January 2027. Weather, camps, aarti times, getting there and what to wear.",
         alt="The Ganga at dusk in Rishikesh with temple towers on the bank, with the words Rishikesh in December.",
         html=photo("rishikesh-ganga", "Rishikesh in December", "Rafting, the Ganga aarti, which bridges are open and what to wear")),
    dict(slug="udaipur-winter", board="India Trip Ideas", link="trips/udaipur.html",
         title="Udaipur trip plan for 2 or 3 days in winter",
         description="Udaipur in December is about 26 °C by day and 8 °C at night, with almost no rain. A simple 2-day plan for City Palace, Lake Pichola boats, Bagore ki Haveli and Fateh Sagar, a third day for Kumbhalgarh and Ranakpur, the Shilpgram Utsav and what to wear.",
         alt="City Palace in Udaipur seen from Lake Pichola, with the words Udaipur trip plan.",
         html=photo("udaipur-city-palace", "Udaipur trip plan", "2 or 3 days in winter: palaces, lake boats, Shilpgram and day trips")),
    # 16 Nov 2026 (2 PM job): Andaman and Darjeeling winter guides.
    dict(slug="andaman-december", board="India Trip Ideas", link="trips/andaman-in-december.html",
         title="Andaman in December: weather, ferries, permits and what to pack",
         description="Andaman in December is warm, with days about 30–31 °C and nights about 24–26 °C, and some rain. Ferries to Havelock (Swaraj Dweep) and Neil (Shaheed Dweep), Jolly Buoy from mid-November, permits, coral and beach rules, the Island Tourism Festival (27–31 Dec 2026) and what to pack.",
         alt="A white sand beach on Havelock with turquoise water, with the words Andaman in December.",
         html=photo("andaman-havelock", "Andaman in December", "Weather, ferries to Havelock and Neil, permits and what to pack")),
    dict(slug="darjeeling-december", board="India Trip Ideas", link="trips/darjeeling-in-december.html",
         title="Darjeeling in December: weather, snow chances, toy train and what to wear",
         description="Darjeeling in December is about 14 °C by day and 4 °C at night (IMD averages), and very dry, with clear views of Kanchenjunga. Snow in town is rare; Sandakphu gets it most winters. Tiger Hill sunrise and its vehicle pass, toy train joy rides and what to wear.",
         alt="A blue Darjeeling toy train engine between hillside buildings, with the words Darjeeling in December.",
         html=photo("darjeeling-toy-train", "Darjeeling in December", "Snow chances, Tiger Hill, the toy train and what to wear")),
    # 16 Nov 2026: packing lists for trips abroad from India, and the UAE customs page.
    dict(slug="thailand-packing", board="Packing and What to Wear", link="guides/thailand-packing-list.html",
         title="Thailand packing list from India: what to pack and wear",
         description="Thailand is hot all year, and mostly dry in Bangkok from December to February. Pack light cotton clothes, one outfit that covers shoulders and knees for temples, a light jacket for the north, rain gear for Phuket, and a cabin bag that fits your airline.",
         alt="Bangkok's average December day and night temperatures, and a short Thailand packing list: light clothes, a temple outfit, rain gear and the right cabin bag.",
         html=chart("Thailand from India", "Thailand packing list: the short version",
                    '<div class="big"><div><b>31 °C</b><span>a typical December day in Bangkok</span></div><div><b>21 °C</b><span>a typical night. Chiang Mai is cooler</span></div></div>'
                    + group("Clothes", "Light cotton or linen, swimwear, and one outfit that covers shoulders and knees for temples.")
                    + group("Rain and sun", "A poncho for Phuket showers in November and December. Sunscreen, a cap and sunglasses.")
                    + group("Your bag", "IndiGo gives 20 kg to Bangkok, Phuket and Krabi on regular fares, and a 7 kg cabin bag.")
                    + '<p class="note">Weather: Thai Meteorological Department averages via WMO.</p>')),
    dict(slug="dubai-packing", board="Packing and What to Wear", link="guides/dubai-packing-list.html",
         title="Dubai packing list from India: what to pack and wear",
         description="Dubai is warm and dry from November to March, with cool nights in December and January. Pack light clothes, modest outfits for malls, souks and mosques, a warm layer for the desert safari, and a cabin bag that fits Emirates, flydubai or IndiGo.",
         alt="Dubai's average December day and night temperatures, and a short Dubai packing list: light clothes, modest outfits, a warm layer and the cabin bag limit.",
         html=chart("Dubai from India", "Dubai packing list: the short version",
                    '<div class="big"><div><b>26 °C</b><span>a typical December day in Dubai</span></div><div><b>15 °C</b><span>a typical night. Take a jacket</span></div></div>'
                    + group("Clothes", "Light cotton for the day, and outfits that cover shoulders and knees for malls, souks and mosques.")
                    + group("One warm layer", "A light jacket or shawl for winter evenings, the desert safari and cold malls.")
                    + group("Your bag", "Emirates: one 7 kg cabin bag, 55 x 38 x 22 cm. Check-in 20–35 kg by fare.")
                    + '<p class="note">Weather: UAE NCM averages via WMO.</p>')),
    dict(slug="uae-customs", board="Flight and Train Baggage Rules", link="baggage/customs/uae-dubai.html",
         title="What can I carry from India to Dubai? UAE customs rules",
         description="UAE customs lets you bring gifts worth AED 3,000, 200 cigarettes and 4 litres of alcohol duty free. Declare more than AED 60,000 in cash or gold. Poppy seeds (khus khus) and paan are banned, and medicines like tramadol and pregabalin need a prescription.",
         alt="A table of UAE duty-free limits: AED 3,000 of gifts, 200 cigarettes, 4 litres of alcohol and cash over AED 60,000 to declare, plus banned items and the medicine rule.",
         html=chart("Flying India to Dubai", "UAE customs: what you can bring in", table(
             ["What", "Duty-free limit"],
             [["Gifts and perfume", "AED 3,000"], ["Cigarettes", "200"], ["Alcohol (18+)", "4 litres"], ["Cash and gold", "Declare over 60,000"]])
             + group("Banned", "Poppy seeds (khus khus), paan and betel leaves, drugs, fake goods.")
             + group("Controlled medicines", "Tramadol, pregabalin, codeine and others: prescription, up to 3 months.")
             + '<p class="note">Limits in AED. Checked 16 Nov 2026.</p>')),
    dict(slug="bali-packing", board="Packing and What to Wear", link="guides/bali-packing-list.html",
         title="Bali packing list from India: what to pack and wear",
         description="Bali is hot all year, and December and January bring rain on most days. Pack quick-dry clothes, a rain poncho, sandals that can get wet, a temple outfit that covers shoulders and knees, and pay the Rp 150,000 Bali levy on the official Love Bali site.",
         alt="Denpasar's December rain and temperatures, and a short Bali packing list: quick-dry clothes, rain gear, a temple outfit and the bag allowance.",
         html=chart("Bali from India", "Bali packing list: the short version",
                    '<div class="big"><div><b>22 days</b><span>with rain in a typical December in Denpasar</span></div><div><b>33 °C</b><span>a typical December day</span></div></div>'
                    + group("Rain gear", "A poncho, quick-dry clothes and a waterproof phone pouch.")
                    + group("Temples", "Cover shoulders and knees. Many temples give or rent a sarong and sash.")
                    + group("Your bag", "IndiGo gives 20 kg to Bali on regular fares, and a 7 kg cabin bag.")
                    + '<p class="note">Weather: BMKG averages via WMO.</p>')),
    # 16 Nov 2026: farewell gifts (all year, no feature date).
    dict(slug="farewell-gifts", board="Gift Ideas", link="guides/farewell-gift-for-colleague.html",
         title="Farewell gift ideas for a colleague, your boss or someone retiring",
         description="Useful farewell gifts for a colleague: a wallet gift set for a male colleague, a zip-around wallet or a watch for a female colleague, a classic Titan for your boss, a passport holder for someone moving abroad, and a weekender bag for someone retiring. Plus how to choose a team gift.",
         alt="Farewell gift ideas by who is leaving: a male colleague, a female colleague, your boss, someone moving abroad and someone retiring.",
         html=chart("Farewell gifts", "Farewell gifts your colleague will use",
                    group("For a male colleague", "A leather wallet, keychain and pen set that comes in a gift box.")
                    + group("For a female colleague", "A zip-around wallet, or a Titan watch as a team gift.")
                    + group("For your boss or a senior", "A classic watch or a slim laptop backpack.")
                    + group("Moving abroad", "A passport holder, a luggage scale and packing cubes.")
                    + group("Retiring", "A weekender bag for trips, or a couple watch set."))),
    # 18 Nov 2026: more packing lists (Andaman, then trips abroad).
    dict(slug="andaman-packing", board="Packing and What to Wear", link="guides/andaman-packing-list.html",
         title="Andaman packing list: what to pack and wear, for women, men and couples",
         description="Andaman is warm all year, at about 30 °C, and December still brings showers. Pack light cotton clothes and dresses, swimwear, a rain poncho, floaters that can get wet, a waterproof pouch for ferries, a towel and a steel bottle. Government ferries allow 25–40 kg by class.",
         alt="Port Blair's December weather and a short Andaman packing list: light clothes, rain gear, shoes that can get wet and the ferry baggage limits.",
         html=chart("Andaman trip", "Andaman packing list: the short version",
                    '<div class="big"><div><b>30 °C</b><span>a typical December day in Sri Vijaya Puram</span></div><div><b>113 mm</b><span>of rain in a usual December</span></div></div>'
                    + group("Clothes", "Light cotton, swimwear with a cover-up, a long-sleeved top and a poncho.")
                    + group("Boats and beaches", "Floaters that can get wet, a waterproof pouch, a towel and a steel bottle.")
                    + group("Your bags", "Ferries: 25 kg Deck, 30 kg Bunk, 40 kg Cabin. Flights: 15 kg.")
                    + '<p class="note">Weather: IMD Port Blair station. Ferry rules: DSS.</p>')),
    dict(slug="vietnam-packing", board="Packing and What to Wear", link="guides/vietnam-packing-list.html",
         title="Vietnam packing list from India: what to pack and wear in December",
         description="Vietnam has three kinds of weather in winter: Hanoi is cool, about 22 °C by day and 15 °C at night, Da Nang and Hoi An are rainy, and Ho Chi Minh City is hot, about 32 °C. Pack a light jacket, a poncho, summer clothes, a temple outfit, and leave your vape at home: Vietnam bans them.",
         alt="December weather in Hanoi, Da Nang and Ho Chi Minh City, and a short Vietnam packing list: a jacket for the north, a poncho for the centre and summer clothes for the south.",
         html=chart("Vietnam from India", "Vietnam packing list: the short version", table(
             ["December", "Day", "Night"],
             [["Hanoi", "22 °C", "15 °C"], ["Da Nang", "25 °C", "21 °C"], ["Ho Chi Minh City", "32 °C", "24 °C"]])
             + group("North", "A light jacket and long trousers. Sa Pa is colder.")
             + group("Centre and south", "A poncho for Da Nang and Hoi An, summer clothes for the south.")
             + group("Don't pack", "Vapes and e-cigarettes: Vietnam bans them.")
             + '<p class="note">Weather: VNMHA averages via WMO.</p>')),
    dict(slug="maldives-packing", board="Packing and What to Wear", link="guides/maldives-packing-list.html",
         title="Maldives packing list from India: what to pack and wear, for couples",
         description="The Maldives is about 30 °C all year. Pack beach clothes, modest outfits for Malé and local islands, light evening wear, sunscreen and a waterproof pouch. Don't bring alcohol, idols for worship or a vape, and pack light for seaplanes: Trans Maldivian allows 20 kg plus 5 kg of hand luggage.",
         alt="Malé's average day temperature and the seaplane bag limit, and a short Maldives packing list: what to wear and what you can't bring in.",
         html=chart("Maldives from India", "Maldives packing list: the short version",
                    '<div class="big"><div><b>30 °C</b><span>a typical day in Malé, all year</span></div><div><b>20 + 5 kg</b><span>on a Trans Maldivian seaplane</span></div></div>'
                    + group("Clothes", "Beachwear for resorts, modest clothes for Malé and local islands.")
                    + group("Sun and sea", "Sunscreen, polarized sunglasses and a waterproof pouch.")
                    + group("Don't bring", "Alcohol, pork, idols for worship, vapes and e-cigarettes.")
                    + '<p class="note">Weather: Maldives Met Service via WMO.</p>')),
]


def render(pin, work):
    """Write the pin's HTML, take a screenshot with headless Chrome and save it as a JPEG."""
    html = '<!doctype html><meta charset="utf-8"><link href="%s" rel="stylesheet"><style>%s</style><body>%s</body>' % (FONTS, CSS, pin["html"])
    page = work / (pin["slug"] + ".html")
    page.write_text(html, encoding="utf-8")
    png = work / (pin["slug"] + ".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", "--allow-file-access-from-files",
                    "--user-data-dir=%s" % (work / "chrome"), "--window-size=1000,1500", "--virtual-time-budget=6000",
                    "--screenshot=%s" % png, page.as_uri()], check=True, capture_output=True, timeout=120)
    subprocess.run(["magick", str(png), "-crop", "1000x1500+0+0", "-quality", "88", str(OUT / (pin["slug"] + ".jpg"))], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:] or [p["slug"] for p in PINS]
    with tempfile.TemporaryDirectory() as tmp:
        for pin in PINS:
            if pin["slug"] in wanted:
                render(pin, Path(tmp))
                print("Made", pin["slug"])
    data = [{"slug": p["slug"], "image": p["slug"] + ".jpg", "board": p["board"], "title": p["title"], "alt": p["alt"], "link": SITE + p["link"],
             "description": p["description"] + " " + DISCLOSURE} for p in PINS]
    too_long = [p["slug"] for p in data if len(p["title"]) > 100 or len(p["description"]) > 500]
    if too_long:
        sys.exit("Error: title or description too long: %s" % ", ".join(too_long))
    (OUT / "pins.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
