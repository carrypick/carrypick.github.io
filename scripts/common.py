"""Shared helpers: paths, config, deals file and Amazon link handling."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "data" / "config.json"
DEALS_FILE = ROOT / "data" / "deals.json"
ENV_FILE = ROOT / ".env"

IST = timezone(timedelta(hours=5, minutes=30))

AMAZON_HOSTS = {"amazon.in", "www.amazon.in", "m.amazon.in"}
SHORT_HOSTS = {"amzn.in", "amzn.to", "a.co", "amzn.eu"}
ASIN_RE = re.compile(
    r"/(?:dp|gp/product|gp/aw/d|exec/obidos/ASIN|o/ASIN|product)/([A-Z0-9]{10})(?=[/?&#]|$)",
    re.IGNORECASE,
)
BARE_ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def load_deals():
    return json.loads(DEALS_FILE.read_text(encoding="utf-8"))


def save_deals(deals):
    DEALS_FILE.write_text(json.dumps(deals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_deal(deals, asin):
    for deal in deals:
        if deal["asin"] == asin:
            return deal
    return None


def now_ist():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def load_env():
    """Read KEY=value lines from .env (the user fills this file, never commit it)."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def amazon_link(asin, tag):
    """The one link format we use: clean product URL plus the Associates tag."""
    url = "https://www.amazon.in/dp/" + asin
    return url + "?tag=" + tag if tag else url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _resolve_short_link(url):
    """Follow amzn.in / amzn.to redirects one hop at a time until we reach amazon.in."""
    opener = urllib.request.build_opener(_NoRedirect)
    for _ in range(5):
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0"})
        try:
            opener.open(req, timeout=15)
            return url
        except urllib.error.HTTPError as err:
            location = err.headers.get("Location")
            if err.code not in (301, 302, 303, 307, 308) or not location:
                raise ValueError("Could not open the short link (HTTP %s)." % err.code)
            url = urllib.parse.urljoin(url, location)
            if urllib.parse.urlparse(url).hostname in AMAZON_HOSTS:
                return url
    raise ValueError("The short link redirected too many times.")


def extract_asin(text):
    """Return the 10-character ASIN from an Amazon India URL, a short link or a bare ASIN."""
    text = text.strip()
    if BARE_ASIN_RE.match(text.upper()):
        return text.upper()
    if "://" not in text:
        text = "https://" + text
    host = (urllib.parse.urlparse(text).hostname or "").lower()
    if host in SHORT_HOSTS:
        text = _resolve_short_link(text)
        host = (urllib.parse.urlparse(text).hostname or "").lower()
    if host not in AMAZON_HOSTS:
        raise ValueError("This is not an Amazon India (amazon.in) link: " + host)
    match = ASIN_RE.search(urllib.parse.urlparse(text).path)
    if not match:
        raise ValueError("Could not find the product ID (ASIN) in this link.")
    return match.group(1).upper()
