"""Tell Bing and the other IndexNow search engines that our pages changed.

Google doesn't use IndexNow; it reads docs/sitemap.xml (submitted in Search Console).
Run after publishing:
  python3 scripts/indexnow.py                          # every page in docs/sitemap.xml
  python3 scripts/indexnow.py picks/B0ABCDEFGH.html    # only these pages
"""

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from common import ROOT, load_config

ENDPOINT = "https://api.indexnow.org/indexnow"


def main():
    cfg = load_config()
    key, base = cfg.get("indexnow_key"), cfg["base_url"].rstrip("/")
    if not key:
        sys.exit("Error: add indexnow_key to data/config.json first.")
    if len(sys.argv) > 1:
        urls = [base + "/" + path.lstrip("/") for path in sys.argv[1:]]
    else:
        urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "docs" / "sitemap.xml").read_text(encoding="utf-8"))
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
