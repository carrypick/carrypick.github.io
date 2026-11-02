"""Post a pick to the Telegram channel (and print a WhatsApp version).

Examples:
  python3 scripts/post_telegram.py B0ABCDEFGH --dry-run       # show the post, send nothing
  python3 scripts/post_telegram.py B0ABCDEFGH --mark-posted   # record a post made by hand in Telegram Web
  python3 scripts/post_telegram.py B0ABCDEFGH                 # send with the bot (needs TELEGRAM_BOT_TOKEN)
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import escape as e

from common import find_deal, load_config, load_deals, load_env, now_ist, save_deals

DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."


def pick_url(cfg, asin, src="tg"):
    """src tells the site which channel's tracking ID to use (see static/site.js)."""
    base = cfg["base_url"].rstrip("/") or "https://YOUR-SITE"
    return "%s/picks/%s.html?src=%s" % (base, asin, src)


def hashtag(cat):
    return cat.get("hashtag") or "#" + "".join(ch for ch in cat["name"].title() if ch.isalnum())


def telegram_text(cfg, deal):
    cat = cfg["categories"][deal["category"]]
    lines = ["%s <b>%s</b>" % (cat["emoji"], e(deal["title"])), ""]
    lines += ["✅ " + e(h) for h in deal["highlights"]]
    if deal.get("note"):
        lines += ["", "💡 " + e(deal["note"])]
    lines += [
        "",
        '👉 <a href="%s">See this pick and today\'s price</a>' % e(pick_url(cfg, deal["asin"])),
        "",
        hashtag(cat),
        "<i>%s</i>" % DISCLOSURE,
    ]
    return "\n".join(lines)


def plain_text(cfg, deal, bold="*", italic="_", src="wa"):
    """Text for pasting by hand: WhatsApp uses *bold* and _italic_, Telegram Web uses ** and __."""
    cat = cfg["categories"][deal["category"]]
    lines = ["%s %s%s%s" % (cat["emoji"], bold, deal["title"], bold), ""]
    lines += ["✅ " + h for h in deal["highlights"]]
    if deal.get("note"):
        lines += ["", "💡 " + deal["note"]]
    lines += ["", "👉 See this pick and today's price: " + pick_url(cfg, deal["asin"], src), "", hashtag(cat)]
    lines += ["%s%s%s" % (italic, DISCLOSURE, italic)]
    return "\n".join(lines)


def whatsapp_text(cfg, deal):
    # WhatsApp channels don't support hashtags, so drop that line.
    return "\n".join(line for line in plain_text(cfg, deal).splitlines() if not line.startswith("#"))


def telegram_web_text(cfg, deal):
    return plain_text(cfg, deal, bold="**", italic="__", src="tg")


def send(token, channel, text):
    data = urllib.parse.urlencode({"chat_id": channel, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token, data=data)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        return json.load(err)


def main():
    parser = argparse.ArgumentParser(description="Post a pick to Telegram")
    parser.add_argument("asin")
    parser.add_argument("--dry-run", action="store_true", help="print the post without sending")
    parser.add_argument("--mark-posted", action="store_true", help="record that the pick was posted by hand")
    args = parser.parse_args()

    cfg = load_config()
    deals = load_deals()
    deal = find_deal(deals, args.asin.upper())
    if deal is None:
        sys.exit("Error: %s is not in data/deals.json. Add it with add_deal.py first." % args.asin)

    text = telegram_text(cfg, deal)
    if args.dry_run:
        print("----- Telegram Web (copy and paste) -----\n" + telegram_web_text(cfg, deal))
        print("\n----- WhatsApp (copy and paste) -----\n" + whatsapp_text(cfg, deal))
        return
    if args.mark_posted:
        deal["telegram_posted_at"] = now_ist()
        save_deals(deals)
        print("Marked %s as posted." % deal["asin"])
        return

    token = load_env().get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Error: put TELEGRAM_BOT_TOKEN=... in the .env file first (see guides/03-telegram-setup.md).")
    if not cfg["telegram_channel"] or not cfg["base_url"]:
        sys.exit("Error: set telegram_channel and base_url in data/config.json first.")

    result = send(token, cfg["telegram_channel"], text)
    if not result.get("ok"):
        sys.exit("Telegram said: %s" % result.get("description", "unknown error"))
    deal["telegram_posted_at"] = now_ist()
    save_deals(deals)
    print("Posted to %s." % cfg["telegram_channel"])
    print("\n----- WhatsApp (copy and paste) -----\n" + whatsapp_text(cfg, deal))


if __name__ == "__main__":
    main()
