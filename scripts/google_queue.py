"""Keep the list of pages to send to Google with Request Indexing in Search Console.

The list is guides/google-queue.txt (private, not published), one page per line: STATE DATE PATH.
States are waiting, requested and indexed. New pages in docs/sitemap.xml join the front of the list,
except picks, which are added by name, and pages that don't need search traffic.
  python3 scripts/google_queue.py next 8                       # the next 8 pages to request
  python3 scripts/google_queue.py add picks/B0ABCDEFGH.html    # put a page at the front
  python3 scripts/google_queue.py mark PATH requested          # or indexed
  python3 scripts/google_queue.py count                        # how many in each state
"""

import collections
import re
import sys
from datetime import date

from common import ROOT, load_config

QUEUE = ROOT / "guides" / "google-queue.txt"
SKIP = {"", "about.html", "disclosure.html", "privacy.html", "contact.html"}
STATES = ("requested", "indexed")


def load():
    if not QUEUE.exists():
        return []
    return [line.split(" ", 2) for line in QUEUE.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(rows):
    QUEUE.write_text("".join(" ".join(row) + "\n" for row in rows), encoding="utf-8")


def add_new_pages(rows):
    """Put sitemap pages the list doesn't know yet at the front, so new pages go first."""
    base = load_config()["base_url"].rstrip("/") + "/"
    urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "docs" / "sitemap.xml").read_text(encoding="utf-8"))
    known = {row[2] for row in rows}
    paths = [url[len(base):] for url in urls if url.startswith(base)]
    fresh = [path for path in paths if path not in known and path not in SKIP and not path.startswith("picks/")]
    return [["waiting", "-", path] for path in fresh] + rows


def main():
    args = sys.argv[1:]
    rows = load()
    if len(args) == 2 and args[0] == "next" and args[1].isdigit():
        rows = add_new_pages(rows)
        save(rows)
        print("\n".join([row[2] for row in rows if row[0] == "waiting"][:int(args[1])]))
    elif len(args) == 2 and args[0] == "add":
        if args[1] not in {row[2] for row in rows}:
            save([["waiting", "-", args[1]]] + rows)
    elif len(args) == 3 and args[0] == "mark" and args[2] in STATES:
        if args[1] not in {row[2] for row in rows}:
            sys.exit("Error: %s is not in the list." % args[1])
        save([[args[2], date.today().isoformat(), row[2]] if row[2] == args[1] else row for row in rows])
    elif args == ["count"]:
        counts = collections.Counter(row[0] for row in rows)
        print(", ".join("%s %d" % (state, counts[state]) for state in ("waiting",) + STATES))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
