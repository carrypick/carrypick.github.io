"""Download the free photos listed in data/photos.json into static/photos/.

Run:  python3 scripts/fetch_photos.py
Each photo is saved three times: 800 and 1600 px wide WebP for the page,
and a 1200 x 630 JPEG for link previews (Telegram, WhatsApp, Google).
Files that already exist are skipped, so it only fetches new photos.

Unsplash photos come ready-sized from Unsplash's image server.
Wikimedia Commons photos ("commons": "File:...") are fetched once at 1920 px
and resized here with ImageMagick (brew install imagemagick).
"""

import json
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from common import ROOT

PHOTOS_FILE = ROOT / "data" / "photos.json"
OUT_DIR = ROOT / "static" / "photos"
CDN = "https://images.unsplash.com/photo-%s?%s"
UA = {"User-Agent": "CarryPick-site-builder/1.0 (static site photo credits)"}
VARIANTS = {
    "800.webp": "w=800&q=70&fm=webp&fit=max",
    "1600.webp": "w=1600&q=68&fm=webp&fit=max",
    "og.jpg": "w=1200&h=630&fit=crop&crop=entropy&q=72&fm=jpg",
}
# ImageMagick settings close to the Unsplash ones above (q60 at 1600 px keeps big photos under 400 KB)
MAGICK = {
    "800.webp": ["-resize", "800x", "-quality", "70"],
    "1600.webp": ["-resize", "1600x", "-quality", "60"],
    "og.jpg": ["-resize", "1200x630^", "-gravity", "center", "-extent", "1200x630", "-quality", "72"],
}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as resp:
        return resp.read()


def commons_thumb(title):
    query = urllib.parse.urlencode({"action": "query", "format": "json", "titles": title,
                                    "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "1920"})
    page = next(iter(json.loads(fetch("https://commons.wikimedia.org/w/api.php?" + query))["query"]["pages"].values()))
    return page["imageinfo"][0]["thumburl"]


def main():
    photos = json.loads(PHOTOS_FILE.read_text(encoding="utf-8"))["photos"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for slot, info in photos.items():
        missing = [s for s in VARIANTS if not (OUT_DIR / ("%s-%s" % (slot, s))).exists()]
        if not missing:
            continue
        if info.get("commons"):
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "source.jpg"
                src.write_bytes(fetch(commons_thumb(info["commons"])))
                for suffix in missing:
                    target = OUT_DIR / ("%s-%s" % (slot, suffix))
                    subprocess.run(["magick", str(src), "-strip", *MAGICK[suffix], str(target)], check=True)
                    print("Saved %s (%d KB)" % (target.relative_to(ROOT), target.stat().st_size // 1024))
            continue
        for suffix in missing:
            target = OUT_DIR / ("%s-%s" % (slot, suffix))
            target.write_bytes(fetch(CDN % (info["image"], VARIANTS[suffix])))
            print("Saved %s (%d KB)" % (target.relative_to(ROOT), target.stat().st_size // 1024))
    keep = {"%s-%s" % (slot, suffix) for slot in photos for suffix in VARIANTS}
    for old in OUT_DIR.iterdir():
        if old.name not in keep:
            print("Not in photos.json, consider deleting: %s" % old.relative_to(ROOT))


if __name__ == "__main__":
    main()
