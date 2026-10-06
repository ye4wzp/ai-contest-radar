"""Fetch 阿里云天池 competitions (public JSON API) into data/sources/tianchi.json.

列表按状态排序，报名中/进行中的在前，翻到整页都已结束为止。系列赛（isSeries）本身不收，
展开其 trackList 里的子赛道；raceListStatus：0 报名中、1 即将开始、2 进行中（报名已截止）、4 已结束。
"""
import json
from datetime import date

from common import fetch, write_source

API = "https://tianchi.aliyun.com/v3/proxy/competition/api/race/page?pageNum={page}&pageSize=50"
URL = "https://tianchi.aliyun.com/competition/entrance/{id}"
SIGNUP = {0: "open", 1: "upcoming", 2: "closed", 4: "ended"}


def normalize(r: dict) -> dict:
    bonus = r.get("bonus") or 0
    tags = [t["tagNameCn"].replace("‌", "").strip() for t in r.get("tagsList") or []]
    return {
        "id": f"tianchi-{r['raceId']}",
        "name": r["name"].strip(),
        "organizer": "阿里云天池",
        "official_url": URL.format(id=r["raceId"]),
        "type": "黑客松" if "黑客松" in r["name"] else "数据算法赛",
        "tags": ["天池"] + tags,
        "city": None,
        "prize": f"{'$' if r.get('currency') == 1 else '¥'}{bonus:,}" if bonus else None,
        "start": (r.get("signupStartTime") or r.get("raceStartTime") or "")[:10] or None,
        "deadline": (r.get("signupEndTime") or "")[:10] or None,
        "end": (r.get("raceEndTime") or "")[:10] or None,
        "signup": SIGNUP.get(r.get("raceListStatus")),
        "description": (r.get("introduction") or r.get("highlight") or "").strip()[:300],
        "sources": [{"name": "天池", "url": "https://tianchi.aliyun.com/competition/activeList"}],
    }


def main():
    races, seen = [], set()
    for page in range(1, 20):
        items = json.loads(fetch(API.format(page=page)))["data"]["list"]
        flat = [t for r in items for t in ((r.get("trackList") or []) if r.get("isSeries") else [r])]
        live = [r for r in flat if r.get("raceListStatus") != 4]
        for r in live:
            if r["raceId"] not in seen:
                seen.add(r["raceId"])
                races.append(r)
        if not items or not live:
            break
    today = date.today().isoformat()
    comps = [normalize(r) for r in races]
    write_source("tianchi", [c for c in comps if (c["end"] or c["deadline"] or today) >= today])


if __name__ == "__main__":
    main()
