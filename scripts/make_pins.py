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
.over .foot small{color:#d8e4e8}"""


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
         description="What to wear in Manali and the hills in winter: how to layer, what to wear on your feet, and what to carry for snow.",
         alt="A person in a winter jacket in the snow, with the words What to wear on a winter hill trip.",
         html=photo("snow-jacket", "What to wear on a winter hill trip", "Simple layers for Manali and the hills")),
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
