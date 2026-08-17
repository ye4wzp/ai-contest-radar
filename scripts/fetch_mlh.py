"""Scrape mlh.io season events (schema.org microdata) into data/sources/mlh.json."""
import re
import sys
from datetime import date

from common import fetch, write_source

SEASONS = [date.today().year, date.today().year + 1]


def meta(card: str, prop: str) -> str | None:
    m = re.search(r'itemProp="%s" content="([^"]*)"' % prop, card)
    return m.group(1) if m else None


def main():
    today, comps, seen = date.today().isoformat(), [], set()
    for season in SEASONS:
        try:
            scan(f"https://mlh.io/seasons/{season}/events", today, comps, seen)
        except Exception as e:
            print(f"season {season}: {e}", file=sys.stderr)
    write_source("mlh", comps)


def scan(url: str, today: str, comps: list, seen: set):
    html = fetch(url)
    for m in re.finditer(r'itemType="https://schema.org/Event"', html):
        card = html[m.start() : html.find("</a>", m.start())]
        url, start, end = meta(card, "url"), meta(card, "startDate"), meta(card, "endDate")
        name = re.search(r"<h4[^>]*>([^<]+)<", card)
        if not (url and start and end and name) or end[:10] < today:
            continue
        online = "OnlineEventAttendanceMode" in card
        loc = re.search(r'itemProp="addressLocality" content="([^"]*)"', card)
        country = re.search(r'itemProp="addressCountry" content="([^"]*)"', card)
        cid = "mlh-" + re.sub(r"\W+", "-", url.split("//")[-1]).strip("-")
        if cid in seen:
            continue
        seen.add(cid)
        comps.append({
            "id": cid,
            "name": name.group(1).strip(),
            "organizer": "MLH 认证",
            "official_url": url,
            "type": "黑客松",
            "tags": ["MLH", "国际"],
            "city": "线上" if online else ", ".join(
                x.group(1).strip(" ,") for x in (loc, country) if x and x.group(1).strip(" ,")),
            "prize": None,
            "start": start[:10],
            "deadline": start[:10],
            "end": end[:10],
            "description": "MLH（Major League Hacking）官方认证黑客松，开赛前均可报名。",
            "sources": [{"name": "MLH", "url": url}],
        })


if __name__ == "__main__":
    main()
