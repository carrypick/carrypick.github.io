"""Tell Bing and the other IndexNow search engines that our pages changed.

Google doesn't use IndexNow; it reads the sitemaps (submitted in Search Console).
Run after publishing, with only the pages you changed:
  python3 scripts/indexnow.py trips/goa.html guides/x.html   # only these pages
  python3 scripts/indexnow.py all                            # every page in the sitemaps (rarely: a site-wide change)

Pages that are not in the sitemaps (noindex picks, subcategories, gift guides, merged pages) are skipped:
search engines shouldn't index them, so there is no point asking. index.html means the home page.
Since 27 Nov 2026 a run with no pages stops instead of sending the whole site: Bing's IndexNow report showed
2,600 URLs on 21 Nov and 1,300 on 24 Nov for a site of about 360 indexable pages, and IndexNow is for changed
pages only.
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from common import ROOT, load_config

ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls():
    """Page URLs in docs/sitemap-*.xml (docs/sitemap.xml is a sitemap index that points to them)."""
    return [u for child in sorted((ROOT / "docs").glob("sitemap-*.xml"))
            for u in re.findall(r"<loc>([^<]+)</loc>",
                                re.sub(r"<image:image>.*?</image:image>", "", child.read_text(encoding="utf-8"), flags=re.S))]


def main():
    cfg = load_config()
    key, base = cfg.get("indexnow_key"), cfg["base_url"].rstrip("/")
    args = sys.argv[1:]
    if not key:
        sys.exit("Error: add indexnow_key to data/config.json first.")
    if not args or any(arg.startswith("-") for arg in args):
        sys.exit(__doc__)
    listed = sitemap_urls()
    if args == ["all"]:
        urls = listed
    else:
        wanted = [base + "/" + ("" if path.lstrip("/") == "index.html" else path.lstrip("/")) for path in args]
        known = set(listed)
        urls = list(dict.fromkeys(u for u in wanted if u in known))
        skipped = [u[len(base) + 1:] for u in wanted if u not in known]
        if skipped:
            print("Skipped %d page(s) not in the sitemaps (noindex or merged): %s" % (len(skipped), " ".join(skipped)))
    if not urls:
        print("Nothing to send to IndexNow.")
        return
    body = json.dumps({"host": urllib.parse.urlparse(base).hostname, "key": key,
                       "keyLocation": "%s/%s.txt" % (base, key), "urlList": urls}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("IndexNow accepted %d URLs (HTTP %d)." % (len(urls), resp.status))
    except urllib.error.HTTPError as err:
        sys.exit("IndexNow refused the list (HTTP %d): %s" % (err.code, err.read().decode(errors="replace")[:300]))


if __name__ == "__main__":
    main()
