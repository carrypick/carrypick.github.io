"""Our own SVG diagrams. build.py writes them to docs/assets/diagrams/.

Each diagram brings its own light and dark colours, because an SVG shown
with <img> can't use the page's CSS. Drawn to scale where the caption says so.
"""

import math
from html import escape as e

FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif'
STYLE = """<style>
.bg{fill:#fbfaf7}.ink{fill:#14202b}.muted{fill:#5b6573}.line{stroke:#14202b}
.body{fill:#e5edf8}.side{fill:#c9d8ee}.top{fill:#d8e4f5}.rib{stroke:#9fb6d9}
.dim{stroke:#c2410c}.dimtext{fill:#c2410c}.hl{fill:#fde3cf}.hlside{fill:#f6c9a6}.hltop{fill:#fad5b8}
.dial{fill:#ffffff}.strap{fill:#3b4652}.case{fill:#cfd5db}
text{font-family:%s}
@media (prefers-color-scheme: dark){
.bg{fill:#171e24}.ink{fill:#e8edf1}.muted{fill:#9ba6b2}.line{stroke:#c9d3db}
.body{fill:#22324a}.side{fill:#192638}.top{fill:#2a3c57}.rib{stroke:#3f587c}
.dim{stroke:#fb923c}.dimtext{fill:#fb923c}.hl{fill:#4a2a14}.hlside{fill:#3a200f}.hltop{fill:#5a3419}
.dial{fill:#e8edf1}.strap{fill:#566270}.case{fill:#8a96a3}}
</style>""" % FONT
ARROW = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         'orient="auto-start-reverse"><path d="M0 1 9 5 0 9z" class="dimtext"/></marker></defs>')


def svg(width, height, title, inner):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img">'
            '<title>%s</title>%s%s<rect class="bg" width="100%%" height="100%%" rx="14"/>%s</svg>\n'
            % (width, height, width, height, e(title), STYLE, ARROW, inner))


def text(x, y, words, cls="ink", size=17, anchor="middle", weight=400):
    return ('<text x="%g" y="%g" class="%s" font-size="%d" font-weight="%d" text-anchor="%s">%s</text>'
            % (x, y, cls, size, weight, anchor, e(words)))


def dim_line(x1, y1, x2, y2):
    return ('<line x1="%g" y1="%g" x2="%g" y2="%g" class="dim" stroke-width="2.2" '
            'marker-start="url(#a)" marker-end="url(#a)"/>' % (x1, y1, x2, y2))


def box(x, y, w, h, d, hl=False):
    """A box drawn in oblique view: front face w x h at (x, y), depth d going up and right."""
    dx, dy = d * 0.87, d * 0.5
    pre = "hl" if hl else ""
    top = "%g,%g %g,%g %g,%g %g,%g" % (x, y, x + w, y, x + w + dx, y - dy, x + dx, y - dy)
    side = "%g,%g %g,%g %g,%g %g,%g" % (x + w, y, x + w + dx, y - dy, x + w + dx, y + h - dy, x + w, y + h)
    return ('<polygon points="%s" class="%s line" stroke-width="1.5" stroke-linejoin="round"/>'
            '<polygon points="%s" class="%s line" stroke-width="1.5" stroke-linejoin="round"/>'
            '<rect x="%g" y="%g" width="%g" height="%g" class="%s line" stroke-width="1.5"/>'
            % (top, pre + "top" if hl else "top", side, pre + "side" if hl else "side",
               x, y, w, h, "hl" if hl else "body"))


# ---------- how to measure a cabin bag ----------

def measure_bag():
    x, y, w, h, d = 170, 110, 130, 190, 64
    dx, dy = d * 0.87, d * 0.5
    bag = box(x, y, w, h, d)
    ribs = "".join('<line x1="%g" y1="%g" x2="%g" y2="%g" class="rib" stroke-width="3" stroke-linecap="round"/>'
                   % (x + w * f, y + 22, x + w * f, y + h - 22) for f in (0.3, 0.5, 0.7))
    grip_x = x + w / 2 + dx / 2 - 26
    handle = ('<line x1="%g" y1="%g" x2="%g" y2="%g" class="line" stroke-width="5" stroke-linecap="round"/>'
              '<line x1="%g" y1="%g" x2="%g" y2="%g" class="line" stroke-width="5" stroke-linecap="round"/>'
              '<rect x="%g" y="%g" width="52" height="13" rx="6.5" class="strap"/>'
              % (grip_x + 8, y - dy / 2 + 2, grip_x + 8, 76, grip_x + 44, y - dy / 2 + 2, grip_x + 44, 76, grip_x, 68))
    wheels = "".join('<circle cx="%g" cy="%g" r="%g" class="strap"/>' % c
                     for c in ((x + w + dx - 12, y + h - dy + 9, 8), (x + 18, y + h + 11, 10), (x + w - 18, y + h + 11, 10)))
    bottom = y + h + 21
    marks = (
        # height, from the top of the handle to the bottom of the wheels
        '<line x1="112" y1="68" x2="%g" y2="68" class="dim" stroke-width="1" stroke-dasharray="4 4"/>' % grip_x
        + '<line x1="112" y1="%g" x2="%g" y2="%g" class="dim" stroke-width="1" stroke-dasharray="4 4"/>' % (bottom, x + 8, bottom)
        + dim_line(122, 70, 122, bottom - 2)
        + text(106, 186, "Height", "dimtext", 19, "end", 700)
        + text(106, 208, "with wheels", "muted", 14, "end")
        + text(106, 226, "and handle", "muted", 14, "end")
        # width
        + '<line x1="%g" y1="%g" x2="%g" y2="360" class="dim" stroke-width="1" stroke-dasharray="4 4"/>' % (x, y + h + 4, x)
        + '<line x1="%g" y1="%g" x2="%g" y2="360" class="dim" stroke-width="1" stroke-dasharray="4 4"/>' % (x + w, y + h + 4, x + w)
        + dim_line(x + 2, 352, x + w - 2, 352)
        + text(x + w / 2, 382, "Width", "dimtext", 19, "middle", 700)
        # depth, along the bottom edge of the side
        + dim_line(x + w + 16, y + h + 22, x + w + dx + 16, y + h - dy + 22)
        + text(x + w + dx + 26, y + h - dy + 48, "Depth", "dimtext", 19, "start", 700)
        + text(x + w + dx + 26, y + h - dy + 68, "with pockets", "muted", 14, "start")
    )
    return svg(500, 400, "How to measure a cabin bag: height with wheels and handle, width, and depth with pockets",
               handle + bag + ribs + wheels + marks)


# ---------- cabin size limits of each airline, to scale ----------

def cabin_limits(entries, highlight=None):
    """entries: (slug, label, [h, w, d]) for each limit. Two columns, drawn to one scale."""
    scale, cell_w, cell_h, top = 2.1, 210, 240, 20
    rows = (len(entries) + 1) // 2
    parts = []
    for i, (slug, label, dims) in enumerate(entries):
        h, w, d = (dims[0] * scale, dims[1] * scale, dims[2] * scale)
        col, row = i % 2, i // 2
        cx = 10 + col * cell_w + cell_w / 2
        base = top + row * cell_h + 145
        x = cx - (w + d * 0.87) / 2
        parts.append(box(x, base - h, w, h, d, hl=slug.replace("-variant", "") == highlight))
        parts.append(text(cx, base + 30, label, "ink", 17, "middle", 700))
        parts.append(text(cx, base + 52, "%g × %g × %g cm" % tuple(dims), "muted", 15))
        parts.append(text(cx, base + 72, "%g cm in total" % sum(dims), "muted", 15))
    title = "Cabin bag size limits drawn to scale: " + "; ".join(
        "%s %g × %g × %g cm" % ((label,) + tuple(dims)) for slug, label, dims in entries)
    return svg(430, top + rows * cell_h, title, "".join(parts))


# ---------- luggage sizes by trip length ----------

def luggage_sizes():
    bags = [("Cabin", "about 55 cm", "2–4 days", 55, 37),
            ("Medium", "65–69 cm", "5–8 days", 67, 44),
            ("Large", "75–79 cm", "10+ days", 77, 51)]
    scale, ground, gap, x = 3, 290, 34, 30
    parts = ['<line x1="16" y1="%d" x2="504" y2="%d" class="line" stroke-width="1.5" opacity=".35"/>' % (ground + 12, ground + 12)]
    for name, size, days, hcm, wcm in bags:
        h, w = hcm * scale, wcm * scale
        top = ground - h
        parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="16" class="body line" stroke-width="1.6"/>' % (x, top, w, h))
        parts.extend('<line x1="%g" y1="%g" x2="%g" y2="%g" class="rib" stroke-width="3.5" stroke-linecap="round"/>'
                     % (x + w * f, top + 22, x + w * f, ground - 22) for f in (0.3, 0.5, 0.7))
        parts.append('<rect x="%g" y="%g" width="44" height="12" rx="6" class="strap"/>' % (x + w / 2 - 22, top - 16))
        parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" class="line" stroke-width="5"/>' % (x + w / 2 - 14, top - 6, x + w / 2 - 14, top))
        parts.append('<line x1="%g" y1="%g" x2="%g" y2="%g" class="line" stroke-width="5"/>' % (x + w / 2 + 14, top - 6, x + w / 2 + 14, top))
        parts.extend('<circle cx="%g" cy="%g" r="7.5" class="strap"/>' % (cx, ground + 4) for cx in (x + 16, x + w - 16))
        parts.append(text(x + w / 2, ground + 44, name, "ink", 20, "middle", 700))
        parts.append(text(x + w / 2, ground + 66, size, "muted", 16))
        parts.append(text(x + w / 2, ground + 86, days, "dimtext", 16, "middle", 700))
        x += w + gap
    return svg(520, 390, "Cabin, medium and large trolleys drawn to scale: about 55 cm for 2 to 4 days, "
               "65 to 69 cm for 5 to 8 days, 75 to 79 cm for 10 or more days", "".join(parts))


# ---------- watch dial sizes ----------

def watch_face(cx, cy, mm, scale):
    r = mm * scale / 2
    strap_w = r * 1.05
    ticks = []
    for i in range(12):
        a = math.radians(i * 30)
        inner = r * (0.72 if i % 3 == 0 else 0.78)
        ticks.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#14202b" stroke-width="%g" stroke-linecap="round"/>'
                     % (cx + inner * math.sin(a), cy - inner * math.cos(a), cx + r * 0.86 * math.sin(a),
                        cy - r * 0.86 * math.cos(a), 2.6 if i % 3 == 0 else 1.4))
    return (
        '<rect x="%g" y="%g" width="%g" height="%g" rx="8" class="strap"/>' % (cx - strap_w / 2, cy - r - 46, strap_w, r * 2 + 92)
        + '<rect x="%g" y="%g" width="9" height="%g" rx="3" class="line strap"/>' % (cx + r - 2, cy - 7, 14)
        + '<circle cx="%g" cy="%g" r="%g" class="case line" stroke-width="2"/>' % (cx, cy, r)
        + '<circle cx="%g" cy="%g" r="%g" class="dial"/>' % (cx, cy, r * 0.9)
        + "".join(ticks)
        # hands at 10:10
        + '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#14202b" stroke-width="3" stroke-linecap="round"/>'
        % (cx, cy, cx - r * 0.42, cy - r * 0.24)
        + '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#14202b" stroke-width="2.2" stroke-linecap="round"/>'
        % (cx, cy, cx + r * 0.55, cy - r * 0.32)
        + '<circle cx="%g" cy="%g" r="3" fill="#c2410c"/>' % (cx, cy)
    )


def watch_sizes():
    sizes = [("Small", "under 36 mm", 32), ("Medium", "36–40 mm", 38), ("Large", "41–45 mm", 44)]
    scale, cy, x = 3.5, 150, 30
    parts = []
    for name, label, mm in sizes:
        d = mm * scale
        parts.append(watch_face(x + d / 2, cy, mm, scale))
        parts.append(text(x + d / 2, 300, name, "ink", 20, "middle", 700))
        parts.append(text(x + d / 2, 322, label, "muted", 16))
        x += d + 36
    return svg(520, 345, "Watch dial sizes drawn to scale: small under 36 mm, medium 36 to 40 mm, large 41 to 45 mm",
               "".join(parts))


# ---------- registry ----------

def build_all(airlines, checked_text):
    """Returns {name: (svg, alt, caption)} for every diagram."""
    entries = []
    for a in airlines:
        if a["cabin"].get("dims_cm"):
            label = a["name"] + (" (Boeing)" if a["cabin"].get("variants") else "")
            entries.append((a["slug"], label, a["cabin"]["dims_cm"]))
        for v in a["cabin"].get("variants", []):
            if v.get("dims_cm"):
                entries.append((a["slug"] + "-variant", "%s (%s)" % (a["name"], v["label"].replace(" planes", "")), v["dims_cm"]))
    limits_caption = ("Cabin bag limits drawn to the same scale (height × width × depth). "
                      "Air India allows a wider but thinner bag. Checked %s." % checked_text)
    out = {
        "measure-bag": (measure_bag(), "Diagram: measure a cabin bag's height including wheels and handle, its width, and its depth including pockets",
                        "Measure the outside of the packed bag. Add height + width + depth to get the total size."),
        "cabin-limits": (cabin_limits(entries), "Diagram comparing the cabin bag size limits of Indian airlines, drawn to scale", limits_caption),
        "luggage-sizes": (luggage_sizes(), "Diagram of cabin, medium and large trolleys drawn to scale, with trip lengths",
                          "Trolley heights drawn to scale. Sizes vary a little by brand, so check the listing."),
        "watch-sizes": (watch_sizes(), "Diagram of small, medium and large watch dials drawn to scale",
                        "Dial sizes drawn to scale. 38–40 mm suits most men's wrists, 28–34 mm most women's."),
    }
    for a in airlines:
        if a["cabin"].get("dims_cm"):
            out["cabin-limits-" + a["slug"]] = (cabin_limits(entries, highlight=a["slug"]),
                                               "Diagram comparing %s's cabin bag limit with other Indian airlines, drawn to scale" % a["name"],
                                               "%s's limit (highlighted) next to other Indian airlines, drawn to the same scale. Checked %s."
                                               % (a["name"], checked_text))
    return out
