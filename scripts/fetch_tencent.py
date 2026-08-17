"""Scrape tch.cloud.tencent.com (腾讯云黑客松官网) into data/sources/tencent.json."""
import json
import re

from common import fetch, iso_date, rsc_payload, write_source

BASE = "https://tch.cloud.tencent.com"


def parse_object(payload: str, start: int) -> dict | None:
    depth = 0
    for i in range(start, len(payload)):
        if payload[i] == "{":
            depth += 1
        elif payload[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(payload[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def normalize(d: dict) -> dict:
    return {
        "id": f"tch-{d['id']}",
        "name": d["name"].strip(),
        "organizer": d.get("sponsor") or "腾讯云",
        "official_url": d.get("detailUrl") or d.get("signUrl") or BASE,
        "type": "黑客松",
        "tags": ["腾讯云", "官方赛事"],
        "city": "线上",
        "prize": d.get("prize") or None,
        "start": iso_date(d.get("signStartTime")),
        "deadline": iso_date(d.get("signEndTime")),
        "end": iso_date(d.get("endTime")),
        "description": (d.get("introduce") or "").replace("\n", " ")[:300],
        "sources": [{"name": "腾讯云黑客松官网", "url": BASE}],
    }


def main():
    payload = rsc_payload(fetch(BASE))
    seen, comps = set(), []
    for m in re.finditer(r'\{"id":\d+,"status"', payload):
        obj = parse_object(payload, m.start())
        if obj and "signEndTime" in obj and obj.get("name") and obj["id"] not in seen:
            seen.add(obj["id"])
            comps.append(normalize(obj))
    write_source("tencent", comps)


if __name__ == "__main__":
    main()
