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
         description="Empty bags use up your baggage allowance too. See typical weights for backpacks, duffles and trolleys, then check your packed bags against your airline's allowance with our free excess baggage calculator.",
         alt="A table of typical empty weights for a backpack, duffle bag and cabin, medium and large trolleys.",
         html=chart("Before you pack", "How heavy is your bag when it's empty?", table(
             ["Bag", "Typical weight"],
             [["Backpack", "0.6 kg"], ["Duffle bag", "1.2 kg"], ["Soft cabin trolley", "2.4 kg"], ["Hard cabin trolley", "2.7 kg"], ["Medium check-in trolley", "3.5 kg"], ["Large check-in trolley", "4.5 kg"]])
             + '<p class="note"><strong>It all counts.</strong> The empty bag uses your allowance. Weigh yours, then check it with our free excess baggage calculator.</p>')),
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
    dict(slug="sri-lanka-packing", board="Packing and What to Wear", link="guides/sri-lanka-packing-list.html",
         title="Sri Lanka packing list from India: what to pack and wear",
         description="Sri Lanka's coasts are about 30 °C, but Nuwara Eliya nights are about 9–11 °C in winter. Pack light clothes, a warm layer for the hills, a rain poncho and temple clothes that cover shoulders and legs. Don't bring cigarettes, beedis, gutka or fruit: Sri Lanka Customs doesn't allow them in.",
         alt="Colombo and Nuwara Eliya December temperatures, and a short Sri Lanka packing list: light clothes, a warm layer, temple clothes and what you can't bring in.",
         html=chart("Sri Lanka from India", "Sri Lanka packing list: the short version",
                    '<div class="big"><div><b>30 °C</b><span>a typical December day in Colombo</span></div><div><b>11 °C</b><span>a December night in Nuwara Eliya</span></div></div>'
                    + group("Clothes", "Light cotton, a warm layer for the hills, and a poncho.")
                    + group("Temples", "Cover shoulders and legs. No shorts or sleeveless tops in Kandy.")
                    + group("Don't bring", "Cigarettes, beedis, gutka or fresh fruit.")
                    + '<p class="note">Weather: National Meteorological Centre via WMO.</p>')),
    dict(slug="ooty-december", board="India Trip Ideas", link="trips/ooty-in-december.html",
         title="Ooty in December: weather, frost (no snow) and a 2-3 day plan",
         description="Ooty in December is about 21 °C by day and 7 °C at night (IMD averages). It doesn't snow, but cold mornings bring ground frost. Plan 2 or 3 days with the toy train, tea gardens and Doddabetta, plus the e-pass and what to wear.",
         alt="Green tea estate hills in Ooty, with the words Ooty in December.",
         html=photo("ooty-tea-estate", "Ooty in December", "About 21 °C by day, 7 °C at night. Frost, not snow. A 2–3 day plan")),
    dict(slug="varanasi-december", board="India Trip Ideas", link="trips/varanasi-in-december.html",
         title="Varanasi in December: weather, fog, the aarti and a 2-3 day plan",
         description="Varanasi in December is about 24 °C by day and 10 °C at night (IMD averages), and dense fog is common from late December. Plan the ghats, the Ganga aarti, Kashi Vishwanath and Sarnath in 2 or 3 days, and what to wear.",
         alt="Boats on the Ganga beside the ghats of Varanasi, with the words Varanasi in December.",
         html=photo("varanasi-ghats-boat", "Varanasi in December", "Cool, dry and often foggy. Ghats, aarti and Sarnath in 2–3 days")),
    dict(slug="bhutan-december", board="India Trip Ideas", link="trips/bhutan-in-december.html",
         title="Bhutan in December: weather, snow chances, festivals and a 6-day plan",
         description="Bhutan in December is sunny by day (about 15-20 °C) and freezing at night in Paro and Thimphu. Snow is possible on the high passes. See the December festivals, how to get there from India, the SDF for Indians and what to wear.",
         alt="Tiger's Nest monastery on a cliff in Bhutan, with the words Bhutan in December.",
         html=photo("bhutan-tigers-nest", "Bhutan in December", "Sunny days, freezing nights, festivals and a 6-day plan")),
    dict(slug="bhutan-packing", board="Packing and What to Wear", link="guides/bhutan-packing-list.html",
         title="Bhutan packing list from India: documents, clothes and bag limits",
         description="Indians don't need a visa for Bhutan, but you need a passport or original voter ID, a guide and the daily SDF. Pack thermals for nights near 0 °C in Paro and Thimphu, walking shoes for Tiger's Nest, and a small cabin bag for Drukair.",
         alt="Bhutan short list: passport or voter ID, no visa, SDF Nu 1,200 a night, thermals and Paro and Thimphu night temperatures.",
         html=chart("Bhutan from India", "Bhutan packing list: the short version",
                    '<div class="big"><div><b>No visa</b><span>passport or original voter ID, plus a guide</span></div><div><b>Nu 1,200</b><span>daily fee per person per night for Indians (SDF)</span></div></div>'
                    + group("Cold nights", "Thermals, a warm jacket, cap and gloves. Paro and Thimphu fall to about 0 °C.")
                    + group("Temples and treks", "Long sleeves and trousers for dzongs. Grip shoes for Tiger's Nest.")
                    + group("Bag", "Drukair's cabin limit is 45 x 35 x 20 cm.")
                    + '<p class="note">Rules from Bhutan\'s Department of Tourism. Checked 18 Nov 2026.</p>')),
    dict(slug="nepal-packing", board="Packing and What to Wear", link="guides/nepal-packing-list.html",
         title="Nepal packing list from India: documents, money and what to wear",
         description="Indians don't need a visa for Nepal, but only a passport or an original voter ID is accepted on flights, and Indian notes above ₹100 have a ₹25,000 limit. Pack for Kathmandu nights near 3 °C, temple clothes and a cabin bag that fits.",
         alt="Nepal short list: only passport or voter ID accepted on flights, ₹25,000 limit on ₹200 and ₹500 notes, and Kathmandu January temperatures.",
         html=chart("Nepal from India", "Nepal packing list: the short version",
                    '<div class="big"><div><b>2 IDs</b><span>only a passport or original voter ID works on flights</span></div><div><b>₹25,000</b><span>limit in ₹200 and ₹500 notes per person</span></div></div>'
                    + group("Cold nights", "Kathmandu is about 20 °C by day and 4 °C at night in December.")
                    + group("Temples", "Clothes that cover shoulders and knees. Shoes that are easy to take off.")
                    + group("Don't take", "Aadhaar, PAN or a driving licence as your travel ID. They aren't accepted.")
                    + '<p class="note">Rules from the Embassy of India in Kathmandu and Nepal Rastra Bank.</p>')),
    dict(slug="travel-tech", board="Flight and Train Baggage Rules", link="category/travel-tech.html",
         title="Power banks and travel adapters for flights: what to look for",
         description="Power banks go in your cabin bag only. 10,000 and 20,000 mAh power banks are about 37 and 74 Wh, under the 100 Wh limit on Indian airlines. Our picks list the mAh, ports and size, plus universal adapters for plugs abroad.",
         alt="A table of power bank sizes in mAh and watt-hours, with a note that they go in the cabin bag only.",
         html=chart("Travel tech", "Power banks for flights",
                    table(["Power bank", "Watt-hours", "Cabin bag"], [["10,000 mAh", "37 Wh", "Yes"], ["20,000 mAh", "74 Wh", "Yes"], ["26,800 mAh", "99 Wh", "Yes"], ["30,000 mAh", "111 Wh", "IndiGo only"]])
                    + group("Cabin bag only", "Never in check-in, on every Indian airline.")
                    + group("Going abroad?", "A universal adapter covers the plugs in most countries.")
                    + '<p class="note">Rules checked 20 Nov 2026. Watt-hours = mAh x 3.7 ÷ 1,000.</p>')),
    dict(slug="sunglasses", board="Watches and Everyday Bags", link="category/sunglasses.html",
         title="How to read sunglasses numbers: 56-19-140 and polarized lenses",
         description="The three numbers on a frame, like 56-19-140, are lens width, bridge and arm length in mm. Narrow face? Try 50 to 52 mm lenses. See sunglasses for beaches, snow and driving, with polarized and UV details read from each listing.",
         alt="A chart explaining the three numbers on a sunglasses frame: lens width, bridge width and arm length in millimetres.",
         html=chart("Sunglasses guide", "What do the numbers on sunglasses mean?",
                    '<div class="stat">56-19-140</div>'
                    + table(["On the arm", "What it is"], [["56", "Lens width, mm"], ["19", "Bridge, mm"], ["140", "Arm length, mm"]])
                    + group("Narrow face?", "Try a lens width of about 50 to 52 mm.")
                    + group("Polarized or UV?", "Polarized cuts glare on water and roads. Check for UV400 too.")
                    )),
    dict(slug="wallets-belts", board="Gift Ideas", link="category/wallets-belts.html",
         title="Wallet and belt gifts: genuine, full grain and vegan leather explained",
         description="Genuine leather is real leather, but a lower grade than full grain or top grain. Vegan or PU leather is not leather at all. See wallets and belts that make easy gifts, with card slots, leather type and waist range read from each listing.",
         alt="A table comparing full grain, top grain, genuine and vegan leather, for choosing a wallet or belt gift.",
         html=chart("Wallets and belts", "Which leather is it? A gift guide",
                    table(["Label", "What it means"], [["Full grain", "Real leather, higher grade"], ["Top grain", "Real leather, higher grade"], ["Genuine", "Real leather, lower grade"], ["Vegan or PU", "Not leather at all"]])
                    + group("Wallet gift", "Check the card slots, RFID blocking and zip or bifold.")
                    + group("Belt gift", "Check the waist range. A reversible belt works with black and brown shoes.")
                    + '<p class="note">Read from product listings. Good for Secret Santa and Christmas.</p>')),
    dict(slug="perfumes", board="Gift Ideas", link="category/perfumes.html",
         title="Perfume gift sets for flights: the 100 ml cabin rule and IndiGo's ban",
         description="Perfume is a liquid at airport security: 100 ml or less in your clear 1-litre bag. IndiGo doesn't allow perfume in the cabin at all, so pack it in check-in. See gift sets, attars and pocket sprays from Indian brands.",
         alt="A real perfume bottle photo with the words Perfume gifts and the 100 ml cabin rule.",
         html=photo("perfume-bottle", "Perfume gifts for travellers", "Cabin bags: 100 ml or less each. IndiGo: pack it in check-in")),
    dict(slug="perfume-guide", board="Gift Ideas", link="guides/perfume-buying-guide.html",
         title="EDP vs EDT vs attar: perfume gift guide with travel sizes",
         description="The words on a perfume box tell you how strong it is and how long it lasts. Learn EDP, EDT, deo and attar in plain words, which sizes you can take on a flight, and gift sets for men, women and couples.",
         alt="A table comparing EDP, EDT, deo or body spray and attar by strength and how long they last.",
         html=chart("Perfume gift guide", "EDP, EDT, deo or attar?",
                    table(["Type", "In plain words"], [["EDP", "Strong, most of a day"], ["EDT", "Medium, a few hours"], ["Body mist or deo", "Light, 1–2 hours"], ["Attar", "Pure oil, no alcohol"]])
                    + group("On a flight", "Bottles of 100 ml or less in your clear 1-litre bag. IndiGo: check-in only.")
                    + group("Gift tip", "Sets of four 20 ml sprays let them try four scents.")
                    + '<p class="note">Rules checked on airline sites. They can change.</p>')),
    dict(slug="shoe-size-tool", board="Packing and What to Wear", link="tools/shoe-size.html",
         title="Shoe size chart for India: India/UK to US, EU and cm",
         description="India and UK shoe sizes are the same number. On Bata India's chart, a men's UK 8 is a US 8.5 and an EU 42, for a foot of 25.8 to 26.5 cm. Measure your foot in cm and use the free converter for men, women and kids.",
         alt="A shoe size chart showing India or UK 6 to 10 with US, EU sizes and foot length in cm.",
         html=chart("Free shoe size tool", "Shoe size chart for India",
                    table(["India / UK", "US", "EU", "Foot cm"], [["6", "6.5", "40", "24.2–24.9"], ["7", "7.5", "41", "25–25.7"], ["8", "8.5", "42", "25.8–26.5"], ["9", "9.5", "43", "26.6–27.3"], ["10", "10.5", "44", "27.4–28.3"]])
                    + '<p class="note"><strong>India and UK are the same number.</strong> Men\'s sizes, from Bata India\'s chart. Measure your foot in cm: it is the surest way.</p>')),
    dict(slug="power-bank-tool", board="Flight and Train Baggage Rules", link="tools/power-bank-flight-check.html",
         title="Is my power bank allowed on the flight? mAh to Wh checker",
         description="Type your power bank's mAh to see its watt-hours and whether IndiGo, Air India and Akasa Air allow it. Up to 100 Wh is fine on all three. Power banks go in the cabin bag only, never in check-in.",
         alt="A table of power bank sizes from 5,000 to 30,000 mAh with watt-hours and whether IndiGo, Air India and Akasa Air allow them.",
         html=chart("Free flight checker", "Is my power bank allowed?",
                    table(["Power bank", "Wh", "IndiGo", "Air India", "Akasa"], [["10,000 mAh", "37", "Yes", "Yes", "Yes"], ["20,000 mAh", "74", "Yes", "Yes", "Yes"], ["26,800 mAh", "99", "Yes", "Yes", "Yes"], ["30,000 mAh", "111", "Yes", "No", "No"]])
                    + group("Always", "Cabin bag only. Never in check-in.")
                    + '<p class="note"><strong>Wh = mAh x 3.7 ÷ 1,000.</strong> Rules checked 20 Nov 2026.</p>')),
    dict(slug="packing-list-maker", board="Packing and What to Wear", link="tools/packing-list-maker.html",
         title="Free packing list maker: a list for your trip, days and month",
         description="Pick the kind of trip, the days, the month and who is going, and get a packing list with the right counts. Tick items off, print it or share it on WhatsApp. Free, and your ticks stay in your browser.",
         alt="Steps of the packing list maker: choose trip type, days, month and who is going, then tick items off.",
         html=chart("Free tool", "Make your own packing list",
                    table(["Step", "You choose"], [["1", "Beach, hills, city or abroad"], ["2", "How many days"], ["3", "The month"], ["4", "Who is going"]])
                    + group("You get", "A list with counts for your days. Tick items off, print it or share it.")
                    + '<p class="note"><strong>Rule of thumb:</strong> one top a day plus one spare, trousers for every 3 days.</p>')),
    dict(slug="gift-finder", board="Gift Ideas", link="tools/gift-finder.html",
         title="Gift finder quiz: what gift should I give? Answer 3 questions",
         description="Not sure what to give? Say who the gift is for, the occasion and how big a gift, and get ideas for Christmas, Secret Santa, farewell, birthday or wedding. Free quiz with links to our gift guides.",
         alt="Three questions of the gift finder quiz: who is it for, what is the occasion, and how big a gift.",
         html=chart("Free quiz", "What gift should I give?",
                    table(["Question", "Examples"], [["1. Who is it for?", "Boss, wife, kids, parents"], ["2. What occasion?", "Christmas, farewell, wedding"], ["3. How big?", "Token, nice or big gift"]])
                    + group("Then", "See ideas for that person, with links to our full gift guides.")
                    + '<p class="note">Takes under a minute. No sign-up.</p>')),
    dict(slug="clothing-size", board="Packing and What to Wear", link="tools/clothing-size.html",
         title="Size chart for men, women and kids in India: UK, US, EU to Indian size",
         description="India has no single size system. Measure your chest, waist and hips in cm, then convert UK, US and EU sizes to Indian sizes for tops, jeans and kids' clothes. Free converter. Sizes vary by brand.",
         alt="A women's size chart for M&S India with UK, US, EU and bust size in cm.",
         html=chart("Free size converter", "Clothing size chart for India",
                    table(["UK", "Letter", "US", "EU", "Bust cm"], [["8", "S", "4–6", "36–38", "82"], ["10", "S", "4–6", "36–38", "87"], ["12", "M", "8–10", "40–42", "92"], ["14", "M", "8–10", "40–42", "97"], ["16", "L", "12–14", "44–46", "102.5"]])
                    + '<p class="note"><strong>Go by your body in cm, not the letter.</strong> Women\'s tops from Marks &amp; Spencer India\'s chart. Sizes vary by brand.</p>')),
    dict(slug="nepal-december", board="India Trip Ideas", link="trips/nepal-in-december.html",
         title="Nepal in December: weather, snow, festivals and a 6-day plan",
         description="Nepal in December is dry and sunny, with Kathmandu at about 20 °C by day and 4 °C at night. Snow stays on the high trekking routes, not in Kathmandu or Pokhara. See the festivals, the Everest mountain flight, how to get there from India, the ID you need and what to wear.",
         alt="Annapurna mountains above Pokhara in Nepal, with the words Nepal in December.",
         html=photo("nepal-pokhara-annapurna", "Nepal in December", "Dry, sunny and cold at night. Weather, snow, festivals and a 6-day plan")),
    dict(slug="bhutan-by-road", board="India Trip Ideas", link="trips/bhutan-by-road.html",
         title="Bhutan by road from India: permit, route and driving your own car",
         description="Yes, Indians can go to Bhutan by road. Most people fly to Bagdogra or take a train to New Jalpaiguri, then cross at Jaigaon and Phuentsholing. See the entry permit, the daily SDF, the guide rule and what driving your own car costs.",
         alt="Dochula pass in Bhutan, with the words Bhutan by road from India.",
         html=photo("bhutan-dochula", "Bhutan by road from India", "Jaigaon to Phuentsholing: the permit, the SDF and your own car")),
    dict(slug="what-to-wear-tool", board="Packing and What to Wear", link="tools/what-to-wear.html",
         title="What to wear in 20 places by month: Manali, Goa, Dubai and more",
         description="Pick a place and a month and see what to wear: layers for hills, light clothes for beaches, and what to carry abroad. A free tool for 20 places in India and abroad, with numbers from official weather sources.",
         alt="Lists of the 20 places in the what to wear tool: hill places, beach places and places abroad.",
         html=chart("Free tool", "What to wear, by place and month",
                    group("Hills and snow", "Manali, Shimla, Kashmir, Darjeeling, Ooty, Bhutan, Nepal")
                    + group("Cities and culture", "Rishikesh, Varanasi, Udaipur, Jaipur")
                    + group("Beaches and coast", "Goa, Kerala, Andaman, Maldives, Bali, Sri Lanka")
                    + group("Abroad", "Dubai, Thailand, Vietnam")
                    + '<p class="note"><strong>Pick a place and a month.</strong> You get what to wear by day, at night and on your feet.</p>')),
    dict(slug="singapore-packing", board="Packing and What to Wear", link="guides/singapore-packing-list.html",
         title="Singapore packing list from India: what to pack and wear",
         description="Singapore is hot and humid all year, about 30 °C by day, and rain is most likely from November to January. Pack light cotton clothes, a poncho or umbrella, walking shoes and one layer for cold air conditioning. Indians need a visa and an SG Arrival Card, and Singapore has strict rules on chewing gum and vapes.",
         alt="Singapore December weather and a short packing list: visa, SG Arrival Card, light clothes, a layer for air conditioning and rain gear.",
         html=chart("Singapore from India", "Singapore packing list: the short version",
                    '<div class="big"><div><b>30 °C</b><span>average December day, humid at about 85%</span></div><div><b>Visa</b><span>needed for Indians, plus an SG Arrival Card</span></div></div>'
                    + group("Clothes", "Light cotton or linen, and one layer for cold malls, trains and cinemas.")
                    + group("Rain", "A small umbrella or poncho. November to January is the wettest time.")
                    + group("Strict rules", "Chewing gum, vapes and cigarettes.")
                    + '<p class="note">Rules from ICA. Checked 21 Nov 2026.</p>')),
    dict(slug="honeymoon-packing", board="Packing and What to Wear", link="guides/honeymoon-packing-list.html",
         title="Honeymoon packing list: what to pack for the bride, groom and trip",
         description="Most couples leave a few days after the wedding, when everyone is tired and things get forgotten. This honeymoon packing list covers what you both need, what to share, and what changes for a beach honeymoon like the Maldives, Bali or Goa, or a hill honeymoon like Manali or Kashmir.",
         alt="A honeymoon packing list: documents, clothes for the weather, things to share and what changes for a beach or hill trip.",
         html=chart("Honeymoon packing", "Honeymoon packing list: the short version",
                    group("Documents", "Photo ID for both. Abroad, the name on the ticket must match the passport.")
                    + group("Share these", "One power bank, one first-aid kit and one charger with two ports.")
                    + group("Beach honeymoon", "Summer clothes, sunscreen and polarized sunglasses.")
                    + group("Hill honeymoon", "Warm layers, snow boots and lip balm.")
                    + '<p class="note">Packing cubes keep two people\'s things apart in one bag.</p>')),
    dict(slug="birthday-gifts", board="Gift Ideas", link="guides/birthday-gift-ideas.html",
         title="Birthday gift ideas for husband, wife, brother, sister, mom and dad",
         description="A good birthday gift is something they will use every week: a watch, a slim wallet, a bag that fits their day or a small perfume set. See ideas for your husband, wife, brother, sister, mom, dad and friends, plus simple lines to write in the card.",
         alt="A cake with a red ribbon and the words Birthday gift ideas for everyone.",
         html=photo("birthday-cake", "Birthday gift ideas for everyone", "Husband, wife, brother, sister, mom, dad and friends, plus lines for the card")),
    dict(slug="anniversary-gifts", board="Gift Ideas", link="guides/anniversary-gift-ideas.html",
         title="Anniversary gift ideas for husband, wife, parents and couples",
         description="The best anniversary gifts are things you both see every day, like a watch, or something for time together, like a weekend trip bag. See ideas for your husband, wife, parents and a couple you love, plus lines to write in the card.",
         alt="White and red roses with the words Anniversary gift ideas for husband, wife and parents.",
         html=photo("anniversary-rings", "Anniversary gift ideas", "For your husband, wife, parents and couples, plus lines for the card")),
    dict(slug="valentines-gifts", board="Gift Ideas", link="guides/valentines-day-gift-ideas.html",
         title="Valentine's Day gift ideas for girlfriend, wife, boyfriend and husband",
         description="Roses and chocolates are gone in a day. A watch, a perfume or a bag reminds them of you every time they use it. See Valentine's Day gift ideas for him and her, things to share as a couple and a plan for Valentine week. In 2027 it falls on a Sunday, so order by early February.",
         alt="Red roses with the words Valentine's Day gift ideas for him and her.",
         html=photo("red-roses", "Valentine's Day gift ideas", "For him and her: gifts they will use every day, and a plan for Valentine week")),
    dict(slug="school-bag-size", board="Luggage Size Guides", link="guides/school-bag-size-chart.html",
         title="School bag size chart by class and age: litres, cm and inches",
         description="Which school bag size suits your child? See litres, height in cm and inches for Nursery to Class 12, plus the 10% body weight rule from India's School Bag Policy 2020. Our chart is a rough guide, so check the fit on your child.",
         alt="A school bag size chart: Nursery 5 to 10 litres, Class 1-2 12 to 18, Class 3-5 18 to 25, Class 6-8 25 to 32 and Class 9-12 30 to 37 litres.",
         html=chart("School bag guide", "School bag size by class",
                    table(["Class", "Litres", "Height"], [["Nursery to UKG", "5–10 L", "28–32 cm"], ["Class 1–2", "12–18 L", "35–38 cm"], ["Class 3–5", "18–25 L", "38–43 cm"],
                                                           ["Class 6–8", "25–32 L", "43–47 cm"], ["Class 9–12", "30–37 L", "46–50 cm"]])
                    + '<p class="note"><strong>Weight matters more than size.</strong> India\'s School Bag Policy 2020 suggests about 10% of the child\'s body weight, books included.</p>'
                    + '<p class="note">Our rough guide, not an official chart.</p>')),
    dict(slug="laptop-156", board="Luggage Size Guides", link="guides/15-6-inch-laptop-backpack-size.html",
         title="15.6 inch laptop backpack size in cm and litres: will it fit?",
         description="15.6 inch is the screen size, so the laptop itself is about 35-36 x 23-25 cm. See the laptop sleeve size you need, the backpack height and litres that fit, how to measure your laptop and why a bag marked only 15 inch can be tight.",
         alt="15.6 inch laptop size is about 35 to 36 by 23 to 25 cm. You need a sleeve of at least 37 by 26 cm and a backpack of 20 to 30 litres.",
         html=chart("Laptop bag guide", "Will a 15.6 inch laptop fit?",
                    '<div class="big"><div><b>35–36 cm</b><span>laptop width, about 23–25 cm deep</span></div><div><b>37 x 26 cm</b><span>smallest sleeve that fits it</span></div></div>'
                    + group("Backpack size", "About 45–48 cm tall and 30–33 cm wide.")
                    + group("Litres", "20–30 L for daily use, 30–40 L for trips.")
                    + '<p class="note"><strong>Look for "up to 15.6 inch" or bigger.</strong> A bag marked only "15 inch" can be tight.</p>')),
    dict(slug="titan-fastrack", board="Watches and Everyday Bags", link="guides/titan-vs-fastrack.html",
         title="Titan vs Fastrack watch: which is better for you?",
         description="Titan and Fastrack are both brands of Titan Company, so service and warranty work the same way. The real question is style: Titan is classic and formal, Fastrack is young and sporty. See the differences in straps, water resistance and warranty.",
         alt="A table comparing Titan, for office and formal gifts, with Fastrack, for college and casual wear.",
         html=chart("Watch guide", "Titan vs Fastrack",
                    table(["", "Titan", "Fastrack"], [["Style", "Classic, formal", "Young, sporty"], ["Best for", "Office, weddings, gifts", "College, daily wear"],
                                                      ["Straps", "Leather, steel", "Silicone, metal"], ["Analog warranty", "24 months", "24 months"]])
                    + '<p class="note"><strong>Same company.</strong> Titan Company makes both, so the choice is about style.</p>'
                    + '<p class="note">Warranty from the brands\' own sites.</p>')),
    dict(slug="singapore-trip", board="India Trip Ideas", link="trips/singapore-trip-from-india.html",
         title="Singapore trip from India: visa, 5-day plan and December weather",
         description="Indians need a visa for Singapore, applied for through an authorised agent, and an SG Arrival Card before landing. See the visa fee and time, direct flights from India, a simple 5-day plan, December weather and the Christmas lights on Orchard Road.",
         alt="The Supertree Grove in Singapore, with the words Singapore trip from India.",
         html=photo("singapore-supertrees", "Singapore trip from India", "Visa, SG Arrival Card, a 5-day plan and the weather in December")),
    dict(slug="grooming-kit", board="Gift Ideas", link="guides/grooming-kit-buying-guide.html",
         title="Grooming kit or trimmer for men: how to choose one and gift it",
         description="Trimmer, beard trimmer, multi-groomer, 10-in-1, hybrid: what the names mean in plain words, what to check on the listing and how to take a trimmer on a flight. A simple guide if you are buying a grooming kit for your husband, brother or dad.",
         alt="A table of trimmer types: beard trimmer, all-in-one grooming kit and hybrid trimmer-shaver, with what each is good for.",
         html=chart("Grooming gift guide", "Trimmer or grooming kit?",
                    table(["Type", "Good for"], [["Beard trimmer", "Shaping a beard and moustache"], ["All-in-one kit", "Beard, home haircut, body, nose and ears"], ["Hybrid (like OneBlade)", "Stubble, edges and a close shave"]])
                    + group("What 10-in-1 means", "It counts every head and comb. It doesn't mean ten motors.")
                    + '<p class="note"><strong>Check the run time and charging</strong> on the listing before you buy.</p>')),
    dict(slug="long-weekends-2027", board="India Trip Ideas", link="tools/long-weekends-2027.html",
         title="Long weekends 2027 in India: holiday list and leave planner",
         description="Plan your 2027 breaks from the official central government holiday list: 4 long weekends need no leave, and 3 days of leave can give you 9 days off. Filter by month and leave days with our free planner. States and companies have their own lists.",
         alt="A table of 2027 long weekends: Good Friday, Mahavir Jayanti, Id-ul-Zuha and Diwali need no leave, and a 9-day break needs 3 days of leave.",
         html=chart("Free leave planner", "Long weekends 2027 in India", table(
             ["Long weekend", "Dates"],
             [["Good Friday", "26–28 Mar"], ["Mahavir Jayanti", "17–19 Apr"], ["Id-ul-Zuha", "15–17 May"], ["Diwali", "29–31 Oct"]])
             + group("No leave needed", "These 4 long weekends come free with the holidays.")
             + group("Longest break", "9 days for 3 days of leave, 20–28 Mar or 15–23 May.")
             + '<p class="note">From the central government holiday list. Your state or company may differ. Checked 21 Nov 2026.</p>')),
    dict(slug="visa-free-countries", board="India Trip Ideas", link="guides/visa-free-countries-for-indians.html",
         title="Visa-free countries for Indians: visa on arrival and e-visa list",
         description="Which countries let Indian passport holders in without a visa, with a visa on arrival or with an e-visa? A searchable list of 29 countries, with each rule checked on the country's official site. Visa rules change often, so check before you book.",
         alt="Counts of countries by visa type for Indians: 7 visa-free, 2 visa on arrival, 7 e-visa, 9 visa needed and 4 not confirmed.",
         html=chart("Checked 21 Nov 2026", "Visa-free countries for Indians",
                    '<div class="big"><div><b>7</b><span>visa-free, like Thailand, Nepal and Bhutan</span></div><div><b>2</b><span>visa on arrival: Bali and the Maldives</span></div></div>'
                    + '<div class="big"><div><b>7</b><span>e-visa online, like Vietnam and Sri Lanka</span></div><div><b>9</b><span>visa needed first, like Dubai and Singapore</span></div></div>'
                    + '<p class="note"><strong>Rules change often.</strong> We checked each one on the country\'s official site. Confirm with the embassy before you book.</p>')),
    dict(slug="trip-budget", board="Packing and What to Wear", link="tools/trip-budget-calculator.html",
         title="Trip budget calculator: plan your trip and split the bill",
         description="A free trip budget calculator: add your travel, hotel, food, local transport, tickets and visa fees, then see the total, the cost per person and per day. Split the bill with friends too. You type your own amounts.",
         alt="A checklist of what to add to a trip budget: travel, hotel, food, local transport, activities, visa fees and a buffer.",
         html=chart("Free tool", "Trip budget calculator", table(
             ["Add up", "How"],
             [["Travel there and back", "per person"], ["Hotel", "room x nights"], ["Food", "per person per day"], ["Local transport", "per day"], ["Tickets", "whole group"], ["Visa or permit", "per person"]])
             + group("Then add a buffer", "Shopping plus 10% or so for surprises.")
             + '<p class="note"><strong>Split the bill with friends</strong> and see who pays whom. You type the amounts, we do the sums.</p>')),
    dict(slug="road-trip-cost", board="India Trip Ideas", link="tools/road-trip-cost-calculator.html",
         title="Road trip fuel cost calculator for petrol, diesel and CNG",
         description="Work out the fuel for your road trip: distance divided by mileage, times the fuel price. Add tolls and parking, and split the cost between everyone in the car. Free, for petrol, diesel and CNG.",
         alt="The sums for road trip cost: fuel needed is distance divided by mileage, and trip cost is fuel plus tolls and parking.",
         html=chart("Free tool", "Road trip fuel cost calculator",
                    group("Fuel needed", "Distance in km ÷ mileage in km per litre")
                    + group("Fuel cost", "Fuel needed x price per litre at your pump")
                    + group("Trip cost", "Fuel + tolls + parking, then split by people")
                    + '<p class="note"><strong>Example:</strong> a 600 km round trip at 15 km/l needs 40 litres. For CNG, use km per kg.</p>'
                    + '<p class="note">Works for petrol, diesel, CNG and bikes.</p>')),
    dict(slug="abroad-hub", board="India Trip Ideas", link="trips/international-trips-from-india.html",
         title="International trips from India: flight time, best months and visa type",
         description="Compare Nepal, Bhutan, Sri Lanka, the Maldives, Dubai, Thailand, Vietnam, Malaysia, Singapore and Bali: rough flying time from Delhi and Mumbai, best months, the kind of visa Indians need, and which suit a honeymoon or a family trip.",
         alt="A table of international trips from India with rough flying time and visa type for Nepal, Sri Lanka, Maldives, Dubai and Thailand.",
         html=chart("Trips abroad from India", "Flight time and visa type", table(
             ["Country", "Rough flight", "Visa"],
             [["Nepal", "1½ h from Delhi", "None"], ["Sri Lanka", "2½ h from Mumbai", "Free ETA"], ["Maldives", "2½ h from Mumbai", "On arrival"],
              ["Dubai", "3 h", "Before you fly"], ["Thailand", "4 h", "None, 30 days"], ["Vietnam", "4–5 h", "e-visa"]])
             + '<p class="note"><strong>Flight times are a rough guide</strong> from distance. Your ticket shows the real time.</p>'
             + '<p class="note">Also: Bhutan, Malaysia, Singapore and Bali. Checked 21 Nov 2026.</p>')),
    dict(slug="thailand-trip", board="India Trip Ideas", link="trips/thailand-trip-from-india.html",
         title="Thailand trip from India: visa, 5 to 7-day plan and December weather",
         description="Indians don't need a visa for up to 30 days in Thailand, but there is a free TDAC arrival card to fill in online. See flights from India, a 5 to 7-day plan, the weather in December, getting around and vegetarian food.",
         alt="Wat Arun temple in Bangkok, with the words Thailand trip from India.",
         html=photo("bangkok-wat-arun", "Thailand trip from India", "Visa-free for 30 days, the TDAC card, a 5 to 7-day plan and December weather")),
    dict(slug="dubai-trip", board="India Trip Ideas", link="trips/dubai-trip-from-india.html",
         title="Dubai trip from India: visa, 5-day plan and December weather",
         description="Most Indians need a visa before flying to Dubai, usually through a tourism company, airline or hotel. See who gets a visa on arrival, direct flights, a 5-day plan with an Abu Dhabi day trip, the metro and the weather in December.",
         alt="The Burj Khalifa in Dubai, with the words Dubai trip from India.",
         html=photo("dubai-burj-khalifa", "Dubai trip from India", "Visa, a 5-day plan with Abu Dhabi, the metro and December weather")),
    dict(slug="bali-trip", board="India Trip Ideas", link="trips/bali-trip-from-india.html",
         title="Bali trip from India: visa, 6-day itinerary and honeymoon tips",
         description="Indians get a visa on arrival in Bali for 30 days. See the All Indonesia arrival card, the Bali tourist levy, flights from India, a 6-day plan, honeymoon tips, the weather in December and vegetarian food.",
         alt="Rice terraces in Bali, with the words Bali trip from India.",
         html=photo("bali-rice-terraces", "Bali trip from India", "Visa on arrival, a 6-day plan, honeymoon tips and the weather")),
    dict(slug="maldives-trip", board="India Trip Ideas", link="trips/maldives-trip-from-india.html",
         title="Maldives trip from India: visa, resort or local island, honeymoon tips",
         description="Indians get a tourist visa on arrival in the Maldives. See the free IMUGA form, the green tax, resort vs local island, speedboat and seaplane transfers, a 5-day plan and the rules on alcohol and idols.",
         alt="Overwater villas in the Maldives at sunset, with the words Maldives trip from India.",
         html=photo("maldives-villas-sunset", "Maldives trip from India", "Visa on arrival, resort or local island, a 5-day plan and honeymoon tips")),
    dict(slug="sri-lanka-trip", board="India Trip Ideas", link="trips/sri-lanka-trip-from-india.html",
         title="Sri Lanka trip from India: free ETA, 6-day itinerary and Ramayana trail",
         description="Indians need a free ETA, applied for online, for Sri Lanka. See direct flights, a 6-day itinerary with Sigiriya, Kandy, Ella and the south coast, the Ramayana sites, weather by month and vegetarian food.",
         alt="The train through Ella in Sri Lanka, with the words Sri Lanka trip from India.",
         html=photo("sri-lanka-ella-train", "Sri Lanka trip from India", "The free ETA, a 6-day itinerary and the Ramayana trail")),
    dict(slug="vietnam-trip", board="India Trip Ideas", link="trips/vietnam-trip-from-india.html",
         title="Vietnam trip from India: e-visa, 7-day itinerary and December weather",
         description="Indians need an e-visa for Vietnam, applied for online before you fly. See the pre-arrival form, direct flights, a 5 or 7-day itinerary with Hanoi, Ha Long Bay and Hoi An, the weather in December and vegetarian food.",
         alt="Trang An in Vietnam, with the words Vietnam trip from India.",
         html=photo("vietnam-trang-an", "Vietnam trip from India", "The e-visa, a 7-day itinerary and the weather in December")),
    dict(slug="malaysia-trip", board="India Trip Ideas", link="trips/malaysia-trip-from-india.html",
         title="Malaysia trip from India: visa-free entry, MDAC and a 5-day plan",
         description="Indians can visit Malaysia without a visa for up to 30 days until 31 December 2026, and fill in the free MDAC arrival card online. See flights, a 5-day plan, the best time to go, a Singapore combo and vegetarian food.",
         alt="The Petronas Towers in Kuala Lumpur, with the words Malaysia trip from India.",
         html=photo("kuala-lumpur-petronas", "Malaysia trip from India", "Visa-free until 31 Dec 2026, the MDAC card and a 5-day plan")),
    dict(slug="new-year-2027", board="India Trip Ideas", link="trips/new-year-trips-2027.html",
         title="Where to go for New Year 2027: best trips in India and abroad",
         description="New Year 2027 trip ideas: Goa, Kerala, Andaman, Udaipur, Rishikesh, Manali and Kashmir in India, and Dubai, Thailand, Bali, Singapore and the Maldives abroad. Weather, New Year's Eve events, visas and when to book.",
         alt="Beach party on New Year's Eve in Goa, with the words Where to go for New Year 2027.",
         html=photo("goa-anjuna-new-year", "Where to go for New Year 2027", "Trips in India and abroad, with weather, visas and when to book")),
    dict(slug="goa-new-year", board="India Trip Ideas", link="trips/goa-new-year-2027.html",
         title="Goa New Year 2027: parties, beaches, rules and how to plan the night",
         description="Planning New Year's Eve 2027 in Goa? See North or South Goa, the midnight music rule, last year's traffic plan, beach fines, safety, how to get there and where to stay.",
         alt="Anjuna beach in Goa on New Year's Eve, with the words Goa New Year 2027.",
         html=photo("goa-anjuna-new-year-night", "Goa New Year 2027", "North or South Goa, the music rule, traffic, safety and where to stay")),
    dict(slug="dubai-new-year", board="India Trip Ideas", link="trips/dubai-new-year-2027.html",
         title="Dubai New Year's Eve 2027: Burj Khalifa fireworks and where to watch for free",
         description="Plan New Year's Eve 2027 in Dubai: what Emaar has announced for the Burj Khalifa fireworks, free viewing areas in Downtown Dubai, last year's metro hours and road closures, and visas for Indians.",
         alt="Fireworks over the Burj Al Arab in Dubai, with the words Dubai New Year's Eve 2027.",
         html=photo("dubai-burj-al-arab-fireworks", "Dubai New Year's Eve 2027", "Burj Khalifa fireworks, free viewing spots and getting home")),
    dict(slug="gulmarg-december", board="India Trip Ideas", link="trips/gulmarg-in-december.html",
         title="Gulmarg in December: weather, snow, the gondola and what to wear",
         description="Plan Gulmarg for December: IMD temperatures, the chance of snow in the first and last week, the Gulmarg Gondola and how to book online, skiing, the Tangmarg road in snow and what to wear.",
         alt="The Gulmarg Gondola above snow, with the words Gulmarg in December.",
         html=photo("gulmarg-gondola", "Gulmarg in December", "Weather, snow chances, the gondola and what to wear")),
    dict(slug="rann-utsav", board="India Trip Ideas", link="trips/rann-utsav-2026.html",
         title="Rann Utsav 2026-27: dates, booking and a Rann of Kutch trip plan",
         description="Rann Utsav runs from 1 November 2026 to 7 March 2027 at Dhordo. See full-moon nights, tents and how to book on the official site, the White Rann permit, December weather, a 2-3 day Kutch plan and what to wear.",
         alt="The white salt desert of the Rann of Kutch, with the words Rann Utsav 2026-27.",
         html=photo("white-rann", "Rann Utsav 2026-27", "Dates, how to book, the White Rann permit and a Kutch plan")),
    dict(slug="study-abroad-packing", board="Packing and What to Wear", link="guides/study-abroad-packing-list.html",
         title="Study abroad packing list for Indian students: USA, UK, Canada, Australia, Germany",
         description="A packing list for Indian students going abroad: documents for your hand bag, student baggage on Air India and Virgin Atlantic, which trolley fits 23 kg, each country's rules on Indian food and medicines, plugs, and what not to pack.",
         alt="A packed suitcase, with the words Study abroad packing list for Indian students.",
         html=photo("packed-suitcase", "Study abroad packing list", "Documents, baggage, food rules and plugs for 5 countries")),
    dict(slug="usa-student-packing", board="Packing and What to Wear", link="guides/usa-packing-list-for-indian-students.html",
         title="USA packing list for Indian students: what to carry from India",
         description="What to carry to the USA as a student: the documents CBP says to keep in your hand bag (passport, F-1 visa, Form I-20), student baggage, Indian food and medicine rules at US customs, plugs and winter clothes.",
         alt="A university yard in autumn in the USA, with the words USA packing list for Indian students.",
         html=photo("harvard-yard-autumn", "USA packing list for students", "Documents, baggage, customs rules and winter clothes")),
    dict(slug="uk-student-packing", board="Packing and What to Wear", link="guides/uk-packing-list-for-indian-students.html",
         title="UK packing list for Indian students: what to carry from India",
         description="What to carry to the UK as a student: the documents GOV.UK lists for a Student visa (passport, CAS, eVisa), student baggage, the UK's rules on Indian food, sweets and medicines, Type G plugs and clothes for cold, wet weather.",
         alt="The Radcliffe Camera in Oxford, with the words UK packing list for Indian students.",
         html=photo("oxford-radcliffe-camera", "UK packing list for students", "Visa papers, baggage, food rules, plugs and clothes")),
    dict(slug="canada-student-packing", board="Packing and What to Wear", link="guides/canada-packing-list-for-indian-students.html",
         title="Canada packing list for Indian students going to Canada from India",
         description="What to carry to Canada as a student: the documents IRCC says to have at the border, student baggage on Air India and Virgin Atlantic, which trolley fits 23 kg, CBSA food rules, the 90-day medicine limit, plugs and winter clothes.",
         alt="A university building in a Toronto winter, with the words Canada packing list for Indian students.",
         html=photo("toronto-trinity-college-winter", "Canada packing list for students", "Border documents, baggage, food rules and winter clothes")),
    dict(slug="australia-student-packing", board="Packing and What to Wear", link="guides/australia-packing-list-for-indian-students.html",
         title="Australia packing list for Indian students: what to bring, and what not to",
         description="What to carry to Australia as a student: CoE and OSHC papers, Border Force rules on declaring Indian food, spices and medicines, duty-free limits, which trolley to take, Type I plugs and clothes for summer and winter.",
         alt="The quadrangle of the University of Sydney, with the words Australia packing list for Indian students.",
         html=photo("sydney-university-quadrangle", "Australia packing list for students", "Papers, food declaration rules, plugs and clothes")),
    dict(slug="germany-student-packing", board="Packing and What to Wear", link="guides/germany-packing-list-for-indian-students.html",
         title="Packing list for Indian students going to Germany",
         description="What to take to Germany as a student: papers from your visa file, German customs relief for students' clothes and laptops, the EU's no meat or dairy rule, medicines, Type C and F plugs, student baggage and winter clothes.",
         alt="The old town of Heidelberg, with the words Germany packing list for Indian students.",
         html=photo("heidelberg-old-town", "Germany packing list for students", "Visa papers, customs relief, food rules and plugs")),
    dict(slug="canada-winter-packing", board="Packing and What to Wear", link="guides/canada-packing-list.html",
         title="Canada packing list for winter: what to pack in December and January",
         description="What to pack for Canada in winter: Toronto, Vancouver and Banff temperatures, how to layer, a warm jacket, thermals, gloves and boots with grip, the 120 V plug, the CAN$10,000 cash rule and lists for men, women and kids.",
         alt="A frozen Lake Louise in Canada, with the words Canada packing list for winter.",
         html=photo("lake-louise-frozen", "Canada packing list for winter", "Temperatures, layers, boots and the cash rule")),
    dict(slug="south-korea-packing", board="Packing and What to Wear", link="guides/south-korea-packing-list.html",
         title="South Korea packing list for winter: what to pack for Seoul and Busan",
         description="What to pack for South Korea in December and January: Seoul, Busan and Jeju temperatures, how to layer for freezing nights, a padded jacket, thermals, gloves, shoes for metro stairs, plugs and customs rules. Lists for men, women and kids.",
         alt="Gyeongbokgung palace in the snow in Seoul, with the words South Korea packing list for winter.",
         html=photo("gyeongbokgung-snow", "South Korea winter packing list", "Seoul and Busan temperatures, layers, shoes and plugs")),
    dict(slug="kenya-safari-packing", board="Packing and What to Wear", link="guides/kenya-safari-packing-list.html",
         title="Kenya safari packing list: what to wear and pack for the Masai Mara",
         description="What to pack for a Kenya safari: layers in earth colours, hat, torch, insect repellent and binoculars, Masai Mara and Nairobi temperatures, the 15 kg soft-bag limit on small safari planes, the plastic bag ban and the plug.",
         alt="A safari vehicle in the Masai Mara, with the words Kenya safari packing list.",
         html=photo("masai-mara-safari-vehicle", "Kenya safari packing list", "What to wear, the 15 kg soft-bag rule and the plastic bag ban")),
    dict(slug="winter-jacket", board="Packing and What to Wear", link="guides/winter-jacket-for-travel.html",
         title="Winter jacket for travel: what to buy for Kashmir, Manali or Europe",
         description="How to choose a winter jacket for a trip: how cold Kashmir, Gulmarg, Manali, Shimla and Europe get in December, down vs synthetic fill, what fill power means and how to read water repellent, resistant and waterproof.",
         alt="A traveller in a winter jacket in the snow, with the words Winter jacket for travel.",
         html=photo("snow-jacket", "Winter jacket for travel", "Down or synthetic, fill power and water-resistant vs waterproof")),
    dict(slug="lightest-cabin-trolley", board="Luggage Size Guides", link="guides/lightest-cabin-trolley-bag.html",
         title="Lightest cabin trolley bags: empty weights compared",
         description="The bag's own weight counts against your 7 kg cabin allowance. We sorted our cabin, medium and large trolleys by the empty weight their listings state.",
         alt="A traveller with a cabin trolley bag at an airport, with the words Lightest cabin trolley bags.",
         html=photo("cabin-bag-airport", "Lightest cabin trolley bags", "Empty weights compared, because the bag counts toward 7 kg")),
    dict(slug="hard-vs-soft", board="Luggage Size Guides", link="guides/hard-vs-soft-luggage.html",
         title="Hard vs soft luggage: which is better for your trip?",
         description="Hard shells protect better and shrug off rain. Soft bags squeeze into tight spaces and have outside pockets. We compared the listed weights of our hard and soft picks.",
         alt="A packed suitcase, with the words Hard vs soft luggage.",
         html=photo("packed-suitcase", "Hard vs soft luggage", "Protection, rain, tight spaces and listed weights")),
    dict(slug="trolley-set-of-3", board="Luggage Size Guides", link="guides/trolley-bag-set-of-3.html",
         title="Trolley bag set of 3: sizes, total weight and what to check",
         description="A set of 3 gives you a cabin, medium and large bag. We compared the sizes, total weight, lock and warranty that five Amazon.in sets list, and the size trap in the large bag.",
         alt="Trolley bag handles, with the words Trolley bag set of 3.",
         html=photo("trolley-handles", "Trolley bag set of 3", "Sizes, total weight, lock and warranty, and the size trap")),
    dict(slug="wheels-4-vs-8", board="Luggage Size Guides", link="guides/4-wheel-vs-8-wheel-trolley.html",
         title="4 wheel vs 8 wheel trolley bags: which is better?",
         description="An 8 wheel trolley has four double spinner wheels, not eight separate ones. See how 8, 4 and 2 wheels compare, with the listed weights of our picks.",
         alt="A traveller walking with a trolley bag, with the words 4 wheel vs 8 wheel trolley bags.",
         html=photo("trolley-walk", "4 wheel vs 8 wheel trolley", "What 8 wheels really means, and how 8, 4 and 2 compare")),
    dict(slug="carry-on-by-airline", board="Flight and Train Baggage Rules", link="guides/carry-on-size-by-airline.html",
         title="Carry-on bag size and weight limits for 30 airlines",
         description="Carry-on bag size and weight limits for 30 airlines, from American, Delta, United and Ryanair to Emirates, Lufthansa and IndiGo, in cm and inches. Check your airline before you fly.",
         alt="An aeroplane cabin, with the words Carry-on bag size by airline.",
         html=photo("plane-cabin", "Carry-on size by airline", "Size and weight limits for 30 airlines, in cm and inches")),
    dict(slug="books", board="Packing and What to Wear", link="category/books.html",
         title="Travel books and audiobooks: guidebooks, phrasebooks and journals",
         description="Hand-picked travel books from Amazon India: printed guidebooks, a phrasebook, travel journals, kids' travel books and travel stories for your next trip.",
         alt="A plane window view, with the words Travel books and audiobooks.",
         html=photo("plane-window", "Travel books and audiobooks", "Guidebooks, a phrasebook, journals and travel stories")),
    dict(slug="audiobooks", board="Packing and What to Wear", link="guides/audiobooks-for-long-flights.html",
         title="Audiobooks for long flights and train journeys: offline, battery and headphone tips",
         description="Why audiobooks make long flights, road trips and train journeys easier, how to download them offline before you fly, battery and headphone tips, and how Audible's 30-day free trial works on Amazon.in.",
         alt="A plane window view, with the words Audiobooks for long flights.",
         html=photo("plane-window", "Audiobooks for long journeys", "Download offline, battery tips and the Audible free trial")),
    dict(slug="jaisalmer-december", board="India Trip Ideas", link="trips/jaisalmer-in-december.html",
         title="Jaisalmer in December: temperature, desert camps and a 2-3 day plan",
         description="Plan Jaisalmer for December: IMD temperatures, how cold the Sam dunes get, a 2-day and 3-day plan for the fort, havelis and a desert camp, flights and trains, and what to wear.",
         alt="The Sam sand dunes near Jaisalmer, with the words Jaisalmer in December.",
         html=photo("jaisalmer-sam-dunes", "Jaisalmer in December", "Temperatures, desert camps and a 2-3 day plan")),
    dict(slug="coorg-december", board="India Trip Ideas", link="trips/coorg-in-december.html",
         title="Coorg in December and January: weather, a 2-3 day plan and what to wear",
         description="Plan Coorg for December: IMD temperatures, misty mornings but no snow, a 2-day and 3-day plan with Abbey Falls, Raja's Seat, Dubare and the Golden Temple, the trip from Bangalore and what to wear.",
         alt="Abbey Falls in Coorg, with the words Coorg in December.",
         html=photo("coorg-abbey-falls", "Coorg in December", "Weather, a 2-3 day plan and what to wear")),
    dict(slug="meghalaya-december", board="India Trip Ideas", link="trips/meghalaya-in-december.html",
         title="Meghalaya in December and January: weather, itinerary and what to wear",
         description="Plan Meghalaya for December: IMD temperatures for Shillong and Cherrapunji, the truth about snowfall, a 4-day and 5-day itinerary with Sohra, Dawki and Mawlynnong, getting there from Guwahati and what to wear.",
         alt="The Umngot river in Meghalaya, with the words Meghalaya in December.",
         html=photo("meghalaya-umngot-river", "Meghalaya in December", "Weather, a 4-5 day plan, Dawki and Mawlynnong")),
    dict(slug="munnar-december", board="India Trip Ideas", link="trips/munnar-in-december.html",
         title="Munnar in December and January: weather, frost and a 2-3 day plan",
         description="Plan Munnar for December: how cold it gets, why you may see frost but not snow, a 2-day and 3-day plan, Eravikulam National Park tickets, the road from Kochi and what to wear.",
         alt="Tea hills in Munnar, with the words Munnar in December.",
         html=photo("munnar-tea-hills", "Munnar in December", "Frost not snow, a 2-3 day plan and what to wear")),
    dict(slug="usa-trip", board="India Trip Ideas", link="trips/usa-trip-from-india.html",
         title="USA trip from India: B1/B2 visa, direct flights and a 10-day plan",
         description="Plan a USA trip from India: the B1/B2 tourist visa, the DS-160 and the interview, why Indians can't use ESTA, direct flights to New York and San Francisco, a 10-day plan, the weather by month and food rules at US customs.",
         alt="The Statue of Liberty, with the words USA trip from India.",
         html=photo("statue-of-liberty", "USA trip from India", "The B1/B2 visa, direct flights and a 10-day plan")),
    dict(slug="egypt-trip", board="India Trip Ideas", link="trips/egypt-trip-from-india.html",
         title="Egypt trip from India: e-visa, flights and a 7-day plan with a Nile cruise",
         description="Plan an Egypt trip from India: the e-visa on the official portal, apply at least 7 days ahead, direct EgyptAir flights to Cairo, a 7-day Cairo, Aswan, Nile cruise and Luxor plan, the weather by month and veg food tips.",
         alt="The pyramids of Giza, with the words Egypt trip from India.",
         html=photo("giza-pyramids", "Egypt trip from India", "The e-visa, direct flights and a 7-day Nile plan")),
    dict(slug="south-korea-trip", board="India Trip Ideas", link="trips/south-korea-trip-from-india.html",
         title="South Korea trip from India: visa, flights to Seoul and a 7-day plan",
         description="Plan a South Korea trip from India: the Korean tourist visa and documents, visa-free Jeju for 30 days, the e-Arrival Card, flights to Seoul, a 7-day Seoul, Busan and Gyeongju plan, the weather by month and veg food tips.",
         alt="Gyeongbokgung palace in Seoul, with the words South Korea trip from India.",
         html=photo("seoul-gyeongbokgung", "South Korea trip from India", "The visa, visa-free Jeju and a 7-day plan")),
    dict(slug="philippines-trip", board="India Trip Ideas", link="trips/philippines-trip-from-india.html",
         title="Philippines trip from India: visa-free rule, flights and a 7-day island plan",
         description="Plan a Philippines trip from India: Indians can visit without a visa for 14 days, or 30 days with a valid US, UK, Japan, Australia, Canada, Schengen or Singapore visa, says the DFA. Flights, a 7-day plan and veg food tips.",
         alt="A lagoon in El Nido, with the words Philippines trip from India.",
         html=photo("el-nido-lagoon", "Philippines trip from India", "Visa-free rule, flights and a 7-day island plan")),
    dict(slug="cambodia-trip", board="India Trip Ideas", link="trips/cambodia-trip-from-india.html",
         title="Cambodia trip from India: e-visa, Angkor Wat tickets and a 6-day plan",
         description="Plan a Cambodia trip from India: the e-visa on the official site, Angkor Pass prices from the official Angkor Enterprise site, flights to Phnom Penh, a 6-day Siem Reap and Phnom Penh plan, weather and veg food tips.",
         alt="Angkor Wat in Cambodia, with the words Cambodia trip from India.",
         html=photo("angkor-wat", "Cambodia trip from India", "The e-visa, Angkor Wat tickets and a 6-day plan")),
    dict(slug="oman-trip", board="India Trip Ideas", link="trips/oman-trip-from-india.html",
         title="Oman trip from India: visa, direct flights to Muscat and a 7-day plan",
         description="Plan an Oman trip from India: the Tourist Visit Visa on the Royal Oman Police e-visa site, the 14-day visa-free rule with some US, UK, Schengen or Japan visas, direct flights to Muscat, a 7-day plan and the weather by month.",
         alt="The Grand Mosque in Muscat, with the words Oman trip from India.",
         html=photo("muscat-grand-mosque", "Oman trip from India", "The visa, direct flights to Muscat and a 7-day plan")),
    dict(slug="uzbekistan-trip", board="India Trip Ideas", link="trips/uzbekistan-trip-from-india.html",
         title="Uzbekistan trip from India: e-visa, flights to Tashkent and a 7-day plan",
         description="Plan an Uzbekistan trip from India: the e-visa on the official portal, direct flights to Tashkent, a 7-day Tashkent, Samarkand, Bukhara and Khiva plan by fast train, the weather by month and veg food tips.",
         alt="The Registan in Samarkand, with the words Uzbekistan trip from India.",
         html=photo("samarkand-registan", "Uzbekistan trip from India", "The e-visa, flights to Tashkent and a 7-day plan")),
    dict(slug="new-zealand-trip", board="India Trip Ideas", link="trips/new-zealand-trip-from-india.html",
         title="New Zealand trip from India: visitor visa, flights and a 10-day plan",
         description="Plan a New Zealand trip from India: the Visitor Visa, why Indians can't use the NZeTA, money and documents you need, one-stop flights, a 10-day Auckland to Queenstown and Milford Sound plan and the weather by month.",
         alt="Milford Sound in New Zealand, with the words New Zealand trip from India.",
         html=photo("milford-sound", "New Zealand trip from India", "The visitor visa, flights and a 10-day plan")),
    dict(slug="canada-trip", board="India Trip Ideas", link="trips/canada-trip-from-india.html",
         title="Canada trip from India: visitor visa, direct flights and a 10-day plan",
         description="Plan a Canada trip from India: the visitor visa and biometrics, why Indians can't use the eTA, direct flights to Toronto and Vancouver, a 10-day Toronto, Niagara, Banff and Vancouver plan and the weather by month.",
         alt="Moraine Lake in Canada, with the words Canada trip from India.",
         html=photo("moraine-lake", "Canada trip from India", "The visitor visa, direct flights and a 10-day plan")),
    dict(slug="kenya-trip", board="India Trip Ideas", link="trips/kenya-safari-from-india.html",
         title="Kenya safari from India: eTA, flights and a 7-day Masai Mara plan",
         description="Plan a Kenya safari from India: the Kenya eTA on the official site, documents, direct flights to Nairobi, a 7-day Masai Mara, Nakuru and Amboseli plan, park fees, the dry and rainy seasons and the yellow fever card rule.",
         alt="An elephant in the Masai Mara, with the words Kenya safari from India.",
         html=photo("masai-mara-elephant", "Kenya safari from India", "The eTA, direct flights and a 7-day Masai Mara plan")),
dict(slug='christmas-gift-parents', board='Gift Ideas', link='guides/christmas-gift-for-parents.html',
         title='Christmas gift for parents and parents-in-law: useful ideas in India',
         description='Christmas gift ideas for parents and parents-in-law in India: pair watches for mom and dad, warm thermals, walking shoes and an attar gift set. Simple, useful gifts they will use.',
         alt='A Christmas tree with wrapped gifts, with the words Christmas gifts for parents.',
         html=photo('christmas-tree-gifts', 'Christmas gifts for parents', 'Pair watches, thermals, walking shoes and an attar set')),
dict(slug='christmas-gift-friends', board='Gift Ideas', link='guides/christmas-gift-for-friends.html',
         title='Christmas gift for friends: useful ideas for female and male friends',
         description='Christmas gift ideas for friends in India: slings, sunglasses and a zip-around wallet for a female friend, a watch, a wallet set or a pocket perfume for a male friend.',
         alt='A wrapped gift with a ribbon, with the words Christmas gifts for friends.',
         html=photo('gift-box', 'Christmas gifts for friends', 'Slings, sunglasses, wallets and watches they will use')),
dict(slug='christmas-gift-couples', board='Gift Ideas', link='guides/christmas-gift-for-couples.html',
         title="Christmas gift for couples: ideas they'll both use (India)",
         description='Christmas gift ideas for couples in India: pair watches, luggage sets and travel gifts for couples who travel, perfume for two, and ideas for married couples.',
         alt='A Christmas tree with wrapped gifts, with the words Christmas gifts for couples.',
         html=photo('christmas-tree-gifts', 'Christmas gifts for couples', 'Pair watches, travel gifts and perfume for two')),
dict(slug='anti-theft-backpack', board='Watches and Everyday Bags', link='guides/anti-theft-backpack.html',
         title="Anti-theft backpack: what it means, what it doesn't, and which to buy",
         description="What 'anti-theft' means on a backpack listing: a hidden back zip, a number lock, a secret back pocket. Also what it doesn't protect against, and our anti-theft picks for men and women in India.",
         alt='A backpack on a street, with the words Anti-theft backpack: what it really means.',
         html=photo('backpack-street', 'Anti-theft backpack: what it really means', 'Hidden zip, number lock and secret pocket, explained')),
dict(slug='travel-backpack-40l', board='Packing and What to Wear', link='guides/travel-backpack-40l-carry-on.html',
         title='40L travel backpack: will it fit as cabin baggage?',
         description='Will a 40 L travel backpack fit as cabin baggage? We checked three 40 to 45 L backpacks by listed size against IndiGo and Air India cabin limits. Read before you buy.',
         alt='A backpack in a field, with the words Will a 40 L backpack fit as cabin baggage?',
         html=photo('backpack-field', 'Will a 40 L backpack fit as cabin baggage?', 'We checked three against Indian airline limits')),
dict(slug='office-backpack-men', board='Watches and Everyday Bags', link='guides/office-backpack-for-men.html',
         title='Office backpack for men: waterproof, leather-look and slim laptop bags',
         description='How to choose an office backpack for men in India: a slim size that looks smart, water resistance vs a rain cover for the monsoon, and faux leather bags. With picks.',
         alt='A backpack on a city street, with the words Office backpack for men.',
         html=photo('backpack-street', 'Office backpack for men', 'Slim, smart and rain-ready: how to choose')),
dict(slug='couple-watches', board='Gift Ideas', link='guides/couple-watches.html',
         title='Couple watches set: Titan, Sonata, Fastrack and Timex pair watches compared',
         description="Couple watch sets (pair watches) for weddings, anniversaries and Valentine's Day: Titan Bandhan, Sonata Bandhan, Fastrack Mixmatched and Timex Classics compared.",
         alt='A wrist watch, with the words Couple watches: pair sets compared.',
         html=photo('watch-wrist', 'Couple watches: pair sets compared', 'Titan, Sonata, Fastrack and Timex for weddings and anniversaries')),
dict(slug='watch-gift-husband', board='Gift Ideas', link='guides/watch-gift-for-husband.html',
         title='Watch gift for husband: which watch to choose, plus messages for the card',
         description='Choosing a watch gift for your husband for a birthday, anniversary or wedding day: dial size, strap and style, six picks from Titan, Timex, Casio, Fastrack and Invicta, and card messages.',
         alt='A steel mesh watch, with the words Watch gift for husband.',
         html=photo('watch-mesh', 'Watch gift for your husband', 'Dial size, strap and style, plus messages for the card')),
dict(slug="travel-adapter-by-country", board="Packing and What to Wear", link="guides/travel-adapter-by-country.html",
         title="Travel adapter by country: plug type and voltage for 45 places Indians visit",
         description="Plug types and voltage for 45 countries Indians visit, from Thailand and Dubai to Europe, the UK, the USA and Japan, in one table. Check before you pack.",
         alt="A table of plug type and voltage for the UK, Dubai, Singapore, Australia, the USA, Thailand and Japan.",
         html=chart("Before you pack", "Which travel adapter do you need?", table(["Country","Plug type","Voltage"], [['UK', 'G', '230 V, 50 Hz'], ['Dubai and UAE', 'G', '230 V, 50 Hz'], ['Singapore and Malaysia', 'G', '230 V'], ['Australia and NZ', 'I', '230 V, 50 Hz'], ['USA and Canada', 'A and B', '120 V, 60 Hz'], ['Thailand', 'A, B, C, O', '220 V'], ['Japan', 'A', '100 V']])
             + '<p class="note"><strong>Plug types for 45 countries</strong> are on our page. Indian plugs fit almost nowhere abroad, so check yours.</p>')),
dict(slug="travel-adapter-uk", board="Packing and What to Wear", link='guides/travel-adapter-for-uk.html',
         title='Travel adapter for UK from India: type G plug, 230 V, which adapter to buy',
         description="The UK uses type G plugs (three rectangular pins) at 230 V and 50 Hz. Indian plugs don't fit but Indian chargers work. Which adapter to take.",
         alt='A table of the plug type, pins and voltage for UK.',
         html=chart("Travel adapter from India", 'Adapter for UK', table(["UK",""],[["Plug type",'G'],["Pins",'three rectangular pins'],["Voltage",'230 V, 50 Hz']])
             + group("Will your charger work?", "Indian plugs don't fit, but Indian chargers work.") + group("Good to know", 'Take a type G adapter.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-usa", board="Packing and What to Wear", link='guides/travel-adapter-for-usa.html',
         title='Travel adapter for USA from India: plug type A and B, 120 V, do you need a converter?',
         description="The USA and Canada use flat-pin type A and B plugs at 120 V and 60 Hz, about half of India's voltage. Indian plugs don't fit, and 230 V-only appliances need care.",
         alt='A table of the plug type, pins and voltage for USA and Canada.',
         html=chart("Travel adapter from India", 'Adapter for USA and Canada', table(["USA and Canada",""],[["Plug type",'A and B'],["Pins",'flat pins'],["Voltage",'120 V, 60 Hz']])
             + group("Will your charger work?", "Indian plugs don't fit.") + group("Good to know", "Voltage is about half of India's, so check that each device takes 100-240 V.")
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-dubai", board="Packing and What to Wear", link='guides/travel-adapter-for-dubai.html',
         title='Travel adapter for Dubai from India: plug type G, 230 V, which adapter to buy',
         description="Dubai and the UAE use the UK-style type G plug at 230 V and 50 Hz. Indian plugs don't fit, but Indian chargers work. Which adapter to take.",
         alt='A table of the plug type, pins and voltage for Dubai and UAE.',
         html=chart("Travel adapter from India", 'Adapter for Dubai and UAE', table(["Dubai and UAE",""],[["Plug type",'G'],["Pins",'three rectangular pins'],["Voltage",'230 V, 50 Hz']])
             + group("Will your charger work?", "Indian plugs don't fit, but Indian chargers work.") + group("Good to know", 'Take a type G adapter.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-europe", board="Packing and What to Wear", link='guides/travel-adapter-for-europe.html',
         title='Travel adapter for Europe from India: plug types C, E, F, J, L by country, 230 V',
         description='Most of Europe uses round-pin types C, E and F at 230 V, but Switzerland, Italy, Denmark, the UK and Ireland differ. Plug types for 26 European countries.',
         alt='A table of the plug type, pins and voltage for Europe.',
         html=chart("Travel adapter from India", 'Adapter for Europe', table(["Europe",""],[["Plug type",'C, E, F, J, L'],["Pins",'round pins, differs by country'],["Voltage",'230 V']])
             + group("Will your charger work?", 'Plug type changes by country.') + group("Good to know", 'Switzerland, Italy, Denmark, the UK and Ireland differ from the rest.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-thailand", board="Packing and What to Wear", link='guides/travel-adapter-for-thailand.html',
         title='Travel adapter for Thailand from India: plug types A, B, C, O, 220 V, do you need one?',
         description="Thailand's sockets take flat US-style pins and thin round pins at 220 V. A thin Indian two-pin charger usually fits. When you need an adapter.",
         alt='A table of the plug type, pins and voltage for Thailand.',
         html=chart("Travel adapter from India", 'Adapter for Thailand', table(["Thailand",""],[["Plug type",'A, B, C, O'],["Pins",'flat US-style and thin round pins'],["Voltage",'220 V']])
             + group("Will your charger work?", 'A thin Indian two-pin charger usually fits.') + group("Good to know", 'Sockets take flat US-style and thin round pins.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-singapore", board="Packing and What to Wear", link='guides/travel-adapter-for-singapore.html',
         title='Travel adapter for Singapore and Malaysia from India: type G plug, 230 V',
         description="Singapore and Malaysia use the UK-style type G plug at 230 V. Indian plugs don't fit but Indian chargers work. Which adapter to take.",
         alt='A table of the plug type, pins and voltage for Singapore and Malaysia.',
         html=chart("Travel adapter from India", 'Adapter for Singapore and Malaysia', table(["Singapore and Malaysia",""],[["Plug type",'G'],["Pins",'three rectangular pins'],["Voltage",'230 V']])
             + group("Will your charger work?", "Indian plugs don't fit, but Indian chargers work.") + group("Good to know", 'Take a type G adapter.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-australia", board="Packing and What to Wear", link='guides/travel-adapter-for-australia.html',
         title='Travel adapter for Australia and New Zealand from India: type I plug, 230 V',
         description="Australia and New Zealand use type I plugs at 230 V and 50 Hz. Indian plugs don't fit, but Indian chargers work. Which adapter to take.",
         alt='A table of the plug type, pins and voltage for Australia and New Zealand.',
         html=chart("Travel adapter from India", 'Adapter for Australia and New Zealand', table(["Australia and New Zealand",""],[["Plug type",'I'],["Pins",'two angled flat pins and an earth pin'],["Voltage",'230 V, 50 Hz']])
             + group("Will your charger work?", "Indian plugs don't fit, but Indian chargers work.") + group("Good to know", 'Take a type I adapter.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug="travel-adapter-japan", board="Packing and What to Wear", link='guides/travel-adapter-for-japan.html',
         title='Travel adapter for Japan from India: type A plug, 100 V, 50 or 60 Hz',
         description='Japan runs at 100 V everywhere, with 50 Hz in the east and 60 Hz in the west. Most sockets take two flat pins. What to check before you go.',
         alt='A table of the plug type, pins and voltage for Japan.',
         html=chart("Travel adapter from India", 'Adapter for Japan', table(["Japan",""],[["Plug type",'A'],["Pins",'two flat pins'],["Voltage",'100 V, 50 or 60 Hz']])
             + group("Will your charger work?", "Japan runs at 100 V, lower than India's 230 V.") + group("Good to know", '50 Hz in the east, 60 Hz in the west. Check your device label.')
             + '<p class="note"><strong>Check before you pack.</strong> Our page says which adapter to take.</p>')),
dict(slug='tsa-lock', board='Packing and What to Wear', link='guides/tsa-lock.html',
         title='TSA lock meaning: do you need one, and which to buy',
         description='What a TSA lock is (a lock US airport security can open with a master key), how to spot one, and whether you need it for flights to the USA or within India.',
         alt='Luggage on an airport belt, with the words What is a TSA lock?',
         html=photo('baggage-belt', 'What is a TSA lock?', 'Do you need one for the USA or within India?')),
dict(slug='neck-pillow', board='Packing and What to Wear', link='guides/neck-pillow-for-flights.html',
         title='Neck pillow for flights: memory foam vs inflatable, and which to buy',
         description='How to choose a travel neck pillow for a long flight, a night train or a bus: memory foam vs inflatable, packed size, weight and washable covers.',
         alt='A plane window seat, with the words Neck pillow for flights.',
         html=photo('plane-window', 'Neck pillow for flights', 'Memory foam or inflatable? Size, weight and covers')),
dict(slug='packing-cubes', board='Packing and What to Wear', link='guides/packing-cubes.html',
         title='Packing cubes for travel: are they worth it, and which to buy',
         description='What packing cubes do, compression vs regular cubes, how many you need for a cabin bag or a check-in trolley, and whether they save weight.',
         alt='An open packed suitcase, with the words Are packing cubes worth it?',
         html=photo('packed-suitcase', 'Are packing cubes worth it?', 'Compression vs regular, and how many you need')),
dict(slug='toiletry-bag', board='Packing and What to Wear', link='guides/toiletry-bag-for-travel.html',
         title='Toiletry bag for travel for men and women: hanging or flat, and which to buy',
         description='How to choose a toiletry bag for travel: hanging vs flat, size in litres, water-resistant lining, weight, and how it works with the 100 ml liquids bag at airports.',
         alt='A trolley bag at an airport, with the words Toiletry bag for travel.',
         html=photo('trolley-walk', 'Toiletry bag for travel', 'Hanging or flat? Size, lining and the 100 ml rule')),
dict(slug='passport-holder', board='Packing and What to Wear', link='guides/passport-holder.html',
         title='Passport holder for men, women and families: RFID, size and which to buy',
         description='How to choose a passport holder or travel wallet: single vs family holders, what RFID blocking does, what fits inside, size and weight.',
         alt='An airport terminal, with the words Passport holder: what to look for.',
         html=photo('airport-terminal', 'Passport holder: what to look for', 'Single or family, what RFID does, and what fits')),
dict(slug='gadget-organiser', board='Packing and What to Wear', link='guides/gadget-organiser.html',
         title='Gadget organiser bag for travel: hard case vs pouch, size, and which to buy',
         description='How to choose a gadget or cable organiser bag for travel and work: hard case vs soft pouch vs double layer, and what size fits a laptop charger.',
         alt='A cabin bag at an airport, with the words Gadget organiser for travel.',
         html=photo('cabin-bag-airport', 'Gadget organiser for travel', 'Hard case or soft pouch? Which size fits your charger')),
dict(slug='sling-bag-travel', board='Watches and Everyday Bags', link='guides/sling-bag-for-travel.html',
         title='Sling bag for travel: anti-theft slings for men and women, size and what fits',
         description='How to choose a sling bag for travel: chest sling vs crossbody vs waist bag, which anti-theft features really help, and what fits (passport, phone, power bank).',
         alt='A grey handbag, with the words Sling bag for travel.',
         html=photo('handbag-grey', 'Sling bag for travel', 'Chest, crossbody or waist? What fits and what helps')),
dict(slug='tote-bag-office-travel', board='Watches and Everyday Bags', link='guides/tote-bag-for-office-and-travel.html',
         title='Tote bag for office and travel: laptop totes for women, zip, size and flight rules',
         description='How to choose a tote bag for work and travel: laptop compartment sizes (13, 14 and 15.6 inch), zip vs open top, a trolley sleeve, weight and whether it counts as a personal bag.',
         alt='A grey handbag, with the words Tote bag for office and travel.',
         html=photo('handbag-grey', 'Tote bag for office and travel', 'Laptop sizes, zip or open top, and flight rules')),
dict(slug='shoes-manali-kashmir', board='Packing and What to Wear', link='guides/shoes-for-manali-and-kashmir-trip.html',
         title='Shoes for a Manali or Kashmir trip: snow boots, hiking shoes or rented gumboots?',
         description="Which shoes to wear on a Manali, Kashmir or Gulmarg trip in winter: snow boots, waterproof hiking shoes or rented gumboots, and what 'waterproof' means on a listing.",
         alt='Boots on a mountain, with the words Shoes for Manali or Kashmir.',
         html=photo('boots-mountain', 'Shoes for Manali or Kashmir', 'Snow boots, hiking shoes or rented gumboots?')),
dict(slug='walking-shoes-europe', board='Packing and What to Wear', link='guides/walking-shoes-for-europe-trip.html',
         title='Walking shoes for a Europe trip: what to wear for cobbles, rain and winter',
         description='How to choose walking shoes for a Europe trip from India: cushioning for 20,000-step days, cobblestones, slip-ons for airports and waterproof shoes for winter.',
         alt='A Christmas market in Strasbourg, with the words Walking shoes for Europe.',
         html=photo('europe-strasbourg-christmas-market', 'Walking shoes for Europe', 'Cobbles, rain and 20,000-step days')),
dict(slug='shoes-goa', board='Packing and What to Wear', link='guides/shoes-for-goa-trip.html',
         title='Shoes for a Goa trip: flip-flops, sandals or clogs for men and women',
         description='Which footwear to take on a Goa trip: flip-flops for hot sand, strap sandals for scooter rides and markets, clogs that can get wet, and shoes for Dudhsagar.',
         alt='Palolem beach in Goa, with the words Shoes for a Goa trip.',
         html=photo('goa-palolem', 'Shoes for a Goa trip', 'Flip-flops, sandals or clogs? What suits each plan')),
dict(slug='honeymoon-india', board='India Trip Ideas', link='trips/honeymoon-destinations-in-india.html',
         title='Honeymoon places in India for the wedding season: beaches, snow, lakes and tea hills',
         description='Where to go for a honeymoon in India from November to February: Goa and Andaman beaches, Kerala backwaters, Udaipur lakes, snow in Gulmarg and Manali. Best months, weather and nearest airport for each.',
         alt='A houseboat on the Kerala backwaters, with the words Honeymoon places in India.',
         html=photo('kerala-houseboat', 'Honeymoon places in India', 'Beach, snow, lakes or tea hills? Best months and airports for 15 places')),
dict(slug='honeymoon-abroad', board='India Trip Ideas', link='trips/honeymoon-destinations-outside-india.html',
         title='Honeymoon abroad from India: visa and flight time for 13 countries',
         description='International honeymoon destinations from India with the visa you need and a rough flying time: the Maldives, Bali, Thailand, Mauritius, Sri Lanka, Dubai, Singapore and more, with the best months for each.',
         alt='Water villas in the Maldives at sunset, with the words Honeymoon abroad from India.',
         html=photo('maldives-villas-sunset', 'Honeymoon abroad from India', 'Visa and flying time for the Maldives, Bali, Thailand, Mauritius and more')),
dict(slug='weekend-getaways-delhi', board='India Trip Ideas', link='trips/weekend-getaways-from-delhi.html',
         title='12 weekend getaways from Delhi: distance and travel time by road, train or flight',
         description='Weekend trips from Delhi with the distance and travel time: Mathura, Agra, Rishikesh, Mussoorie, Nainital, Jaipur, Shimla, Amritsar and Manali. Best months, December trips and the 2027 long weekends.',
         alt='A table of weekend getaways from Delhi with distance and travel time.',
         html=chart('Weekend trips from Delhi', 'Weekend getaways from Delhi', table(['Trip', 'Distance', 'By road'], [
             ['Mathura', '~150 km', '2½–3½ hrs'], ['Agra', '~210 km', '3–4 hrs'], ['Rishikesh', '~240 km', '4–5 hrs'],
             ['Mussoorie', '~260 km', '5–6 hrs'], ['Nainital', '~280 km', '6–7 hrs'], ['Jaipur', '~280–310 km', '3½–5 hrs']])
             + '<p class="note"><strong>Distances and times are our estimates.</strong> Shimla, Amritsar, Manali, Udaipur and Varanasi need a long weekend: see the full list.</p>')),
dict(slug='weekend-getaways-mumbai', board='India Trip Ideas', link='trips/weekend-getaways-from-mumbai.html',
         title='11 weekend getaways from Mumbai: distance and travel time by road, train or ferry',
         description='Weekend trips from Mumbai with the distance and travel time: Lonavala, Matheran, Alibaug, Igatpuri, Nashik, Daman and Mahabaleshwar. Distances from Maharashtra Tourism, plus monsoon trips, December and 2027 long weekends.',
         alt='A table of weekend getaways from Mumbai with distance and travel time.',
         html=chart('Weekend trips from Mumbai', 'Weekend getaways from Mumbai', table(['Trip', 'Distance', 'By road'], [
             ['Lonavala', '84 km', '~2 hrs'], ['Matheran', '88 km', '2½–3 hrs*'], ['Alibaug', '~90 km', '2½–3½ hrs'],
             ['Igatpuri', '130 km', '~3 hrs'], ['Nashik', '~180 km', '3½–4½ hrs'], ['Daman', '~190 km', '4–5 hrs']])
             + '<p class="note"><strong>Distances from Maharashtra Tourism or our estimates.</strong> *Matheran: cars stop below the town, no vehicles inside. Goa, Udaipur and Jaipur are for longer weekends.</p>')),
dict(slug='weekend-getaways-bangalore', board='India Trip Ideas', link='trips/weekend-getaways-from-bangalore.html',
         title='11 weekend getaways from Bangalore: distance and travel time by road, train or flight',
         description='Weekend trips from Bangalore (Bengaluru) with the distance and travel time: Nandi Hills, Mysuru, Chikkamagaluru, Coorg, Wayanad, Ooty, Hampi and Gokarna. Distances from Karnataka Tourism, plus December and 2027 long weekends.',
         alt='A table of weekend getaways from Bangalore with distance and travel time.',
         html=chart('Weekend trips from Bangalore', 'Weekend getaways from Bangalore', table(['Trip', 'Distance', 'By road'], [
             ['Nandi Hills', '~60 km', '1½–2 hrs'], ['Mysuru', '~140 km', '2½–3 hrs'], ['Chikkamagaluru', '~250 km', '5–6 hrs'],
             ['Coorg', '~257 km', '5–6 hrs'], ['Wayanad', '~280 km', '6–7 hrs*'], ['Ooty', '~290 km', '7–8 hrs*']])
             + '<p class="note"><strong>Distances from Karnataka Tourism or our estimates.</strong> *The forest road is shut at night. Hampi, Gokarna and Goa suit a 3-day weekend.</p>')),
dict(slug='baby-travel-gear', board='Packing and What to Wear', link='category/baby-kids.html',
         title='Travelling with a baby or toddler: gear and guides for Indian families',
         description='Travel gear for families with a baby or young kids: strollers that fold small, baby carriers, diaper bags and kids travel picks, with simple guides on flying and packing for a baby.',
         alt='A list of baby travel gear ideas, with the words Travelling with a baby.',
         html=chart('Baby and kids travel', 'Travelling with a baby or toddler', group('Getting around', 'A stroller that folds small, or a baby carrier')
             + group('On the plane', 'A diaper bag that works as the baby\'s cabin bag')
             + group('Kids\' travel', 'Small things that keep a toddler busy on a long journey')
             + '<p class="note"><strong>Plus two simple guides:</strong> a packing checklist and the airline rules for flying with an infant.</p>')),
dict(slug='baby-travel-checklist', board='Packing and What to Wear', link='guides/travelling-with-baby-checklist.html',
         title='Travelling with a baby checklist: documents, feeding, diapers, clothes and sleep',
         description='A simple checklist for travelling with a baby or toddler: the age proof and documents, feeding, about 6 diapers a day plus a spare day, clothes, sleep, a stroller or carrier, and what goes in the diaper bag.',
         alt='A baby travel checklist table, with the words Travelling with a baby checklist.',
         html=chart('Baby travel checklist', 'Travelling with a baby: what to pack', table(['What', 'How much'], [
             ['Documents', 'Birth certificate, your ID'], ['Diapers', '~6 a day + 1 spare day'], ['Clothes', 'One set a day + 2 spare'],
             ['Feeding', 'Milk, bottles, brush, bib'], ['Sleep', 'Blanket, muslins, a toy'], ['Getting around', 'Light stroller or carrier']])
             + '<p class="note"><strong>The diaper bag is your cabin bag for the baby.</strong> Ask your paediatrician about medicines.</p>')),
dict(slug='flying-with-baby', board='Flight and Train Baggage Rules', link='guides/flying-with-baby-or-toddler.html',
         title='Flying with a baby in India: infant age, baggage and stroller rules by airline',
         description='Infant rules on IndiGo, Air India, Akasa Air, SpiceJet and Emirates: the minimum age, the infant ticket, the baby\'s baggage allowance, strollers at the gate, bassinets and the documents a baby needs.',
         alt='A table of infant rules by airline, with the words Flying with a baby.',
         html=chart('Airline rules, as listed by each airline', 'Flying with a baby in India', table(['Airline', 'Infant age', 'Stroller'], [
             ['IndiGo', '3 days–2 yrs', '1 free'], ['Air India', '7 days–2 yrs', 'Not on board'], ['Akasa Air', '7 days–2 yrs', '1 free'],
             ['SpiceJet', '7 days–2 yrs', 'Not in cabin']])
             + '<p class="note"><strong>Under 2 years is an infant</strong> and sits on your lap. Carry a birth certificate: without age proof the airline can charge a full fare.</p>')),
    dict(slug="russia-trip", board="India Trip Ideas", link="trips/russia-trip-from-india.html",
         title="Russia trip from India: the e-visa, flights and a 7-day plan",
         description="Indians can apply for a Russian e-visa online: one trip of up to 16 days within 60 days, no invitation needed. See the direct Delhi to Moscow flight, a 7-day Moscow and St Petersburg plan and the weather by month.",
         alt="The domes of St. Basil's Cathedral in Moscow, with the words Russia trip from India.",
         html=photo("moscow-st-basils", "Russia trip from India", "E-visa for up to 16 days, direct flights to Moscow and a 7-day plan")),
    dict(slug="seychelles-trip", board="India Trip Ideas", link="trips/seychelles-trip-from-india.html",
         title="Seychelles trip from India: no visa, but get this first",
         description="No visa for Indians: a free visitor's permit on arrival for up to 3 months. You must get the paid Travel Authorisation online before you fly. Direct IndiGo flights from Mumbai, a 7-day island plan and the best time to go.",
         alt="Anse Source d'Argent beach in the Seychelles, with the words Seychelles trip from India.",
         html=photo("seychelles-anse-source-dargent", "Seychelles from India: no visa", "Get the Travel Authorisation online first. Direct flights from Mumbai.")),
    dict(slug="travel-essentials-women", board="Packing and What to Wear", link="guides/travel-essentials-for-women.html",
         title="Travel essentials for women: the checklist and kit list",
         description="A practical travel checklist for women: a sling or tote, a hanging toiletry bag, packing cubes, a jewellery roll, power bank and adapter, sun care and a door stop alarm for hotel rooms.",
         alt="A checklist of travel essentials for women: day bag, toiletries, cubes, jewellery roll, power and sun care, with the words Travel essentials for women.",
         html=chart("Travel checklist", "Travel essentials for women", table(["Pack", "Why"], [
             ["Sling or tote", "Hands free, bag kept close"], ["Hanging toiletry bag", "Hooks on the door or rail"], ["Packing cubes", "Outfits sorted, easy to find"],
             ["Jewellery roll", "Nothing tangles or gets lost"], ["Power bank + adapter", "Phone alive, plug fits"], ["Sun care", "Cream and sunglasses"],
             ["Door stop alarm", "An extra lock at night"]])
             + '<p class="note"><strong>Keep your passport, cards and phone on you,</strong> not in the bag you check in.</p>')),
    dict(slug="solo-female-travel-india", board="India Trip Ideas", link="guides/solo-female-travel-india.html",
         title="Solo female travel in India: helplines, trains and easy first trips",
         description="Travelling alone in India as a woman: the official helplines 112, 181 and 139, the women's berth quota and Meri Saheli on Indian Railways, tips for cabs and stays, easy first solo trips and what to pack.",
         alt="A ladies coach on a Chennai train, with the words Solo female travel in India.",
         html=chart("Travelling alone in India", "Solo female travel: save these first", table(["Number", "For"], [
             ["112", "Police, fire, ambulance"], ["181", "Women Helpline"], ["139", "Railway helpline"]])
             + group("On trains", "Ask about the women's berth quota and Meri Saheli on Indian Railways.")
             + group("Before you go", "Share your plan and live location with someone, and book your first night's stay.")
             + '<p class="note">Helpline numbers as listed by the government. Check before you travel.</p>')),
    dict(slug="train-journey-packing", board="Flight and Train Baggage Rules", link="guides/things-to-carry-in-train-journey.html",
         title="Things to carry in a train journey: a packing list for Indian trains",
         description="What to carry on a long or overnight train in India: ticket and ID, food and water, a chain lock, a sleep kit, a power bank and clothes for the AC coach. Plus Indian Railways luggage limits and banned items.",
         alt="A train coach aisle, with the words Things to carry in a train journey.",
         html=photo("train-coach-aisle", "Things to carry in a train journey", "Ticket and ID, water, a chain lock, a shawl and a power bank")),
    dict(slug="business-trip-packing", board="Packing and What to Wear", link="guides/business-trip-packing-list.html",
         title="Business trip packing list: what to pack for a work trip",
         description="A simple packing list for a work trip in India or abroad: documents, a laptop backpack or office tote, a cabin bag that keeps formals neat, chargers, an adapter, a grooming kit and formal shoes.",
         alt="A suit and a cabin bag, with the words Business trip packing list.",
         html=photo("suit-cabin-bag", "Business trip packing list", "Documents, a laptop bag, formals, chargers and formal shoes in one cabin bag")),
    dict(slug="plug-type-india", board="Packing and What to Wear", link="guides/plug-type-in-india.html",
         title="Plugs and voltage in India: which adapter to bring",
         description="India uses round-pin plug types C, D and M at 230 V and 50 Hz. US and UK plugs don't fit, and 120 V-only appliances from the USA can be damaged. How to read your charger and which adapter to bring.",
         alt="The Taj Mahal, with the words Plugs and voltage in India for visitors.",
         html=photo("taj-mahal", "Plugs and voltage in India", "Types C, D and M at 230 V. Check your charger before you plug in.")),
    dict(slug="auli-december", board="India Trip Ideas", link="trips/auli-in-december.html",
         title="Auli in December: is there snow? Weather, skiing and the road up",
         description="Snow in Auli is not certain in December: official pages name January to March as the snow and ski season. See IMD temperatures for Joshimath, why the ropeway is closed, the road up, a 3-day plan and what to wear.",
         alt="Snow-covered slopes at Auli, with the words Auli in December.",
         html=photo("auli-snow", "Auli in December: is there snow?", "Snow is not certain. The ski season is January to March. The ropeway is shut.")),
    dict(slug="nainital-december", board="India Trip Ideas", link="trips/nainital-in-december.html",
         title="Nainital in December: weather, snow chances and a 2-3 day plan",
         description="Nainital in December is cold, clear and calm: about 14 °C by day and near freezing at night. Snow is not certain. A 2-day and 3-day plan, getting there from Delhi via Kathgodam or Pantnagar, and what to wear.",
         alt="Naini Lake with hills around it, with the words Nainital in December.",
         html=photo("nainital-lake", "Nainital in December", "Cold, clear days and near-freezing nights. Snow is not certain.")),
    dict(slug="mussoorie-december", board="India Trip Ideas", link="trips/mussoorie-in-december.html",
         title="Mussoorie in December: weather, snow chances and the Winterline",
         description="Mussoorie in December is cold, sunny and clear, with the Winterline at sunset. Snow is possible but not certain. IMD temperatures, a 2-day and 3-day plan, getting there from Dehradun and what to wear.",
         alt="Hills around Mussoorie, with the words Mussoorie in December.",
         html=photo("mussoorie-hills", "Mussoorie in December", "About 13 °C by day, the Winterline at sunset, and snow that is possible but not certain.")),
    dict(slug="jim-corbett-december", board="India Trip Ideas", link="trips/jim-corbett-in-december.html",
         title="Jim Corbett safari in December: open zones and how to book",
         description="Which Jim Corbett safari zones are open in December, how to book the permit only on the official site up to 45 days ahead, the rules, the weather, a 2-day plan, getting there from Delhi and what to wear on a cold open jeep.",
         alt="Morning mist over Dhikala in Jim Corbett, with the words Jim Corbett safari in December.",
         html=photo("corbett-dhikala-mist", "Jim Corbett in December", "Eight zones open, booking only on the official site, and cold misty mornings.")),
    dict(slug="return-gift-ideas", board="Gift Ideas", link="guides/return-gift-ideas.html",
         title="Return gift ideas for kids' birthday parties, by age",
         description="Small, useful return gifts that are the same for every child: art kits, sketch pens, puzzles and story books. Ideas by age for a 1st birthday, a class birthday at school and grown-up guests.",
         alt="A checklist of return gift ideas for kids by age, with the words Return gift ideas.",
         html=chart("Birthday party", "Return gift ideas by age", table(["Age", "Idea"], [
             ["Babies, 1st birthday", "Baby toy gift set"], ["3 to 5 years", "Animal puzzles, colouring kit"], ["4 to 8 years", "Junior art kit, sketch pens"],
             ["9 to 12 years", "Steel bottle, sketch pens"], ["Teens", "Steel flask, phone pouch"]])
             + '<p class="note"><strong>Keep it small and the same for every child,</strong> so nobody compares.</p>')),
    dict(slug="birthday-gifts-kids-by-age", board="Gift Ideas", link="guides/birthday-gift-ideas-for-kids.html",
         title="Birthday gifts for kids by age: ideas for boys and girls",
         description="Birthday gift ideas for kids in India by age, from a 1 year old to teens, for boys and girls: baby gift sets, art kits, puzzles, story books, board games and a first watch.",
         alt="A chart of birthday gift ideas for kids by age, with the words Birthday gifts for kids.",
         html=chart("Kids' birthday", "Birthday gifts for kids by age", table(["Age", "Idea"], [
             ["1 year", "Baby toy gift set, board books"], ["2 to 4", "Animal puzzles, story books"], ["5", "Doodle and draw kit"],
             ["6 to 9", "Puzzles, a first watch"], ["10 to 12", "Board game, fact book"]])
             + '<p class="note"><strong>Not sure?</strong> Our gift finder shows ideas straight away.</p>')),
    dict(slug='christmas-gift-teenagers', board='Gift Ideas', link='guides/christmas-gift-for-teenagers.html',
         title='Christmas gift for teenagers: ideas a teen boy or girl will use',
         description='Christmas gift ideas for teenagers in India: a Fastrack watch, sunglasses, a college backpack, a power bank, a first beard trimmer for a teenage boy and more. Useful things, not clutter.',
         alt='Gifts under a Christmas tree, with the words Christmas gifts for teenagers.',
         html=photo('christmas-tree-gifts', 'Christmas gifts for teenagers', 'Things a teenager will use: a watch, sunglasses, a college backpack, a power bank.')),
    dict(slug='christmas-gift-grandparents', board='Gift Ideas', link='guides/christmas-gift-for-grandparents.html',
         title='Christmas gift for grandparents: useful ideas for grandma and grandpa',
         description='Christmas gift ideas for grandparents in India: pair watches, easy-to-read watches, warm thermals and winter caps, slip-on walking shoes and a steel bottle. Useful and easy to use.',
         alt='Gifts under a Christmas tree, with the words Christmas gifts for grandparents.',
         html=photo('christmas-tree-gifts', 'Christmas gifts for grandparents', 'Easy-to-read watches, warm thermals, slip-on shoes and a steel bottle.')),
    dict(slug='manali-january', board='India Trip Ideas', link='trips/manali-in-january.html',
         title='Manali in January: snow, weather, the Winter Carnival and roads',
         description='Plan Manali for January 2027: IMD averages for January, how snow came late in January 2026, the first, middle and last week of the month, the Winter Carnival and the roads.',
         alt='Snow at Solang near Manali, with the words Manali in January.',
         html=photo('manali-solang-snow', 'Manali in January', 'IMD averages, how snow came late in January 2026, and the roads.')),
    dict(slug='kashmir-january', board='India Trip Ideas', link='trips/kashmir-in-january.html',
         title='Kashmir in January: snow, Chillai Kalan, roads and flights',
         description='Plan Srinagar, Pahalgam, Sonamarg and Gulmarg for January 2027: IMD January averages, the end of Chillai Kalan, how January 2026 went, roads and flights.',
         alt='Dal Lake in winter, with the words Kashmir in January.',
         html=photo('dal-lake-winter', 'Kashmir in January', 'Chillai Kalan, snow, roads and flights for Srinagar, Pahalgam, Sonamarg and Gulmarg.')),
    dict(slug='gulmarg-january', board='India Trip Ideas', link='trips/gulmarg-in-january.html',
         title='Gulmarg in January: snow, skiing and the gondola',
         description='Plan Gulmarg for January 2027: IMD January averages and how much snow a January can bring, the first week versus the last week, ski courses and when the gondola runs.',
         alt='Snow slopes at Gulmarg, with the words Gulmarg in January.',
         html=photo('gulmarg-snow', 'Gulmarg in January', 'Snow, skiing and the gondola: first week versus last week.')),
    dict(slug='goa-january', board='India Trip Ideas', link='trips/goa-in-january.html',
         title='Goa in January: weather, festivals and a quieter beach month',
         description='Plan Goa for January 2027: IMD averages, how Goa changes after New Year, the Feast of the Three Kings on 6 January, festivals and beach safety.',
         alt='The Reis Magos church in Goa, with the words Goa in January.',
         html=photo('goa-reis-magos-church', 'Goa in January', 'A quieter beach month after New Year, with the Feast of the Three Kings on 6 January.')),
    dict(slug='rajasthan-january', board='India Trip Ideas', link='trips/rajasthan-in-january.html',
         title='Rajasthan in January: weather, festivals and where to go',
         description='Plan Rajasthan for January 2027: IMD averages for Jaipur, Udaipur, Jaisalmer and Bikaner, the Bikaner Camel Festival on 9 to 10 January, the Kite Festival and train fog.',
         alt='Camels at the Bikaner Camel Festival, with the words Rajasthan in January.',
         html=photo('bikaner-camel-festival', 'Rajasthan in January', 'Weather for Jaipur, Udaipur, Jaisalmer and Bikaner, plus the Camel Festival and Kite Festival.')),
    dict(slug='gift-for-sister', board='Gift Ideas', link='guides/gift-for-sister.html',
         title="Gift for sister: ideas she'll use for Rakhi, her birthday or any day",
         description='Gift ideas for your sister in India, for any day of the year: a Fastrack or Titan watch, a light sling bag, cat-eye sunglasses and a perfume gift set.',
         alt='A gift box, with the words Gift for your sister.',
         html=photo('gift-box', 'Gift for your sister', 'A watch, a light sling bag, sunglasses or a perfume gift set. Good for Rakhi or any day.')),
    dict(slug='gift-for-brother', board='Gift Ideas', link='guides/gift-for-brother.html',
         title="Gift for brother: ideas he'll use for Rakhi, his birthday or any day",
         description='Gift ideas for your brother in India, for any day of the year: a Fastrack or Invicta watch, polarized sunglasses, a beard trimmer, a perfume set and a wallet.',
         alt='A gift box, with the words Gift for your brother.',
         html=photo('gift-box', 'Gift for your brother', 'A watch, polarized sunglasses, a beard trimmer or a wallet. Good for Rakhi or any day.')),
    dict(slug='gift-for-mother', board='Gift Ideas', link='guides/gift-for-mother.html',
         title='Gift for mom: useful ideas for your mother on any day',
         description='Gift ideas for your mom in India, for any day of the year: a Titan watch, a small tote or satchel, slip-on walking shoes, a thermal set and a steel bottle.',
         alt='Red roses, with the words Gift for mom.',
         html=photo('red-roses', 'Gift for mom', 'Useful ideas: a watch, a small tote, slip-on walking shoes, a thermal set, a steel bottle.')),
    dict(slug='gift-for-father', board='Gift Ideas', link='guides/gift-for-father.html',
         title='Gift for dad: useful ideas for your father on any day',
         description='Gift ideas for your dad in India, for any day of the year: a Casio or Titan watch, a leather wallet with 14 card slots, an auto-lock belt and slip-on walking shoes.',
         alt='A watch on a wrist, with the words Gift for dad.',
         html=photo('watch-wrist', 'Gift for dad', 'A watch, a leather wallet, an auto-lock belt, slip-on walking shoes.')),
    dict(slug='gift-for-husband', board='Gift Ideas', link='guides/gift-for-husband.html',
         title="Gift for husband: useful ideas he'll use on any day",
         description='Gift ideas for your husband in India, for any day of the year: a Timex or Titan watch, a slim leather wallet, a Philips grooming kit and a perfume gift set.',
         alt='A mesh-strap watch, with the words Gift for your husband.',
         html=photo('watch-mesh', 'Gift for your husband', 'A watch, a slim wallet, a grooming kit or a perfume gift set he will use.')),
    dict(slug='gift-for-wife', board='Gift Ideas', link='guides/gift-for-wife.html',
         title="Gift for wife: ideas she'll love on any day",
         description='Gift ideas for your wife in India, for any day of the year: a Timex or Titan Raga watch, a tote or sling bag, a perfume gift set and a zip-around wallet.',
         alt='A perfume bottle, with the words Gift for your wife.',
         html=photo('perfume-bottle', 'Gift for your wife', 'A watch, a tote or sling bag, a perfume gift set, a zip-around wallet.')),
    dict(slug='pondicherry-december', board='India Trip Ideas', link='trips/pondicherry-in-december.html',
         title='Pondicherry in December: weather, rain, a 3-day plan and what to wear',
         description='Plan Pondicherry (Puducherry) for December: IMD temperatures and rain, cyclone warnings, a 3-day plan and what to wear.',
         alt='The rocky beach at Pondicherry, with the words Pondicherry in December.',
         html=photo('pondicherry-rock-beach', 'Pondicherry in December', 'December is the wettest month of the winter. Rain, cyclone warnings and a 3-day plan.')),
    dict(slug='hampi-december', board='India Trip Ideas', link='trips/hampi-in-december.html',
         title='Hampi in December: weather, monuments, a 2-day plan and what to wear',
         description='Plan Hampi for December: IMD temperatures, the monument hours and where to buy the ASI ticket, the Virupaksha temple timings, a 2-day plan and what to wear.',
         alt='The stone chariot at Hampi, with the words Hampi in December.',
         html=photo('hampi-stone-chariot', 'Hampi in December', 'Monument hours, where to buy the ASI ticket and a simple 2-day plan.')),
    dict(slug='ranthambore-december', board='India Trip Ideas', link='trips/ranthambore-in-december.html',
         title='Ranthambore in December: safari booking, zones, timings and what to wear',
         description='Plan a Ranthambore safari in December: how to book on the official website the Forest Department links to, when booking opens, zones, timings and what to wear.',
         alt='A tiger in Ranthambore, with the words Ranthambore safari in December.',
         html=photo('ranthambore-tiger', 'Ranthambore safari in December', 'How to book on the official site, zones, timings and what to wear.')),
    dict(slug='vip-vs-safari', board='Luggage Size Guides', link='guides/vip-vs-safari.html',
         title='VIP vs Safari: trolley bags compared by the facts',
         description="VIP or Safari? We compared their Amazon.in trolley listings by shell, weight, full size and lock, and read both brands' official warranty terms.",
         alt='A traveller walking with a trolley bag, with the words VIP vs Safari.',
         html=photo('trolley-walk', 'VIP vs Safari trolley bags', "Compared by shell, weight, full size and lock, and the brands' own warranty terms.")),
    dict(slug='vip-vs-american-tourister', board='Luggage Size Guides', link='guides/vip-vs-american-tourister.html',
         title='VIP vs American Tourister: trolley bags compared by the facts',
         description="VIP or American Tourister? We compared their trolley listings on Amazon.in by shell, weight, full size, wheels and lock, and read both brands' official warranty terms.",
         alt='Trolley bag handles, with the words VIP vs American Tourister.',
         html=photo('trolley-handles', 'VIP vs American Tourister', 'Trolley bags compared by shell, weight, size, wheels and lock.')),
    dict(slug='safari-vs-skybags', board='Luggage Size Guides', link='guides/safari-vs-skybags.html',
         title='Safari vs Skybags: trolley bags compared by the facts',
         description='Safari or Skybags? We compared their trolley listings on Amazon.in by shell, weight, full size, wheels and lock, and read the official warranty terms of both.',
         alt='Bags on an airport baggage belt, with the words Safari vs Skybags.',
         html=photo('baggage-belt', 'Safari vs Skybags', 'Trolley bags compared by shell, weight, size, wheels and lock.')),
    dict(slug='mokobara-vs-american-tourister', board='Luggage Size Guides', link='guides/mokobara-vs-american-tourister.html',
         title='Mokobara vs American Tourister: trolley bags compared by the facts',
         description="Mokobara or American Tourister? We compared their trolley listings on Amazon.in by shell, weight, full size and lock, and read both brands' warranty terms.",
         alt='A cabin bag at an airport, with the words Mokobara vs American Tourister.',
         html=photo('cabin-bag-airport', 'Mokobara vs American Tourister', 'Trolley bags compared by shell, weight, size and lock.')),
    dict(slug='22-inch-trolley', board='Luggage Size Guides', link='guides/22-inch-trolley-bag-size.html',
         title='22 inch trolley bag: size in cm, and is it allowed as a cabin bag?',
         description='A 22 inch trolley is 55.9 cm, a small cabin size, but 0.9 cm over the 55 cm limit of most Indian airlines. See what 22 inch bags measure and three that fit.',
         alt='A cabin bag, with the words 22 inch trolley bag size.',
         html=photo('suit-cabin-bag', '22 inch trolley bag size', '55.9 cm: small, but 0.9 cm over the 55 cm limit of most Indian airlines.')),
    dict(slug='26-inch-trolley', board='Luggage Size Guides', link='guides/26-inch-trolley-bag-size.html',
         title='26 inch trolley bag: size in cm, litres and how many kg it holds',
         description='A 26 inch trolley is 66 cm, the most common medium size in India. See what 66 to 70 cm bags really measure, how many litres and kg they hold, and three picks.',
         alt='A packed suitcase, with the words 26 inch trolley bag size.',
         html=photo('packed-suitcase', '26 inch trolley bag size', '66 cm: the most common medium size in India. Litres, kg and three picks.')),
    dict(slug='32-inch-trolley', board='Luggage Size Guides', link='guides/32-inch-trolley-bag-size.html',
         title='32 inch trolley bag: size in cm, weight and is it allowed in flight?',
         description='A 32 inch trolley is 81.3 cm tall. We read 11 of the biggest bags on Amazon.in: none is within the 158 cm limit of Indian airlines. See which airlines take them.',
         alt='An airport terminal, with the words 32 inch trolley bag size.',
         html=photo('airport-terminal', '32 inch trolley bag size', '81.3 cm tall. None is within the 158 cm limit of Indian airlines.')),
    dict(slug='republic-day-sale-guide', board='Watches and Everyday Bags', link='guides/republic-day-sale-guide.html',
         title='Amazon Republic Day Sale 2027: what we know and how to choose bags and watches',
         description="Amazon hasn't announced its 2027 Republic Day sale yet. Last year's began on 16 January. How to get ready, and what to check on bags and watches.",
         alt='A gift box, with the words Republic Day Sale 2027.',
         html=photo('gift-box', 'Republic Day Sale 2027', "Not announced yet. Last year's began on 16 January. What to check on bags and watches.")),
    dict(slug='europe-packing-list', board='Packing and What to Wear', link='guides/europe-packing-list.html',
         title='Europe packing list: what to pack for a winter trip from India',
         description='What to pack for Europe in December and January: what to wear for Zurich, Paris and Rome weather, shoes for wet streets and the Type C and F plug and voltage.',
         alt='A Christmas market in Strasbourg, with the words Europe winter packing list.',
         html=photo('europe-strasbourg-christmas-market', 'Europe winter packing list', 'What to wear, shoes for wet streets and the Type C and F plug.')),
    dict(slug='japan-packing-list', board='Packing and What to Wear', link='guides/japan-packing-list.html',
         title='Japan packing list: what to pack for a winter trip from India',
         description="What to pack for Japan in December and January: what to wear for Tokyo, Kyoto and Osaka weather, slip-off shoes, the 100 V Type A plug and Japan's rules for medicines.",
         alt='A frozen pond at Kinkaku-ji in Japan, with the words Japan winter packing list.',
         html=photo('japan-kinkakuji-frozen-pond', 'Japan winter packing list', 'Tokyo, Kyoto and Osaka weather, slip-off shoes and the 100 V Type A plug.')),
    dict(slug='japan-trip', board='India Trip Ideas', link='trips/japan-trip-from-india.html',
         title='Japan trip from India: visa, a 7-day plan, December weather and cherry blossom',
         description='Plan a Japan trip from India: the Japan eVISA for Indians through VFS, direct flights, a 7-day plan, December weather and cherry blossom.',
         alt='Mount Fuji at Kawaguchiko, with the words Japan trip from India.',
         html=photo('mount-fuji-kawaguchiko', 'Japan trip from India', 'The eVISA, direct flights, a 7-day plan and cherry blossom.')),
    dict(slug='turkey-trip', board='India Trip Ideas', link='trips/turkey-trip-from-india.html',
         title='Turkey trip from India: the visa, direct flights, a 7-day plan and Cappadocia',
         description='Plan a Turkey (Turkiye) trip from India: the visa for Indians, the e-visa rules, direct flights, a 7-day plan and Cappadocia.',
         alt='Hot air balloons over Cappadocia, with the words Turkey trip from India.',
         html=photo('cappadocia-balloon', 'Turkey trip from India', 'The visa, direct flights, a 7-day plan and Cappadocia.')),
    dict(slug='first-analog-watch', board='Watches and Everyday Bags', link='guides/first-analog-watch-guide.html',
         title='How to choose your first analog watch',
         description='Dial size, strap type, water resistance and warranty in plain words, with picks for men and women.',
         alt='A watch on a wrist, with the words How to choose your first analog watch.',
         html=photo('watch-wrist', 'How to choose your first analog watch', 'Dial size, strap, water resistance and warranty in plain words.')),
    dict(slug='laptop-backpack-guide', board='Watches and Everyday Bags', link='guides/laptop-backpack-guide.html',
         title='How to choose a laptop backpack for college or office',
         description='Laptop size, litres, comfort and monsoon protection explained simply, with our picks.',
         alt='A backpack on a street, with the words How to choose a laptop backpack.',
         html=photo('backpack-street', 'How to choose a laptop backpack', 'Laptop size, litres, comfort and monsoon protection in plain words.')),
    dict(slug='vietnam-january', board='India Trip Ideas', link='trips/vietnam-in-january.html',
         title='Vietnam in January: weather north to south, Tet and a 7-9 day route',
         description='Plan Vietnam for January 2027: weather averages for Hanoi, Sa Pa, Ha Long, Hue, Da Nang, Hoi An, Ho Chi Minh City and Phu Quoc, plus Tet on 6 February 2027.',
         alt='Hoi An lanterns, with the words Vietnam in January.',
         html=photo('hoi-an-lanterns', 'Vietnam in January', 'Weather from Hanoi to Phu Quoc, and Tet on 6 February 2027.')),
    dict(slug='thailand-january', board='India Trip Ideas', link='trips/thailand-in-january.html',
         title='Thailand in January: weather, which coast is drier and what to plan',
         description='Plan Thailand for January 2027 with Thai Meteorological Department averages for Bangkok, Chiang Mai, Phuket, Pattaya and Ko Samui, and which coast is drier.',
         alt='Wat Arun in Bangkok, with the words Thailand in January.',
         html=photo('bangkok-wat-arun', 'Thailand in January', 'Averages for Bangkok, Chiang Mai, Phuket and Ko Samui, and which coast is drier.')),
    dict(slug='kerala-january', board='India Trip Ideas', link='trips/kerala-in-january.html',
         title='Kerala in January: weather, Munnar frost, festivals and houseboats',
         description="Plan Kerala for January 2027: IMD January averages for Kochi, Thiruvananthapuram, Alappuzha, Kottayam and Kozhikode, frost in Munnar's tea hills and the January festivals.",
         alt='A houseboat in Kerala, with the words Kerala in January.',
         html=photo('kerala-houseboat', 'Kerala in January', 'IMD averages, Munnar frost, January festivals and a one-week route.')),
    dict(slug='dubai-january', board='India Trip Ideas', link='trips/dubai-in-january.html',
         title='Dubai in January: the coolest month, Shopping Festival and events',
         description="Plan Dubai for January 2027: National Center of Meteorology averages for Dubai's coolest month, the Dubai Shopping Festival to 17 January and January events.",
         alt='Burj Khalifa in Dubai, with the words Dubai in January.',
         html=photo('dubai-burj-khalifa', 'Dubai in January', 'The coolest month, the Shopping Festival to 17 January and the events.')),
    dict(slug='bali-january', board='India Trip Ideas', link='trips/bali-in-january.html',
         title='Bali in January: is the wettest month a good time to go?',
         description="Plan Bali for January 2027: BMKG averages for January, Bali's wettest month, whether it is a good time to go, and Galungan on 13 January.",
         alt='Rice terraces in Bali, with the words Bali in January.',
         html=photo('bali-rice-terraces', 'Bali in January', "Bali's wettest month: is it still worth going? Plus Galungan on 13 January.")),
    dict(slug='gift-for-girlfriend', board='Gift Ideas', link='guides/gift-for-girlfriend.html',
         title="Gift for girlfriend: ideas she'll use, for any day",
         description='Gift ideas for your girlfriend in India, for any day of the year: a Titan Raga or Fastrack watch, a vegan leather sling, cat-eye sunglasses and a perfume gift set.',
         alt='A perfume bottle, with the words Gift for your girlfriend.',
         html=photo('perfume-bottle', 'Gift for your girlfriend', 'A watch, a sling bag, cat-eye sunglasses or a perfume gift set.')),
    dict(slug='gift-for-boyfriend', board='Gift Ideas', link='guides/gift-for-boyfriend.html',
         title="Gift for boyfriend: ideas he'll use, for any day",
         description='Gift ideas for your boyfriend in India, for any day of the year: a Timex or Fastrack watch, polarized sunglasses, a leather sling and a wallet gift set.',
         alt='A mesh-strap watch, with the words Gift for your boyfriend.',
         html=photo('watch-mesh', 'Gift for your boyfriend', 'A watch, polarized sunglasses, a leather sling or a wallet gift set.')),
    dict(slug='gift-for-best-friend', board='Gift Ideas', link='guides/gift-for-best-friend.html',
         title='Gift for best friend: useful ideas for any day',
         description='Gift ideas for your best friend in India, for any day of the year: round polarized sunglasses, a light crossbody bag and a perfume set for men and women.',
         alt='A gift box, with the words Gift for your best friend.',
         html=photo('gift-box', 'Gift for your best friend', 'Sunglasses, a light crossbody bag or a perfume set.')),
    dict(slug='gift-for-colleague', board='Gift Ideas', link='guides/gift-for-colleague.html',
         title='Gift for colleague: ideas for a birthday, wedding, promotion or thank you',
         description='Gift ideas for a colleague in India: a wallet gift set, a zip-around wallet and a steel bottle, for a birthday, wedding, promotion, Diwali or a thank you.',
         alt='A gift box, with the words Gift for a colleague.',
         html=photo('gift-box', 'Gift for a colleague', 'A wallet gift set, a zip-around wallet or a steel bottle.')),
    dict(slug='europe-trip-from-india', board='India Trip Ideas', link='trips/europe-trip-from-india.html',
         title='First Europe trip from India: Schengen visa, documents and a plan',
         description='Plan your first Europe trip from India: the Schengen visa for Indians, which country to apply to, documents, travel insurance and the 90 euro fee.',
         alt='Strasbourg Christmas market, with the words Europe trip from India.',
         html=photo('europe-strasbourg-christmas-market', 'Europe trip from India', 'Schengen visa, documents, insurance and the fee.')),
    dict(slug='uk-trip-from-india', board='India Trip Ideas', link='trips/uk-trip-from-india.html',
         title='UK trip from India: Standard Visitor visa and a London plan',
         description='Plan a UK trip from India with London at the centre: the Standard Visitor visa for Indians, 135 pounds for up to 6 months, and what to know before you go.',
         alt='Tower Bridge in London, with the words UK trip from India.',
         html=photo('london-tower-bridge', 'UK trip from India', 'The Standard Visitor visa and a London-centred plan.')),
    dict(slug='australia-trip-from-india', board='India Trip Ideas', link='trips/australia-trip-from-india.html',
         title='Australia trip from India: Visitor visa subclass 600 and flights',
         description='Plan an Australia trip from India: the Visitor visa (subclass 600) for Indians, why the ETA and eVisitor do not work for Indian passports, and direct flights.',
         alt='Sydney Opera House, with the words Australia trip from India.',
         html=photo('sydney-opera-house', 'Australia trip from India', 'The Visitor visa (subclass 600) and direct flights.')),
    dict(slug='hong-kong-trip-from-india', board='India Trip Ideas', link='trips/hong-kong-trip-from-india.html',
         title='Hong Kong trip from India: free pre-arrival registration, no visa',
         description='Plan a Hong Kong trip from India: the free pre-arrival registration that lets Indians visit for up to 14 days without a visa, plus direct flights.',
         alt='Victoria Harbour in Hong Kong, with the words Hong Kong trip from India.',
         html=photo('hong-kong-victoria-harbour', 'Hong Kong trip from India', 'Free pre-arrival registration, up to 14 days, no visa.')),
    dict(slug='mauritius-trip-from-india', board='India Trip Ideas', link='trips/mauritius-trip-from-india.html',
         title='Mauritius trip from India: no visa, and what to show on arrival',
         description='Plan a Mauritius trip from India: no visa needed for Indians, per the Mauritius Passport and Immigration Office, and what you must show on arrival.',
         alt='A lagoon in Mauritius, with the words Mauritius trip from India.',
         html=photo('mauritius-le-morne-lagoon', 'Mauritius trip from India', 'No visa needed, and what to show on arrival.')),
    dict(slug='georgia-trip-from-india', board='India Trip Ideas', link='trips/georgia-trip-from-india.html',
         title='Georgia trip from India: e-visa, visa-free rules and a plan',
         description='Plan a Georgia trip from India: the Georgian e-visa for Indians, the visa-free entry rules and how to get there.',
         alt='Gergeti church in Georgia, with the words Georgia trip from India.',
         html=photo('georgia-gergeti', 'Georgia trip from India', 'The e-visa, visa-free rules and a simple plan.')),
    dict(slug='azerbaijan-trip-from-india', board='India Trip Ideas', link='trips/azerbaijan-trip-from-india.html',
         title='Azerbaijan trip from India: e-visa, registration and a plan',
         description="Plan an Azerbaijan trip from India: the e-visa for Indians with 30 days' stay, standard in 3 working days or urgent in 3 hours, and registration rules.",
         alt='Flame Towers in Baku, with the words Azerbaijan trip from India.',
         html=photo('baku-flame-towers', 'Azerbaijan trip from India', 'The e-visa, registration and a plan for Baku.')),
    dict(slug='kazakhstan-trip-from-india', board='India Trip Ideas', link='trips/kazakhstan-trip-from-india.html',
         title='Kazakhstan trip from India: no visa up to 14 days and a 5-day plan',
         description='Plan a Kazakhstan trip from India: no visa for Indians for up to 14 days at a time, direct flights from Delhi and Mumbai to Almaty, and a 5-day plan.',
         alt='Big Almaty Lake, with the words Kazakhstan trip from India.',
         html=photo('big-almaty-lake', 'Kazakhstan trip from India', 'No visa up to 14 days, flights to Almaty and a 5-day plan.')),
    dict(slug='visiting-india', board='India Trip Ideas', link='trips/visiting-india.html',
         title='First trip to India: e-Visa, e-Arrival card, SIM and what to pack',
         description='A first trip to India: the e-Visa from the official site, the e-Arrival card, customs for tourists, what to pack and wear, SIM cards and UPI.',
         alt='The Taj Mahal, with the words First trip to India.',
         html=photo('taj-mahal', 'First trip to India', 'e-Visa, e-Arrival card, customs, SIM cards and what to pack.')),
    dict(slug='what-to-pack-for-india', board='Packing and What to Wear', link='guides/what-to-pack-for-india.html',
         title='What to pack for India: clothes, temple dress and the seasons',
         description='A packing list for a trip to India from abroad: what to wear as a woman or a man, temple dress, and what to pack for October to March and for summer.',
         alt='A packed suitcase, with the words What to pack for India.',
         html=photo('packed-suitcase', 'What to pack for India', 'Clothes, temple dress and what changes by season.')),
    dict(slug='packing-abroad', board='Packing and What to Wear', link='packing/abroad.html',
         title='International trip packing list for Indians: 37 things, documents first',
         description='A free international packing checklist for Indians: passport, visa, insurance and local currency first, then the rest.',
         alt='A packed suitcase, with the words International packing list.',
         html=photo('packed-suitcase', 'Packing for a trip abroad', 'A free checklist. Documents first: passport, visa, insurance, some local currency.')),
    dict(slug='power-bank-rules', board='Flight and Train Baggage Rules', link='guides/power-bank-rules-on-flights.html',
         title='Power bank on a plane: the 100 Wh limit and in-flight bans',
         description='Can you take a power bank on a plane? The 100 Wh limit, how many you can carry, and which airlines ban using one in flight.',
         alt='A plane cabin, with the words Power bank on a plane.',
         html=photo('plane-cabin', 'Power bank on a plane?', 'The 100 Wh limit, how many you can carry, and in-flight bans.')),
    dict(slug='power-bank-adapter', board='Flight and Train Baggage Rules', link='guides/power-bank-and-travel-adapter-guide.html',
         title='Power bank and travel adapter guide: mAh, Wh and plug types',
         description='Which power bank is allowed on Indian flights, how to read mAh and Wh, and the plug types for Thailand, Dubai, Bali and Singapore.',
         alt='An airport terminal, with the words Power bank and travel adapter guide.',
         html=photo('airport-terminal', 'Power bank and travel adapter', 'How to read mAh and Wh, and which plug for which country.')),
    dict(slug='trolley-international', board='Luggage Size Guides', link='guides/trolley-bag-size-for-international-travel.html',
         title='Trolley bag size for international flights: the 158 cm rule',
         description='For flights abroad most airlines limit one checked bag to 158 cm in total, and to 23 kg on USA, Canada and Europe routes. See which size fits.',
         alt='Bags on an airport baggage belt, with the words Trolley size for international flights.',
         html=photo('baggage-belt', 'Trolley size for flights abroad', 'Most airlines allow 158 cm in total and 23 kg on USA, Canada and Europe routes.')),
    dict(slug='wallet-belt-guide', board='Gift Ideas', link='guides/wallet-and-belt-buying-guide.html',
         title='Wallet and belt buying guide: leather types, card slots, belt size',
         description='Full grain, top grain, genuine or PU leather? How many card slots you need, what RFID blocking does, and how to pick a belt size from your waist.',
         alt='A watch on a wrist, with the words Wallet and belt buying guide.',
         html=photo('watch-wrist', 'Wallet and belt buying guide', 'Leather types, card slots, RFID blocking and belt size.')),
    dict(slug='manali-packing-list', board='Packing and What to Wear', link='guides/manali-packing-list.html',
         title='Manali packing list for snow: what to pack for December and January',
         description='A Manali packing list for the 2026-27 winter: layers, snow shoes, what to rent at the snow points and the kit for the overnight bus.',
         alt='Snow at Solang near Manali, with the words Manali snow packing list.',
         html=photo('manali-solang-snow', 'Manali snow packing list', 'What to pack for Manali in December and January.')),
    dict(slug='kashmir-packing-list', board='Packing and What to Wear', link='guides/kashmir-packing-list.html',
         title='Kashmir packing list for winter: Srinagar, Gulmarg and Pahalgam',
         description='What to pack for Kashmir in winter 2026-27: layering for Srinagar, Gulmarg and Pahalgam, snow shoes, a postpaid SIM and what to wear at shrines.',
         alt='Snow-covered pine trees at Pahalgam, with the words Kashmir winter packing list.',
         html=photo('pahalgam-snow-pines', 'Kashmir winter packing list', 'Srinagar, Gulmarg and Pahalgam: layers, shoes, SIM and shrine dress.')),
    dict(slug='snow-trip-packing-list', board='Packing and What to Wear', link='guides/snow-trip-packing-list.html',
         title='Snow trip packing list for India: what to pack for family and kids',
         description="A snow trip packing list for India 2026-27 with layering, shoes, kids' lists and 4-day and 7-day versions.",
         alt='A snowy slope at Auli, with the words Snow trip packing list.',
         html=photo('auli-snow', 'Snow trip packing list', 'What to pack for snow in India, for family and kids.')),
    dict(slug='february-trips', board='India Trip Ideas', link='trips/where-to-go-in-february.html',
         title='Where to go in February 2027: snow, beaches, desert festivals and abroad',
         description='Places to visit in February 2027 in India and abroad: snow in Gulmarg, Auli and Manali, desert festivals in Rajasthan, beaches, plus long weekends in the month.',
         alt='A camel at Jaisalmer, with the words Where to go in February 2027.',
         html=photo('jaisalmer-dancing-camel', 'Where to go in February 2027', 'Snow, beaches, desert festivals and trips abroad.')),
    dict(slug='best-time-india', board='India Trip Ideas', link='trips/best-time-to-visit-india.html',
         title='Best time to visit India (2026-27) and a Golden Triangle itinerary',
         description='When to visit India by season and region, with a 5-day or 7-day Golden Triangle itinerary for first-time visitors.',
         alt='The Taj Mahal, with the words Best time to visit India.',
         html=photo('taj-mahal', 'Best time to visit India', 'Season by season, plus a 5 or 7 day Golden Triangle plan.')),
    dict(slug='india-e-visa', board='India Trip Ideas', link='trips/india-e-visa-for-tourists.html',
         title='India e-Visa for tourists (2026): official website, cost, time and photo',
         description='A guide to the India e-Visa for tourists: the official website, cost, processing time and the photo rules.',
         alt='The Taj Mahal, with the words India e-Visa for tourists.',
         html=photo('taj-mahal', 'India e-Visa for tourists', 'The official website, cost, processing time and photo.')),
    dict(slug='india-sim-upi', board='India Trip Ideas', link='trips/india-sim-card-upi-and-money-for-tourists.html',
         title='India SIM card, eSIM, UPI and cash for tourists: what foreigners need',
         description='What foreign visitors to India need for a SIM card or eSIM, UPI payments and cash, in plain words.',
         alt="Humayun's Tomb in Delhi, with the words SIM, eSIM, UPI and cash in India.",
         html=photo('delhi-humayuns-tomb', 'SIM, eSIM, UPI and cash in India', 'What foreign visitors need to get connected and pay.')),
    dict(slug='sunglasses-guide', board='Watches and Everyday Bags', link='guides/sunglasses-buying-guide.html',
         title='Sunglasses buying guide for India: polarized vs UV400, size and face shape',
         description='Polarized or UV400? How to read frame sizes and match a frame to your face shape, in plain words.',
         alt='A gift box, with the words Sunglasses buying guide.',
         html=photo('gift-box', 'Sunglasses buying guide', 'Polarized vs UV400, frame sizes and face shapes.')),
    dict(slug='charger-guide', board='Packing and What to Wear', link='guides/which-charger-for-iphone-17-and-samsung-s25.html',
         title='Which charger for iPhone 17, Samsung S25 Ultra or Pixel 10? Watts for each',
         description='How many watts each phone charges at, and which charger is enough for iPhone 17, Samsung S25 Ultra and Pixel 10.',
         alt='An airport terminal, with the words Which charger for your phone.',
         html=photo('airport-terminal', 'Which charger for your phone?', 'iPhone 17, Samsung S25 Ultra and Pixel 10: the watts for each.')),
    dict(slug='vip-coupon', board='Luggage Size Guides', link='guides/vip-bags-coupon-code.html',
         title='VIP Bags coupon code, checked 25 Nov 2026: VIP, Skybags, Aristocrat, Caprese',
         description='The current VIP Bags coupon code for VIP, Skybags, Aristocrat and Caprese, checked on 25 November 2026.',
         alt='A woman walking with a trolley bag, with the words VIP Bags coupon code.',
         html=photo('trolley-walk', 'VIP Bags coupon code', 'Checked 25 Nov 2026: VIP, Skybags, Aristocrat and Caprese.')),
    dict(slug='packing-week-holiday', board='Packing and What to Wear', link='packing/index.html',
         title='Packing list for a week-long holiday: a free checklist',
         description='A free packing list for a week-long holiday, from documents and clothes to toiletries and chargers.',
         alt='A packed suitcase, with the words Week-long holiday packing list.',
         html=photo('packed-suitcase', 'Week-long holiday packing list', 'A free checklist you can tick on your phone.')),
    dict(slug='packing-business', board='Packing and What to Wear', link='packing/business.html',
         title='Business trip packing checklist',
         description='A packing checklist for a business trip: work clothes, laptop and chargers, documents and toiletries.',
         alt='A cabin bag at an airport, with the words Business trip packing list.',
         html=photo('cabin-bag-airport', 'Business trip packing list', 'A short checklist for a cabin-bag work trip.')),
    dict(slug='packing-train', board='Flight and Train Baggage Rules', link='packing/train.html',
         title='Train journey packing list for Indian Railways',
         description='A checklist of what to carry on a long train journey in India, from bedding and chargers to snacks and a lock.',
         alt='A train coach aisle, with the words Train journey packing list.',
         html=photo('train-coach-aisle', 'Train journey packing list', 'What to carry on Indian Railways.')),
    dict(slug='packing-wedding', board='Packing and What to Wear', link='packing/wedding.html',
         title='Wedding packing list: what to carry to a family wedding',
         description='A packing list for a family wedding trip: outfits, jewellery, shoes, toiletries and a gift.',
         alt='A gift box, with the words Wedding packing list.',
         html=photo('gift-box', 'Wedding packing list', 'What to carry to a family wedding.')),
    dict(slug='packing-weekend', board='Packing and What to Wear', link='packing/weekend.html',
         title='Weekend trip packing list',
         description='A short packing list for a weekend trip, so everything fits in one small bag.',
         alt='A plane window, with the words Weekend trip packing list.',
         html=photo('plane-window', 'Weekend trip packing list', 'Travel light for two nights.')),
    dict(slug='duty-free-india', board='Flight and Train Baggage Rules', link='baggage/customs.html',
         title='Duty free allowance India 2026: Rs 75,000 limit, gold, alcohol, customs',
         description='What you can bring into India: the duty free limit, gold, alcohol and other customs rules, as of 2026.',
         alt='An airport terminal, with the words India duty free allowance.',
         html=photo('airport-terminal', 'India duty free allowance', 'The Rs 75,000 limit, gold, alcohol and customs rules.')),
    dict(slug='liquids-100ml', board='Flight and Train Baggage Rules', link='baggage/can-i-carry/liquids.html',
         title='100 ml liquid rule for flights in India 2026: shampoo, toothpaste, water',
         description='How the 100 ml liquid rule works on flights in India, with shampoo, toothpaste and water as examples.',
         alt='A cabin bag at an airport, with the words The 100 ml liquid rule.',
         html=photo('cabin-bag-airport', 'The 100 ml liquid rule', 'Shampoo, toothpaste, water: what is allowed on flights in India.')),
    dict(slug='laptop-flight', board='Flight and Train Baggage Rules', link='baggage/can-i-carry/laptop.html',
         title='Laptop in flight: cabin bag or check-in? IndiGo, Air India rules 2026',
         description='Can you carry a laptop in your cabin bag or check it in? What IndiGo and Air India say, as of 2026.',
         alt='A plane cabin, with the words Laptop in flight.',
         html=photo('plane-cabin', 'Laptop in flight', 'Cabin bag or check-in? IndiGo and Air India rules.')),
    dict(slug='indigo-intl-baggage', board='Flight and Train Baggage Rules', link='baggage/indigo-international.html',
         title='IndiGo international baggage allowance from India 2026: cabin bag and kg',
         description="IndiGo's international baggage allowance from India: cabin bag size and checked kg by fare, as of 2026.",
         alt='A plane window, with the words IndiGo international baggage.',
         html=photo('plane-window', 'IndiGo international baggage', 'Cabin bag size and kg by fare.')),
    dict(slug='air-india-intl-baggage', board='Flight and Train Baggage Rules', link='baggage/air-india-international.html',
         title='Air India international baggage allowance from India 2026: cabin bag and kg',
         description="Air India's international baggage allowance from India: cabin bag size and checked kg by fare, as of 2026.",
         alt='A plane cabin, with the words Air India international baggage.',
         html=photo('plane-cabin', 'Air India international baggage', 'Cabin bag size and kg by fare.')),
    dict(slug='rajasthan-packing-list', board='Packing and What to Wear', link='guides/rajasthan-packing-list.html',
         title='Rajasthan packing list: Jaipur, Udaipur and Jaisalmer, October to March',
         description='What to pack for Rajasthan from October to March: day and night temperatures for Jaipur, Udaipur and Jaisalmer, desert camp nights and temple dress.',
         alt='Sam sand dunes near Jaisalmer, with the words Rajasthan packing list.',
         html=photo('jaisalmer-sam-dunes', 'Rajasthan packing list', 'Jaipur, Udaipur and Jaisalmer: what to wear by day and at a desert camp.')),
    dict(slug='kerala-packing-list', board='Packing and What to Wear', link='guides/kerala-packing-list.html',
         title='Kerala packing list for November to February: coast, backwaters and Munnar',
         description='What to pack for Kerala from November to February: light cotton for the coast, a warm layer for cold Munnar mornings and temple dress rules.',
         alt='A houseboat in the Kerala backwaters, with the words Kerala packing list.',
         html=photo('kerala-houseboat', 'Kerala packing list', 'Coast, backwaters and Munnar: light cotton plus one warm layer.')),
    dict(slug='rishikesh-packing-list', board='Packing and What to Wear', link='guides/rishikesh-packing-list.html',
         title='Rishikesh packing list: rafting clothes, camp kit and what to wear',
         description='What to pack for Rishikesh from October to March: what to wear for rafting in cold Ganga water, camp kit and a 3-day list.',
         alt='The Ganga at Rishikesh, with the words Rishikesh packing list.',
         html=photo('rishikesh-ganga', 'Rishikesh packing list', 'Rafting clothes, camp kit and a 3-day list.')),
    dict(slug='march-trips', board='India Trip Ideas', link='trips/where-to-go-in-march.html',
         title='Where to go in March 2027: Holi, hill stations, beaches and abroad',
         description='Places to visit in March 2027 in India and abroad: Holi on 23 March, the last snow, hill stations, beaches and cherry blossom in Japan.',
         alt='Japanese cherry blossom along the Meguro River, with the words Where to go in March 2027.',
         html=photo('tokyo-meguro-cherry-blossom', 'Where to go in March 2027', 'Holi, hill stations, beaches and trips abroad.')),
    dict(slug='holi-2027', board='India Trip Ideas', link='trips/holi-2027.html',
         title='Holi 2027 date and where to celebrate: Tuesday 23 March',
         description='Holi 2027 is on Tuesday 23 March, with Holika Dahan on Monday 22 March. Where to celebrate in India, what to wear and how to stay safe.',
         alt='Heaps of Holi colour powder, with the words Holi 2027.',
         html=photo('holi-colour-sacks', 'Holi 2027: Tuesday 23 March', 'Where to celebrate, what to wear and how to stay safe.')),
    dict(slug='womens-day-gifts', board='Gift Ideas', link='guides/womens-day-gift-ideas.html',
         title="Women's Day 2027 gift ideas: colleagues, wife, mom, sister and friends",
         description="Women's Day gift ideas for Monday 8 March 2027: small office gifts for female colleagues and staff, plus gifts for your wife, mom, sister and friends.",
         alt="Red roses, with the words Women's Day gift ideas.",
         html=photo('red-roses', "Women's Day gift ideas", 'Monday 8 March 2027: for colleagues, wife, mom, sister and friends.')),
    dict(slug='april-trips', board='India Trip Ideas', link='trips/where-to-go-in-april.html',
         title='Where to go in April 2027: hill stations, tulips, Char Dham and abroad',
         description='Places to visit in April 2027 in India and abroad: hill stations, Srinagar tulip garden, Char Dham registration, long weekends, safaris and trips abroad.',
         alt='Tulips in the Srinagar garden, with the words Where to go in April 2027.',
         html=photo('srinagar-tulip-garden', 'Where to go in April 2027', 'Hill stations, tulips, Char Dham and long weekends.')),
    dict(slug='may-trips', board='India Trip Ideas', link='trips/where-to-go-in-may.html',
         title='Where to go in May 2027: summer vacation hills, Ladakh and abroad',
         description='Places to visit in May 2027, the school summer holiday month: cool hill stations, Char Dham, Ladakh roads, long weekends and family trips in India and abroad.',
         alt='Kedarnath temple in the mountains, with the words Where to go in May 2027.',
         html=photo('kedarnath-temple', 'Where to go in May 2027', 'Summer vacation hills, Char Dham, Ladakh and family trips.')),
    dict(slug='ladakh-trip-guide', board='India Trip Ideas', link='trips/ladakh-trip-guide.html',
         title='Leh Ladakh trip guide: best time, permits, roads and a 7-day plan',
         description='Plan a Leh Ladakh trip: the best months, flying to Leh or driving the Srinagar and Manali roads, permits for Nubra and Pangong, the 48-hour rest rule for altitude and a 7-day plan.',
         alt='Leh town seen from Shanti Stupa, with the words Leh Ladakh trip guide.',
         html=photo('leh-from-shanti-stupa', 'Leh Ladakh trip guide', 'Best time, permits, roads and a 7-day plan.')),
    dict(slug='spiti-valley-guide', board='India Trip Ideas', link='trips/spiti-valley-trip-guide.html',
         title='Spiti Valley trip guide: best time, routes, permits and an 8-day plan',
         description='Plan a Spiti Valley trip: the best time to visit, the two roads in (Shimla and Kinnaur all year, Manali and Kunzum La only in summer), permits, altitude advice and an 8-day circuit.',
         alt='Key Monastery in Spiti Valley, with the words Spiti Valley trip guide.',
         html=photo('key-monastery-spiti', 'Spiti Valley trip guide', 'Best time, two roads in, permits and an 8-day plan.')),
    dict(slug='sikkim-trip-plan', board='India Trip Ideas', link='trips/sikkim-trip-plan.html',
         title='Sikkim trip plan: Gangtok, permits, the best time to go and a 6-day route',
         description='Plan a Sikkim trip: the best time to visit Gangtok, getting there from Bagdogra and NJP, permits for Tsomgo Lake, Nathu La and North Sikkim, local rules and a 6-day plan.',
         alt='Tsomgo Lake in Sikkim, with the words Sikkim trip plan.',
         html=photo('tsomgo-lake', 'Sikkim trip plan', 'Gangtok, permits, best time and a 6-day route.')),
    dict(slug='char-dham-2027', board='India Trip Ideas', link='trips/char-dham-yatra-2027.html',
         title='Char Dham Yatra 2027: dates, free registration and an 11-day route',
         description='Plan the Char Dham Yatra 2027 to Yamunotri, Gangotri, Kedarnath and Badrinath: opening dates, how the free registration works, Kedarnath helicopter booking only on IRCTC and an 11-day route from Haridwar.',
         alt='Badrinath temple, with the words Char Dham Yatra 2027.',
         html=photo('badrinath-temple', 'Char Dham Yatra 2027', 'Dates, free registration and an 11-day route.')),
    dict(slug='kedarnath-packing', board='Packing and What to Wear', link='guides/kedarnath-packing-list.html',
         title='Kedarnath packing list: what to wear and carry for the trek',
         description='What to pack for the 16-17 km Kedarnath trek: clothes for May, June and October, a rain jacket, warm layers for a cold night at 3,580 m, shoes, a walking stick and documents.',
         alt='Kedarnath temple in the mountains, with the words Kedarnath packing list.',
         html=photo('kedarnath-temple', 'Kedarnath packing list', 'What to wear and carry for the trek and a cold night.')),
    dict(slug='which-usb-c-cable', board='Packing and What to Wear', link='guides/which-usb-c-cable.html',
         title='Which USB-C cable do I need? 3 A vs 5 A, 60 W vs 100 W and 240 W',
         description='How to choose a USB-C cable: 3 A vs 5 A, what an e-marker chip is, why 5 A cables need one, USB 2.0 vs USB 3 data speed and one cable for phone, laptop and power bank on a trip.',
         alt='A plane window, with the words Which USB-C cable do I need.',
         html=photo('plane-window', 'Which USB-C cable do I need?', '3 A vs 5 A, e-marker chips and one cable for a trip.')),
    dict(slug='malaysia-packing-list', board='Packing and What to Wear', link='guides/malaysia-packing-list.html',
         title='Malaysia packing list: what to pack and wear for a trip from India',
         description='What to pack for Malaysia from India: light clothes for heat and rain, an umbrella, modest clothes for mosques and Batu Caves, a type G plug adapter and the right bag for your airline.',
         alt='The Petronas Towers in Kuala Lumpur, with the words Malaysia packing list.',
         html=photo('kuala-lumpur-petronas', 'Malaysia packing list', 'Heat, rain, mosque dress and a type G adapter.')),
    dict(slug='mothers-day-gifts', board='Gift Ideas', link='guides/mothers-day-gift-ideas.html',
         title="Mother's Day 2027 gift ideas for mom: Sunday 9 May in India",
         description="Mother's Day 2027 is Sunday 9 May in India. Useful gift ideas for your mom, from daughter, son, kids and husband.",
         alt="A grey handbag, with the words Mother's Day gift ideas.",
         html=photo('handbag-grey', "Mother's Day gift ideas", 'Sunday 9 May 2027: useful gifts for mom, from daughter, son, kids and husband.')),
    dict(slug='luggage-scale-guide', board='Packing and What to Wear', link='guides/luggage-scale.html',
         title='Luggage scale: how to weigh your bag at home, accuracy and airline limits',
         description='Why weigh your bag at home, how to use a hanging digital luggage scale step by step, what tare means and how accurate scales are.',
         alt='A bathroom scale, with the words Luggage scale guide.',
         html=photo('bathroom-scale', 'Luggage scale guide', 'How to weigh your bag at home, tare and airline limits.')),
    dict(slug='travel-chargers', board='Packing and What to Wear', link='category/travel-tech/chargers.html',
         title='USB-C chargers and cables for travel: phone and laptop picks',
         description='USB-C chargers and cables for phones and laptops, hand-picked for travel, including fast charging for iPhone and Samsung.',
         alt='An airport terminal, with the words USB-C chargers for travel.',
         html=photo('airport-terminal', 'USB-C chargers for travel', 'Phone and laptop chargers and cables, hand-picked.')),
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
