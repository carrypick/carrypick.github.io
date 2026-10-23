"""Post a pick to the Telegram channel (and print a WhatsApp version).

Examples:
  python3 scripts/post_telegram.py B0ABCDEFGH --dry-run     # show the post, send nothing
  python3 scripts/post_telegram.py B0ABCDEFGH               # send to the channel
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


def pick_url(cfg, asin):
    base = cfg["base_url"].rstrip("/") or "https://YOUR-SITE"
    return "%s/picks/%s.html" % (base, asin)


def hashtag(name):
    return "#" + "".join(ch for ch in name.title() if ch.isalnum())


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
        hashtag(cat["name"]),
        "<i>%s</i>" % DISCLOSURE,
    ]
    return "\n".join(lines)


def whatsapp_text(cfg, deal):
    cat = cfg["categories"][deal["category"]]
    lines = ["%s *%s*" % (cat["emoji"], deal["title"]), ""]
    lines += ["✅ " + h for h in deal["highlights"]]
    if deal.get("note"):
        lines += ["", "💡 " + deal["note"]]
    lines += ["", "👉 See this pick and today's price: " + pick_url(cfg, deal["asin"]), "", "_%s_" % DISCLOSURE]
    return "\n".join(lines)


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
    args = parser.parse_args()

    cfg = load_config()
    deals = load_deals()
    deal = find_deal(deals, args.asin.upper())
    if deal is None:
        sys.exit("Error: %s is not in data/deals.json. Add it with add_deal.py first." % args.asin)

    text = telegram_text(cfg, deal)
    if args.dry_run:
        print("----- Telegram -----\n" + text + "\n\n----- WhatsApp (copy and paste) -----\n" + whatsapp_text(cfg, deal))
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
