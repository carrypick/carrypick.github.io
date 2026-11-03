"""Download the free Unsplash photos listed in data/photos.json into static/photos/.

Run:  python3 scripts/fetch_photos.py
Each photo is saved three times: 800 and 1600 px wide WebP for the page,
and a 1200 x 630 JPEG for link previews (Telegram, WhatsApp, Google).
Files that already exist are skipped, so it only fetches new photos.
"""

import json
import urllib.request

from common import ROOT

PHOTOS_FILE = ROOT / "data" / "photos.json"
OUT_DIR = ROOT / "static" / "photos"
CDN = "https://images.unsplash.com/photo-%s?%s"
VARIANTS = {
    "800.webp": "w=800&q=70&fm=webp&fit=max",
    "1600.webp": "w=1600&q=68&fm=webp&fit=max",
    "og.jpg": "w=1200&h=630&fit=crop&crop=entropy&q=72&fm=jpg",
}


def main():
    photos = json.loads(PHOTOS_FILE.read_text(encoding="utf-8"))["photos"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for slot, info in photos.items():
        for suffix, query in VARIANTS.items():
            target = OUT_DIR / ("%s-%s" % (slot, suffix))
            if target.exists():
                continue
            req = urllib.request.Request(CDN % (info["image"], query), headers={"User-Agent": "CarryPick site builder"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                target.write_bytes(resp.read())
            print("Saved %s (%d KB)" % (target.relative_to(ROOT), target.stat().st_size // 1024))
    keep = {"%s-%s" % (slot, suffix) for slot in photos for suffix in VARIANTS}
    for old in OUT_DIR.iterdir():
        if old.name not in keep:
            print("Not in photos.json, consider deleting: %s" % old.relative_to(ROOT))


if __name__ == "__main__":
    main()
