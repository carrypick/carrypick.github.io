"""Add (or update) a product pick.

Examples:
  python3 scripts/add_deal.py --link-only "https://www.amazon.in/Some-Bag/dp/B0ABCDEFGH/ref=sr_1_1?keywords=bag"
  python3 scripts/add_deal.py "https://amzn.in/d/abc123" --title "Skybags Brat 46 cm Backpack" \
      --category backpacks --highlight "3 compartments" --highlight "Fits a 15.6 inch laptop" \
      --note "Light and roomy for college" --brand Skybags --best-for College \
      --spec "Capacity=30 L" --spec "Warranty=1 year" --skip-if "you need a rain cover."
  python3 scripts/add_deal.py B0ABCDEFGH --deal-seen "2026-11-03T09:15"   # Amazon shows a deal label right now
  python3 scripts/add_deal.py B0ABCDEFGH --no-deal                         # remove the deal badge

The site shows "Deal spotted <time>" for 24 hours after --deal-seen, with no price or % off.
Only use it when the Amazon page itself shows a deal label such as "Limited time deal".
"""

import argparse
import sys
from datetime import datetime, timedelta

from common import IST, amazon_link, extract_asin, find_deal, load_config, load_deals, now_ist, save_deals

DEAL_HOURS = 24


def main():
    parser = argparse.ArgumentParser(description="Add a product pick to data/deals.json")
    parser.add_argument("url", help="amazon.in product link, amzn.in short link, or ASIN")
    parser.add_argument("--link-only", action="store_true", help="only print the affiliate link")
    parser.add_argument("--title")
    parser.add_argument("--category")
    parser.add_argument("--highlight", action="append", default=[], help="a key feature (repeat for more)")
    parser.add_argument("--note", help="one line on why we picked it")
    parser.add_argument("--brand")
    parser.add_argument("--best-for", action="append", default=[], help="short tag like College (repeat for more)")
    parser.add_argument("--spec", action="append", default=[], help='a spec as "Name=Value" (repeat for more)')
    parser.add_argument("--skip-if", help='ends the sentence "Skip it if ...", e.g. "you need wheels."')
    parser.add_argument("--deal-seen", nargs="?", const="now", metavar="TIME",
                        help='when Amazon showed a deal label, as "2026-11-03T09:15" (India time) or "now"')
    parser.add_argument("--no-deal", action="store_true", help="remove the deal badge")
    args = parser.parse_args()

    config = load_config()
    try:
        asin = extract_asin(args.url)
    except ValueError as err:
        sys.exit("Error: %s" % err)

    if args.link_only:
        print(amazon_link(asin, config["amazon_tag"]))
        return

    specs = {}
    for spec in args.spec:
        name, sep, value = spec.partition("=")
        if not (sep and name.strip() and value.strip()):
            sys.exit('Error: --spec must look like "Capacity=30 L".')
        specs[name.strip()] = value.strip()

    deal_seen = None
    if args.deal_seen:
        try:
            seen = datetime.now(IST) if args.deal_seen == "now" else datetime.fromisoformat(args.deal_seen)
        except ValueError:
            sys.exit('Error: --deal-seen must look like "2026-11-03T09:15" or "now".')
        seen = seen.replace(tzinfo=IST) if seen.tzinfo is None else seen.astimezone(IST)
        if seen > datetime.now(IST) + timedelta(minutes=5):
            sys.exit("Error: --deal-seen is in the future.")
        if datetime.now(IST) - seen > timedelta(hours=DEAL_HOURS):
            print("Note: that is more than %d hours ago, so the site won't show the badge." % DEAL_HOURS)
        deal_seen = seen.replace(second=0, microsecond=0).isoformat()

    if args.category and args.category not in config["categories"]:
        sys.exit("Error: category must be one of: " + ", ".join(config["categories"]))

    deals = load_deals()
    deal = find_deal(deals, asin)
    if deal is None:
        if not (args.title and args.category and args.highlight):
            sys.exit("Error: a new pick needs --title, --category and at least one --highlight.")
        deal = {"asin": asin, "added_at": now_ist()}
        deals.insert(0, deal)
        action = "Added"
    else:
        action = "Updated"

    if args.title:
        deal["title"] = args.title
    if args.category:
        deal["category"] = args.category
    if args.highlight:
        deal["highlights"] = args.highlight
    if args.note is not None:
        deal["note"] = args.note
    if args.brand:
        deal["brand"] = args.brand
    if args.best_for:
        deal["best_for"] = args.best_for
    if specs:
        deal["specs"] = specs
    if args.skip_if is not None:
        deal["skip_if"] = args.skip_if
    if deal_seen:
        deal["deal_seen_at"] = deal_seen
    if args.no_deal:
        deal.pop("deal_seen_at", None)

    save_deals(deals)
    print("%s %s: %s" % (action, asin, deal["title"]))
    print(amazon_link(asin, config["amazon_tag"]))


if __name__ == "__main__":
    main()
