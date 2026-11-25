"""Long weekends 2027 planner (tools/long-weekends-2027.html, static/long-weekends.js, tools/long-weekends-2027.ics).

data/holidays_2027.json is the DoPT holiday list for central government offices in Delhi / New Delhi (gazetted and
restricted), with the O.M. number, date, source and checked date. Nothing here guesses a date: every holiday comes
from that file, and its weekdays are checked against the calendar.
plans() works out every long weekend at build time: runs of days off (Saturday, Sunday, gazetted holidays) with up to
3 days of leave, where leave on a restricted-holiday date can be swapped for one of the 2 restricted holidays
each employee gets. The page is a plain table of those plans; the JS only hides rows by month and leave days.
build.py calls register(B) where it lists TOOLS, and build(B, ...) after the trips, so trip links can be checked.
"""
import json
import re
import sys
import urllib.parse
from datetime import date, timedelta
from html import escape as e

from common import ROOT

FILE = ROOT / "data" / "holidays_2027.json"
PATH = "tools/long-weekends-2027.html"
ICS = "tools/long-weekends-2027.ics"
REPUBLIC = "trips/republic-day-long-weekend-2027.html"
MAX_LEAVE = 3
RH_PER_YEAR = 2
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


CAL_ICON = ('<rect x="4" y="5.5" width="16" height="15" rx="2.5"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>'
            '<path d="M8 14h2M12 14h2M16 14h0M8 17.5h2M12 17.5h2"/>')


def register(B):
    if not FILE.exists():
        return
    B.ICONS.setdefault("calendar", CAL_ICON)
    # Second on the home page's tools list: December and January are when people plan the year's trips.
    B.TOOLS.insert(1, (PATH, "Long weekends 2027", "Free planner", "Long weekends 2027: plan your leave",
                       "Every 2027 long weekend from the official holiday list, and the leave days that turn a holiday into 4, 5 or 9 days off.",
                       "Plan my leave", "calendar", "travel-gear", "plane-window"))


def load():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    for key in ("om", "om_date", "checked", "sources", "gazetted", "restricted"):
        if not data.get(key):
            sys.exit("Error: data/holidays_2027.json needs %s" % key)
    for s in data["sources"]:
        if not s.get("url", "").startswith("https://dopt.gov.in/"):
            sys.exit("Error: data/holidays_2027.json sources must be DoPT's own site, not %s" % s.get("url"))
    for kind in ("gazetted", "restricted"):
        for h in data[kind]:
            d = date.fromisoformat(h["date"])
            if d.year != data["year"]:
                sys.exit("Error: %s holiday %s is not in %d" % (kind, h["name"], data["year"]))
            if d.strftime("%A") != h["day"]:
                sys.exit("Error: %s holiday %s on %s is a %s, not a %s" % (kind, h["name"], h["date"], d.strftime("%A"), h["day"]))
    if re.search(r"(₹|\bRs\.?\s?|\bINR\s?)\d|\bratings?\b|\bprice", json.dumps(data, ensure_ascii=False), re.I):
        sys.exit("Error: data/holidays_2027.json mentions a price or rating.")
    return data


def names_on(rows):
    out = {}
    for h in rows:
        out.setdefault(date.fromisoformat(h["date"]), []).append(h["name"])
    return out


def need(leave):
    """Days a plan must give for its leave: 0 leave -> 3 days, 1 -> 4, 2 -> 5, 3 -> 7."""
    return max(3, leave + 3, 2 * leave + 1)


def plans(data):
    """Every long weekend in the year, best first within each month. Each plan is a dict:
    start, end, days, leave (dates to take off), rh (those of them that are restricted holidays, at most 2 used),
    holidays (gazetted names in the span), ok_plain / ok_rh (worth showing without / with restricted holidays)."""
    year = data["year"]
    gaz, rh = names_on(data["gazetted"]), names_on(data["restricted"])
    first, last = date(year, 1, 1), date(year, 12, 31)

    def off(d):
        return d.weekday() >= 5 or d in gaz

    found = []
    d = first
    while d <= last:
        for length in range(3, 12):
            end = d + timedelta(days=length - 1)
            if end > last:
                break
            if off(d - timedelta(days=1)) or off(end + timedelta(days=1)):
                continue  # not the whole run: a free day off sits just outside
            span = [d + timedelta(days=i) for i in range(length)]
            leave = [x for x in span if not off(x)]
            gaz_weekday = [x for x in span if x in gaz and x.weekday() < 5]
            rh_used = [x for x in leave if x in rh][:RH_PER_YEAR]
            if not gaz_weekday and not rh_used:
                continue  # a plain weekend with leave around it
            found.append({"start": d, "end": end, "days": length, "leave": leave, "rh": rh_used,
                          "gaz_weekday": bool(gaz_weekday),
                          "holidays": [(x, n) for x in span if x in gaz for n in gaz[x]],
                          "rh_names": [(x, n) for x in span if x in rh for n in rh[x]]})
        d += timedelta(days=1)

    def overlap(a, b):
        return a["start"] <= b["end"] and b["start"] <= a["end"]

    # Two views: leave only, and leave with restricted holidays swapped in. In each, a plan must give enough days for
    # its leave (need()), and is dropped when an overlapping plan with no more leave is at most that many days shorter
    # (so each extra day of leave must add at least two days off).
    views = (("ok_plain", lambda p: len(p["leave"]), lambda p: p["gaz_weekday"]),
             ("ok_rh", lambda p: len(p["leave"]) - len(p["rh"]), lambda p: True))
    for mode, cost, eligible in views:
        cand = [p for p in found if eligible(p) and cost(p) <= MAX_LEAVE and p["days"] >= need(cost(p))]
        for p in found:
            p[mode] = False
        for p in cand:
            p[mode] = not any(q is not p and overlap(p, q) and cost(q) <= cost(p) and p["days"] - q["days"] <= cost(p) - cost(q)
                              and (cost(q), -q["days"]) != (cost(p), -p["days"]) for q in cand)
    out = [p for p in found if p["ok_plain"] or p["ok_rh"]]
    out.sort(key=lambda p: (p["start"], len(p["leave"])))
    return out


def day(d, weekday=True):
    return ("%s %d %s" % (d.strftime("%a"), d.day, d.strftime("%b"))) if weekday else "%d %s" % (d.day, d.strftime("%b"))


def span_text(p):
    return "%s to %s" % (day(p["start"]), day(p["end"]))



def cost(p, rh):
    return len(p["leave"]) - (len(p["rh"]) if rh else 0)


def leave_text(p):
    if not p["leave"]:
        return "None"
    by_month = {}
    for x in p["leave"]:
        by_month.setdefault(x.month, []).append(x)
    parts = []
    for m, xs in by_month.items():
        parts.append(", ".join("%s %d" % (x.strftime("%a"), x.day) for x in xs) + " " + xs[0].strftime("%b"))
    n = len(p["leave"])
    return "%d day%s: %s" % (n, "" if n == 1 else "s", "; ".join(parts))


def ics_text(cfg, data, items):
    """A plain iCalendar file: every gazetted holiday, and the long weekends that need at most 1 day of leave."""
    host = (cfg.get("base_url") or "https://carrypick.github.io/").split("//")[-1].strip("/")
    stamp = data["checked"].replace("-", "") + "T000000Z"

    def fold(line):
        out, raw = [], line.encode("utf-8")
        while len(raw) > 74:
            cut = 74
            while (raw[cut] & 0xC0) == 0x80:
                cut -= 1
            out.append(raw[:cut].decode("utf-8"))
            raw = b" " + raw[cut:]
        out.append(raw.decode("utf-8"))
        return "\r\n".join(out)

    def esc(t):
        return t.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//CarryPick//Long weekends %d//EN" % data["year"], "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:Long weekends %d - India central govt Delhi" % data["year"]]
    note = "From DoPT O.M. %s dated %s (central government offices in Delhi / New Delhi). States and private companies follow their own lists." % (
        data["om"], date.fromisoformat(data["om_date"]).strftime("%d %B %Y").lstrip("0"))
    for uid, start, end, summary, desc in items:
        lines += ["BEGIN:VEVENT", "UID:%s@%s" % (uid, host), "DTSTAMP:" + stamp,
                  "DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + (end + timedelta(days=1)).strftime("%Y%m%d"),
                  "SUMMARY:" + esc(summary), "DESCRIPTION:" + esc(desc + " " + note), "TRANSP:TRANSPARENT", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in lines) + "\r\n"


def build(B, cfg, deals_by_asin, pages, lastmod):
    if not FILE.exists():
        return
    data = load()
    for a in data.get("picks", []):
        if a not in deals_by_asin:
            sys.exit("Error: data/holidays_2027.json picks %s, which is not in data/deals.json" % a)
    year, checked = data["year"], data["checked"]
    om_date = date.fromisoformat(data["om_date"])
    om_line = "DoPT O.M. %s dated %d %s" % (data["om"], om_date.day, om_date.strftime("%B %Y"))
    src = data["sources"][0]
    url = B.abs_url(cfg, PATH)
    all_plans = plans(data)
    plain = [p for p in all_plans if p["ok_plain"]]
    free = [p for p in plain if not p["leave"]]
    one = [p for p in plain if len(p["leave"]) == 1]
    gaz = [(date.fromisoformat(h["date"]), h) for h in data["gazetted"]]
    rhs = [(date.fromisoformat(h["date"]), h) for h in data["restricted"]]

    def built(href):
        return (B.DOCS / href.split("#")[0]).exists()

    # Trip ideas: the month's guides that are built, turned a little for each plan so the rows don't all repeat.
    seen_in_month = {}

    def trips_for(p):
        m = p["start"].month
        rows = [t for t in data.get("trips_by_month", {}).get(str(m), []) if built(t[0])]
        has_rday = any(x.month == 1 and x.day == 26 for x, _ in p["holidays"])
        if has_rday:
            return ([t for t in rows if t[0] == REPUBLIC] + [t for t in rows if t[0] != REPUBLIC])[:3]
        rows = [t for t in rows if t[0] != REPUBLIC]
        k = seen_in_month.get(m, 0)
        seen_in_month[m] = k + 1
        if rows:
            k = (k * 2) % len(rows)
            rows = rows[k:] + rows[:k]
        return rows[:3]

    def trip_html(rows):
        if not rows:
            return '<span class="muted">Monsoon: pick a short trip near home</span>'
        return "<br>".join(f'<a href="../{e(h)}">{e(n)}</a> <span class="muted small">({e(why)})</span>' for h, n, why in rows)

    moon = {h["name"] for h in data["gazetted"] if h.get("moon")}
    moon_mark = ' <span class="muted small">(moon-based, may move)</span>'
    table_rows = []
    for p in all_plans:
        hol = [f"{e(n)} ({day(x)}){moon_mark if n in moon else ''}" for x, n in p["holidays"] if x.weekday() < 5]
        hol += [f"{e(n)} ({day(x)}, already a {x.strftime('%A')})" for x, n in p["holidays"] if x.weekday() >= 5]
        rh_bits = [f'<span class="muted">Restricted holiday: {e(n)} ({day(x)})</span>' for x, n in p["rh_names"] if x in p["rh"]]
        lv, lv_rh = len(p["leave"]), cost(p, True)
        rh_cell = ("%d day%s" % (lv_rh, "" if lv_rh == 1 else "s") if lv_rh else "None") if p["rh"] else "–"
        days_cell = f'<strong>{p["days"]} days</strong>'
        badge = ' <span class="lw-free">No leave</span>' if not p["leave"] else ""
        na = "" if p["rh"] else ' class="lw-na"'
        table_rows.append(
            f'<tr data-month="{p["start"].month}" data-leave="{lv}" data-leave-rh="{lv_rh}" data-plain="{int(p["ok_plain"])}" data-rh="{int(p["ok_rh"])}">'
            f'<td class="lw-m">{MONTHS[p["start"].month - 1]}</td><td>{span_text(p)}{badge}</td><td data-label="Days off">{days_cell}</td>'
            f'<td data-label="Leave">{e(leave_text(p))}</td><td data-label="With restricted holidays"{na}>{rh_cell}</td>'
            f'<td data-label="Holidays">{"<br>".join(hol + rh_bits)}</td><td data-label="Trip ideas">{trip_html(trips_for(p))}</td></tr>')

    months_with = sorted({p["start"].month for p in all_plans})
    month_opts = '<option value="all">All months</option>' + "".join(f'<option value="{m}">{MONTHS[m - 1]}</option>' for m in months_with)

    # Gazetted holidays, one row each, with what it does for a long weekend.
    def best_for(x):
        mine = [p for p in plain if p["start"] <= x <= p["end"]]
        mine.sort(key=lambda p: (len(p["leave"]), -p["days"]))
        return mine

    gaz_rows = []
    for x, h in gaz:
        if x.weekday() >= 5:
            what = "Falls on a %s, so no extra day off." % x.strftime("%A")
        else:
            mine = best_for(x)
            if not mine:
                what = "A midweek holiday: no short bridge."
            elif not mine[0]["leave"]:
                what = "Long weekend with no leave: %s (%d days)." % (span_text(mine[0]), mine[0]["days"])
            else:
                b = mine[0]
                what = "Take %s off for %d days: %s." % (", ".join(day(y) for y in b["leave"]), b["days"], span_text(b))
        moon = ' <span class="muted small">(moon-based; DoPT may move it)</span>' if h.get("moon") else ""
        gaz_rows.append(f"<tr><td>{day(x, False)}</td><td>{h['day']}</td><td>{e(h['name'])}{moon}</td><td>{e(what)}</td></tr>")

    # Restricted holidays that help: the ones a restricted-holiday plan uses.
    rh_help = {}
    for p in all_plans:
        if p["ok_rh"]:
            for x in p["rh"]:
                rh_help.setdefault(x, []).append(p)
    rh_rows = []
    for x, h in rhs:
        if x not in rh_help:
            continue
        b = min(rh_help[x], key=lambda p: (cost(p, True), -p["days"]))
        extra = cost(b, True)
        how = "%s, %d days" % (span_text(b), b["days"]) + (" with no other leave" if not extra else ", plus %d day%s of leave" % (extra, "" if extra == 1 else "s"))
        if len(b["rh"]) > 1:
            how += " (uses both your restricted holidays)"
        rh_rows.append(f"<tr><td>{day(x, False)}</td><td>{h['day']}</td><td>{e(h['name'])}</td><td>{e(how)}</td></tr>")

    # Calendar file
    chosen = [p for p in plain if len(p["leave"]) <= 1]
    chosen = [p for p in chosen if not any(q is not p and q["start"] <= p["start"] and p["end"] <= q["end"] for q in chosen)]
    items = [("holiday-%s-%d" % (x.strftime("%Y%m%d"), i), x, x, "Holiday: %s" % h["name"], "Gazetted holiday.")
             for i, (x, h) in enumerate(gaz)]
    for p in chosen:
        summ = "Long weekend: %d days" % p["days"] + (" (take %s off)" % ", ".join(day(y) for y in p["leave"]) if p["leave"] else " (no leave)")
        items.append(("lw-%s-%s" % (p["start"].strftime("%Y%m%d"), p["end"].strftime("%Y%m%d")), p["start"], p["end"], summ,
                      "Holidays: %s." % ", ".join(n for _, n in p["holidays"])))
    items.sort(key=lambda t: (t[1], t[0]))
    (B.DOCS / ICS).parent.mkdir(parents=True, exist_ok=True)
    (B.DOCS / ICS).write_bytes(ics_text(cfg, data, items).encode("utf-8"))

    # Numbers for the answers and FAQ, all from the plans above.
    def short(p):
        return "%s (%s)" % (" and ".join(dict.fromkeys(n.split(" (")[0] for x, n in p["holidays"] if x.weekday() < 5)),
                            "%d–%d %s" % (p["start"].day, p["end"].day, p["end"].strftime("%b")) if p["start"].month == p["end"].month
                            else "%s–%s" % (day(p["start"], False), day(p["end"], False)))
    longest = max(plain, key=lambda p: (p["days"], -len(p["leave"])))
    long_list = [p for p in plain if p["days"] == longest["days"]]
    best_one = max(one, key=lambda p: p["days"])
    rday = next((p for p in plain if any(x.month == 1 and x.day == 26 for x, _ in p["holidays"]) and len(p["leave"]) == 1), None)
    jan_rh = [p for p in all_plans if p["ok_rh"] and p["start"].month == 1 and p["rh"] and cost(p, True) == 0]
    diwali = next(x for x, h in gaz if h["name"].startswith("Diwali"))
    weekend_hols = [(x, h) for x, h in gaz if x.weekday() >= 5]
    n_gaz = len(data["gazetted"])

    free_txt = ", ".join(short(p) for p in free)
    one_txt = ", ".join("%s: take %s off for %d days" % (short(p), day(p["leave"][0]), p["days"]) for p in one)
    faq = [
        ("How many long weekends are there in %d?" % year,
         "With no leave at all, central government offices in Delhi get %d long weekends of 3 days in %d: %s. Take 1 day of leave and you get %d more: %s." % (
             len(free), year, free_txt, len(one), one_txt)),
        ("Is there a long weekend in January %d?" % year,
         ("Yes, with 1 day of leave. Republic Day, 26 January %d, is a Tuesday. Take Monday 25 January off and you get %s to %s, 4 days. " % (year, day(rday["start"]), day(rday["end"])) if rday else "")
         + ("If you can use your restricted holidays, %s." % "; ".join(
             "%s gives %s (%d days)" % (" and ".join(n for x, n in p["rh_names"] if x in p["rh"]), span_text(p), p["days"]) for p in jan_rh) if jan_rh else "")),
        ("Which is the longest holiday break in %d?" % year,
         "Take 3 days of leave and you get %d days off: %s. With just 1 day of leave, %s gives %d days (%s)." % (
             longest["days"], " or ".join("%s (take %s off)" % (short(p), ", ".join(day(y) for y in p["leave"])) for p in long_list),
             short(best_one).split(" (")[0], best_one["days"], span_text(best_one))),
        ("What is the %d holiday list for central government offices?" % year,
         "%s lists %d gazetted holidays for central government offices in Delhi / New Delhi in %d, and %d restricted holidays, of which each employee may take 2. The full list is in the table above, with the day of the week." % (
             om_line, n_gaz, year, len(data["restricted"]))),
        ("Which %d holidays fall on a weekend?" % year,
         "%s. No extra day off is given for these (para 3.2 of the O.M.)." % "; ".join("%s on %s %s" % (h["name"].split(" (")[0], h["day"], day(x, False)) for x, h in weekend_hols)),
        ("When is Diwali %d?" % year,
         "Diwali (Deepavali) is on %s, %d %s %d, in the central government list, so %s to %s is a 3-day weekend with no leave. Naraka Chaturdasi, the day before, is a restricted holiday." % (
             diwali.strftime("%A"), diwali.day, diwali.strftime("%B"), year, day(diwali), day(diwali + timedelta(days=2)))),
        ("Do states, banks and private companies follow this list?",
         "No. This list is for central government administrative offices in Delhi / New Delhi. Central offices in other cities pick 3 of their holidays locally, states publish their own lists, banks follow their own rules, and private companies set their own holidays. Check your office's list before you book."),
        ("Can moon-based holiday dates change?",
         "Yes. For Id-ul-Fitr, Id-ul-Zuha, Muharram and Id-e-Milad, DoPT may change the date after the moon is sighted, sometimes at short notice. Keep those trips flexible."),
        ("Can I add these long weekends to my calendar?",
         "Yes. Download the calendar file on this page and open it with Google Calendar, Outlook or your phone's calendar. It has every gazetted holiday and the long weekends that need 1 day of leave or none."),
    ]
    faq_html, faq_schema = B.faq_block(faq)

    picks = [deals_by_asin[a] for a in data.get("picks", [])]
    picks_html = (f"""<h2 id="pack">Pack for a long weekend</h2>
<p>Three or four days is cabin-bag territory: a 55–56 cm trolley or a weekender, with packing cubes to keep it tidy. Check your <a href="../baggage/index.html">airline's cabin limits</a> first.</p>
{B.grid(cfg, picks, "../")}""" if picks else "")

    title = "Long weekends %d in India: holiday list and leave planner" % year
    seo = "Long weekends %d India: holiday list and leave planner" % year
    desc = ("All long weekends in %d from the official central government holiday list: %d with no leave, %d more with 1 day off, "
            "and up to %d days with 3. Filter by month and leave, and add them to your calendar." % (year, len(free), len(one), longest["days"]))
    inner = f"""<nav class="crumbs"><a href="../index.html">Home</a><span>/</span>Long weekends {year}</nav>
      <h1>{e(title)}</h1>
      <p class="muted small">A free planner from the official list. Checked {B.fmt_date(checked)}</p>"""
    head = B.page_head("travel-gear", f'<div class="media media-tile tint-travel-gear">{B.icon("calendar", "icon media-icon")}</div>', inner, "../")
    rday_link = (f' For Republic Day itself, see our <a href="../{REPUBLIC}">Republic Day long weekend trip ideas</a>.' if built(REPUBLIC) else "")
    hub = "trips/where-to-go-in-december-january.html"
    hub_link = f' For winter trips, see <a href="../{hub}">where to go in December and January</a>.' if built(hub) else ""
    feb = "trips/where-to-go-in-february.html"
    if built(feb):
        hub_link += f' For February, see <a href="../{feb}">where to go in February</a>.'
    newyear = "trips/new-year-trips-2027.html"
    if built(newyear):
        rday_link += f' For the New Year weekend (1 January 2027 is a Friday), see <a href="../{newyear}">where to go for New Year 2027</a>.'
        hub_link += f' Going away for New Year? See our <a href="../{newyear}">New Year trips 2027</a>.'
    weekend = [(c, "trips/weekend-getaways-from-%s.html" % c.lower()) for c in ("Delhi", "Mumbai", "Bangalore")]
    weekend = [(c, h) for c, h in weekend if (B.TRIPS_DIR / h.replace("trips/", "").replace(".html", ".md")).exists()]
    if weekend:
        hub_link += " Short trips by road, train or flight: weekend getaways from %s." % ", ".join(
            f'<a href="../{h}">{c}</a>' for c, h in weekend)
    body = f"""{head}
<div class="wrap"><article class="guide">
<div class="answer"><h2>Quick answer</h2><ul>
<li><strong>{len(free)} long weekends need no leave</strong> in {year}: {e(free_txt)}.</li>
<li><strong>Best deal:</strong> {e(short(best_one).split(" (")[0])}. Take {e(", ".join(day(y) for y in best_one["leave"]))} off and get {best_one["days"]} days ({e(span_text(best_one))}).</li>
<li><strong>Longest break:</strong> {longest["days"]} days for 3 days of leave, around {e(" or ".join(short(p) for p in long_list))}.</li>
</ul></div>
<p class="pm-notes"><strong>Whose holidays?</strong> These dates are from {e(om_line)}, the Government of India's list for central government offices in Delhi / New Delhi. States, banks and private companies follow their own holiday lists, so check yours. Weekends here are Saturday and Sunday.</p>
<p class="pm-nojs" id="lw-nojs">Turn on JavaScript to filter by month and leave days, or read the full table below.</p>
<form class="checker lw" id="lw" onsubmit="return false" hidden>
<div class="checker-fields"><label>Month<select id="lw-month">{month_opts}</select></label>
<label>Leave days I can take<select id="lw-leave"><option value="0">0 (no leave)</option><option value="1">Up to 1</option><option value="2">Up to 2</option><option value="3" selected>Up to 3</option></select></label></div>
<label class="lw-check"><input type="checkbox" id="lw-rh"> Use my 2 restricted holidays (central government staff)</label>
<p class="hint" id="lw-count" aria-live="polite"></p>
</form>
<h2 id="table">Long weekends {year}, month by month</h2>
<p>Each row is one way to get a long break. "Leave" is the working days you take off. Where a leave day is also a restricted holiday, the next column shows the leave left if you use one of your 2 restricted holidays for it (you get only 2 in the whole year).{rday_link}</p>
<div class="table-wrap"><table class="compare snug lw-table" id="lw-table"><thead><tr><th>Month</th><th>Dates</th><th>Days off</th><th>Leave</th><th>Leave with restricted holidays</th><th>Holidays</th><th>Trip ideas</th></tr></thead>
<tbody>{"".join(table_rows)}</tbody></table></div>
<p id="lw-none" class="muted" hidden>No long weekend matches. Try more leave days, another month, or tick restricted holidays.</p>
<p class="pm-actions"><a class="btn" href="long-weekends-{year}.ics" download>Add to my calendar (.ics)</a></p>
<p class="small muted">The calendar file has the {n_gaz} gazetted holidays and the long weekends that need 1 day of leave or none. It works with Google Calendar, Outlook and phone calendars.</p>
<h2 id="gazetted">{year} gazetted holidays for central government offices (Delhi / New Delhi)</h2>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Date</th><th>Day</th><th>Holiday</th><th>Long weekend?</th></tr></thead>
<tbody>{"".join(gaz_rows)}</tbody></table></div>
<h2 id="restricted">Restricted holidays that make a long weekend</h2>
<p>Central government staff in Delhi / New Delhi may pick any 2 of the {len(data["restricted"])} restricted holidays in {year}. These are the ones that sit next to a weekend or a holiday:</p>
<div class="table-wrap"><table class="compare snug"><thead><tr><th>Date</th><th>Day</th><th>Restricted holiday</th><th>Long weekend it makes</th></tr></thead>
<tbody>{"".join(rh_rows)}</tbody></table></div>
<h2 id="tips">Tips for booking a long weekend</h2>
<ul>
<li><strong>Book trains early.</strong> Reservations open about 60 days before you travel, and long weekends sell out first.</li>
<li><strong>Keep moon-based trips flexible.</strong> Id-ul-Fitr, Id-ul-Zuha, Muharram and Id-e-Milad can move by a day after the moon is sighted.</li>
<li><strong>Pick one place.</strong> Three or four days is enough for one city or hill town; moving between places eats a day.{hub_link}</li>
</ul>
{picks_html}
<p class="checked">Holiday dates: <a href="{e(src["url"])}" target="_blank" rel="noopener">{e(om_line)}</a> (Annexure I: gazetted, Annexure II: restricted), read on {B.fmt_date(checked)}. Days of the week checked against the calendar.</p>
{faq_html}
{B.tool_pills("../", PATH)}
</article></div>
<script src="../assets/long-weekends.js" defer></script>
{B.telegram_band(cfg, "../")}"""
    crumbs = B.crumbs_schema(cfg, [("Home", ""), ("Long weekends %d" % year, PATH)])
    app = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Long weekends %d planner" % year, "url": url,
           "applicationCategory": "TravelApplication", "operatingSystem": "Any", "description": desc}
    pages.append(B.write(PATH, B.page(cfg, seo, desc, body, 1, PATH,
                                      [B.tool_article(cfg, seo, desc, PATH, "2026-11-21", checked), crumbs, faq_schema, app],
                                      og_type="article", photo="plane-window")))
    lastmod[PATH] = checked
    return {"plans": all_plans, "free": free, "one": one}


if __name__ == "__main__":
    for p in plans(load()):
        print(span_text(p), p["days"], leave_text(p), "plain" if p["ok_plain"] else "", "rh" if p["ok_rh"] else "")
