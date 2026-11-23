"""Our own drawing of every pick, made only from the facts in data/deals.json.

build.py writes one SVG per pick to docs/assets/picks/<ASIN>.svg and shows it on the pick page,
product cards and guide pick boxes. These are simple outlines with no logos and no brand details,
never traced or copied from a product photo. They are painted in the colour the listing names
(the deal's "colour" field, read as text) and show the parts the listing describes: wheels, locks,
compartments, dial and strap colours, a date window. Where the listing gives a size, the shape is
drawn to that size and labelled; cabin-size bags also get IndiGo's cabin limit as a dashed box.
Every drawing says "Illustration, not a product photo" on the image itself.
"""

import hashlib
import math
import re
from html import escape as e
from pathlib import Path

from diagrams import FONT

W, H = 480, 360
FLOOR = 272
NOTE = "Illustration, not a product photo"
SCALED = " · listed sizes drawn to scale"
CSS_FILE = Path(__file__).resolve().parent.parent / "static" / "style.css"
CATS = ("luggage", "backpacks", "watches", "clothing", "shoes", "skincare", "handbags", "travel-gear",
        "travel-tech", "sunglasses", "wallets-belts", "perfumes", "grooming", "books")
DASH = ' stroke-dasharray="7 5"'

# Pixels per cm (bags) or per mm (watches, glasses), fixed per kind so picks of one kind compare fairly.
SCALE = {"trolley": 2.6, "duffle": 3.3, "backpack": 3.75, "bag": 5.6, "watch": 4.0, "watch-pair": 2.7, "glasses": 2.6}


def n(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def D(template, *vals):
    """A path string with every number rounded to one decimal."""
    return template % tuple(n(v) for v in vals)


# ---------- colours: the category tint and icon colour from static/style.css ----------

def _colors():
    css = CSS_FILE.read_text(encoding="utf-8")
    light, _, dark = css.partition("@media (prefers-color-scheme: dark)")

    def grab(block, var, fallback):
        m = re.search(r"--%s:\s*(#[0-9a-fA-F]{6})" % re.escape(var), block)
        return m.group(1).lower() if m else fallback
    return {c: (grab(light, "tint-" + c, "#eef1f3"), grab(light, "icon-" + c, "#0f4c5c"),
                grab(dark, "tint-" + c, "#1c2329"), grab(dark, "icon-" + c, "#7cc4d4")) for c in CATS}


COLORS = _colors()


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x * t + y * (1 - t)) for x, y in zip(a, b))


def style(cat, paint=""):
    """Classes: f body, s side or panel, a accent panel, p small dark parts; k, ks, ka, fs, pk the matching outlines."""
    lt, li, dt, di = COLORS.get(cat, COLORS["travel-gear"])
    rule = (".bg{fill:%s}.f{fill:%s}.s,.a{fill:%s}.p{fill:%s}.k{stroke:%s}.ks,.ka{stroke:%s}.fs{stroke:%s}.pk{stroke:%s}"
            ".d{stroke:%s}.dt{fill:%s}.t{fill:%s}.m{fill:%s}.l{stroke:%s}.lt{fill:%s}")
    return ("<style>.k,.ks,.ka,.fs,.pk,.d,.l{fill:none;stroke-linecap:round;stroke-linejoin:round}"
            + rule % (lt, "#ffffff", mix(li, "#ffffff", .15), "#3b4652", li, mix(li, "#ffffff", .15), "#ffffff", "#3b4652",
                      "#c2410c", "#c2410c", "#14202b", "#5b6573", "#0f4c5c", "#0f4c5c")
            + "text{font-family:%s}@media (prefers-color-scheme:dark){" % FONT
            + rule % (dt, "#1d262e", mix(di, "#1d262e", .2), "#7d8995", di, mix(di, "#1d262e", .2), "#1d262e", "#7d8995",
                      "#fb923c", "#fb923c", "#e8edf1", "#9ba6b2", "#7cc4d4", "#7cc4d4")
            + "}" + paint + "</style>")


# ---------- the colour the listing names ----------

# Colour words, longest first so "blue grey" wins over "blue", with the shade we paint each one.
PALETTE = [
    ("charcoal black", "#2e3236"), ("coral purple", "#9d86c2"), ("army green", "#56603a"), ("dusk green", "#5f7d6e"), ("sea blue", "#5aa3b5"),
    ("slate grey", "#66717c"), ("dark grey", "#4a5057"), ("dark brown", "#4a2f20"), ("deep red", "#7a2834"),
    ("blue grey", "#6b7f95"), ("lime green", "#9ccb3b"), ("rose gold", "#d6a28e"), ("gunmetal", "#4f565d"), ("charcoal", "#363b40"),
    ("navy blue", "#22325a"), ("wine red", "#6d1f33"), ("turquoise", "#2bb0ad"), ("lime", "#a9c94b"),
    ("red", "#c0392b"), ("navy", "#22325a"), ("olive", "#6b6d3b"), ("teal", "#1f7a7a"), ("coral", "#ee7b63"), ("mint", "#a6dac6"),
    ("beige", "#d8c7a6"), ("vanilla", "#efe2c4"), ("champagne", "#dcc7a1"), ("silver", "#c5cbd1"),
    ("black", "#26292d"), ("grey", "#7d858d"), ("gray", "#7d858d"), ("blue", "#2f5fa7"), ("green", "#3f7d55"), ("brown", "#7a4e2f"), ("coffee", "#5a3a26"),
    ("yellow", "#f1c232"), ("pink", "#e89ab1"), ("aqua", "#45b8c4"), ("white", "#f6f6f4"), ("gold", "#d1ad5b"), ("tan", "#b07a45"), ("caramel", "#a8692f"),
]


def luminance(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return .2126 * r + .7152 * g + .0722 * b


def colours_in(text):
    """'Coral and teal' -> ['#ee7b63', '#1f7a7a'], in the order the words appear. Prints get no colour."""
    t, found = (text or "").lower(), []
    if "print" in t:
        return []
    for word, hex_ in PALETTE:
        for m in re.finditer(r"\b%s\b" % re.escape(word), t):
            found.append((m.start(), hex_))
            t = t[:m.start()] + "#" * len(word) + t[m.end():]
    return [h for _, h in sorted(found)]


def paint(colour):
    """CSS that paints the body in the listed colour, in light and dark mode alike: it is the product's real colour."""
    cols = colours_in(colour)
    if not cols:
        return "", None
    main = cols[0]
    dark = luminance(main) < .3
    shade = mix(main, "#ffffff", .84) if dark else mix(main, "#000000", .84)
    line = mix(main, "#ffffff", .42) if dark else mix(main, "#000000", .5)
    accent = cols[1] if len(cols) > 1 else None
    css = (".f{fill:%s}.s{fill:%s}.a{fill:%s}.k{stroke:%s}.fs{stroke:%s}.ks{stroke:%s}.ka{stroke:%s}"
           % (main, shade, accent or shade, line, main, shade, accent or shade))
    return css, accent


# ---------- drawing helpers ----------

def R(x, y, w, h, rx=0, cls="f k", sw=2, more=""):
    return '<rect x="%s" y="%s" width="%s" height="%s"%s class="%s" stroke-width="%s"%s/>' % (
        n(x), n(y), n(max(w, 0)), n(max(h, 0)), ' rx="%s"' % n(rx) if rx else "", cls, n(sw), more)


def L(x1, y1, x2, y2, cls="k", sw=2, more=""):
    return '<line x1="%s" y1="%s" x2="%s" y2="%s" class="%s" stroke-width="%s"%s/>' % (n(x1), n(y1), n(x2), n(y2), cls, n(sw), more)


def C(cx, cy, r, cls="p", sw=0, more=""):
    return '<circle cx="%s" cy="%s" r="%s" class="%s"%s%s/>' % (n(cx), n(cy), n(r), cls, ' stroke-width="%s"' % n(sw) if sw else "", more)


def P(d, cls="f k", sw=2, more=""):
    return '<path d="%s" class="%s" stroke-width="%s"%s/>' % (d, cls, n(sw), more)


def T(x, y, words, cls="t", size=15, anchor="middle", weight=400):
    return '<text x="%s" y="%s" class="%s" font-size="%s"%s text-anchor="%s">%s</text>' % (
        n(x), n(y), cls, n(size), ' font-weight="%d"' % weight if weight != 400 else "", anchor, e(words))


def label(x, y, value, word, anchor="middle"):
    return ('<text x="%s" y="%s" font-size="15" text-anchor="%s"><tspan class="dt" font-weight="700">%s</tspan>'
            '<tspan class="m" font-size="13"> %s</tspan></text>' % (n(x), n(y), anchor, e(value), e(word)))


def dim_h(x1, x2, y, value, word, above=False):
    arrows = ' marker-start="url(#a)" marker-end="url(#a)"' if x2 - x1 > 26 else ""
    return (L(x1, y - 7, x1, y + 7, "d", 1.2) + L(x2, y - 7, x2, y + 7, "d", 1.2)
            + L(x1 + 1, y, x2 - 1, y, "d", 1.8, arrows)
            + label((x1 + x2) / 2, y - 12 if above else y + 22, value, word))


def dim_v(x, y1, y2, value, word, side="left"):
    arrows = ' marker-start="url(#a)" marker-end="url(#a)"' if y2 - y1 > 26 else ""
    tx, anchor = (x - 9, "end") if side == "left" else (x + 9, "start")
    mid = (y1 + y2) / 2
    return (L(x - 7, y1, x + 7, y1, "d", 1.2) + L(x - 7, y2, x + 7, y2, "d", 1.2)
            + L(x, y1 + 1, x, y2 - 1, "d", 1.8, arrows)
            + T(tx, mid + 1, value, "dt", 15, anchor, 700) + T(tx, mid + 18, word, "m", 13, anchor))


def bottom_info(main, sub="", y=300):
    """One bold line and one muted line under drawings that have no measurements."""
    out = T(W / 2, y, main, "t", 16, "middle", 700) if main else ""
    if sub:
        out += T(W / 2, y + 22 if main else y, sub, "m", 13.5)
    return out


def wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    return lines + [line] if line else lines


# ---------- facts from the listing ----------

def parse_dims(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)", text or "")
    return [float(x) for x in m.groups()] if m else None


def first_cm(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*cm\b", text or "")
    return float(m.group(1)) if m else None


def lead_amount(text, units):
    """'82 L (one listing field...)' -> '82 L'; only when the value starts the text."""
    m = re.match(r"\s*(?:About\s+)?(\d+(?:\.\d+)?)\s*(%s)\b" % units, text or "", re.I)
    return "%s %s" % (m.group(1), m.group(2)) if m else None


def ndims(dims):
    return " × ".join(n(x) for x in dims)


def bag_info(sp, dims=None):
    cap = lead_amount(sp.get("Capacity"), "L")
    weight = lead_amount(sp.get("Weight"), "kg|g")
    first = " · ".join(x for x in (cap, weight) if x)
    return [(first, "t", 16, 700), ("%s cm in total" % n(sum(dims)), "m", 13, 400) if dims else None]


# ---------- bags seen from the front and the side ----------

def box_sides(bag, limit):
    """Match the limit's sides to the bag's, largest to largest, as the fit check does."""
    order = sorted(range(3), key=lambda i: -bag[i])
    lim = sorted(limit, reverse=True)
    out = [0, 0, 0]
    for rank, i in enumerate(order):
        out[i] = lim[rank]
    return out


def two_views(s, hcm, wcm, dcm, front, side, box=None, words=("high", "wide", "deep")):
    """Front view (w x h) and side view (d x h) standing on the floor, at s px per cm."""
    h, w, dp = hcm * s, wcm * s, dcm * s
    bh, bw, bd = [x * s for x in box] if box else (0, 0, 0)
    fw, sw = max(w, bw), max(dp, bd)
    left = (W - (84 + fw + 40 + sw)) / 2 + 84
    fcx, scx = left + fw / 2, left + fw + 40 + sw / 2
    out = L(left - 24, FLOOR, scx + sw / 2 + 16, FLOOR, "k", 1.2, ' opacity=".3"')
    out += front(fcx, w, h) + side(scx, dp, h)
    if box:
        out += R(fcx - bw / 2, FLOOR - bh, bw, bh, 0, "l", 2, DASH) + R(scx - bd / 2, FLOOR - bh, bd, bh, 0, "l", 2, DASH)
    out += dim_v(left - 14, FLOOR - h, FLOOR, n(hcm) + " cm", words[0])
    out += dim_h(fcx - w / 2, fcx + w / 2, FLOOR + 16, n(wcm) + " cm", words[1])
    out += dim_h(scx - dp / 2, scx + dp / 2, FLOOR + 16, n(dcm) + " cm", words[2])
    return out


def bag_parts(d):
    """The parts a luggage or backpack listing names, from its specs and highlights."""
    sp = d.get("specs", {})
    text = " ".join([d["title"]] + d.get("highlights", []) + ["%s %s" % kv for kv in sp.items()]).lower()
    lock_text = (sp.get("Lock") or "").lower() + " " + " ".join(h.lower() for h in d.get("highlights", []) if "lock" in h.lower())
    lock = None if "none" in (sp.get("Lock") or "").lower() else (
        "tsa" if "tsa" in lock_text else "combo" if "combination" in lock_text or "lock" in lock_text else None)
    m = re.search(r"\b(\d)\s+(?:\w+\s+){0,2}compartments\b", text)
    comps = int(sp["Compartments"]) if (sp.get("Compartments") or "").isdigit() else int(m.group(1)) if m else 1
    return dict(lock=lock, laptop="laptop" in text and d["category"] == "luggage", usb="usb" in text,
                comps=max(1, min(comps, 3)), sleeve="trolley sleeve" in text or "luggage sleeve" in text
                or "luggage strap" in text, strap="shoulder strap" in text, bottle="bottle" in text)


def lock_box(x, y, kind):
    """A small lock with three number wheels; a TSA lock also has a keyhole."""
    out = R(x, y, 26, 16, 3.5, "p", 0)
    out += "".join(R(x + 4 + i * 6.4, y + 4, 4.6, 8, 1.2, "", 0, ' fill="#dfe3e7"') for i in range(3))
    if kind == "tsa":
        out += C(x + 31, y + 8, 4.2, "p") + C(x + 31, y + 8, 1.4, "", 0, ' fill="#dfe3e7"')
    return out


def trolley_front(hard=True, eight=True, parts=None, two=False):
    parts = parts or {}

    def draw(cx, w, h):
        x, top, wr = cx - w / 2, FLOOR - h, 4.6
        bt, bb = top + 13, FLOOR - 2 * wr - 1.5
        out = L(cx - w * .2, top + 6, cx - w * .2, bt + 2, "pk", 3) + L(cx + w * .2, top + 6, cx + w * .2, bt + 2, "pk", 3)
        out += R(cx - w * .27, top, w * .54, 8, 4, "a" if two else "p", 0)
        for xc in (x + 12, x + w - 12):
            out += R(xc - 9, bb - 3, 18, 6, 2, "p", 0)
            out += (C(xc - 4.2, FLOOR - wr, wr) + C(xc + 4.2, FLOOR - wr, wr)) if eight else C(xc, FLOOR - wr, wr + .8)
        out += R(x, bt, w, bb - bt, min(12, w * .1))
        if hard:
            ribs = (.3, .5, .7)
            out += "".join(L(x + w * f, bt + 14, x + w * f, bb - 14, "ka", 4) if two else
                           L(x + w * f, bt + 14, x + w * f, bb - 14, "k", 2.2, ' opacity=".35"') for f in ribs)
        else:
            ph = (bb - bt) * .55
            out += R(x + w * .14, bb - ph - 12, w * .72, ph, 8, "a k", 1.5)
        if parts.get("laptop") and w > 60:
            py, ph = bt + 32, (bb - bt) * .38
            out += (R(x + w * .1, py, w * .8, ph, 8, "a k", 1.6)
                    + L(x + w * .1 + 9, py + 8, x + w * .9 - 9, py + 8, "k", 1.3, ' stroke-dasharray="3 3"'))
        if parts.get("lock") and w > 60:
            out += lock_box(x + w - (44 if parts["lock"] == "tsa" else 36), bt + 9, parts["lock"])
        return out
    return draw


def trolley_side(eight=True, parts=None):
    parts = parts or {}

    def draw(cx, dp, h):
        x, top, wr = cx - dp / 2, FLOOR - h, 4.6
        bt, bb = top + 13, FLOOR - 2 * wr - 1.5
        out = L(x + dp - 5, top + 4, x + dp - 5, bt + 2, "pk", 3) + R(x + dp - 11, top, 14, 7, 3, "p", 0)
        out += C(x + 9, FLOOR - wr, wr) + C(x + dp - 9, FLOOR - wr, wr)
        out += R(x, bt, dp, bb - bt, min(10, dp * .18), "s k")
        out += R(cx - 3, bt + (bb - bt) * .36, 6, (bb - bt) * .22, 3, "p", 0)
        if parts.get("usb"):
            out += R(cx - 4, bt + (bb - bt) * .2, 8, 5, 1.5, "p", 0)
        return out
    return draw


def duffle_front(strap=False):
    def draw(cx, w, h):
        x, top = cx - w / 2, FLOOR - h
        b, c = top + 6, top - h * .55
        peak = b + .75 * (c - b)
        rx = min(h * .32, 24)
        long_strap = (P(D("M%s %s C%s %s %s %s %s %s", x + 9, top + 13, x + w * .08, top - h * .95, x + w * .92, top - h * .95,
                          x + w - 9, top + 13), "pk", 2.5, ' opacity=".7"') if strap else "")
        return (long_strap
                + P(D("M%s %s C%s %s %s %s %s %s", cx - w * .17, b, cx - w * .17, c, cx + w * .17, c, cx + w * .17, b), "pk", 5)
                + R(cx - 13, peak - 4.5, 26, 9, 4, "p", 0)
                + R(x, top, w, h, rx)
                + L(x + rx * .8, top + 8, x + w - rx * .8, top + 8, "k", 1.5, ' stroke-dasharray="3 3"')
                + R(x + w * .22, top + h * .42, w * .56, h * .4, 6, "a k", 1.5)
                + C(x + 9, top + 13, 3) + C(x + w - 9, top + 13, 3))
    return draw


def duffle_side(cx, dp, h):
    return R(cx - dp / 2, FLOOR - h, dp, h, min(dp, h) * .3, "s k") + C(cx, FLOOR - h + 11, 3.5)


def pack_front(comps=1):
    def draw(cx, w, h):
        x, top = cx - w / 2, FLOOR - h
        bt, r = top + 11, min(w * .36, 44)
        body = D("M%s %s H%s Q%s %s %s %s V%s Q%s %s %s %s H%s Q%s %s %s %s V%s Q%s %s %s %sZ",
                 x + 12, FLOOR, x + w - 12, x + w, FLOOR, x + w, FLOOR - 12, bt + r, x + w, bt, x + w - r, bt,
                 x + r, x, bt, x, bt + r, FLOOR - 12, x, FLOOR, x + 12, FLOOR)
        zips = ""
        for i in range(comps):
            # One zip per compartment, each a little lower and further in than the one behind it.
            k, rr = 8 + i * 10, max(r - i * 10, 10)
            zips += P(D("M%s %s V%s Q%s %s %s %s H%s Q%s %s %s %s V%s", x + k, bt + h * .42, bt + rr + i * 8, x + k, bt + k,
                        x + k + rr, bt + k, x + w - k - rr, x + w - k, bt + k, x + w - k, bt + rr + i * 8, bt + h * .42),
                      "k", 1.4, ' stroke-dasharray="3 3"')
        py = top + h * .55
        return (P(D("M%s %s C%s %s %s %s %s %s", cx - 11, bt + 3, cx - 11, top - 3, cx + 11, top - 3, cx + 11, bt + 3), "pk", 4)
                + P(body) + zips
                + R(x + w * .16, py, w * .68, h * .34, 10, "a k", 1.8)
                + L(x + w * .16 + 10, py + 9, x + w * .84 - 10, py + 9, "k", 1.3, ' stroke-dasharray="3 3"'))
    return draw


def pack_side(sleeve=False):
    def draw(cx, dp, h):
        x, top = cx - dp / 2, FLOOR - h
        bt = top + 11
        body = D("M%s %s H%s Q%s %s %s %s V%s Q%s %s %s %s H%s Q%s %s %s %s V%s Q%s %s %s %sZ",
                 x + 8, FLOOR, x + dp - 6, x + dp, FLOOR, x + dp, FLOOR - 6, bt + 8, x + dp, bt, x + dp - 8, bt,
                 x + dp * .55, x, bt, x, bt + dp * .5, FLOOR - 8, x, FLOOR, x + 8, FLOOR)
        out = P(body, "s k") + R(x + 2, top + h * .6, dp * .5, h * .3, 5, "a k", 1.5)
        if sleeve:
            # The strap on the back that slides over a trolley handle.
            out += R(x + dp - 4, top + h * .42, 7, h * .2, 2, "p", 0)
        return out + P(D("M%s %s C%s %s %s %s %s %s", x + dp - 1, bt + 12, x + dp + 10, bt + h * .3, x + dp + 10, bt + h * .6,
                         x + dp - 1, FLOOR - h * .14), "pk", 5)
    return draw


def strap_loop(x1, x2, y, peak=48):
    return P(D("M%s %s Q%s %s %s %s", x1, y, (x1 + x2) / 2, 2 * peak - y, x2, y), "pk", 4)


def handbag_front(style_):
    def draw(cx, w, h):
        x, top = cx - w / 2, FLOOR - h
        if style_ == "tote":
            return (P(D("M%s %s C%s %s %s %s %s %s", x + w * .24, top + 2, x + w * .24, top - h * .72, x + w * .76, top - h * .72,
                        x + w * .76, top + 2), "pk", 5, ' opacity=".45"')
                    + R(x, top, w, h, 6)
                    + P(D("M%s %s C%s %s %s %s %s %s", x + w * .3, top + 12, x + w * .3, top - h * .58, x + w * .7, top - h * .58,
                          x + w * .7, top + 12), "pk", 5)
                    + R(x + w * .3 - 5, top + 8, 10, 12, 2, "p", 0) + R(x + w * .7 - 5, top + 8, 10, 12, 2, "p", 0))
        if style_ == "satchel":
            return (P(D("M%s %s C%s %s %s %s %s %s", x + w * .34, top + 4, x + w * .34, top - h * .42, x + w * .66, top - h * .42,
                        x + w * .66, top + 4), "pk", 6)
                    + R(x, top, w, h, 14)
                    + L(x + 14, top + 10, x + w - 14, top + 10, "k", 1.4, ' stroke-dasharray="3 3"')
                    + L(x + 10, top + h * .36, x + w - 10, top + h * .36, "k", 1.2, ' opacity=".5"')
                    + C(x + 8, top + 8, 3) + C(x + w - 8, top + 8, 3))
        if style_ == "crescent":
            shape = D("M%s %s Q%s %s %s %s C%s %s %s %s %s %s C%s %s %s %s %s %sZ", x, top + h * .22, cx, top - h * .06,
                      x + w, top + h * .22, x + w, top + h * .95, x + w * .7, FLOOR, cx, FLOOR, x + w * .3, FLOOR, x, top + h * .95,
                      x, top + h * .22)
            return (strap_loop(x + 4, x + w - 4, top + h * .22) + P(shape)
                    + P(D("M%s %s Q%s %s %s %s", x + 12, top + h * .3, cx, top + h * .06, x + w - 12, top + h * .3), "k", 1.4,
                        ' stroke-dasharray="3 3"'))
        if style_ == "flap":
            flap = D("M%s %s H%s V%s Q%s %s %s %s H%s Q%s %s %s %sZ", x, top, x + w, top + h * .5, x + w, top + h * .58,
                     x + w - 12, top + h * .58, x + 12, x, top + h * .58, x, top + h * .5)
            return (strap_loop(x + 8, x + w - 8, top + 6) + R(x, top, w, h, 8) + P(flap, "a k")
                    + C(cx, top + h * .5, 4.5))
        # sling or crossbody
        return (strap_loop(x + 10, x + w - 10, top + 6) + R(x, top, w, h, min(w, h) * .18)
                + L(x + 12, top + 12, x + w - 12, top + 12, "k", 1.4, ' stroke-dasharray="3 3"')
                + R(x + w * .14, top + h * .45, w * .72, h * .42, 6, "a k", 1.5))
    return draw


def handbag_side(cx, dp, h):
    return R(cx - dp / 2, FLOOR - h, dp, h, min(dp / 2, 8), "s k")


def trolley_alone(cx, hcm, wcm, hard, eight, s, parts=None, two=False):
    return trolley_front(hard, eight, parts, two)(cx, wcm * s, hcm * s)


def size_word(hcm):
    return "cabin" if hcm <= 56 else ("medium" if hcm <= 70 else "large")


def draw_luggage(d, limit):
    sp, title = d.get("specs", {}), d["title"]
    tl = title.lower()
    dims = parse_dims(sp.get("Size"))
    shell = ((sp.get("Shell") or "") + " " + (sp.get("Material") or "")).lower()
    hard = "soft" not in shell and "leatherette" not in shell and not ("polyester" in shell and "hard" not in shell)
    wheels = (sp.get("Wheels") or "").lower() + " " + tl
    eight = not ("4 spinner" in wheels or "4 wheel" in wheels)  # most trolleys have 8 spinner wheels
    parts, two = bag_parts(d), len(colours_in(d.get("colour"))) > 1
    if "duffle" in tl or "weekender" in tl:
        if not dims:
            return generic(d, "a duffle bag")
        s = SCALE["duffle"]
        box = box_sides(dims, limit) if sum(dims) <= 130 else None
        # Duffles are listed length x height x depth; the box is drawn lying down, matched largest to largest.
        inner = two_views(s, dims[1], dims[0], dims[2], duffle_front(parts["strap"]), duffle_side,
                          box and [box[1], box[0], box[2]], ("high", "long", "deep"))
        alt = "Drawing of a soft duffle bag, front and end views, drawn to its listed size of %s cm" % ndims(dims)
        return dict(inner=inner, legend=bool(box), info=bag_info(sp, dims), scaled=True,
                    alt=alt + (", with IndiGo's %s cm cabin limit as a dashed box" % ndims(limit) if box else ""))
    s = SCALE["trolley"]
    if "set of" in tl:
        if "set of 3" in tl:
            heights = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)", re.search(r"\(([^)]*)\)", title).group(1))]
            big = dims or [heights[-1], heights[-1] * .72, 30]
            bags = [(h, big[1] * h / big[0], size_word(h).capitalize(), "%s cm" % n(h)) for h in heights]
            # Without a listed size the widths are only a guess for the drawing, so the label never shows them.
            info = [("Large bag %s cm" % ndims(big) if dims else "Large bag %s cm high" % n(heights[-1]), "t", 15, 700), ("Set of 3", "m", 13, 400)]
            alt = "Drawing of a set of three hard trolleys, %s cm high, drawn to scale" % ", ".join(n(h) for h in heights)
        else:
            bags = [(55, dims[1] * 55 / dims[0], "Cabin", "size not listed"), (dims[0], dims[1], "Medium", "%s cm" % n(dims[0]))]
            info = [("Medium %s cm" % ndims(dims), "t", 15, 700), ("Set of 2", "m", 13, 400)]
            alt = "Drawing of a set of two hard trolleys, cabin and medium; the medium is drawn to its listed size of %s cm" % ndims(dims)
        gap = 26
        total = sum(w * s for h, w, _, _ in bags) + gap * (len(bags) - 1)
        x = (W - total) / 2
        inner = L(x - 20, FLOOR, x + total + 20, FLOOR, "k", 1.2, ' opacity=".3"')
        for h, w, name, size in bags:
            cx = x + w * s / 2
            inner += trolley_alone(cx, h, w, hard, eight, s, parts, two)
            inner += T(cx, FLOOR + 24, size, "dt" if "cm" in size else "m", 15 if "cm" in size else 13, "middle", 700 if "cm" in size else 400)
            inner += T(cx, FLOOR + 42, name, "m", 13)
            x += w * s + gap
        return dict(inner=inner, legend=False, info=info, scaled=True, alt=alt)
    if not dims:
        hcm = first_cm(sp.get("Size")) or first_cm(title)
        if not hcm:
            return generic(d, "a trolley bag")
        wcm = hcm * .66
        cx = W / 2 + 30
        inner = (L(cx - 90, FLOOR, cx + 90, FLOOR, "k", 1.2, ' opacity=".3"') + trolley_alone(cx, hcm, wcm, hard, eight, s, parts, two)
                 + dim_v(cx - wcm * s / 2 - 14, FLOOR - hcm * s, FLOOR, n(hcm) + " cm", "high")
                 + T(cx, FLOOR + 26, "Width and depth not listed", "m", 13))
        return dict(inner=inner, legend=False, info=bag_info(sp), scaled=True,
                    alt="Drawing of a hard %s trolley, %s cm high (width and depth not listed)" % (size_word(hcm), n(hcm)))
    if dims[0] != max(dims):
        dims = sorted(dims, reverse=True)  # listed as width x depth x height: stand it up
    box = box_sides(dims, limit) if sum(dims) <= 130 else None
    inner = two_views(s, dims[0], dims[1], dims[2], trolley_front(hard, eight, parts, two), trolley_side(eight, parts), box)
    alt = "Drawing of a %s %s trolley, front and side views, drawn to its listed size of %s cm" % (
        "hard" if hard else "soft", size_word(dims[0]), ndims(dims))
    return dict(inner=inner, legend=bool(box), info=bag_info(sp, dims), scaled=True,
                alt=alt + (", with IndiGo's %s cm cabin limit as a dashed box" % ndims(limit) if box else ""))


def draw_backpack(d, limit):
    sp = d.get("specs", {})
    dims = parse_dims(sp.get("Size"))
    s = SCALE["backpack"]
    parts = bag_parts(d)
    if not dims:
        # Size not listed: a typical shape, with no measurements.
        h, w = 44 * s, 30 * s
        inner = L(W / 2 - 110, FLOOR, W / 2 + 110, FLOOR, "k", 1.2, ' opacity=".3"') + pack_front(parts["comps"])(W / 2, w, h)
        inner += T(W / 2, FLOOR + 26, "Size not listed", "m", 13)
        return dict(inner=inner, legend=False, info=bag_info(sp), scaled=False, alt="Drawing of a backpack (size not listed)")
    box = box_sides(dims, limit)
    inner = two_views(s, dims[0], dims[1], dims[2], pack_front(parts["comps"]), pack_side(parts["sleeve"]), box)
    return dict(inner=inner, legend=True, info=bag_info(sp, dims), scaled=True,
                alt="Drawing of a backpack, front and side views, drawn to its listed size of %s cm, with IndiGo's %s cm "
                    "cabin limit as a dashed box" % (ndims(dims), ndims(limit)))


def draw_wallet(d):
    """A closed wallet seen from the front; a gift set adds the pen and keychain the listing names."""
    sp, tl = d.get("specs", {}), d["title"].lower()
    stitch = ' stroke-dasharray="4 3"'
    if "zip" in tl:
        out = (R(120, 100, 240, 140, 14) + R(131, 111, 218, 118, 9, "k", 1.4, ' stroke-dasharray="2 3" opacity=".7"')
               + R(348, 96, 12, 24, 4, "p", 0) + L(354, 120, 354, 132, "pk", 2))
        sub = sp.get("Sections") or ""
        return dict(inner=out + bottom_info("Zip-around wallet", ("Sections: " + sub) if sub else ""), legend=False, info=[],
                    scaled=False, alt="Simple drawing of a closed zip-around wallet")
    set_ = "pen" in tl and "keychain" in tl
    x0 = 92 if set_ else 155
    out = (R(x0, 112, 170, 132, 10) + R(x0, 112, 16, 132, 6, "s k", 1.5)
           + R(x0 + 24, 120, 138, 116, 7, "k", 1, stitch + ' opacity=".6"'))
    if set_:
        out += (R(300, 92, 14, 160, 7, "p", 0) + R(303, 86, 8, 36, 3, "s k", 1.2) + P("M300 252 L307 268 L314 252Z", "p", 0)
                + C(380, 112, 15, "k", 3) + R(366, 128, 28, 70, 7) + R(372, 136, 16, 54, 5, "k", 1, stitch + ' opacity=".6"'))
    size = parse_dims(sp.get("Size"))
    first = "Wallet, keychain and pen" if set_ else "Bi-fold wallet"
    second = "Wallet listed at %s × %s cm" % (n(size[0]), n(size[1])) if size else ""
    return dict(inner=out + bottom_info(first, second), legend=False, info=[], scaled=False,
                alt="Simple drawing of a closed bi-fold wallet" + (" with a pen and a keychain" if set_ else ""))


def draw_handbag(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    if "wallet" in tl:
        return draw_wallet(d)
    dims = parse_dims(sp.get("Size"))
    kind = ("tote" if "tote" in tl else "satchel" if "satchel" in tl else "crescent" if "crescent" in tl
            else "flap" if "flap" in tl or "messenger" in tl else "sling")
    names = {"tote": "tote bag", "satchel": "satchel bag", "crescent": "crescent crossbody bag", "flap": "flap sling bag",
             "sling": "sling bag"}
    if not dims:
        return generic(d, "a " + names[kind])
    # Listings give width x depth x height or similar: the smallest side is the depth.
    dp = min(dims)
    rest = list(dims)
    rest.remove(dp)
    wcm, hcm = rest
    inner = two_views(SCALE["bag"], hcm, wcm, dp, handbag_front(kind), handbag_side)
    info = [(" · ".join(x for x in (lead_amount(sp.get("Capacity"), "L"), lead_amount(sp.get("Weight"), "kg|g")) if x), "t", 16, 700)]
    return dict(inner=inner, legend=False, info=info, scaled=True,
                alt="Drawing of a %s, front and side views, drawn to its listed size of %s cm (%s wide, %s high, %s deep)"
                    % (names[kind], ndims(dims), n(wcm), n(hcm), n(dp)))


# ---------- watches ----------

STEEL, GOLD, ROSE = "#cfd5db", "#d4b062", "#dba692"


def watch_look(d):
    """Dial, case and strap from the title, highlights, listed colour and strap spec."""
    sp = d.get("specs", {})
    t = " ".join([d["title"], " ".join(d.get("highlights", [])), d.get("colour", "")]).lower()
    s = (sp.get("Strap") or "").lower()
    dial, dial_name = "#e6e9ed", ""
    for words, col, name in ((("mother of pearl",), "pearl", "mother of pearl dial"),
                             (("champagne dial",), "#e8d4a6", "champagne dial"),
                             (("white dial",), "#f7f6f2", "white dial"),
                             (("black dial", "black analog", "all-black"), "#202428", "black dial"),
                             (("blue dial",), "#24508f", "blue dial"),
                             (("silver dial", "silver-tone dial"), "#e3e7eb", "silver dial")):
        if any(w in t for w in words):
            dial, dial_name = col, name
            break
    sunray = "sunray" in t
    rose = "rose gold" in t
    gold_strap = ("gold-tone metal" in t or "gold strap" in t) and not rose
    case = (ROSE if rose and "two-tone" not in s else GOLD if "gold-tone case" in t or gold_strap
            else "#2b2f34" if "all-black case" in t else STEEL)
    if "leather" in s:
        tone = "brown" if "brown" in s + t else "tan" if "tan " in t + " " else "black"
        strap = ("leather", {"brown": "#7b4a2b", "tan": "#b07a45", "black": "#2a2623"}[tone])
        name = ("black " if tone == "black" and "black strap" in t else tone + " " if tone != "black" else "") + "leather strap"
    elif "polyurethane" in s:
        # A kids' PU strap in the colour the listing names, e.g. "Polyurethane (PU), blue".
        word = next((w for w, _ in PALETTE if re.search(r"\b%s\b" % w, s)), "")
        strap, name = ("rubber", dict(PALETTE).get(word, "#25292d")), (word + " " if word else "") + "PU strap"
    elif "silicone" in s or "rubber" in s:
        strap, name = ("rubber", "#25292d"), "black silicone strap" if "black" in t else "silicone strap"
    elif "two-tone" in s or "two-tone" in t:
        strap, name = ("bracelet", "#c6ccd2", ROSE if rose else "#d4b46a"), (
            "silver and rose gold strap" if rose else "two-tone steel strap")
    elif rose:
        strap, name = ("bracelet", ROSE, None), "rose gold strap"
    elif gold_strap:
        strap, name = ("bracelet", "#d8b766", None), "gold-tone strap"
    else:
        strap, name = ("bracelet", "#c6ccd2", None), "steel strap" if "steel" in s else "metal strap"
    extras = dict(date="date" in t, crystals="crystal" in s + t, sunray=sunray)
    case_name = {GOLD: "gold-tone case", ROSE: "", "#2b2f34": "black case"}.get(case, "")
    return dial, dial_name, strap, name, case, case_name, extras


def strap_band(cx, y, w, h, strap, top, crystals=False):
    kind = strap[0]
    if kind == "bracelet":
        out = R(cx - w / 2, y, w, h, 4, "", 0, ' fill="%s"' % strap[1])
        if strap[2]:
            out += R(cx - w * .17, y, w * .34, h, 0, "", 0, ' fill="%s"' % strap[2])
        line = mix(strap[1], "#000000", .62)
        out += "".join(L(cx - w / 2, yy, cx + w / 2, yy, "", 1.1, ' stroke="%s"' % line) for yy in
                       [y + 7 + i * 9 for i in range(int((h - 8) / 9))])
        if crystals:
            out += "".join(C(cx + dx, yy + 4.5, 1.6, "", 0, ' fill="#ffffff"') for yy in
                           [y + 7 + i * 9 for i in range(int((h - 8) / 9) - 1)] for dx in (-w * .22, w * .22))
        return out
    out = R(cx - w / 2, y, w, h, 7, "", 0, ' fill="%s"' % strap[1])
    if kind == "leather":
        out += R(cx - w / 2 + 3, y + 3, w - 6, h - 6, 5, "", 1, ' fill="none" stroke="#ffffff" stroke-opacity=".35" stroke-dasharray="2 3"')
    if top:
        out += R(cx - w / 2 - 3, y + 3, w + 6, 10, 2, "", 2.5, ' fill="none" stroke="#9aa3ac"')
    else:
        out += "".join(C(cx, y + h - 14 - i * 11, 2.2, "", 0, ' fill="#000" opacity=".45"') for i in range(3))
    return out


def dial_fill(dial, sunray, key):
    """A plain colour, or a gradient for mother of pearl and sunray dials. Returns (defs, fill)."""
    if dial == "pearl":
        return ('<defs><linearGradient id="%s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f8f1ea"/>'
                '<stop offset=".5" stop-color="#e8e4f1"/><stop offset="1" stop-color="#e3efec"/></linearGradient></defs>' % key,
                "url(#%s)" % key)
    if sunray:
        return ('<defs><radialGradient id="%s"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/>'
                '</radialGradient></defs>' % (key, mix(dial, "#ffffff", .55), mix(dial, "#000000", .82)), "url(#%s)" % key)
    return "", dial


def watch(cx, cy, mm, s, look, strap_mm=None, word="case", dim=True, label_text=None, case=None, key="g"):
    dial, _, strap, _, case_, _, extras = look
    case = case or case_
    r = mm * s / 2
    sw = (strap_mm or mm * .5) * s
    sl = 56 if s >= 4 else 48
    out = (strap_band(cx, cy - r - sl, sw, sl + r, strap, True, extras["crystals"])
           + strap_band(cx, cy, sw, r + sl, strap, False, extras["crystals"]))
    out += R(cx + r - 3, cy - 6, 9, 12, 2, "", 1, ' fill="%s" stroke="#5b6573"' % case)
    defs, fill = dial_fill(dial, extras["sunray"], key)
    face = "#efe9e4" if dial == "pearl" else dial
    out += defs + '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#4a5560" stroke-width="1.5"/>' % (n(cx), n(cy), n(r), case)
    out += '<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (n(cx), n(cy), n(r * .85), fill)
    tick = "#f1f3f5" if luminance(face) < .45 else "#1f2933"
    for i in range(12):
        if i == 3 and extras["date"]:
            continue
        a = math.radians(i * 30)
        inner = r * (.62 if i % 3 == 0 else .7)
        out += L(cx + inner * math.sin(a), cy - inner * math.cos(a), cx + r * .77 * math.sin(a), cy - r * .77 * math.cos(a),
                 "", 2.4 if i % 3 == 0 else 1.3, ' stroke="%s" stroke-linecap="round"' % tick)
    if extras["date"]:
        out += R(cx + r * .5, cy - r * .11, r * .26, r * .22, 1.5, "", 1, ' fill="#ffffff" stroke="#8d97a1"')
    out += L(cx, cy, cx - r * .4, cy - r * .23, "", 3, ' stroke="%s" stroke-linecap="round"' % tick)
    out += L(cx, cy, cx + r * .52, cy - r * .3, "", 2.2, ' stroke="%s" stroke-linecap="round"' % tick)
    out += C(cx, cy, 2.8, "", 0, ' fill="#c2410c"')
    x = cx + r + 22
    if dim:
        out += (L(cx + 4, cy - r, x + 6, cy - r, "d", 1, ' stroke-dasharray="3 3"')
                + L(cx + 4, cy + r, x + 6, cy + r, "d", 1, ' stroke-dasharray="3 3"')
                + L(x, cy - r + 1, x, cy + r - 1, "d", 1.8, ' marker-start="url(#a)" marker-end="url(#a)"')
                + T(x + 9, cy + 1, n(mm) + " mm", "dt", 15, "start", 700) + T(x + 9, cy + 18, word, "m", 13, "start"))
    elif label_text:
        out += T(x - 10, cy + 1, label_text[0], "m", 13, "start") + T(x - 10, cy + 18, label_text[1], "m", 13, "start")
    return out


def draw_watch(d):
    sp, title = d.get("specs", {}), d["title"]
    sizes = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", sp.get("Case size") or "")]
    strap_mm = re.search(r"(\d+(?:\.\d+)?)\s*mm", sp.get("Strap") or "")
    strap_mm = float(strap_mm.group(1)) if strap_mm else None
    look = watch_look(d)
    dial, dial_name, strap, strap_name, case, case_name, extras = look
    words = [x for x in (dial_name, case_name, strap_name, "date window" if extras["date"] else "") if x]
    look_text = ", ".join(words)
    info = [(x[0].upper() + x[1:], "m", 13, 400) for x in words[:3]]
    if "couple" in title.lower():
        s, cy = SCALE["watch-pair"], 172
        men = sizes[0] if sizes else None
        women = sizes[1] if len(sizes) > 1 else None
        rose = "rose gold" in title.lower()
        mw, ww = (men or 42) * s, (women or 32) * s
        start = (W - (mw + 96 + 10 + ww + 96)) / 2
        out = watch(start + mw / 2, cy, men or 42, s, look, word="men's", dim=bool(men), label_text=("Men's", "not listed"), key="g1")
        out += watch(start + mw + 106 + ww / 2, cy, women or 32, s, look, word="women's", dim=bool(women),
                     label_text=("Women's", "not listed"), case=ROSE if rose else None, key="g2")
        if men and women:
            sized = ", with %s mm and %s mm cases drawn to scale" % (n(men), n(women))
        elif men:
            sized = ", with the men's %s mm case drawn to scale (women's size not listed)" % n(men)
        else:
            sized = " (case sizes not listed)"
        alt = "Drawing of a pair of watches, men's and women's%s%s" % (sized, ", " + look_text if look_text else "")
        return dict(inner=out, legend=False, info=[], scaled=bool(sizes), alt=alt)
    s = SCALE["watch"]
    mm = sizes[0] if sizes else 40
    out = watch(W / 2 - 34, 176, mm, s, look, strap_mm=strap_mm, dim=bool(sizes), label_text=("Case size", "not listed"))
    alt = "Drawing of a watch%s%s" % (" with a %s mm case drawn to scale" % n(mm) if sizes else " (case size not listed)",
                                      ", " + look_text if look_text else "")
    if strap_mm:
        info.append(("%s mm strap" % n(strap_mm), "m", 13, 400))
    return dict(inner=out, legend=False, info=info, scaled=bool(sizes), alt=alt)


# ---------- shoes (side view, toe to the right) ----------

SOLE = "M8 114H298C301 124 294 130 282 130H22C12 130 6 124 8 114Z"
LOW = "M18 114C10 96 9 74 16 60C24 48 42 46 56 52C70 58 84 58 98 50L122 40C138 48 156 60 178 72C204 86 238 90 264 96C286 101 296 108 296 118H18Z"
BOOT = "M18 116C10 86 10 44 16 10C40 4 66 4 88 8C92 30 100 50 122 64C152 80 214 86 256 94C282 99 296 108 296 118H18Z"
MID = "M18 116C10 90 10 56 16 30C40 24 64 24 84 28C92 44 102 56 124 66C154 80 214 86 256 94C282 99 296 108 296 118H18Z"


def lugged_sole():
    pts = ["M6 114H298V124L292 132"]
    x, up = 278, True
    while x > 14:
        pts.append("L%d %d" % (x, 128 if up else 133))
        x, up = x - 13, not up
    return "".join(pts) + "L10 132L6 124Z"


def laces(x1, y1, x2, y2, count=5):
    out = ""
    for i in range(count):
        t = (i + .5) / count
        x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
        out += L(x - 6, y - 4, x + 6, y + 5, "k", 1.8) + L(x - 6, y + 5, x + 6, y - 4, "k", 1.8)
    return out


def draw_shoe(d):
    sp = d.get("specs", {})
    kind = (sp.get("Type") or "").lower()
    closure = (sp.get("Closure") or "").lower()
    ankle = (sp.get("Height") or "").lower() == "ankle"
    cols = colours_in(d.get("colour"))
    two = len(cols) > 1
    dots = ' fill="#ffffff" opacity=".4"' if cols and luminance(cols[0]) < .3 else ' fill="#000000" opacity=".25"'
    g = ""
    if "flip" in kind:
        sole = "M60 0C98 0 118 28 116 68C114 108 98 138 98 172C98 212 112 242 102 264C94 282 28 282 18 264C8 242 22 212 22 172C22 138 6 108 4 68C2 28 22 0 60 0Z"
        thong = "M50 50Q22 74 12 128M50 50Q86 72 108 126"
        one = P(sole, "f k") + P(thong, "k", 10) + P(thong, "ks", 6) + C(50, 50, 5)
        g = ('<g transform="translate(252 34) scale(.86)">%s</g><g transform="translate(228 34) scale(-.86 .86)">%s</g>' % (one, one))
        name = "flip-flops"
    elif "sandal" in kind:
        straps = ["M190 96C200 56 250 56 262 98", "M104 94C114 34 172 34 184 96", "M26 92C18 58 46 48 74 56L110 66"]
        g = (P("M10 104C6 96 14 92 32 92L268 96C290 96 298 104 296 112L292 124H16C8 124 6 112 10 104Z", "s k")
             + L(14, 101, 292, 103, "k", 1.2, ' opacity=".5"')
             + "".join(P(s_, "k", 13) + P(s_, "fs", 9) for s_ in straps)
             + R(134, 36, 20, 12, 3, "p", 0) + R(218, 58, 18, 11, 3, "p", 0))
        g = '<g transform="translate(52 108) scale(1.24)">%s</g>' % g
        name = "sandals"
    else:
        hiking, boot = "hiking" in kind, "boot" in kind
        upper = BOOT if boot else (MID if hiking and ankle else LOW)
        g = P(upper)
        if not boot and not (hiking and ankle):
            g += "".join(C(60 + c * 22, 84 + r_ * 10, 1.4, "", 0, dots) for r_ in range(3) for c in range(6)) if "mesh" in (sp.get("Material") or "").lower() else ""
        if two:
            # The second listed colour, as a band along the side.
            g += P("M40 100C96 90 170 92 246 104", "ka", 6)
        if "lace" in closure:
            g += (laces(90, 14, 120, 60) if boot else laces(86, 32, 122, 62) if hiking and ankle else laces(122, 44, 192, 78))
        else:
            g += P("M20 62C14 44 30 40 34 52", "pk", 3)
        if boot:
            g += P("M18 12C12 -2 26 -4 28 8", "pk", 3)
        if hiking:
            g += P("M244 96C266 100 286 106 296 118", "pk", 3)
        g += P(lugged_sole(), "p", 0) if hiking or boot else (P(SOLE, "a k" if two else "s k") + L(10, 121, 297, 121, "k", 1.2, ' opacity=".5"'))
        if not hiking and not boot:
            g += P("M238 92C258 98 276 106 288 116", "k", 1.4, ' opacity=".6"')
        g = '<g transform="translate(52 %d) scale(1.24)">%s</g>' % (100 if not boot else 104, g)
        name = "boots" if boot else ("hiking shoes" if hiking else "walking shoes")
    type_ = sp.get("Type") or name.capitalize()
    first = type_ + (" · " + closure if closure else "")
    material = ", ".join(x for x in (sp.get("Material"), (sp.get("Sole") + " sole") if sp.get("Sole") else None,
                                     "ankle height" if ankle else None) if x)
    return dict(inner=g + bottom_info(first, material), legend=False, info=[], scaled=False,
                alt="Simple drawing of %s%s" % (name, " with a %s closure" % closure if closure and "flip" not in kind else ""))


# ---------- clothing ----------

def draw_clothing(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    fabric = sp.get("Fabric") or ""
    fabric = "" if ";" in fabric else fabric  # the listing disagrees with itself: leave it to the specs table
    if "sunglasses" in tl:
        return draw_glasses(d)
    if "jacket" in tl:
        body = "M72 34L40 46L10 186L34 194L58 102L56 224H164L162 102L186 194L210 186L180 46L148 34Q110 54 72 34Z"
        g = P("M66 42C58 -4 162 -4 154 42Q110 26 66 42Z", "s k") + P(body)
        g += "".join(L(58, y, 162, y, "k", 1.2, ' opacity=".55"') for y in (80, 114, 148, 182))
        for y in (88, 120, 152):
            ox = 40 - (y - 46) * 30 / 140
            ix = 58 - max(y - 102, 0) * 24 / 92 if y >= 102 else 52
            g += L(ox + 3, y, ix - 3, y + 6, "k", 1.2, ' opacity=".55"') + L(217 - ox, y, 223 - ix, y + 6, "k", 1.2, ' opacity=".55"')
        g += L(110, 46, 110, 224, "k", 1.6) + L(70, 170, 80, 196, "k", 1.4) + L(150, 170, 140, 196, "k", 1.4)
        g = '<g transform="translate(130 50)">%s</g>' % g
        name = "a hooded quilted jacket" if "quilted" in tl else "a hooded puffer jacket"
        return dict(inner=g + bottom_info("Hooded jacket" if sp.get("Hood") == "Yes" else "Jacket", fabric), legend=False, info=[],
                    scaled=False, alt="Simple drawing of " + name)
    if "poncho" in tl:
        drop = "M0 -9C4 -3 6 1 6 4A6 6 0 0 1 -6 4C-6 1 -4 -3 0 -9Z"
        g = (P("M110 4C84 4 76 30 78 54L24 196Q110 232 196 196L142 54C144 30 136 4 110 4Z")
             + '<ellipse cx="110" cy="40" rx="20" ry="24" class="s k" stroke-width="2"/>'
             + L(100, 66, 98, 86, "pk", 1.6) + L(120, 66, 122, 86, "pk", 1.6)
             + "".join(C(110, y, 3) for y in (100, 130, 160, 190))
             + "".join('<path d="%s" fill="#9cc9e3" stroke="#5b8fb0" stroke-width="1.2" transform="translate(%d %d)"/>' % (drop, x, y)
                       for x, y in ((18, 70), (206, 60), (214, 120), (6, 132))))
        g = '<g transform="translate(130 52)">%s</g>' % g
        return dict(inner=g + bottom_info("Rain poncho with hood", sp.get("Size") or fabric), legend=False, info=[], scaled=False,
                    alt="Simple drawing of a hooded rain poncho")
    if "cap" in tl and "gloves" in tl:
        cap = ('<g transform="translate(100 206)">' + P("M-46 0C-46 -66 46 -66 46 0Z") + C(0, -62, 11, "s k", 2)
               + R(-50, -4, 100, 28, 7, "s k") + "".join(L(i * 10, 1, i * 10, 19, "k", 1, ' opacity=".45"') for i in range(-4, 5)) + "</g>")
        warmer = ('<g transform="translate(240 186)">' + P("M-42 -30V30A42 11 0 0 0 42 30V-30")
                  + "".join(L(i * 12, -16, i * 12, 36, "k", 1, ' opacity=".4"') for i in range(-3, 4))
                  + '<ellipse cx="0" cy="-30" rx="42" ry="11" class="s k" stroke-width="2"/></g>')
        glove = ('<g transform="translate(380 178)">' + "".join(R(-31 + i * 15.6, -64, 13, 50, 6.5) for i in range(4))
                 + R(-44, -10, 15, 42, 7.5, "f k", 2, ' transform="rotate(-32 -31 28)"') + R(-33, -28, 66, 66, 12)
                 + R(-35, 36, 70, 26, 6, "s k") + "</g>")
        items = [x.strip() for x in re.split(r",|\band\b", sp.get("Pack") or "Cap, neck warmer, gloves") if x.strip()]
        labels = "".join(T(x, 262, item.capitalize(), "t", 15, "middle", 700) for x, item in zip((100, 240, 380), items))
        return dict(inner=cap + warmer + glove + labels + bottom_info("", fabric), legend=False,
                    info=[], scaled=False, alt="Simple drawing of a winter cap, a neck warmer and a pair of gloves")
    # folded set or single folded garment
    parts = [x.strip() for x in re.split(r"\band\b", sp.get("Pack") or "") if x.strip()] or ["Top"]
    x0, w = 100, 220
    g = ""
    y = FLOOR - 4
    stack = []
    for i, part in enumerate(reversed(parts)):
        h = 58 if i == 0 and len(parts) > 1 else 64
        x = x0 + (8 if i else 0)
        ww = w - (16 if i else 0)
        top = y - h
        piece = R(x, top, ww, h, 8)
        if "top" in part.lower():
            piece += P(D("M%s %s Q%s %s %s %s", x + ww / 2 - 30, top, x + ww / 2, top + 26, x + ww / 2 + 30, top), "s k")
            piece += L(x + 22, top + 8, x + 62, top + h - 8, "k", 1.3, ' opacity=".5"') + L(x + ww - 22, top + 8, x + ww - 62, top + h - 8, "k", 1.3, ' opacity=".5"')
        else:
            piece += L(x + 4, top + 13, x + ww - 4, top + 13, "k", 1.4) + L(x + ww / 2, top + 13, x + ww / 2, top + h - 6, "k", 1.2, ' opacity=".5"')
        stack.append(piece + T(x + ww + 18, top + h / 2 + 5, part.capitalize(), "t", 15, "start", 700))
        y = top - 2
    g = "".join(stack)
    return dict(inner=g + bottom_info(sp.get("Pack") or "Folded", fabric, 304),
                legend=False, info=[], scaled=False, alt="Simple drawing of a folded thermal %s" % (" and ".join(p.lower() for p in parts)))


LENS_TINT = [("grey", "#4f565d"), ("green", "#3d5a40"), ("brown", "#6b4a2e"), ("blue", "#2f4f7a"), ("black", "#23272b")]


def lens_path(x, y, w, h, shape):
    """The left lens (outer side at x). The right lens is drawn as its mirror image."""
    if shape == "round":
        r = w / 2
        return '<circle cx="%s" cy="%s" r="%s"' % (n(x + r), n(y + h / 2), n(r))
    if shape == "pilot":
        d = D("M%s %s Q%s %s %s %s C%s %s %s %s %s %s C%s %s %s %s %s %sZ", x, y + 6, x + w / 2, y - 6, x + w, y + 6,
              x + w + 4, y + h * .62, x + w * .78, y + h, x + w * .5, y + h, x + w * .14, y + h, x - 6, y + h * .55, x, y + 6)
    elif shape == "cat":
        d = D("M%s %s Q%s %s %s %s C%s %s %s %s %s %s C%s %s %s %s %s %sZ", x + w, y + 10, x + w * .45, y, x - 8, y - 12,
              x, y + h * .62, x + w * .22, y + h, x + w * .55, y + h, x + w * .9, y + h, x + w, y + h * .6, x + w, y + 10)
    else:
        rx = 10 if shape == "wayfarer" else 18
        return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s"' % (n(x), n(y), n(w), n(h), rx)
    return '<path d="%s"' % d


def draw_glasses(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    m = re.search(r"(\d+)-(\d+)-(\d+)", sp.get("Size") or "")
    lens, bridge, arm = (float(x) for x in m.groups()) if m else (54, 18, 140)
    shape = ("round" if "round" in tl else "pilot" if "pilot" in tl or "aviator" in tl else "cat" if "cat-eye" in tl or "cateye" in tl
             else "wayfarer" if "wayfarer" in tl else "rect" if "rectangular" in tl or "sport" in tl else "square")
    s = SCALE["glasses"]
    lw, bw = lens * s, bridge * s
    lh = lw * {"round": 1.0, "pilot": .86, "cat": .7, "wayfarer": .72, "rect": .6}.get(shape, .78)
    total = 2 * lw + bw
    x0, y0 = (W - total) / 2, 168 - lh / 2
    colour = (d.get("colour") or "").lower()
    lens_words = colour.split("lens")[-1] + " " + (sp.get("Lens") or "").lower()
    if "lens" not in colour:
        lens_words += " " + colour
    lens_col = next((hx for word, hx in LENS_TINT if re.search(r"\b%s\b" % word, lens_words)), "#2c3742")
    frame_words = colour.split("lens")[0] if "frame" in colour else ""
    frame_col = (colours_in(frame_words) or ["#26292d"])[0]
    thick = 4 if shape in ("round", "pilot") else 7
    one = lens_path(x0, y0, lw, lh, shape) + ' style="fill:%s;fill-opacity:.85;stroke:%s" stroke-width="%d"/>' % (lens_col, frame_col, thick)
    out = one + '<g transform="matrix(-1 0 0 1 %d 0)">%s</g>' % (W, one)
    bar = '<path d="%s" style="fill:none;stroke:%s" stroke-width="%d" stroke-linecap="round"/>'
    out += bar % (D("M%s %s Q%s %s %s %s", x0 + lw, y0 + 14, W / 2, y0 - 2, x0 + lw + bw, y0 + 14), frame_col, 5)
    if shape == "pilot":
        out += bar % (D("M%s %s H%s", x0 + lw * .6, y0 - 1, x0 + lw + bw + lw * .4), frame_col, 3)
    out += ('<rect x="%s" y="%s" width="12" height="12" rx="3" style="fill:%s"/>' % (n(x0 - 10), n(y0 + 8), frame_col)
            + '<rect x="%s" y="%s" width="12" height="12" rx="3" style="fill:%s"/>' % (n(x0 + total - 2), n(y0 + 8), frame_col))
    out += dim_h(x0, x0 + lw, y0 - 22, n(lens) + " mm", "lens", above=True)
    out += dim_h(x0 + lw, x0 + lw + bw, y0 + lh + 20, n(bridge) + " mm", "bridge")
    lens_text = (sp.get("Lens") or "").split(",")[0].strip()
    info = [("Arms %s mm" % n(arm), "t", 15, 700)] if m else []
    first = " · ".join(x for x in ("Frame " + sp["Frame"] if sp.get("Frame") else None, lens_text + " lenses" if lens_text else None) if x)
    words = {"round": "round", "pilot": "aviator", "cat": "cat-eye", "wayfarer": "wayfarer", "rect": "rectangular"}.get(shape, "square")
    return dict(inner=out + bottom_info("", first, 318), legend=False, info=info, scaled=bool(m),
                alt="Drawing of %s sunglasses from the front, with %s mm lenses and a %s mm bridge drawn to scale" % (words, n(lens), n(bridge)))


# ---------- travel tech: adapters and power banks, drawn to their listed size ----------

def draw_tech(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    dims = sorted(parse_dims(sp.get("Size")) or [], reverse=True)
    weight = lead_amount(sp.get("Weight"), "kg|g") if sp.get("Weight") else ""
    if "power bank" in tl or "powerbank" in tl:
        s = 15.0
        lcm, wcm, tcm = dims if len(dims) == 3 else (14.0, 7.0, 1.5)
        w, h = lcm * s, wcm * s
        x, y = (W - w) / 2 - 30, 168 - h / 2
        out = (R(x, y, w, h, 14) + R(x + 12, y + 12, w - 24, h - 24, 9, "k", 1, ' opacity=".35"')
               + "".join(C(x + w - 22 - i * 12, y + h - 16, 3.2, "s") for i in range(4)))
        for i, port in enumerate(("c", "a")):
            py = y + h / 2 - 22 + i * 30
            out += R(x - 5, py, 10, 16 if port == "a" else 12, 3 if port == "c" else 1, "p", 0)
        if "cable" in tl:
            out += P(D("M%s %s C%s %s %s %s %s %s", x + w, y + 22, x + w + 46, y + 22, x + w + 46, y + h - 22, x + w + 2, y + h - 28), "pk", 5)
        side_x = x + w + 62
        out += R(side_x, y, tcm * s, h, 4, "s k", 1.5)
        out += dim_h(x, x + w, y + h + 22, n(lcm) + " cm", "long") + dim_v(x - 26, y, y + h, n(wcm) + " cm", "wide")
        out += label(side_x + tcm * s / 2, y + h + 26, n(tcm) + " cm", "thick")
        cap = re.match(r"\s*([\d,]+)\s*mAh", sp.get("Capacity") or "")
        cap = cap.group(1) + " mAh" if cap else ""
        wh = re.search(r"(\d+(?:\.\d+)?)\s*Wh", sp.get("Watt-hours") or "")
        info = [(cap, "t", 16, 700), ("about %s Wh" % wh.group(1) if wh else "", "m", 13, 400), (weight, "m", 13, 400)]
        return dict(inner=out, legend=False, info=info, scaled=True,
                    alt="Drawing of a power bank, top and side views, drawn to its listed size of %s cm" % ndims([lcm, wcm, tcm]))
    s = 22.0
    wcm, hcm = (dims[0], dims[1]) if len(dims) >= 2 else (6.0, 6.0)
    w, h = wcm * s, hcm * s
    x, y = (W - w) / 2, 168 - h / 2
    out = R(x, y, w, h, 16)
    # A universal socket face, and the USB ports the listing counts along the bottom edge.
    out += R(x + w * .2, y + h * .18, w * .6, h * .4, 10, "s k", 1.5)
    out += P(D("M%s %s V%s M%s %s V%s M%s %s H%s", x + w * .38, y + h * .26, y + h * .44, x + w * .62, y + h * .26, y + h * .44,
               x + w * .44, y + h * .5, x + w * .56), "pk", 4)
    ports = sp.get("USB ports") or ""
    cc = int((re.search(r"(\d+)\s*USB-C", ports) or [0, 0])[1])
    aa = int((re.search(r"(\d+)\s*USB-A", ports) or [0, 0])[1])
    slots = ["c"] * cc + ["a"] * aa
    for i, port in enumerate(slots):
        px = x + w / 2 - (len(slots) * 22) / 2 + i * 22 + 4
        out += R(px, y + h * .72, 14, 8 if port == "c" else 10, 4 if port == "c" else 1, "p", 0)
    out += R(x + w * .36, y + h, 6, 26, 2, "p", 0) + R(x + w * .58, y + h, 6, 26, 2, "p", 0)
    if "cable" in tl:
        out += P(D("M%s %s C%s %s %s %s %s %s", x + w, y + h * .3, x + w + 60, y + h * .3, x + w + 60, y + h * .9, x + w + 8, y + h * .95), "pk", 5)
    out += dim_h(x, x + w, y - 22, n(wcm) + " cm", "wide", above=True) + dim_v(x - 26, y, y + h, n(hcm) + " cm", "high")
    first = ("%d USB-C, %d USB-A" % (cc, aa)) if slots else "No USB ports"
    return dict(inner=out + bottom_info("", first + (" · " + weight if weight else ""), 330), legend=False, info=[], scaled=bool(dims),
                alt="Drawing of a universal travel adapter from the front, with its pull-out plug pins, drawn to its listed size")


# ---------- belts ----------

def draw_belt(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    wcm = first_cm(sp.get("Width") or "") or 3.5
    s = 16.0
    h = wcm * s
    x, y = 104, 160 - h / 2
    out = R(x + 46, y, 300, h, 6) + R(x + 52, y + 5, 288, h - 10, 4, "k", 1, ' stroke-dasharray="4 3" opacity=".5"')
    if "reversible" in tl:
        out += R(x + 240, y, 106, h, 6, "a k")
        out += T(x + 293, y + h + 22, "other side", "m", 12.5)
    out += "".join(C(x + 270 + i * 18, y + h / 2, 3.5, "p") for i in range(4) if "auto" not in tl and "reversible" not in tl)
    out += R(x, y - 12, 56, h + 24, 8, "pk", 6, ' style="fill:none"')
    if "auto" in tl or "reversible" in tl:
        out += R(x + 4, y - 8, 48, h + 16, 6, "p", 0)
    else:
        out += L(x + 28, y - 10, x + 28, y + h + 10, "pk", 4)
    out += dim_v(x - 18, y, y + h, n(wcm) + " cm", "wide")
    waist = sp.get("Waist") or ""
    return dict(inner=out + bottom_info("Belt", ("Fits waist " + waist) if waist else "", 262), legend=False, info=[], scaled=True,
                alt="Drawing of a belt with its buckle, with the strap width drawn to its listed size of %s cm" % n(wcm))


# ---------- skincare: tube, bottle or stick, sized by how much it holds ----------

def draw_skincare(d):
    sp = d.get("specs", {})
    kind = (sp.get("Type") or "").lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|g)\b", sp.get("Size") or "", re.I)
    amount = float(m.group(1)) if m else 50
    amount_text = "%s %s" % (n(amount), m.group(2).lower()) if m else ""
    hh = 228 * (amount / 100) ** (1 / 3)
    cx = 168
    if "lip" in kind:
        ws = max(hh * .3, 22)
        shape = (R(cx - ws / 2, FLOOR - hh * .62, ws, hh * .62, 4) + R(cx - ws / 2 - 1, FLOOR - hh, ws + 2, hh * .4, 5, "p", 0)
                 + L(cx - ws / 2, FLOOR - hh * .5, cx + ws / 2, FLOOR - hh * .5, "k", 1.2, ' opacity=".5"'))
        name = "stick"
    elif "body" in kind or "moistur" in kind or "lotion" in kind:
        wb = hh * .44
        body_h = hh * .78
        shape = (R(cx - wb * .26, FLOOR - body_h - hh * .06, wb * .52, hh * .08, 3, "s k")
                 + R(cx - wb * .32, FLOOR - hh, wb * .64, hh * .17, 6, "p", 0)
                 + R(cx - wb / 2, FLOOR - body_h, wb, body_h, wb * .22)
                 + L(cx - wb * .3, FLOOR - hh + hh * .06, cx + wb * .3, FLOOR - hh + hh * .06, "", 1.2, ' stroke="#ffffff" opacity=".5"'))
        name = "bottle"
    else:
        wt = hh * .38
        cap_h, crimp = hh * .15, hh * .08
        y0, y1 = FLOOR - cap_h, FLOOR - hh + crimp
        shape = (R(cx - wt * .3, y0, wt * .6, cap_h, 5, "p", 0)
                 + P(D("M%s %s L%s %s H%s L%s %sZ", cx - wt * .28, y0 + 1, cx - wt / 2, y1, cx + wt / 2, cx + wt * .28, y0 + 1))
                 + R(cx - wt / 2 - 1, FLOOR - hh, wt + 2, crimp + 1, 2, "s k", 2)
                 + "".join(L(cx - wt / 2 + i * wt / 7, FLOOR - hh + 2, cx - wt / 2 + i * wt / 7, y1 - 1, "k", 1, ' opacity=".45"')
                           for i in range(1, 7)))
        name = "tube"
    out = L(cx - 70, FLOOR, cx + 70, FLOOR, "k", 1.2, ' opacity=".3"') + shape
    tx = 262
    out += T(tx, 132, amount_text, "dt", 32, "start", 700)
    spf = " · ".join(x for x in ("SPF " + sp["SPF"] if sp.get("SPF") else None, sp.get("PA")) if x)
    y = 164
    for text, cls, size, weight in ((spf, "t", 16, 700), (sp.get("Type"), "m", 14, 400)):
        if text:
            out += T(tx, y, text, cls, size, "start", weight)
            y += 24
    if sp.get("Cabin bag"):
        out += T(tx, y + 4, "Cabin bag", "m", 13, "start")
        for line in wrap(sp["Cabin bag"], 24):
            out += T(tx, y + 23, line, "t", 14, "start", 700)
            y += 19
    return dict(inner=out, legend=False, info=[], scaled=False,
                alt="Simple drawing of a %s %s (%s)" % (amount_text, (sp.get("Type") or "skincare product").lower(), name))


# ---------- perfumes: spray bottles, sized by how much each one holds ----------

def draw_perfume(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    size = sp.get("Size") or ""
    m = re.search(r"(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*ml", size, re.I)
    count, ml = (int(m.group(1)), float(m.group(2))) if m else (1, float((re.search(r"(\d+(?:\.\d+)?)\s*ml", size, re.I) or [0, 50])[1]))
    count = max(1, min(count, 4))
    hh = 200 * (ml / 100) ** (1 / 3)
    pocket = "pocket" in tl
    bw = hh * (.6 if pocket else .5)
    gap = 12
    if count * bw + (count - 1) * gap > 200:
        bw = (200 - (count - 1) * gap) / count
    row = count * bw + (count - 1) * gap
    x0, cx0 = 140 - row / 2, 0
    out = L(40, FLOOR, 246, FLOOR, "k", 1.2, ' opacity=".3"')
    for i in range(count):
        x = x0 + i * (bw + gap)
        body_h = hh * .66
        y = FLOOR - body_h
        cx0 = x + bw / 2
        out += R(x, y, bw, body_h, 5 if pocket else bw * .16)
        out += R(x + 4, y + body_h * .3, bw - 8, body_h * .7 - 4, 3, "s", 0, ' style="fill:#b57fcf;fill-opacity:.7"')
        out += R(cx0 - bw * .14, y - hh * .07, bw * .28, hh * .07, 1.5, "p", 0)
        cap_w = bw * (.4 if pocket else .6)
        out += R(cx0 - cap_w / 2, FLOOR - hh, cap_w, hh * .27, 4, "s k", 1.6)
        out += L(x + 6, y + 8, x + 6, y + body_h * .5, "", 2, ' stroke="#ffffff" opacity=".6"')
    tx = 262
    amount = ("%d × %s ml" % (count, n(ml))) if count > 1 else "%s ml" % n(ml)
    out += T(tx, 120, amount, "dt", 30, "start", 700)
    y = 152
    for text, cls, fs, weight in ((sp.get("Type"), "t", 16, 700), (sp.get("For"), "m", 14, 400)):
        if text:
            for line in wrap(text, 24):
                out += T(tx, y, line, cls, fs, "start", weight)
                y += 22
    if sp.get("Cabin bag"):
        out += T(tx, y + 6, "Cabin bag", "m", 13, "start")
        y += 6
        for line in wrap(sp["Cabin bag"], 24):
            out += T(tx, y + 19, line, "t", 14, "start", 700)
            y += 19
    what = "pocket perfume spray" if pocket else "attar roll-on bottle" if "attar" in tl else "perfume bottle"
    words = {2: "two", 3: "three", 4: "four"}
    alt = ("Simple drawing of %s %s ml %ss" % (words[count], n(ml), what)) if count > 1 else "Simple drawing of a %s %s" % (amount, what)
    return dict(inner=out, legend=False, info=[], scaled=False, alt=alt)


# ---------- grooming: a trimmer and its click-on combs, from the listed run time and parts ----------

def draw_grooming(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    kind = (sp.get("Type") or "").lower()
    hybrid = "oneblade" in tl or "hybrid" in kind
    cx, top = 112, 64
    bw = 46
    # The handle: a rounded body that narrows a little towards the bottom.
    body = D("M%s %s H%s L%s %s Q%s %s %s %s H%s Q%s %s %s %s Z", cx - bw / 2, top + 30, cx + bw / 2, cx + bw / 2 - 5, FLOOR - 18,
             cx + bw / 2 - 5, FLOOR, cx + bw / 2 - 20, FLOOR, cx - bw / 2 + 20, cx - bw / 2 + 5, FLOOR, cx - bw / 2 + 5, FLOOR - 18)
    out = L(40, FLOOR, 246, FLOOR, "k", 1.2, ' opacity=".3"') + P(body)
    if hybrid:
        # A wide, flat blade across the top, as on a hybrid trimmer-shaver.
        out += R(cx - 38, top + 6, 76, 22, 8, "s k", 1.8) + L(cx - 30, top + 17, cx + 30, top + 17, "pk", 2.4)
    else:
        out += R(cx - 30, top + 6, 60, 24, 4, "s k", 1.8)
        out += "".join(L(cx - 26 + i * 6.5, top + 6, cx - 26 + i * 6.5, top + 14, "pk", 1.6) for i in range(9))
    out += C(cx, top + 92, 9, "s", 0) + C(cx, top + 92, 4.5, "p")
    out += R(cx - 4, top + 120, 8, 30, 4, "p", 0, ' opacity=".55"')
    # Combs or heads beside it: one small comb for each one the listing counts, up to six.
    att = sp.get("Attachments") or ""
    m = re.search(r"(\d+)\s*(?:-in-1|in 1|tools|attachments|magnetic|click-on|combs)", att + " " + tl, re.I)
    listed = int(m.group(1)) if m else (1 if "comb" in att.lower() else 0)
    count = max(0, min(listed, 6))
    for i in range(count):
        col, row = i % 2, i // 2
        x, y = 166 + col * 40, 118 + row * 50
        out += R(x, y, 30, 36, 5, "s k", 1.5)
        out += "".join(L(x + 5 + j * 5, y, x + 5 + j * 5, y + 9, "ks", 1.3) for j in range(5))
    tx = 262
    run = re.search(r"(\d+)\s*min", sp.get("Run time") or "")
    out += T(tx, 112, (run.group(1) + " min") if run else "Run time", "dt", 30, "start", 700)
    out += T(tx, 132, "run time (as listed)" if run else "not listed", "m", 13, "start")
    y = 162
    charge = sp.get("Charging") or ""
    port = "USB-C" if "type-c" in charge.lower() else "USB-A" if "usb-a" in charge.lower() else "USB" if "usb" in charge.lower() else ""
    wet = (sp.get("Wet or dry") or "").lower()
    lines = [(sp.get("Type"), "t", 15, 700)]
    if port:
        lines.append((port + " charging", "m", 14, 400))
    if wet.startswith("wet"):
        lines.append(("Wet and dry", "m", 14, 400))
    if (sp.get("Travel lock") or "").lower().startswith("yes"):
        lines.append(("Travel lock", "m", 14, 400))
    for text, cls, fs, weight in lines:
        if text:
            for line in wrap(text, 22):
                out += T(tx, y, line, cls, fs, "start", weight)
                y += 21
    what = "hybrid trimmer and shaver" if hybrid else "beard trimmer" if "beard" in kind else "trimmer"
    alt = "Simple drawing of a %s" % what + (" and %d of its %d listed tools" % (count, listed) if listed > count else " with %d click-on combs or heads" % count if count > 1 else "")
    return dict(inner=out, legend=False, info=[], scaled=False, alt=alt)


# ---------- books: a plain closed book, drawn to its listed size, with no cover art ----------

def draw_book(d):
    """A closed book in a three-quarter view: the front, the page edges and the top, sized from the listed
    dimensions (7 px per cm). The front is left blank: we never copy or imitate a cover."""
    sp = d.get("specs", {})
    dims = parse_dims(sp.get("Size")) or [13.0, 2.5, 19.8]
    wcm, tcm, hcm = dims[0], min(dims[1], dims[2]), max(dims[1], dims[2])  # Amazon lists width x thickness x height
    s = 7.0
    w, h, t = wcm * s, hcm * s, max(tcm * s, 4)
    dx, dy = t * .8, t * .5
    x, top = max(88, 160 - (w + dx) / 2), FLOOR - h  # room for the height label on the left
    kind = (sp.get("Type") or "").lower()
    hard = (sp.get("Format") or "").lower().startswith("hard")
    out = L(40, FLOOR, 300, FLOOR, "k", 1.2, ' opacity=".3"')
    # Page block (right side) and top, then the front.
    out += P(D("M%s %s L%s %s V%s L%s %sZ", x + w, top, x + w + dx, top - dy, FLOOR - dy, x + w, FLOOR), "f k", 1.6)
    lines = max(2, min(int(t / 3), 12))
    for i in range(1, lines):
        f = i / lines
        out += L(x + w + dx * f, top - dy * f + 3, x + w + dx * f, FLOOR - dy * f - 3, "k", .8, ' opacity=".35"')
    out += P(D("M%s %s L%s %s H%s L%s %sZ", x, top, x + dx, top - dy, x + w + dx, x + w, top), "s k", 1.6)
    out += R(x, top, w, h, 4 if hard else 2, "a k", 2)
    out += L(x + 8, top + 3, x + 8, FLOOR - 3, "k", 1.2, ' opacity=".45"')  # the spine fold
    if "journal" in kind:
        out += P(D("M%s %s V%s L%s %s L%s %s V%s", x + w * .7, top - 1, top + h * .32, x + w * .7 + 6, top + h * .28,
                   x + w * .7 + 12, top + h * .32, top - 1), "p", 0)  # a ribbon bookmark
    out += dim_v(x - 14, top, FLOOR, n(hcm) + " cm", "high") + dim_h(x, x + w, FLOOR + 16, n(wcm) + " cm", "wide")
    tx = 300
    pages = re.search(r"\d[\d,]*", sp.get("Pages") or "")
    out += T(tx, 112, pages.group(0) if pages else "Pages", "dt", 30, "start", 700)
    out += T(tx, 132, "pages (as listed)" if pages else "not listed", "m", 13, "start")
    y = 162
    for text, cls, fs, weight in ((sp.get("Type"), "t", 15, 700), (sp.get("Format"), "m", 14, 400), (sp.get("Language"), "m", 14, 400)):
        if text:
            for line in wrap(text, 20):
                out += T(tx, y, line, cls, fs, "start", weight)
                y += 21
    what = (sp.get("Format") or "book").lower()
    alt = ("Drawing of a closed %s %s with a blank front, drawn to its listed size of %s cm wide and %s cm high"
           % (what, (sp.get("Type") or "book").lower(), n(wcm), n(hcm)))
    return dict(inner=out, legend=False, info=[], scaled=True, alt=alt)


# ---------- travel gear ----------

def draw_travel(d):
    sp, tl = d.get("specs", {}), d["title"].lower()
    zip_ = ' stroke-dasharray="2 3"'
    if "toiletry" in tl:
        out = (R(110, 128, 260, 136, 22) + P("M116 150 Q240 128 364 150", "k", 1.4, zip_) + R(344, 136, 20, 12, 4, "p", 0)
               + P("M110 176 C84 176 84 226 110 226", "pk", 6) + L(132, 196, 348, 196, "k", 1, ' opacity=".3"'))
        hanging = "hanging" in tl
        if hanging:
            out = P("M240 128 V104 C240 84 266 84 266 100", "k", 3.5) + out
        bits = " · ".join(x for x in (sp.get("Size", "").replace(" (as listed)", "").replace(" x ", " × ") or None,
                                      sp.get("Weight")) if x)
        return dict(inner=out + bottom_info("Hanging toiletry bag" if hanging else "Toiletry bag", ("Listed at " + bits) if bits else ""),
                    legend=False, info=[], scaled=False,
                    alt="Simple drawing of a zipped toiletry bag with a side handle" + (" and a hanging hook" if hanging else ""))
    if "organiser" in tl or "organizer" in tl:
        out = (R(104, 104, 272, 156, 18) + R(114, 114, 252, 136, 12, "k", 1.4, zip_ + ' opacity=".7"')
               + R(364, 110, 12, 22, 4, "p", 0) + P("M104 150 C80 150 80 214 104 214", "pk", 6)
               + L(240, 104, 240, 260, "k", 1, ' opacity=".25"'))
        shell = (sp.get("Shell") or "").lower()
        hard, double = shell.startswith("hard"), "double" in shell or "double layer" in tl
        if hard:
            out += P("M112 182 Q240 172 368 182", "k", 1.2, ' opacity=".45"')
        if double:
            out += R(114, 182, 252, 3, 1.5, "s", 0)
        second = " · ".join(x for x in (("%s dividers" % sp["Dividers"].split(",")[0]) if sp.get("Dividers") else None,
                                        sp.get("Pockets")) if x)
        first = "Hard-shell gadget organiser" if hard else "Double-layer gadget organiser" if double else "Gadget organiser"
        kind = "hard-shell" if hard else "double-layer" if double else "padded" if "padd" in (sp.get("Material") or "").lower() else "soft"
        return dict(inner=out + bottom_info(first, second), legend=False, info=[], scaled=False,
                    alt="Simple drawing of a closed, %s gadget organiser case with a hand strap" % kind)
    if "bottle" in tl:
        s, cx = 8.4, 240
        size = re.findall(r"(\d+(?:\.\d+)?)\s*cm", sp.get("Size", ""))
        wcm, hcm = (float(size[0]), float(size[1])) if len(size) >= 2 else (7.0, 25.0)
        w, h = wcm * s, hcm * s
        top, lid = FLOOR - h, 34
        out = (L(150, FLOOR, 330, FLOOR, "k", 1.2, ' opacity=".3"')
               + R(cx - w / 2, top + lid - 4, w, h - lid + 4, 12) + R(cx - w / 2 + 6, top + lid + 14, w - 12, 3, 1.5, "s", 0)
               + R(cx - w / 2 + 4, top, w - 8, lid, 9, "p", 0) + R(cx + w / 2 - 14, top + 8, 6, 14, 3, "s", 0)
               + dim_v(cx - w / 2 - 26, top, FLOOR, n(hcm) + " cm", "high")
               + dim_h(cx - w / 2, cx + w / 2, FLOOR + 16, n(wcm) + " cm", "wide"))
        cap = sp.get("Capacity")
        return dict(inner=out, legend=False, info=[(cap, "t", 16, 700)] if cap else [], scaled=True,
                    alt="Drawing of a steel bottle with a flip lid, drawn to its listed size of %s cm wide and %s cm high" % (n(wcm), n(hcm)))
    if "passport" in tl:
        dims = parse_dims(sp.get("Size")) or [14.1, 10.4, 2.1]
        hcm, wcm = sorted(dims, reverse=True)[:2]
        s, cx = min(12.0, 200 / hcm), 228
        w, h = wcm * s, hcm * s
        x, top = cx - w / 2, FLOOR - h
        zipped = "zip" in (sp.get("Closure") or "").lower()
        out = (R(x + 18, top - 22, w - 44, 40, 3, "s k", 1.2) + R(x, top, w, h, 10)
               + R(x + 9, top + 9, w - 18, h - 18, 6, "k", 1, ' stroke-dasharray="4 3" opacity=".6"')
               + ("" if zipped else R(x + w - 10, top + h / 2 - 22, 26, 44, 6, "s k", 1.5) + C(x + w + 3, top + h / 2, 4))
               + ("" if zipped else C(x + 10, top - 4, 9, "k", 2.5))
               + dim_v(x - 18, top, FLOOR, n(hcm) + " cm", "high") + dim_h(x, x + w, FLOOR + 16, n(wcm) + " cm", "wide"))
        info = [(lead_amount(sp.get("Weight"), "kg|g"), "t", 16, 700)] if sp.get("Weight") else []
        return dict(inner=out, legend=False, info=info, scaled=True,
                    alt="Drawing of a closed passport holder with a boarding pass tucked in%s, drawn to its "
                        "listed size of %s cm high and %s cm wide" % (" and a zip around it" if zipped else " and a clip-down lock", n(hcm), n(wcm)))
    if "pouch" in tl:
        out = ""
        for x in (128, 248):
            out += (P(D("M%s %s C%s %s %s %s %s %s", x + 20, 92, x + 20, 50, x + 84, 50, x + 84, 92), "pk", 2.5)
                    + R(x, 88, 104, 176, 16) + R(x + 10, 124, 84, 128, 10, "s k", 1.2) + R(x + 5, 94, 94, 22, 6, "p", 0)
                    + C(x + 22, 105, 3, "f") + C(x + 82, 105, 3, "f"))
        water = (sp.get("Water rating") or "").split(",")[0]
        first = " · ".join(x for x in (sp.get("Pack"), water) if x)
        return dict(inner=out + bottom_info(first, "Fits " + sp["Fits"][0].lower() + sp["Fits"][1:] if sp.get("Fits") else ""),
                    legend=False, info=[], scaled=False, alt="Simple drawing of two waterproof phone pouches with neck straps")
    if "scale" in tl:
        cx = 240
        out = (R(cx - 9, 170, 18, 46, 3, "p", 0) + P(D("M%s %s V%s C%s %s %s %s %s %s", cx, 214, 236, cx, 258, cx - 26, 258, cx - 26, 238), "pk", 6)
               + R(cx - 72, 88, 144, 84, 36) + R(cx - 36, 110, 72, 32, 6, "s k", 1.5) + C(cx - 52, 130, 6) + C(cx + 52, 130, 6))
        first = "Weighs up to " + sp["Max load"] if sp.get("Max load") else "Luggage scale"
        second = "in %s steps" % sp["Steps"] if sp.get("Steps") else ""
        return dict(inner=out + bottom_info(first, second), legend=False, info=[], scaled=False,
                    alt="Simple drawing of a handheld digital luggage scale with a strap and hook")
    if "cube" in tl:
        out, y = "", 262
        for w, h, dp in ((200, 62, 76), (168, 52, 64), (132, 44, 52)):
            x = W / 2 - (w + dp * .6) / 2
            dx, dy = dp * .6, dp * .35
            out += (P(D("M%s %s L%s %s H%s L%s %sZ", x, y - h, x + dx, y - h - dy, x + w + dx, x + w, y - h), "s k")
                    + P(D("M%s %s L%s %s V%s L%s %sZ", x + w, y - h, x + w + dx, y - h - dy, y - dy, x + w, y), "s k")
                    + R(x, y - h, w, h, 3)
                    + L(x + 8, y - h + 9, x + w - 8, y - h + 9, "k", 1.3, ' stroke-dasharray="3 3"')
                    + "".join(L(x + dx * .2 + i * w / 8, y - h - dy * .2, x + dx * .8 + i * w / 8 - 6, y - h - dy * .8, "k", 1, ' opacity=".4"')
                              for i in range(1, 8)))
            y -= h + dy * .4
        pieces = re.search(r"(\d+)-piece", tl) or re.search(r"set of (\d+)", tl)
        squeeze = "compression" in tl
        return dict(inner=out + bottom_info("%s-piece set" % pieces.group(1) if pieces else "Packing cubes",
                                            "Compression cubes in three sizes" if squeeze else "Cubes in three sizes"),
                    legend=False, info=[], scaled=False,
                    alt="Simple drawing of a stack of %s in three sizes" % ("compression packing cubes" if squeeze else "packing cubes"))
    if "pillow" in tl:
        u = "M128 236C110 92 270 92 252 236"
        extras = "eye mask" in tl
        air = "inflatable" in tl
        if not extras:
            u = "M168 236C150 92 310 92 292 236"
        out = (P(u, "k", 60) + P(u, "fs", 56)
               + P("M180 214C168 118 292 118 280 214" if not extras else "M140 214C128 118 252 118 240 214", "k", 1.2, ' opacity=".35"'))
        if extras:
            out += (P("M296 160C296 136 336 134 350 150C364 134 404 136 404 160C404 184 372 192 350 176C328 192 296 184 296 160Z", "s k")
                    + R(332, 210, 14, 26, 7, "p", 0) + R(358, 210, 14, 26, 7, "p", 0))
        if air:
            out += R(284, 214, 12, 18, 4, "p", 0)
        fill = "Memory foam" if "memory foam" in tl else "Inflatable" if air else ""
        return dict(inner=out + bottom_info("Neck pillow, eye mask and ear plugs" if extras else "Neck pillow", fill),
                    legend=False, info=[], scaled=False,
                    alt="Simple drawing of a U-shaped neck pillow" + (", an eye mask and a pair of ear plugs" if extras
                                                                     else " with an air valve" if air else ""))
    if "lock" in tl:
        cable = "cable" in tl or "cable" in (sp.get("Shackle") or "").lower()
        keyed = "key" in (sp.get("Lock type") or "").lower()
        two = "2 locks" in (sp.get("Pack") or "").lower()
        out = ""
        for cx in ((176, 304) if two else (240,)):
            if cable:
                out += P(D("M%s %s C%s %s %s %s %s %s", cx - 34, 160, cx - 60, 60, cx + 60, 60, cx + 34, 160), "k", 5)
            else:
                out += P(D("M%s %s V%s A%s %s 0 0 1 %s %s V%s", cx - 30, 160, 118, 30, 30, cx + 30, 118, 160), "k", 9)
            out += R(cx - 50, 150, 100, 92, 14)
            if keyed:
                out += C(cx, 186, 9, "k", 2.5) + R(cx - 3, 190, 6, 22, 2, "p", 0)
            else:
                out += "".join(R(cx - 36 + i * 26, 170, 20, 44, 4, "s k", 1.5) + L(cx - 32 + i * 26, 192, cx - 20 + i * 26, 192, "k", 1)
                               for i in range(3))
            out += R(cx + 22, 224, 20, 12, 3, "p", 0)
        kind = ("Key lock" if keyed else "Combination lock") + (", pack of 2" if two else "")
        second = "TSA lock, as listed" + (", with a steel cable" if cable else "")
        return dict(inner=out + bottom_info(kind, second), legend=False, info=[], scaled=False,
                    alt="Simple drawing of %s%s" % ("two key padlocks" if two and keyed else "a key padlock" if keyed
                                                    else "a three-digit combination lock", " with a cable shackle" if cable else ""))
    return generic(d, "a travel accessory")


def generic(d, what):
    out = (P("M160 120L240 80L320 120V230L240 270L160 230Z", "f k") + P("M160 120L240 160L320 120M240 160V270", "k", 1.6))
    return dict(inner=out + bottom_info("Size not listed"), legend=False, info=[], scaled=False, alt="Simple drawing of " + what)


# ---------- one image per pick ----------

def frame(cat, alt, parts, limit, css=""):
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img">' % (W, H, W, H),
           "<title>%s</title>" % e(alt), style(cat, css),
           '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
           'orient="auto-start-reverse"><path d="M0 1 9 5 0 9z" class="dt"/></marker></defs>',
           '<rect class="bg" width="100%" height="100%"/>', parts["inner"]]
    if parts.get("legend"):
        out.append(R(16, 17, 24, 15, 0, "l", 2, DASH) + T(48, 29, "IndiGo cabin limit", "lt", 13, "start", 700)
                   + T(48, 45, "%s cm" % ndims(limit), "m", 12.5, "start"))
    y = 30
    for line in parts.get("info") or []:
        if line and line[0]:
            text, cls, size, weight = line
            out.append(T(W - 16, y, text, cls, size, "end", weight))
            y += 19
    out.append(T(W / 2, 348, NOTE + (SCALED if parts.get("scaled") else ""), "m", 13))
    out.append("</svg>\n")
    return "".join(out)


DRAW = {"luggage": lambda d, lim: draw_luggage(d, lim), "backpacks": lambda d, lim: draw_backpack(d, lim),
        "watches": lambda d, lim: draw_watch(d), "handbags": lambda d, lim: draw_handbag(d),
        "shoes": lambda d, lim: draw_shoe(d), "clothing": lambda d, lim: draw_clothing(d),
        "skincare": lambda d, lim: draw_skincare(d), "travel-gear": lambda d, lim: draw_travel(d),
        "travel-tech": lambda d, lim: draw_tech(d), "sunglasses": lambda d, lim: draw_glasses(d),
        "wallets-belts": lambda d, lim: draw_belt(d) if "belt" in d["title"].lower() else draw_wallet(d),
        "perfumes": lambda d, lim: draw_perfume(d), "grooming": lambda d, lim: draw_grooming(d),
        "books": lambda d, lim: draw_book(d)}


def colour_words(colour):
    """How the alt text and the label say the listed colour."""
    c = colour.strip()
    if "print" in c.lower():
        return c[0].upper() + c[1:] + " (print not drawn)"
    return c[0].upper() + c[1:]


def build_all(deals, limit=(55, 35, 25)):
    """Returns {asin: (svg, alt)} for every pick. limit is IndiGo's cabin size from data/airlines.json."""
    out = {}
    for d in deals:
        draw = DRAW.get(d["category"])
        parts = draw(d, list(limit)) if draw else generic(d, "a product")
        colour = d.get("colour") if d["category"] != "watches" else None
        css = paint(colour)[0] if colour else ""
        alt = parts["alt"]
        if colour:
            said = colour_words(colour)
            alt += ", in the listed colour: %s" % said[0].lower() + said[1:]
            info = [x for x in (parts.get("info") or []) if x and x[0]]
            if parts.get("legend") and len(info) >= 2:
                # The dashed box reaches up to the third line: keep to two lines.
                info[1] = (info[1][0] + " · colour: " + said[0].lower() + said[1:],) + tuple(info[1][1:])
            else:
                info.append(("Colour: " + said, "m", 13, 400))
            parts["info"] = info
        alt += ". An illustration, not a product photo"
        out[d["asin"]] = (frame(d["category"], alt, parts, list(limit), css), alt)
    return out


def digest(svg, *extra):
    return hashlib.sha1((svg + "|".join(extra)).encode("utf-8")).hexdigest()[:10]
