"""Make a 1200 x 630 share image (og:image) of each pick's drawing, for WhatsApp, Telegram and Facebook previews.

Renders our own drawing from scripts/pick_art.py next to the pick's name with headless Chrome, like
make_pins.py. Never a product photo. Writes static/picks/<ASIN>-<hash>.jpg; the hash changes when the
drawing or name changes, so apps that cache old previews fetch the new one. build.py uses the file when
it's there, and the logo when it isn't, so a missing image never stops a build.
Usage: python3 scripts/make_pick_images.py          # only new or changed picks
       python3 scripts/make_pick_images.py --all    # every pick again
"""

import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from html import escape as e
from pathlib import Path

import pick_art
from common import ROOT, load_deals
from make_pins import CHROME, FONTS, LOGO

OUT = ROOT / "static" / "picks"


def page_html(deal, svg):
    lt = pick_art.COLORS.get(deal["category"], pick_art.COLORS["travel-gear"])[0]
    best = ("Best for " + deal["best_for"][0]) if deal.get("best_for") else ""
    svg = svg.replace('width="480" height="360"', 'width="760" height="570"', 1)
    return f"""<!doctype html><meta charset="utf-8"><link href="{FONTS}" rel="stylesheet"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1200px;height:630px;overflow:hidden}}
body{{background:{lt};font-family:'Plus Jakarta Sans',Arial,sans-serif;color:#14202b;display:flex;align-items:center}}
.og-art{{flex:none;width:760px;height:570px;margin-left:16px}}
.og-art svg{{display:block}}
.og-side{{flex:1;padding:0 48px 0 20px;display:flex;flex-direction:column;gap:22px}}
.og-brand{{display:flex;align-items:center;gap:14px;font-size:28px;font-weight:800;color:#0f4c5c}}
.og-brand svg{{width:48px;height:48px}}
.og-title{{font-size:36px;line-height:1.18;font-weight:800;letter-spacing:-.01em;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}}
.og-best{{align-self:flex-start;padding:8px 18px;border-radius:999px;background:#fff;font-size:22px;font-weight:700}}
.og-site{{font-size:22px;font-weight:700;color:#5b6573}}
</style><body><div class="og-art">{svg}</div><div class="og-side">
<div class="og-brand">{LOGO}<span>CarryPick</span></div>
<h1 class="og-title">{e(deal["title"])}</h1>
{f'<p class="og-best">{e(best)}</p>' if best else ''}
<p class="og-site">carrypick.github.io</p></div></body>"""


def render(job):
    deal, svg, target, work = job
    page = work / (deal["asin"] + ".html")
    page.write_text(page_html(deal, svg), encoding="utf-8")
    png = work / (deal["asin"] + ".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--user-data-dir=%s" % (work / ("chrome-" + deal["asin"])), "--window-size=1200,630",
                    "--virtual-time-budget=5000", "--screenshot=%s" % png, page.as_uri()],
                   check=True, capture_output=True, timeout=120)
    subprocess.run(["magick", str(png), "-crop", "1200x630+0+0", "+repage", "-strip", "-quality", "86", str(target)], check=True)
    shutil.rmtree(work / ("chrome-" + deal["asin"]), ignore_errors=True)
    return deal["asin"]


def main():
    if not Path(CHROME).exists() or not shutil.which("magick"):
        print("Skipped share images: needs Google Chrome and ImageMagick. Pick pages use the logo until then.")
        return
    redo = "--all" in sys.argv[1:]
    deals = load_deals()
    airlines = json.loads((ROOT / "data" / "airlines.json").read_text(encoding="utf-8"))
    indigo = next((a["cabin"]["dims_cm"] for a in airlines["airlines"] if a["slug"] == "indigo"), (55, 35, 25))
    art = pick_art.build_all(deals, indigo)
    OUT.mkdir(parents=True, exist_ok=True)
    wanted, jobs = set(), []
    with tempfile.TemporaryDirectory() as tmp:
        for d in deals:
            svg = art[d["asin"]][0]
            target = OUT / ("%s-%s.jpg" % (d["asin"], pick_art.digest(svg, d["title"], *(d.get("best_for") or [])[:1])))
            wanted.add(target.name)
            if redo or not target.exists():
                jobs.append((d, svg, target, Path(tmp)))
        with ThreadPoolExecutor(max_workers=4) as pool:
            for asin in pool.map(render, jobs):
                print("Made", asin)
    for old in OUT.glob("*.jpg"):
        if old.name not in wanted:
            old.unlink()
    print("Share images: %d made, %d up to date." % (len(jobs), len(wanted) - len(jobs)))


if __name__ == "__main__":
    main()
